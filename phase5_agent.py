"""
Phase 5: Agentic Control Loop + P2C Load Balancer

Implements:
  - P2CLoadBalancer: Power-of-2-Choices probabilistic load balancer
  - GreenAgent: Autonomous agent that monitors carbon intensity and
                switches scheduling modes (AGGRESSIVE / CONSERVATIVE / SHED)
  - AgenticDPScheduler: Extends DPScheduler with the agentic control loop
"""

import copy
import random
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

from phase1_models import Task, Server, make_cluster
from phase2_energy_model import (
    SLOTS_PER_DAY, energy_at_slot, carbon_intensity,
    build_energy_profile, slot_to_time
)
from phase3_tasks import ScheduleResult, generate_tasks
from phase4_dp_scheduler import (
    DPScheduler, MAX_ENERGY_BUDGET,
    build_dp_table, traceback, schedule_deferred, task_value
)


# ── P2C Load Balancer ─────────────────────────────────────────────────────────

class P2CLoadBalancer:
    """
    Power-of-2-Choices (P2C) load balancer.

    On each routing decision:
      1. Pick 2 servers at random.
      2. Route to the one with fewer active connections.

    This gives O(log log n) max load vs O(log n / log log n) for pure
    random, with only 2 samples — a classic distributed systems result.
    """

    def __init__(self, servers: List[Server], rng_seed: int = 0):
        self.servers = servers
        self._rng    = random.Random(rng_seed)

    def pick(self) -> Server:
        """Return the less-loaded of two randomly sampled servers."""
        if len(self.servers) < 2:
            return self.servers[0]
        a, b = self._rng.sample(self.servers, 2)
        return a if a.active_connections <= b.active_connections else b

    def stats(self) -> Dict:
        return {
            s.name: {
                "active":      s.active_connections,
                "utilisation": round(s.utilisation(), 3),
                "avg_latency": round(s.avg_latency(), 2),
                "total_req":   s.total_requests,
            }
            for s in self.servers
        }


# ── Green Agent ───────────────────────────────────────────────────────────────

@dataclass
class AgentState:
    slot:         int   = 0
    mode:         str   = "CONSERVATIVE"   # AGGRESSIVE | CONSERVATIVE | SHED
    solar_energy: float = 0.0
    carbon_now:   float = 0.0
    deferred_len: int   = 0
    scheduled:    int   = 0
    carbon_total: float = 0.0
    history:      List  = field(default_factory=list)


class GreenAgent:
    """
    Autonomous monitoring agent that decides the scheduling mode each slot.

    Modes:
      AGGRESSIVE   – run DP with full budget; schedule as many tasks as possible
                     in the solar window. Used when solar > 60 units.
      CONSERVATIVE – run DP with reduced budget (50% of max). Used when
                     solar is moderate (20-60 units).
      SHED         – defer all non-critical tasks; only force-schedule critical
                     tasks. Used when solar < 20 units (night / heavy cloud).

    The agent also emits log events for observability.
    """

    MODE_AGGRESSIVE   = "AGGRESSIVE"
    MODE_CONSERVATIVE = "CONSERVATIVE"
    MODE_SHED         = "SHED"

    AGGRESSIVE_THRESHOLD   = 60.0
    CONSERVATIVE_THRESHOLD = 20.0

    def __init__(self, budget: int = MAX_ENERGY_BUDGET, cloudy: bool = False):
        self.budget = budget
        self.cloudy = cloudy
        self.state  = AgentState()
        self._log: List[Dict] = []

    def observe(self, slot: int, deferred_len: int, scheduled: int, carbon_total: float) -> AgentState:
        """Update agent state from environment observations."""
        solar  = energy_at_slot(slot, self.cloudy)
        carbon = carbon_intensity(slot, self.cloudy)

        self.state.slot         = slot
        self.state.solar_energy = solar
        self.state.carbon_now   = carbon
        self.state.deferred_len = deferred_len
        self.state.scheduled    = scheduled
        self.state.carbon_total = carbon_total

        # Decide mode
        if solar >= self.AGGRESSIVE_THRESHOLD:
            new_mode = self.MODE_AGGRESSIVE
        elif solar >= self.CONSERVATIVE_THRESHOLD:
            new_mode = self.MODE_CONSERVATIVE
        else:
            new_mode = self.MODE_SHED

        old_mode = self.state.mode
        self.state.mode = new_mode

        # Log mode transitions
        if new_mode != old_mode:
            self._emit_log("MODE_CHANGE", slot,
                           f"{old_mode} → {new_mode} | solar={solar:.1f} | ci={carbon:.1f}")

        self.state.history.append({
            "slot":   slot,
            "mode":   new_mode,
            "solar":  solar,
            "carbon": carbon,
        })

        return self.state

    def effective_budget(self) -> int:
        """Return the energy budget for the current mode."""
        if self.state.mode == self.MODE_AGGRESSIVE:
            return self.budget
        elif self.state.mode == self.MODE_CONSERVATIVE:
            return max(10, self.budget // 2)
        else:
            return 0   # SHED: no new tasks

    def should_run_dp(self) -> bool:
        return self.state.mode != self.MODE_SHED

    def _emit_log(self, event: str, slot: int, message: str):
        entry = {
            "event":   event,
            "slot":    slot,
            "time":    slot_to_time(slot),
            "message": message,
        }
        self._log.append(entry)

    def get_log(self) -> List[Dict]:
        return list(self._log)

    def summary(self) -> Dict:
        modes = [h["mode"] for h in self.state.history]
        return {
            "aggressive_slots":   modes.count(self.MODE_AGGRESSIVE),
            "conservative_slots": modes.count(self.MODE_CONSERVATIVE),
            "shed_slots":         modes.count(self.MODE_SHED),
            "mode_changes":       len([e for e in self._log if e["event"] == "MODE_CHANGE"]),
        }


# ── Agentic DP Scheduler ──────────────────────────────────────────────────────

class AgenticDPScheduler:
    """
    Full agentic scheduler combining:
      - GreenAgent for dynamic mode switching
      - P2CLoadBalancer for intelligent server selection
      - DPScheduler knapsack logic for solar-window task selection

    This is the most advanced scheduler in the system.
    """

    name = "AgenticDP"

    def __init__(
        self,
        solar_threshold: float = 20.0,
        budget: int = MAX_ENERGY_BUDGET,
        cloudy: bool = False,
        rng_seed: int = 42,
    ):
        self.solar_threshold = solar_threshold
        self.budget          = budget
        self.cloudy          = cloudy
        self.rng_seed        = rng_seed
        self.agent           = GreenAgent(budget=budget, cloudy=cloudy)
        self._balancer: Optional[P2CLoadBalancer] = None

    def run(self, tasks: List[Task], servers: List[Server]) -> ScheduleResult:
        servers = [copy.deepcopy(s) for s in servers]
        for s in servers:
            s.reset()

        # Reset agent state so repeated .run() calls don't accumulate history
        self.agent = GreenAgent(budget=self.budget, cloudy=self.cloudy)
        self._balancer = P2CLoadBalancer(servers, rng_seed=self.rng_seed)

        result = ScheduleResult(
            scheduler_name=self.name,
            tasks=tasks,
            servers=servers,
            cloudy=self.cloudy,
        )

        arrival_index: Dict[int, List[Task]] = defaultdict(list)
        for task in tasks:
            arrival_index[task.arrival_slot].append(task)

        deferred:      List[Task] = []
        scheduled_ids: set        = set()
        latencies:     List[float] = []
        carbon_total   = 0.0

        for slot in range(SLOTS_PER_DAY):
            # Tick servers
            for s in servers:
                s.tick(slot)

            # Collect newly arrived tasks
            for task in arrival_index.get(slot, []):
                deferred.append(task)

            # Agent observes and decides mode
            agent_state = self.agent.observe(
                slot, len(deferred), result.tasks_scheduled, carbon_total
            )

            # Force-schedule tasks at deadline regardless of mode
            forced_ids = set()
            for task in list(deferred):
                if task.deadline <= slot and task.assigned_slot is None:
                    # Force schedule — use P2C balancer
                    server = self._balancer.pick()
                    lat    = server.accept(slot)
                    server.tick(slot)
                    task.mark_scheduled(slot, server.name, lat)

                    ci     = carbon_intensity(slot, self.cloudy)
                    carbon = ci * task.energy_cost
                    carbon_total          += carbon
                    result.tasks_scheduled += 1
                    result.total_carbon_g  += carbon
                    result.schedule_pairs.append((slot, task.energy_cost))
                    latencies.append(lat)
                    scheduled_ids.add(task.id)
                    forced_ids.add(task.id)

                    if task.met_deadline:
                        result.deadline_met    += 1
                    else:
                        result.deadline_missed += 1
                    result.grid_tasks += 1

            deferred = [t for t in deferred if t.id not in forced_ids and t.assigned_slot is None]

            # In SHED mode, only schedule critical tasks in solar windows
            if not self.agent.should_run_dp():
                # SHED: only force-schedule critical tasks if solar is present
                solar = energy_at_slot(slot, self.cloudy)
                if solar > 5:
                    critical = [t for t in deferred if t.priority == "critical"]
                    for task in critical:
                        server = self._balancer.pick()
                        lat    = server.accept(slot)
                        server.tick(slot)
                        task.mark_scheduled(slot, server.name, lat)
                        ci     = carbon_intensity(slot, self.cloudy)
                        carbon = ci * task.energy_cost
                        carbon_total          += carbon
                        result.tasks_scheduled += 1
                        result.total_carbon_g  += carbon
                        result.schedule_pairs.append((slot, task.energy_cost))
                        latencies.append(lat)
                        scheduled_ids.add(task.id)
                        if task.met_deadline:
                            result.deadline_met    += 1
                        else:
                            result.deadline_missed += 1
                        result.solar_tasks += 1
                    deferred = [t for t in deferred if t.id not in {t2.id for t2 in critical} or t.assigned_slot is None]
                continue

            # AGGRESSIVE or CONSERVATIVE: run DP
            solar_energy = energy_at_slot(slot, self.cloudy)
            # In CONSERVATIVE mode, use a higher threshold to avoid marginal solar
            # slots (20-30 units) which have higher carbon intensity than peak solar.
            # This matches DPScheduler's default threshold of 30.0.
            effective_threshold = (
                self.solar_threshold * 1.5
                if self.agent.state.mode == GreenAgent.MODE_CONSERVATIVE
                else self.solar_threshold
            )
            if solar_energy < effective_threshold:
                continue

            eligible = [t for t in deferred if t.arrival_slot <= slot and t.assigned_slot is None]
            if not eligible:
                continue

            eff_budget  = min(self.agent.effective_budget(), int(solar_energy))
            if eff_budget <= 0:
                continue

            dp      = build_dp_table(eligible, slot, eff_budget, self.cloudy)
            chosen  = traceback(dp, eligible, eff_budget)
            chosen_set = {t.id for t in chosen}

            for task in chosen:
                if task.id in scheduled_ids or task.assigned_slot is not None:
                    continue
                server = self._balancer.pick()
                lat    = server.accept(slot)
                server.tick(slot)
                task.mark_scheduled(slot, server.name, lat)
                scheduled_ids.add(task.id)

                ci     = carbon_intensity(slot, self.cloudy)
                carbon = ci * task.energy_cost
                carbon_total          += carbon
                result.tasks_scheduled += 1
                result.total_carbon_g  += carbon
                result.schedule_pairs.append((slot, task.energy_cost))
                latencies.append(lat)

                if task.met_deadline:
                    result.deadline_met    += 1
                else:
                    result.deadline_missed += 1
                result.solar_tasks += 1

            deferred = [t for t in deferred if t.id not in chosen_set or t.assigned_slot is None]

        # End of day: flush remaining deferred tasks to grid
        night_slot = SLOTS_PER_DAY - 1
        for task in deferred:
            if task.assigned_slot is not None or task.id in scheduled_ids:
                continue
            server = self._balancer.pick()
            lat    = server.accept(night_slot)
            task.mark_scheduled(night_slot, server.name, lat)
            scheduled_ids.add(task.id)

            ci     = carbon_intensity(night_slot, self.cloudy)
            carbon = ci * task.energy_cost
            carbon_total          += carbon
            result.tasks_scheduled += 1
            result.total_carbon_g  += carbon
            result.schedule_pairs.append((night_slot, task.energy_cost))
            latencies.append(lat)

            if task.met_deadline:
                result.deadline_met    += 1
            else:
                result.deadline_missed += 1
            result.grid_tasks += 1

        if latencies:
            result.avg_latency_ms = round(sum(latencies) / len(latencies), 2)

        result.total_carbon_g = round(result.total_carbon_g, 2)

        # Attach agent metadata to extras
        result.extras["agent_summary"]  = self.agent.summary()
        result.extras["agent_log"]      = self.agent.get_log()
        result.extras["balancer_stats"] = self._balancer.stats()

        return result


# ── Quick demo ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    tasks   = generate_tasks(n=100, seed=42)
    servers = make_cluster(5)

    scheduler = AgenticDPScheduler(budget=MAX_ENERGY_BUDGET, cloudy=False)
    result    = scheduler.run(tasks, servers)
    print(result.summary())
    print("Agent summary:", result.extras.get("agent_summary"))
    print("Balancer stats:")
    for name, stats in result.extras.get("balancer_stats", {}).items():
        print(f"  {name}: {stats}")
