# Project Context for LLMs

Last updated: 2026-05-16

This document is a current-state handoff for any LLM working on this repository. It describes what the project does, how the code is organized, how to run it, what the current behavior looks like, and which implementation issues are already known.

## 1. Project Summary

This repo is a cloud computing project centered on a carbon-aware task scheduler for a simulated data center.

Main idea:
- Model one day as 96 time slots of 15 minutes each.
- Generate synthetic cloud tasks with arrivals, deadlines, priority, load, and energy cost.
- Compare several scheduling strategies.
- Prefer scheduling work during stronger solar windows to reduce carbon emissions.
- Expose results through a benchmark script and a Streamlit dashboard.

The code is written as a sequence of project phases:
- `phase1_models.py`: core `Task` and `Server` models.
- `phase2_energy_model.py`: solar generation and carbon intensity model.
- `phase3_tasks.py`: workload generator plus baseline schedulers.
- `phase4_dp_scheduler.py`: dynamic-programming carbon-aware scheduler.
- `phase5_agent.py`: agentic scheduler plus power-of-2-choices load balancer.
- `battery_model.py`: battery storage model and battery-aware scheduler.
- `benchmark.py`: batch comparison and chart generation.
- `dashboard.py`: Streamlit UI for live simulation and benchmark visualization.

## 2. Repo Snapshot

Top-level files:
- `phase1_models.py`
- `phase2_energy_model.py`
- `phase3_tasks.py`
- `phase4_dp_scheduler.py`
- `phase5_agent.py`
- `battery_model.py`
- `benchmark.py`
- `dashboard.py`
- `requirements.txt`
- `outputs/` with generated charts

There was no `README.md` or other project markdown in the repo at the time this file was created.

## 3. Core Domain Model

### Time and energy model

From `phase2_energy_model.py`:
- `SLOTS_PER_DAY = 96`
- `SLOT_DURATION = 15` minutes
- `MAX_ENERGY = 100`
- `SUNRISE_SLOT = 24` which represents 06:00
- `SUNSET_SLOT = 80` which represents 20:00
- `PEAK_SLOT = 52` which represents 13:00
- `SOLAR_CARBON = 2.0`
- `GRID_CARBON = 45.0`
- `CLOUD_FACTOR = 0.55`

Solar production is modeled with a Gaussian-shaped bell curve between sunrise and sunset. Carbon intensity is a linear blend between solar and grid based on solar fraction.

Useful helpers:
- `energy_at_slot(slot, cloudy=False)`
- `carbon_intensity(slot, cloudy=False)`
- `build_energy_profile(cloudy=False)`
- `slot_to_time(slot)`
- `time_to_slot("HH:MM")`

### Task model

From `phase1_models.py`, each `Task` has:
- `id`
- `arrival_slot`
- `deadline`
- `load`
- `energy_cost`
- `priority` with values like `normal`, `high`, `critical`
- scheduling outputs such as `assigned_slot`, `assigned_server`, `latency_ms`, `met_deadline`

Useful methods:
- `is_critical()`
- `is_flexible()`
- `deadline_slack()`
- `mark_scheduled(slot, server_name, latency)`

### Server model

Each `Server` has:
- `id`
- `name`
- `base_latency_ms`
- `max_connections`
- runtime counters such as `active_connections`, `total_requests`, `total_latency_ms`

Useful methods:
- `current_latency()`
- `accept(tick)`
- `tick(current_tick)`
- `utilisation()`
- `avg_latency()`
- `reset()`

`make_cluster(n=5)` builds a small cluster with base latencies cycling through:
- 18 ms
- 28 ms
- 35 ms
- 42 ms
- 55 ms

## 4. Workload Generation

From `phase3_tasks.py`, `generate_tasks()` creates synthetic workloads with:
- 10% critical tasks
- 30% high-priority tasks
- 60% normal tasks

Arrival pattern:
- Morning rush around slots 28 to 40
- Afternoon rush around slots 56 to 70
- Remaining tasks spread across the day

Deadline slack:
- Critical: 1 to 4 slots
- High: 3 to 10 slots
- Normal: 5 to 20 slots

Load ranges:
- Critical: 8 to 20
- High: 5 to 15
- Normal: 1 to 10

Energy cost is roughly proportional to load with random variance.

The workload is sorted by arrival time before returning.

## 5. Scheduling Algorithms

### 5.1 RoundRobinScheduler

File:
- `phase3_tasks.py`

Behavior:
- Schedules every task at its arrival slot.
- Assigns servers in fixed round-robin order.
- Does not defer tasks.
- Does not optimize for carbon.

Typical use:
- Baseline comparison.

### 5.2 GreedyEDFScheduler

File:
- `phase3_tasks.py`

Behavior:
- Sorts tasks by earliest deadline first.
- Picks the server with the fewest active connections.
- Still schedules at each task's arrival slot.
- No explicit carbon awareness.

Important note:
- The current implementation mutates server state while iterating in EDF order, even when that order is not chronological. This matters for review and benchmarking.

### 5.3 DPScheduler

File:
- `phase4_dp_scheduler.py`

Behavior:
- Maintains a deferred queue of arrived but unscheduled tasks.
- At solar-friendly slots, runs a knapsack-style DP to pick the best subset under an energy budget.
- Force-schedules tasks that reach their deadline.
- Flushes remaining tasks to the grid at the end of the day.

Important constants:
- `MAX_ENERGY_BUDGET = 60`
- default `solar_threshold = 30.0`

DP-related helpers:
- `task_value(task, slot, cloudy=False)`
- `build_dp_table(tasks, slot, budget, cloudy=False)`
- `traceback(dp, tasks, budget)`
- `schedule_deferred(...)`

### 5.4 AgenticDPScheduler

File:
- `phase5_agent.py`

Adds two ideas on top of DP:
- `GreenAgent`: chooses a scheduling mode per slot.
- `P2CLoadBalancer`: uses power-of-2-choices server selection.

Agent modes:
- `AGGRESSIVE`: full budget when solar is high
- `CONSERVATIVE`: reduced budget when solar is moderate
- `SHED`: do not run DP, mostly defer work

Thresholds:
- aggressive at `solar >= 60`
- conservative at `20 <= solar < 60`
- shed below `20`

The scheduler stores extra metadata in `ScheduleResult.extras`:
- `agent_summary`
- `agent_log`
- `balancer_stats`

### 5.5 BatteryAwareDPScheduler

File:
- `battery_model.py`

Adds a simulated battery system:
- charges from solar surplus
- discharges during low-solar periods
- extends the effective scheduling window

Battery defaults:
- `capacity = 200`
- `max_charge_rate = 25`
- `max_discharge_rate = 25`
- `ROUND_TRIP_EFFICIENCY = 0.90`
- `BATTERY_CARBON_FACTOR = 2.5`

Battery scheduler extras:
- `battery_summary`
- `battery_soc_trace`
- `battery_history`

## 6. Benchmark and Dashboard

### Benchmark

File:
- `benchmark.py`

Main entry point:
- `run_benchmark(n_tasks=100, seed=42, cloudy=False)`

What it does:
- Generates one workload.
- Runs all schedulers on fresh copies of the same tasks.
- Prints text summaries.
- Saves four charts to `outputs/`.

Charts generated:
- `chart1_energy_profile.png`
- `chart2_carbon_comparison.png`
- `chart3_task_distribution.png`
- `chart4_latency_vs_carbon.png`

### Dashboard

File:
- `dashboard.py`

Main UI features:
- Live simulation tab
- Benchmark tab
- Battery analysis tab

Run command:
- `streamlit run dashboard.py`

Important caveat:
- The dashboard's live simulation is presented as the agentic scheduler, but the simulation loop is not a strict reuse of the backend `AgenticDPScheduler` class. It contains its own control logic and battery behavior.

## 7. Dependencies

From `requirements.txt`:
- `streamlit>=1.28.0`
- `plotly>=5.15.0`
- `matplotlib>=3.7.0`
- `numpy>=1.24.0`
- `pandas>=2.0.0`

## 8. How to Run

Install dependencies:

```powershell
pip install -r requirements.txt
```

Run benchmark:

```powershell
python benchmark.py
```

Run dashboard:

```powershell
streamlit run dashboard.py
```

## 9. Current Benchmark Snapshot

Observed locally on 2026-05-16 with:
- `n_tasks=100`
- `seed=42`
- `cloudy=False`

Workload summary:
- total tasks: 100
- priorities: 9 critical, 28 high, 63 normal
- average slack: 9.27
- total energy: 716
- arrivals: 47 morning, 39 afternoon, 14 night
- arrival range: slots 6 to 89

Observed scheduler results:

| Scheduler | Carbon (gCO2) | Tasks Scheduled | Deadline Met | Solar Tasks | Grid Tasks | Avg Latency (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| RoundRobin | 18034.19 | 100 | 100 | 77 | 23 | 46.77 |
| GreedyEDF | 18034.19 | 100 | 100 | 77 | 23 | 37.76 |
| DPScheduler | 16846.37 | 100 | 100 | 87 | 13 | 36.87 |
| AgenticDP | 16578.34 | 100 | 100 | 86 | 14 | 40.49 |
| BatteryAwareDP | 16273.26 | 100 | 100 | 82 | 18 | 36.28 |

Interpretation:
- On this workload, carbon-aware schedulers outperform the two baseline schedulers.
- `BatteryAwareDP` is best on total carbon for this specific run.
- Latency values are not fully stable across runs because `Server.accept()` adds random latency jitter.

Additional observation from review:
- With a smaller run of `n_tasks=50`, `seed=42`, `cloudy=False`, `BatteryAwareDP` performed worse than plain `DPScheduler`. So battery improvement is workload-sensitive and not guaranteed by current implementation.

## 10. Known Issues and Review Findings

These issues were present when this document was created.

### High priority issues

1. Server capacity is not enforced.
- `Server.accept()` always increments `active_connections`.
- `max_connections` affects latency calculation, but it does not block new work.
- This makes overload behavior unrealistic.

2. `GreedyEDFScheduler` simulates time out of order.
- It sorts by deadline but still schedules tasks at their original arrival slots.
- Because server state mutates in iteration order, earlier simulated times can be affected by later tasks.

3. Battery carbon accounting can undercount emissions.
- In end-of-day battery usage, a task can be treated as battery-powered even when only part of its energy is actually discharged from the battery.

### Medium priority issues

4. The dashboard live simulation does not exactly match the backend `AgenticDPScheduler`.
- It has its own scheduling loop.
- It uses battery logic in the live tab even though the description frames it as the agentic scheduler.
- It does not reuse the backend P2C load balancer implementation directly.

5. Battery claims in the UI are stronger than the current implementation justifies.
- The dashboard text says battery storage achieves an additional 5 to 8 percent reduction over vanilla DP.
- That is not consistently true across workloads tested during review.

### Low priority issues

6. `BatteryStorage.reset()` clears state-of-charge to zero even if the battery was initialized with a non-zero `initial_soc`.
- A pre-charged battery configuration does not survive a scheduler run.

7. The repo currently has no automated test suite.
- A search for `pytest`, `unittest`, and test files returned nothing.

## 11. Practical Notes for Future LLMs

If you are asked to modify this repo, these are good assumptions to start from:
- This is a simulation/demo project, not production infra code.
- Correctness of scheduler accounting matters more than micro-optimizations.
- The most fragile areas are time ordering, carbon accounting, and the mismatch between dashboard behavior and backend scheduler classes.
- If you add tests, start with deterministic tests around:
  - EDF chronology
  - DP task selection and deferred queue handling
  - battery discharge accounting
  - server capacity behavior
  - dashboard/backend consistency on a fixed seed

Recommended priorities for future cleanup:
- Add a real test suite.
- Enforce or clearly redefine server capacity semantics.
- Fix EDF time-order simulation.
- Make dashboard live simulation reuse backend scheduler logic more directly.
- Tighten battery accounting so low-carbon attribution matches actual discharged energy.
- Add a proper `README.md` that links to this file.

## 12. Short LLM Handoff Summary

Use this repo as:
- a phased educational project about green cloud scheduling
- a simulation comparing baseline, DP, agentic, and battery-aware schedulers
- a codebase with a working dashboard and benchmark flow
- a codebase that already has known correctness gaps in server capacity, EDF chronology, and battery accounting

If you need a one-paragraph summary for another model:

> This repository simulates a carbon-aware cloud task scheduler across 96 daily 15-minute slots. It contains phased modules for task/server models, solar and carbon modeling, workload generation, baseline schedulers, a DP-based scheduler, an agentic scheduler with mode switching and P2C balancing, and a battery-aware scheduler. The main runnable entry points are `benchmark.py` and `dashboard.py`. As of 2026-05-16, the best observed clear-day benchmark at `n_tasks=100, seed=42` is `BatteryAwareDP` on total carbon, but there are known correctness issues: server capacity is not enforced, `GreedyEDF` mutates server state out of chronological order, battery carbon attribution can over-credit low-carbon energy, the dashboard live simulation is not an exact backend replay, and there is no automated test suite.
