"""
Phase 3: Task Generator and Baseline Schedulers
Generates realistic cloud workloads and provides Round-Robin + Greedy EDF baselines.
"""

import os
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pandas as pd

from phase1_models import Task, Server, make_cluster
from phase2_energy_model import (
    SLOTS_PER_DAY,
    build_energy_profile,
    carbon_intensity,
    total_carbon,
    slot_to_time,
    energy_at_slot,
)


SECONDS_PER_DAY = 24 * 60 * 60
SECONDS_PER_SLOT = 15 * 60

AZURE_TASK_ID_PREFIX = "AZ-"
PADDED_TASK_ID_PREFIX = "PAD-"

AZURE_COLUMN_ALIASES = {
    "vm_id": ["vm_id", "vmid"],
    "timestamp_created": [
        "timestamp_vm_created",
        "vmcreated",
        "timestamp created",
    ],
    "timestamp_deleted": [
        "timestamp_vm_deleted",
        "vmdeleted",
        "timestamp deleted",
    ],
    "priority": ["priority", "vm_priority"],
    "vm_category": ["vm_category", "vmcategory", "category"],
    "cpu_count": [
        "cpu_count",
        "core_count",
        "vm_virtual_core_count",
        "vmcorecount",
        "vmcorecountbucket",
        "core_bucket",
    ],
    "max_cpu": ["max_cpu", "maxcpu"],
    "avg_cpu": ["avg_cpu", "avgcpu"],
    "p95_max_cpu": ["p95_max_cpu", "p95maxcpu", "p95_of_max_cpu_utilization"],
}

AZURE_V2_HEADERLESS_COLUMNS = [
    "vm_id",
    "subscription_id",
    "deployment_id",
    "timestamp_vm_created",
    "timestamp_vm_deleted",
    "max_cpu",
    "avg_cpu",
    "p95_max_cpu",
    "vm_category",
    "core_count",
    "memory_gb",
]


def _find_column(columns, aliases):
    """Return the first matching column name from a list of aliases."""
    lowered = {str(col).strip().lower(): col for col in columns}
    for alias in aliases:
        found = lowered.get(alias.lower())
        if found is not None:
            return found
    return None


def _clamp_slot(slot: int) -> int:
    return max(0, min(SLOTS_PER_DAY - 1, int(slot)))


def _normalize_arrival_slot(timestamp_seconds: float) -> int:
    folded = int(timestamp_seconds) % SECONDS_PER_DAY
    return _clamp_slot(folded // SECONDS_PER_SLOT)


def _priority_from_value(value, rng: random.Random) -> str:
    """
    Map Azure priority/category values to project priorities.

    Preferred mapping:
      - 0 -> critical
      - 1 -> high
      - 2 -> normal

    When the trace exposes categorical VM labels instead of scheduler priority,
    fall back to a weighted distribution that preserves the project's expected
    10/30/60 split.
    """
    value_str = "" if value is None else str(value).strip().lower()

    numeric_map = {
        "0": "critical",
        "0.0": "critical",
        "1": "high",
        "1.0": "high",
        "2": "normal",
        "2.0": "normal",
    }
    if value_str in numeric_map:
        return numeric_map[value_str]

    textual_map = {
        "critical": "critical",
        "high": "high",
        "normal": "normal",
        "interactive": "critical",
        "latency_sensitive": "critical",
        "latency-sensitive": "critical",
        "production": "high",
        "batch": "normal",
        "delay_insensitive": "normal",
        "delay-insensitive": "normal",
    }
    if value_str in textual_map:
        return textual_map[value_str]

    roll = rng.random()
    if roll < 0.10:
        return "critical"
    if roll < 0.40:
        return "high"
    return "normal"


def _scale_load_from_row(
    row,
    cpu_col: Optional[str],
    max_cpu_col: Optional[str],
    avg_cpu_col: Optional[str],
    p95_cpu_col: Optional[str],
) -> int:
    """
    Scale Azure CPU-related features into the project's 1..10 load range.

    Preferred path uses a core-count-like field. If that is unavailable, fall
    back to utilization-derived features.
    """
    cpu_value = None
    if cpu_col is not None:
        candidate = row.get(cpu_col)
        if pd.notna(candidate):
            try:
                cpu_value = float(candidate)
            except (TypeError, ValueError):
                cpu_value = None

    if cpu_value is not None and cpu_value > 0:
        scaled = int(round((cpu_value / max(cpu_value, 64.0)) * 10))
        return max(1, min(10, scaled))

    cpu_features = []
    for col in (max_cpu_col, avg_cpu_col, p95_cpu_col):
        if col is None:
            continue
        value = row.get(col)
        if pd.notna(value):
            try:
                cpu_features.append(float(value))
            except (TypeError, ValueError):
                continue

    if cpu_features:
        scaled = int(round((max(cpu_features) / 100.0) * 10))
        return max(1, min(10, scaled))

    return 1


def _make_synthetic_tasks(
    n: int = 100,
    seed: int = 42,
    id_prefix: str = "T",
) -> List[Task]:
    """Generate synthetic tasks with the original project behavior."""
    rng = random.Random(seed)
    tasks: List[Task] = []

    for i in range(n):
        roll = rng.random()
        if roll < 0.10:
            priority = "critical"
        elif roll < 0.40:
            priority = "high"
        else:
            priority = "normal"

        mode = rng.random()
        if mode < 0.35:
            arrival = int(rng.gauss(34, 4))
        elif mode < 0.70:
            arrival = int(rng.gauss(63, 5))
        else:
            arrival = rng.randint(0, SLOTS_PER_DAY - 1)

        arrival = _clamp_slot(arrival)

        if priority == "critical":
            slack = rng.randint(1, 4)
        elif priority == "high":
            slack = rng.randint(3, 10)
        else:
            slack = rng.randint(5, 20)

        deadline = min(arrival + slack, SLOTS_PER_DAY - 1)

        if priority == "critical":
            load = rng.randint(8, 20)
        elif priority == "high":
            load = rng.randint(5, 15)
        else:
            load = rng.randint(1, 10)

        energy_cost = max(1, int(load * rng.uniform(0.6, 1.4)))

        if id_prefix == "T":
            task_id = f"{id_prefix}{i+1:04d}"
        else:
            task_id = f"{id_prefix}{i+1:05d}"

        tasks.append(Task(
            id=task_id,
            arrival_slot=arrival,
            deadline=deadline,
            load=load,
            energy_cost=energy_cost,
            priority=priority,
        ))

    tasks.sort(key=lambda t: (t.arrival_slot, t.id))
    return tasks


def load_azure_tasks(filepath: str, n: int = 100, seed: int = 42) -> List[Task]:
    """
    Load up to n tasks from Azure VM trace data and map them into Task objects.

    The CSV is read in chunks so the loader can stop after collecting enough
    valid rows from a very large file.
    """
    if not filepath:
        raise FileNotFoundError("Azure trace path was not provided.")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Azure trace file not found: {filepath}")

    rng = random.Random(seed)
    tasks: List[Task] = []
    chunksize = 10_000

    preview = pd.read_csv(filepath, nrows=1, low_memory=False)
    created_preview = _find_column(preview.columns, AZURE_COLUMN_ALIASES["timestamp_created"])
    deleted_preview = _find_column(preview.columns, AZURE_COLUMN_ALIASES["timestamp_deleted"])

    if created_preview is None or deleted_preview is None:
        if len(preview.columns) == len(AZURE_V2_HEADERLESS_COLUMNS):
            read_kwargs = {
                "chunksize": chunksize,
                "low_memory": False,
                "header": None,
                "names": AZURE_V2_HEADERLESS_COLUMNS,
            }
        else:
            raise ValueError(
                "Azure vmtable schema mismatch: expected creation/deletion timestamp columns "
                "(for example timestamp_vm_created and timestamp_vm_deleted)."
            )
    else:
        read_kwargs = {"chunksize": chunksize, "low_memory": False}

    reader = pd.read_csv(filepath, **read_kwargs)

    for chunk in reader:
        if len(tasks) >= n:
            break

        created_col = _find_column(chunk.columns, AZURE_COLUMN_ALIASES["timestamp_created"])
        deleted_col = _find_column(chunk.columns, AZURE_COLUMN_ALIASES["timestamp_deleted"])
        vm_id_col = _find_column(chunk.columns, AZURE_COLUMN_ALIASES["vm_id"])
        priority_col = _find_column(chunk.columns, AZURE_COLUMN_ALIASES["priority"])
        category_col = _find_column(chunk.columns, AZURE_COLUMN_ALIASES["vm_category"])
        cpu_col = _find_column(chunk.columns, AZURE_COLUMN_ALIASES["cpu_count"])
        max_cpu_col = _find_column(chunk.columns, AZURE_COLUMN_ALIASES["max_cpu"])
        avg_cpu_col = _find_column(chunk.columns, AZURE_COLUMN_ALIASES["avg_cpu"])
        p95_cpu_col = _find_column(chunk.columns, AZURE_COLUMN_ALIASES["p95_max_cpu"])

        if created_col is None or deleted_col is None:
            raise ValueError(
                "Azure vmtable schema mismatch: expected creation/deletion timestamp columns "
                "(for example timestamp_vm_created and timestamp_vm_deleted)."
            )

        required_cols = [created_col, deleted_col]
        if cpu_col is not None:
            required_cols.append(cpu_col)

        filtered = chunk.dropna(subset=required_cols)

        for _, row in filtered.iterrows():
            if len(tasks) >= n:
                break

            try:
                created_ts = float(row[created_col])
                deleted_ts = float(row[deleted_col])
            except (TypeError, ValueError):
                continue

            lifetime_seconds = deleted_ts - created_ts
            if lifetime_seconds <= 0:
                continue

            arrival_slot = _normalize_arrival_slot(created_ts)
            lifetime_slots = max(1, int(lifetime_seconds // SECONDS_PER_SLOT))
            deadline = _clamp_slot(arrival_slot + lifetime_slots)
            if deadline < arrival_slot:
                continue

            priority_value = None
            if priority_col is not None:
                priority_value = row.get(priority_col)
            elif category_col is not None:
                priority_value = row.get(category_col)
            priority = _priority_from_value(priority_value, rng)

            load = _scale_load_from_row(
                row,
                cpu_col=cpu_col,
                max_cpu_col=max_cpu_col,
                avg_cpu_col=avg_cpu_col,
                p95_cpu_col=p95_cpu_col,
            )
            if load <= 0:
                continue

            energy_cost = max(1, min(20, int(round(load * rng.uniform(0.8, 1.5)))))

            raw_vm_id = row.get(vm_id_col) if vm_id_col is not None else len(tasks) + 1
            task_suffix = str(raw_vm_id).strip() or str(len(tasks) + 1)
            task_id = f"{AZURE_TASK_ID_PREFIX}{task_suffix}"

            tasks.append(Task(
                id=task_id,
                arrival_slot=arrival_slot,
                deadline=deadline,
                load=load,
                energy_cost=energy_cost,
                priority=priority,
            ))

    azure_count = len(tasks)
    if azure_count < n:
        padded = _make_synthetic_tasks(
            n=n - azure_count,
            seed=seed + 999,
            id_prefix=PADDED_TASK_ID_PREFIX,
        )
        tasks.extend(padded)

    tasks.sort(key=lambda t: (t.arrival_slot, t.id))

    padded_count = max(0, n - azure_count)
    if padded_count:
        print(
            f"[INFO] Loaded {azure_count} Azure tasks from {filepath} and padded with "
            f"{padded_count} synthetic tasks to reach n={n}."
        )
    else:
        print(f"[INFO] Loaded {azure_count} Azure tasks from {filepath}.")

    return tasks[:n]


def generate_tasks(
    n: int = 100,
    seed: int = 42,
    cloudy: bool = False,
    use_azure: bool = False,
    azure_filepath: Optional[str] = None,
) -> List[Task]:
    """
    Generate n cloud tasks.

    By default this uses the original synthetic workload generator.
    When use_azure=True, it attempts to load tasks from Azure VM traces and
    falls back to synthetic generation if the file is missing or invalid.

    Note: cloudy is accepted for API consistency but tasks themselves are
    weather-independent; schedulers apply the cloudy flag when computing
    energy and carbon at scheduling time.
    """
    if use_azure:
        try:
            return load_azure_tasks(azure_filepath or "vmtable.csv", n=n, seed=seed)
        except (FileNotFoundError, ValueError, pd.errors.EmptyDataError) as exc:
            print(
                f"[WARN] Azure trace loading failed ({exc}). Falling back to synthetic task generation."
            )

    return _make_synthetic_tasks(n=n, seed=seed, id_prefix="T")


def describe_workload(tasks: List[Task]) -> Dict:
    """Return a summary dict describing the task workload."""
    priorities = {"critical": 0, "high": 0, "normal": 0}
    for task in tasks:
        priorities[task.priority] = priorities.get(task.priority, 0) + 1

    arrivals = [task.arrival_slot for task in tasks]
    slacks = [task.deadline_slack() for task in tasks]

    morning = sum(1 for task in tasks if 24 <= task.arrival_slot < 48)
    afternoon = sum(1 for task in tasks if 48 <= task.arrival_slot < 72)
    night = sum(1 for task in tasks if task.arrival_slot < 24 or task.arrival_slot >= 72)
    azure_tasks = sum(1 for task in tasks if task.id.startswith(AZURE_TASK_ID_PREFIX))
    padded_tasks = sum(1 for task in tasks if task.id.startswith(PADDED_TASK_ID_PREFIX))
    synthetic_tasks = len(tasks) - azure_tasks - padded_tasks

    return {
        "total_tasks": len(tasks),
        "priority_counts": priorities,
        "avg_slack": round(sum(slacks) / len(slacks), 2) if slacks else 0,
        "min_slack": min(slacks) if slacks else 0,
        "max_slack": max(slacks) if slacks else 0,
        "total_energy": sum(task.energy_cost for task in tasks),
        "morning_tasks": morning,
        "afternoon_tasks": afternoon,
        "night_tasks": night,
        "arrival_range": (min(arrivals), max(arrivals)) if arrivals else (0, 0),
        "azure_tasks": azure_tasks,
        "synthetic_padded": padded_tasks,
        "synthetic_tasks": synthetic_tasks,
    }


@dataclass
class ScheduleResult:
    scheduler_name: str
    tasks: List[Task]
    servers: List[Server]
    total_carbon_g: float = 0.0
    tasks_scheduled: int = 0
    tasks_dropped: int = 0
    deadline_met: int = 0
    deadline_missed: int = 0
    avg_latency_ms: float = 0.0
    solar_tasks: int = 0
    grid_tasks: int = 0
    schedule_pairs: List = field(default_factory=list)
    cloudy: bool = False
    extras: Dict = field(default_factory=dict)

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

        servers = [copy.deepcopy(server) for server in servers]
        for server in servers:
            server.reset()

        result = ScheduleResult(
            scheduler_name=self.name,
            tasks=tasks,
            servers=servers,
            cloudy=self.cloudy,
        )

        rr_idx = 0
        latencies = []

        for task in tasks:
            slot = task.arrival_slot
            server = servers[rr_idx % len(servers)]
            rr_idx += 1

            lat = server.accept(slot)
            server.tick(slot)
            task.mark_scheduled(slot, server.name, lat)

            energy = energy_at_slot(slot, self.cloudy)
            ci = carbon_intensity(slot, self.cloudy)
            carbon = ci * task.energy_cost

            result.tasks_scheduled += 1
            result.total_carbon_g += carbon
            result.schedule_pairs.append((slot, task.energy_cost))
            latencies.append(lat)

            if task.met_deadline:
                result.deadline_met += 1
            else:
                result.deadline_missed += 1

            if energy > 30:
                result.solar_tasks += 1
            else:
                result.grid_tasks += 1

        if latencies:
            result.avg_latency_ms = round(sum(latencies) / len(latencies), 2)

        return result


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
        return min(servers, key=lambda server: server.active_connections)

    def run(self, tasks: List[Task], servers: List[Server]) -> ScheduleResult:
        import copy

        servers = [copy.deepcopy(server) for server in servers]
        for server in servers:
            server.reset()

        result = ScheduleResult(
            scheduler_name=self.name,
            tasks=tasks,
            servers=servers,
            cloudy=self.cloudy,
        )

        edf_tasks = sorted(tasks, key=lambda task: (task.deadline, task.arrival_slot))
        latencies = []

        for task in edf_tasks:
            slot = task.arrival_slot
            server = self._pick_server(servers)

            lat = server.accept(slot)
            server.tick(slot)
            task.mark_scheduled(slot, server.name, lat)

            energy = energy_at_slot(slot, self.cloudy)
            ci = carbon_intensity(slot, self.cloudy)
            carbon = ci * task.energy_cost

            result.tasks_scheduled += 1
            result.total_carbon_g += carbon
            result.schedule_pairs.append((slot, task.energy_cost))
            latencies.append(lat)

            if task.met_deadline:
                result.deadline_met += 1
            else:
                result.deadline_missed += 1

            if energy > 30:
                result.solar_tasks += 1
            else:
                result.grid_tasks += 1

        if latencies:
            result.avg_latency_ms = round(sum(latencies) / len(latencies), 2)

        return result


if __name__ == "__main__":
    tasks = generate_tasks(n=50, seed=1)
    servers = make_cluster(5)
    desc = describe_workload(tasks)
    print("Workload:", desc)
    print()

    rr = RoundRobinScheduler().run(tasks, servers)
    print(rr.summary())

    edf = GreedyEDFScheduler().run(tasks, servers)
    print(edf.summary())
