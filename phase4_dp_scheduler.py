"""
Phase 4: Dynamic Programming Carbon-Aware Scheduler

Uses a knapsack-style DP to select which tasks to schedule in each solar window,
maximising total task value while staying within the solar energy budget.
Tasks that cannot fit in a solar window are deferred to the next or run on grid.
"""

from typing import List, Tuple, Dict, Optional
import copy

from phase1_models import Task, Server, make_cluster
from phase2_energy_model import (
    SLOTS_PER_DAY, energy_at_slot, carbon_intensity,
    build_energy_profile, slot_to_time, is_solar_window
)
from phase3_tasks import ScheduleResult, generate_tasks

# ── Constants ────────────────────────────────────────────────────────────────
MAX_ENERGY_BUDGET = 60   # max energy units the DP may schedule per slot


# ── DP building blocks ────────────────────────────────────────────────────────

def task_value(task: Task, slot: int, cloudy: bool = False) -> int:
    """
    Compute the scheduling value for a task at a given slot.

    Higher value = more desirable to schedule here.
    Rewards:
      - Critical tasks get a large bonus (+50).
      - Scheduling earlier relative to deadline earns a bonus (deadline pressure).
      - Running during peak solar earns a carbon-savings bonus.
    """
    base = 10

    # Priority bonus
    if task.priority == "critical":
        base += 50
    elif task.priority == "high":
        base += 20

    # Deadline urgency: tasks closer to deadline are more urgent
    slack = task.deadline - slot
    if slack <= 0:
        # Already past deadline — very low value (should not schedule late)
        base -= 100
    elif slack <= 2:
        base += 30
    elif slack <= 5:
        base += 15

    # Solar bonus: reward scheduling during high solar energy
    energy = energy_at_slot(slot, cloudy)
    if energy >= 70:
        base += 25
    elif energy >= 40:
        base += 12
    elif energy >= 10:
        base += 5

    return max(0, base)


def build_dp_table(
    tasks: List[Task],
    slot: int,
    budget: int = MAX_ENERGY_BUDGET,
    cloudy: bool = False,
) -> List[List[int]]:
    """
    0/1 Knapsack DP over tasks eligible at this slot.

    tasks  : tasks whose arrival_slot <= slot <= deadline
    slot   : the time slot we are scheduling for
    budget : max total energy_cost we can spend this slot
    Returns: dp table dp[i][w] = best value using first i tasks with weight <= w
    """
    n = len(tasks)
    dp = [[0] * (budget + 1) for _ in range(n + 1)]

    for i, task in enumerate(tasks, start=1):
        w = task.energy_cost
        v = task_value(task, slot, cloudy)
        for cap in range(budget + 1):
            # Don't take task i
            dp[i][cap] = dp[i - 1][cap]
            # Take task i if it fits
            if w <= cap:
                take = dp[i - 1][cap - w] + v
                if take > dp[i][cap]:
                    dp[i][cap] = take

    return dp


def traceback(
    dp: List[List[int]],
    tasks: List[Task],
    budget: int = MAX_ENERGY_BUDGET,
) -> List[Task]:
    """
    Traceback through the DP table to recover the selected task set.
    Returns a list of tasks chosen by the DP.
    """
    selected = []
    cap = budget
    n   = len(tasks)

    for i in range(n, 0, -1):
        if dp[i][cap] != dp[i - 1][cap]:
            selected.append(tasks[i - 1])
            cap -= tasks[i - 1].energy_cost

    return selected


def schedule_deferred(
    deferred: List[Task],
    slot: int,
    servers: List[Server],
    cloudy: bool = False,
) -> Tuple[List[Tuple], float, int, int]:
    """
    Forcibly schedule any deferred tasks that have reached their deadline.
    Returns (schedule_pairs, total_carbon, deadline_met, deadline_missed).
    """
    pairs    = []
    carbon   = 0.0
    met      = 0
    missed   = 0

    forced = [t for t in deferred if t.deadline <= slot]

    server_idx = 0
    for task in forced:
        server = servers[server_idx % len(servers)]
        server_idx += 1
        lat = server.accept(slot)
        server.tick(slot)
        task.mark_scheduled(slot, server.name, lat)
        ci = carbon_intensity(slot, cloudy)
        carbon += ci * task.energy_cost
        pairs.append((slot, task.energy_cost))
        if task.met_deadline:
            met    += 1
        else:
            missed += 1

    return pairs, carbon, met, missed


# ── DP Scheduler Class ────────────────────────────────────────────────────────

class DPScheduler:
    """
    Carbon-aware Dynamic Programming scheduler.

    Strategy:
      1. At each time slot, collect tasks that have arrived and not yet scheduled.
      2. If the slot has sufficient solar energy (>= solar_threshold), run DP
         to select the highest-value subset within the energy budget.
      3. Tasks not selected are deferred to a future solar window.
      4. Any task reaching its deadline is forcibly scheduled (avoids drops).
      5. At the end, remaining tasks are scheduled on the grid (night slots).
    """

    name = "DPScheduler"

    def __init__(
        self,
        solar_threshold: float = 30.0,
        budget: int = MAX_ENERGY_BUDGET,
        cloudy: bool = False,
    ):
        self.solar_threshold = solar_threshold
        self.budget          = budget
        self.cloudy          = cloudy

    def _best_server(self, servers: List[Server]) -> Server:
        return min(servers, key=lambda s: s.active_connections)

    def run(self, tasks: List[Task], servers: List[Server]) -> ScheduleResult:
        servers = [copy.deepcopy(s) for s in servers]
        for s in servers:
            s.reset()

        result = ScheduleResult(
            scheduler_name=self.name,
            tasks=tasks,
            servers=servers,
            cloudy=self.cloudy,
        )

        # Index tasks by arrival slot for efficient lookup
        from collections import defaultdict
        arrival_index: Dict[int, List[Task]] = defaultdict(list)
        for task in tasks:
            arrival_index[task.arrival_slot].append(task)

        deferred:   List[Task] = []   # tasks waiting for a solar window
        scheduled_ids = set()
        latencies  = []

        for slot in range(SLOTS_PER_DAY):
            # Tick all servers (release completed connections)
            for s in servers:
                s.tick(slot)

            # Add newly arrived tasks to the deferred pool
            for task in arrival_index.get(slot, []):
                deferred.append(task)

            # Force-schedule tasks at their deadline
            force_pairs, force_carbon, f_met, f_missed = schedule_deferred(
                deferred, slot, servers, self.cloudy
            )
            for task in deferred[:]:
                if task.assigned_slot is not None and task.id not in scheduled_ids:
                    scheduled_ids.add(task.id)
                    result.tasks_scheduled += 1
                    result.total_carbon_g  += carbon_intensity(task.assigned_slot, self.cloudy) * task.energy_cost
                    result.schedule_pairs.append((task.assigned_slot, task.energy_cost))
                    if task.latency_ms:
                        latencies.append(task.latency_ms)
                    if task.met_deadline:
                        result.deadline_met    += 1
                    else:
                        result.deadline_missed += 1
                    result.grid_tasks += 1

            deferred = [t for t in deferred if t.assigned_slot is None]

            # Check solar energy at this slot
            solar_energy = energy_at_slot(slot, self.cloudy)
            in_solar_window = solar_energy >= self.solar_threshold

            if in_solar_window and deferred:
                # Run DP to select best subset within budget
                eligible = [t for t in deferred if t.arrival_slot <= slot]
                if not eligible:
                    continue

                # Respect the actual solar energy as the budget cap
                effective_budget = min(self.budget, int(solar_energy))
                dp = build_dp_table(eligible, slot, effective_budget, self.cloudy)
                chosen = traceback(dp, eligible, effective_budget)

                chosen_ids = {t.id for t in chosen}

                for task in chosen:
                    if task.id in scheduled_ids:
                        continue
                    server = self._best_server(servers)
                    lat = server.accept(slot)
                    server.tick(slot)
                    task.mark_scheduled(slot, server.name, lat)
                    scheduled_ids.add(task.id)

                    ci     = carbon_intensity(slot, self.cloudy)
                    carbon = ci * task.energy_cost
                    result.tasks_scheduled += 1
                    result.total_carbon_g  += carbon
                    result.schedule_pairs.append((slot, task.energy_cost))
                    latencies.append(lat)

                    if task.met_deadline:
                        result.deadline_met    += 1
                    else:
                        result.deadline_missed += 1
                    result.solar_tasks += 1

                # Remove scheduled tasks from deferred
                deferred = [t for t in deferred if t.id not in chosen_ids or t.assigned_slot is None]

        # End of day: schedule any remaining deferred tasks on the grid
        night_slot = SLOTS_PER_DAY - 1
        for task in deferred:
            if task.assigned_slot is not None or task.id in scheduled_ids:
                continue
            server = self._best_server(servers)
            lat = server.accept(night_slot)
            task.mark_scheduled(night_slot, server.name, lat)
            scheduled_ids.add(task.id)

            ci     = carbon_intensity(night_slot, self.cloudy)
            carbon = ci * task.energy_cost
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
        return result


# ── Quick demo ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    tasks   = generate_tasks(n=80, seed=7)
    servers = make_cluster(5)

    scheduler = DPScheduler(solar_threshold=30.0, budget=MAX_ENERGY_BUDGET, cloudy=False)
    result    = scheduler.run(tasks, servers)
    print(result.summary())
    print(f"  Solar tasks: {result.solar_tasks} | Grid tasks: {result.grid_tasks}")
