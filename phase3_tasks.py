"""
Phase 3: Task Generator and Baseline Schedulers
Generates realistic cloud workloads and provides Round-Robin + Greedy EDF baselines.
"""

import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional

from phase1_models import Task, Server, make_cluster
from phase2_energy_model import (
    SLOTS_PER_DAY, build_energy_profile, carbon_intensity,
    total_carbon, slot_to_time, energy_at_slot
)


# ── Task Generator ────────────────────────────────────────────────────────────

def generate_tasks(
    n: int = 100,
    seed: int = 42,
    cloudy: bool = False,
) -> List[Task]:
    """
    Generate n synthetic cloud tasks with realistic distributions.

    Task priorities:
      - 10% critical   (tight deadlines, high energy)
      - 30% high       (moderate deadline)
      - 60% normal     (flexible, low energy)

    Arrivals follow a bimodal distribution: morning rush (slots 28-40)
    and afternoon rush (slots 56-70), with lighter background traffic.

    Note: cloudy is accepted for API consistency but tasks themselves are
    weather-independent; schedulers apply the cloudy flag when computing
    energy and carbon at scheduling time.
    """
    rng = random.Random(seed)
    tasks: List[Task] = []

    for i in range(n):
        # Priority distribution
        roll = rng.random()
        if roll < 0.10:
            priority = "critical"
        elif roll < 0.40:
            priority = "high"
        else:
            priority = "normal"

        # Arrival slot (bimodal + uniform background)
        mode = rng.random()
        if mode < 0.35:
            # Morning rush ~07:00-10:00 (slots 28-40)
            arrival = int(rng.gauss(34, 4))
        elif mode < 0.70:
            # Afternoon rush ~14:00-17:30 (slots 56-70)
            arrival = int(rng.gauss(63, 5))
        else:
            # Background traffic spread through the day
            arrival = rng.randint(0, SLOTS_PER_DAY - 1)

        arrival = max(0, min(SLOTS_PER_DAY - 1, arrival))

        # Deadline slack based on priority
        if priority == "critical":
            slack = rng.randint(1, 4)
        elif priority == "high":
            slack = rng.randint(3, 10)
        else:
            slack = rng.randint(5, 20)

        deadline = min(arrival + slack, SLOTS_PER_DAY - 1)

        # Load (compute units)
        if priority == "critical":
            load = rng.randint(8, 20)
        elif priority == "high":
            load = rng.randint(5, 15)
        else:
            load = rng.randint(1, 10)

        # Energy cost (roughly proportional to load with some variance)
        energy_cost = max(1, int(load * rng.uniform(0.6, 1.4)))

        tasks.append(Task(
            id=f"T{i+1:04d}",
            arrival_slot=arrival,
            deadline=deadline,
            load=load,
            energy_cost=energy_cost,
            priority=priority,
        ))

    # Sort by arrival time for deterministic processing order
    tasks.sort(key=lambda t: (t.arrival_slot, t.id))
    return tasks


def describe_workload(tasks: List[Task]) -> Dict:
    """Return a summary dict describing the task workload."""
    priorities = {"critical": 0, "high": 0, "normal": 0}
    for t in tasks:
        priorities[t.priority] = priorities.get(t.priority, 0) + 1

    arrivals = [t.arrival_slot for t in tasks]
    deadlines = [t.deadline for t in tasks]
    slacks = [t.deadline_slack() for t in tasks]

    morning   = sum(1 for t in tasks if 24 <= t.arrival_slot < 48)
    afternoon = sum(1 for t in tasks if 48 <= t.arrival_slot < 72)
    night     = sum(1 for t in tasks if t.arrival_slot < 24 or t.arrival_slot >= 72)

    return {
        "total_tasks":      len(tasks),
        "priority_counts":  priorities,
        "avg_slack":        round(sum(slacks) / len(slacks), 2) if slacks else 0,
        "min_slack":        min(slacks) if slacks else 0,
        "max_slack":        max(slacks) if slacks else 0,
        "total_energy":     sum(t.energy_cost for t in tasks),
        "morning_tasks":    morning,
        "afternoon_tasks":  afternoon,
        "night_tasks":      night,
        "arrival_range":    (min(arrivals), max(arrivals)) if arrivals else (0, 0),
    }


# ── Schedule Result ───────────────────────────────────────────────────────────

@dataclass
class ScheduleResult:
    scheduler_name:   str
    tasks:            List[Task]
    servers:          List[Server]
    total_carbon_g:   float = 0.0
    tasks_scheduled:  int   = 0
    tasks_dropped:    int   = 0
    deadline_met:     int   = 0
    deadline_missed:  int   = 0
    avg_latency_ms:   float = 0.0
    solar_tasks:      int   = 0
    grid_tasks:       int   = 0
    schedule_pairs:   List  = field(default_factory=list)   # [(slot, energy_cost), ...]
    cloudy:           bool  = False
    extras:           Dict  = field(default_factory=dict)

    def summary(self) -> str:
        return (
            f"[{self.scheduler_name}] "
            f"Scheduled={self.tasks_scheduled} | "
            f"Dropped={self.tasks_dropped} | "
            f"DeadlineMet={self.deadline_met} | "
            f"Carbon={self.total_carbon_g:.1f} gCO2 | "
            f"AvgLatency={self.avg_latency_ms:.1f} ms | "
            f"Solar={self.solar_tasks} | Grid={self.grid_tasks}"
        )


# ── Round-Robin Scheduler ─────────────────────────────────────────────────────

class RoundRobinScheduler:
    """
    Naive Round-Robin baseline: assigns tasks to servers in order,
    scheduled at arrival time (no deferral, no carbon awareness).
    """

    name = "RoundRobin"

    def __init__(self, cloudy: bool = False):
        self.cloudy = cloudy

    def run(self, tasks: List[Task], servers: List[Server]) -> ScheduleResult:
        import copy
        servers = [copy.deepcopy(s) for s in servers]
        for s in servers:
            s.reset()

        result = ScheduleResult(
            scheduler_name=self.name,
            tasks=tasks,
            servers=servers,
            cloudy=self.cloudy,
        )

        rr_idx = 0
        latencies = []

        for task in tasks:
            slot   = task.arrival_slot
            server = servers[rr_idx % len(servers)]
            rr_idx += 1

            lat = server.accept(slot)
            server.tick(slot)
            task.mark_scheduled(slot, server.name, lat)

            energy = energy_at_slot(slot, self.cloudy)
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

            if energy > 30:
                result.solar_tasks += 1
            else:
                result.grid_tasks  += 1

        if latencies:
            result.avg_latency_ms = round(sum(latencies) / len(latencies), 2)

        return result


# ── Greedy EDF Scheduler ──────────────────────────────────────────────────────

class GreedyEDFScheduler:
    """
    Greedy Earliest Deadline First scheduler: processes tasks in EDF order,
    assigns to the least-loaded server. No carbon awareness (baseline).
    """

    name = "GreedyEDF"

    def __init__(self, cloudy: bool = False):
        self.cloudy = cloudy

    def _pick_server(self, servers: List[Server]) -> Server:
        """Pick the server with fewest active connections (least loaded)."""
        return min(servers, key=lambda s: s.active_connections)

    def run(self, tasks: List[Task], servers: List[Server]) -> ScheduleResult:
        import copy
        servers = [copy.deepcopy(s) for s in servers]
        for s in servers:
            s.reset()

        result = ScheduleResult(
            scheduler_name=self.name,
            tasks=tasks,
            servers=servers,
            cloudy=self.cloudy,
        )

        # Sort by deadline (EDF), then by arrival for ties
        edf_tasks = sorted(tasks, key=lambda t: (t.deadline, t.arrival_slot))

        latencies = []

        for task in edf_tasks:
            slot   = task.arrival_slot
            server = self._pick_server(servers)

            lat = server.accept(slot)
            server.tick(slot)
            task.mark_scheduled(slot, server.name, lat)

            energy = energy_at_slot(slot, self.cloudy)
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

            if energy > 30:
                result.solar_tasks += 1
            else:
                result.grid_tasks  += 1

        if latencies:
            result.avg_latency_ms = round(sum(latencies) / len(latencies), 2)

        return result


# ── Quick demo ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    tasks   = generate_tasks(n=50, seed=1)
    servers = make_cluster(5)
    desc    = describe_workload(tasks)
    print("Workload:", desc)
    print()

    rr  = RoundRobinScheduler().run(tasks, servers)
    print(rr.summary())

    edf = GreedyEDFScheduler().run(tasks, servers)
    print(edf.summary())
