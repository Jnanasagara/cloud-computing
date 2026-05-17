# Azure Integration Update

Date: 2026-05-16

This document explains:
- what the project looked like before today's work
- what exact changes were made today
- why those changes were needed
- how the Azure dataset was matched to the project
- what issues came up during integration
- how the code works now

This is written so that someone reading it later, including you, can understand both the project history and the exact implementation decisions made today.

## 1. Project State Before Today's Changes

Before today's work, the project was a working simulation of a carbon-aware cloud task scheduling system. It already had:

- `phase1_models.py`
  - `Task` dataclass
  - `Server` dataclass
- `phase2_energy_model.py`
  - solar energy generation model
  - carbon intensity model
  - 96 time slots of 15 minutes each
- `phase3_tasks.py`
  - `generate_tasks()` used a fully synthetic workload
  - baseline schedulers:
    - `RoundRobinScheduler`
    - `GreedyEDFScheduler`
- `phase4_dp_scheduler.py`
  - carbon-aware dynamic programming scheduler
- `phase5_agent.py`
  - `AgenticDPScheduler`
  - `GreenAgent`
  - `P2CLoadBalancer`
- `battery_model.py`
  - `BatteryAwareDPScheduler`
  - `BatteryStorage`
- `benchmark.py`
  - ran all schedulers
  - printed scheduler summaries
  - generated 4 charts in `outputs/`

### How task generation worked before today

The biggest limitation before today's work was in [phase3_tasks.py](/c:/Users/Dhimant/Downloads/cloud_impl/cloud-computing/phase3_tasks.py:1).

`generate_tasks()` created tasks randomly:
- arrival slots were synthetic
- priorities were synthetic
- deadlines were synthetic
- loads were synthetic
- energy costs were synthetic

This meant the schedulers were real code, but the workload driving them was not based on any production cloud trace.

## 2. Goal of Today's Work

The goal was to replace the random workload generator with a real Azure public dataset, while leaving the rest of the project untouched.

The target dataset was:
- Azure Public Dataset V2
- Azure 2019 VM workload trace
- file: `vmtable.csv.gz`

The design requirement was:
- use Azure data only for task generation
- keep solar model unchanged
- keep carbon model unchanged
- keep all schedulers unchanged
- keep benchmark chart logic unchanged
- add a safe fallback to synthetic generation if the dataset is missing or invalid

## 3. Dataset File Used

The correct dataset file used for this integration is:

- `vmtable.csv.gz`

Dataset source path from Azure's public link manifest:

- `https://azurepublicdatasettraces.blob.core.windows.net/azurepublicdatasetv2/trace_data/vmtable/vmtable.csv.gz`

Important note:
- The downloaded `AzurePublicDatasetLinksV2.txt` file was not the dataset itself.
- It was only a list of URLs.
- The actual usable file for this project is `vmtable.csv.gz`.

## 4. What We Expected vs What We Actually Found

### What we initially expected

Based on the Azure V2 documentation, we expected the file to contain named columns such as:
- `vm_id`
- `subscription_id`
- `deployment_id`
- `timestamp_vm_created`
- `timestamp_vm_deleted`
- `max_cpu`
- `avg_cpu`
- `p95_max_cpu`
- `vm_category`

### What we actually found

When the real `vmtable.csv.gz` file was inspected locally, the first attempt failed with:
- schema mismatch
- no visible timestamp column names

After checking the file directly, it turned out that:
- the file is effectively headerless
- pandas initially treated the first data row as column names
- the real file has 11 positional columns

The first few rows showed data like:
- VM identifiers
- subscription identifiers
- deployment identifiers
- creation time
- deletion time
- CPU stats
- category
- core count
- memory

So the key discovery today was:
- the Azure V2 `vmtable.csv.gz` being used here does not behave like a normal headered CSV
- the loader needed to support that format explicitly

## 5. Exact Files Changed Today

Only two files were modified:

- [phase3_tasks.py](/c:/Users/Dhimant/Downloads/cloud_impl/cloud-computing/phase3_tasks.py:1)
- [benchmark.py](/c:/Users/Dhimant/Downloads/cloud_impl/cloud-computing/benchmark.py:1)

No changes were made to:
- `phase1_models.py`
- `phase2_energy_model.py`
- `phase4_dp_scheduler.py`
- `phase5_agent.py`
- `battery_model.py`

## 6. Detailed Changes in `phase3_tasks.py`

Today's work in `phase3_tasks.py` had four big parts:

1. Preserve the old synthetic behavior
2. Add Azure task loading
3. Add preprocessing and schema handling
4. Extend workload reporting

### 6.1 Preserving the old synthetic generator

The original synthetic behavior was moved into a helper:
- `_make_synthetic_tasks()`

Why this was done:
- to keep the old logic intact
- to let `generate_tasks()` switch between:
  - Azure-backed generation
  - synthetic fallback

This means the project still works even if the dataset is missing.

### 6.2 New helper constants added

New constants were introduced:
- `SECONDS_PER_DAY = 86400`
- `SECONDS_PER_SLOT = 900`
- `AZURE_TASK_ID_PREFIX = "AZ-"`
- `PADDED_TASK_ID_PREFIX = "PAD-"`

Why:
- `SECONDS_PER_DAY` is needed for modulo normalization into one 24-hour simulated day
- `SECONDS_PER_SLOT` is needed because each slot is 15 minutes = 900 seconds
- task ID prefixes help distinguish:
  - true Azure-derived tasks
  - synthetic padding tasks

### 6.3 New Azure schema support structures

Two structures were added:

1. `AZURE_COLUMN_ALIASES`
2. `AZURE_V2_HEADERLESS_COLUMNS`

#### `AZURE_COLUMN_ALIASES`

This supports alternate names for key fields, such as:
- `vm_id`
- `timestamp_vm_created`
- `timestamp_vm_deleted`
- `vm_category`
- `core_count`
- `max_cpu`
- `avg_cpu`
- `p95_max_cpu`

Why:
- Azure trace versions and exports are not always named identically
- this makes the loader more robust

#### `AZURE_V2_HEADERLESS_COLUMNS`

This was added specifically because the real file turned out to be headerless.

The 11 columns are now interpreted in this exact order:

1. `vm_id`
2. `subscription_id`
3. `deployment_id`
4. `timestamp_vm_created`
5. `timestamp_vm_deleted`
6. `max_cpu`
7. `avg_cpu`
8. `p95_max_cpu`
9. `vm_category`
10. `core_count`
11. `memory_gb`

Why:
- without assigning these names manually, the loader could not find the creation/deletion timestamps
- that was the exact reason the first Azure benchmark attempt fell back to synthetic tasks

### 6.4 New helper functions added

Several new helper functions were added.

#### `_find_column(columns, aliases)`

Purpose:
- find the real column name from a list of possible aliases

Why:
- to support mild schema variation without rewriting the loader

#### `_clamp_slot(slot)`

Purpose:
- keep slot values within `0..95`

Why:
- the project uses exactly 96 slots
- deadlines must not exceed slot 95

#### `_normalize_arrival_slot(timestamp_seconds)`

Purpose:
- convert a raw Unix timestamp into a project slot

How it works:
- `timestamp % 86400`
- then divide by `900`
- then clamp into `0..95`

Why this matters:
- Azure timestamps span long real-world periods
- the simulator is only one 24-hour day
- modulo folding was necessary to map the dataset into the project time model

This is one of the most important changes made today.

#### `_priority_from_value(value, rng)`

Purpose:
- map Azure category/priority information into project priorities:
  - `critical`
  - `high`
  - `normal`

How it works:
- if numeric:
  - `0 -> critical`
  - `1 -> high`
  - `2 -> normal`
- if textual:
  - values such as `interactive`, `latency-sensitive` are treated as more urgent
  - values such as `batch`, `delay-insensitive` are treated as less urgent
- if the value is unclear:
  - fallback random weighting preserves the project's rough 10/30/60 distribution

Why:
- Azure V2 files do not always expose an explicit scheduler-style priority field in the same way the project expects
- `vm_category` was therefore used as a semantic proxy when needed

#### `_scale_load_from_row(...)`

Purpose:
- convert Azure CPU/core information into the project's `load` field on a 1..10 scale

How it works:

Primary path:
- use `core_count` if present
- scale toward the 1..10 range
- large counts saturate near 10

Fallback path:
- if `core_count` is not usable, use:
  - `max_cpu`
  - `avg_cpu`
  - `p95_max_cpu`
- take the strongest available CPU signal
- normalize from roughly 0..100 into 1..10

Why:
- the project's schedulers expect a single compact integer `load`
- Azure provides richer operational fields that needed to be reduced into that abstraction

### 6.5 New function `load_azure_tasks(filepath, n=100, seed=42)`

This is the main Azure integration function added today.

It does the following:

1. Validates that the file exists
2. Reads a one-row preview
3. Detects whether the file is:
   - headered
   - or headerless Azure V2
4. Chooses the correct `pandas.read_csv()` settings
5. Reads the file in chunks of `10000`
6. Stops as soon as enough valid tasks are collected
7. Filters bad rows
8. Maps Azure fields into `Task` objects
9. Sorts tasks by `arrival_slot`
10. Pads with synthetic tasks if not enough valid Azure rows were found

This directly satisfies the requirement to avoid loading the entire giant file into memory.

### 6.6 Filtering and validation rules used

Rows are skipped if:
- required timestamp fields are missing
- lifetime is zero or negative
- load is invalid
- deadline calculation becomes invalid

Required fields for mapping:
- creation timestamp
- deletion timestamp
- CPU/core signal if available

Why:
- these fields are essential for building valid `Task` objects

### 6.7 Exact Azure-to-Task mapping used

Here is the real mapping implemented today.

#### `Task.id`

Source:
- Azure `vm_id`

Mapping:
- `AZ-<vm_id>`

Why:
- preserves trace identity
- makes it easy to recognize Azure-derived tasks in reports and debug output

#### `Task.arrival_slot`

Source:
- `timestamp_vm_created`

Mapping:
- `timestamp_vm_created % 86400`
- then integer divide by `900`
- clamp into `0..95`

Why:
- folds many real-world days into one simulated day

#### `Task.deadline`

Source:
- `timestamp_vm_deleted - timestamp_vm_created`

Mapping:
- convert lifetime seconds into slot count by dividing by `900`
- `deadline = arrival_slot + lifetime_slots`
- cap at slot `95`

Why:
- the project models deadlines as slot indices rather than raw timestamps

#### `Task.priority`

Source:
- `priority` if available
- otherwise `vm_category`

Mapping:
- numeric or textual mapping into:
  - `critical`
  - `high`
  - `normal`

Why:
- project schedulers already expect these three labels

#### `Task.load`

Source:
- `core_count`
- fallback to CPU-related columns if needed

Mapping:
- scaled into `1..10`

Why:
- keeps compatibility with the rest of the scheduler pipeline

#### `Task.energy_cost`

Source:
- derived from `load`

Mapping:
- `round(load * random(0.8, 1.5))`
- clamp into `1..20`

Why:
- the project still expects a compact energy estimate
- this keeps the original project design, while grounding task timing and size in real Azure data

### 6.8 Synthetic padding support

If fewer than `n` valid Azure tasks are found quickly, the loader pads the result using synthetic tasks.

These tasks get IDs like:
- `PAD-00001`

Why:
- guarantees the schedulers always receive exactly `n` tasks
- avoids breaking the benchmark

This also supports the reporting fields:
- `azure_tasks`
- `synthetic_padded`
- `synthetic_tasks`

### 6.9 Changes to `generate_tasks()`

`generate_tasks()` was extended with:
- `use_azure: bool = False`
- `azure_filepath: Optional[str] = None`

Behavior now:
- if `use_azure=False`
  - run synthetic generation exactly as before
- if `use_azure=True`
  - attempt Azure loading
  - if loading fails, print warning and fall back to synthetic generation

Why:
- default behavior remains safe
- Azure mode is optional
- the benchmark and project do not break when the dataset is absent

### 6.10 Changes to `describe_workload()`

This function was extended to report source information:
- `azure_tasks`
- `synthetic_padded`
- `synthetic_tasks`

It already reported:
- total tasks
- priority counts
- average slack
- total energy
- morning / afternoon / night distribution
- arrival range

Why:
- this makes it easy to confirm whether a run is truly dataset-backed

## 7. Detailed Changes in `benchmark.py`

Today's changes in `benchmark.py` were about making Azure-backed runs easy to trigger without affecting the benchmark behavior itself.

### 7.1 Added CLI argument parsing

New command-line arguments:
- `--tasks`
- `--seed`
- `--cloudy`
- `--azure`
- `--azure-path`

Why:
- the original benchmark always used synthetic tasks
- now Azure mode can be switched on explicitly

### 7.2 Updated `run_all()`

`run_all()` now passes through:
- `use_azure`
- `azure_filepath`

It still:
- creates one workload
- runs all schedulers on fresh task copies
- prints summaries
- returns results for chart generation

### 7.3 Updated `run_benchmark()`

The benchmark header now shows:
- task count
- seed
- cloudy mode
- source type:
  - synthetic
  - Azure vmtable
- dataset path when Azure mode is enabled

Why:
- makes each run self-describing

### 7.4 Preserved chart logic

Even though `benchmark.py` was edited, the chart generation behavior was intentionally preserved:
- same 4 output charts
- same chart functions
- same basic result aggregation pattern

This means the benchmark output format stays familiar while only the workload source changes.

## 8. Real Integration Problem Encountered Today

The most important issue encountered today was:

- the real `vmtable.csv.gz` file did not match the assumed headered schema

### What happened

When the Azure benchmark was first run, the loader failed with:
- creation/deletion timestamp columns not found

That caused:
- warning message
- fallback to synthetic workload

### How it was debugged

The file header was inspected directly.

The result showed:
- the first row of actual data had been interpreted as column names
- the file had no usable header row

The first few rows were then read with `header=None`, confirming:
- 11 real positional columns

### How it was fixed

A preview step was added:
- read one row first
- detect whether expected named columns are present
- if not, and there are exactly 11 columns, assume Azure V2 headerless layout
- assign `AZURE_V2_HEADERLESS_COLUMNS`
- then continue with chunked reading

This fix is what made the real Azure benchmark run successfully.

## 9. Verification and Testing Done Today

Several checks were done after the implementation.

### 9.1 Syntax validation

Ran:

```powershell
python -m py_compile phase3_tasks.py benchmark.py
```

Purpose:
- confirm that the modified files compile correctly

### 9.2 Synthetic-mode sanity test

Ran:

```powershell
python benchmark.py --tasks 10 --seed 42
```

Purpose:
- confirm that the benchmark still works with synthetic tasks
- confirm that nothing else in the project broke

### 9.3 Dataset header inspection

The real Azure file was inspected using pandas, which revealed the headerless schema behavior.

Purpose:
- diagnose the initial schema mismatch

### 9.4 Azure-backed benchmark test

Ran successfully:

```powershell
python benchmark.py --azure --azure-path vmtable.csv.gz --tasks 100 --seed 42
```

Observed result:
- `Loaded 100 Azure tasks from vmtable.csv.gz`
- `azure_tasks: 100`
- `synthetic_padded: 0`

This confirmed:
- the Azure path is working
- no fallback occurred
- the benchmark is now using real dataset-backed task generation

## 10. Final Azure-Backed Benchmark Snapshot From Today

Successful Azure-backed run:

- command:

```powershell
python benchmark.py --azure --azure-path vmtable.csv.gz --tasks 100 --seed 42
```

Workload summary:
- total tasks: 100
- priority counts:
  - critical: 14
  - high: 27
  - normal: 59
- average slack: 16.64
- total energy: 107
- morning tasks: 25
- afternoon tasks: 18
- night tasks: 57
- arrival range: 0 to 93
- Azure tasks: 100
- synthetic padded: 0

Scheduler results:
- RoundRobin: `3358.5 gCO2`
- GreedyEDF: `3358.5 gCO2`
- DPScheduler: `3169.4 gCO2`
- AgenticDP: `3195.4 gCO2`
- BatteryAwareDP: `2293.5 gCO2`

Interpretation:
- the project is now successfully running on a real Azure workload source
- battery-aware scheduling performed best on carbon in this specific Azure-backed run

## 11. What Was Not Changed Today

The following parts of the project were intentionally not modified:

- `Task` dataclass
- `Server` dataclass
- solar energy logic
- carbon intensity logic
- all scheduler implementations in phases 4 and 5
- battery scheduler implementation
- benchmark chart-generation behavior

This was important because today's task was specifically about replacing the workload source, not redesigning the scheduling algorithms.

## 12. Current Project Behavior After Today's Work

As of 2026-05-16, the project now supports two workload modes:

### Synthetic mode

Default behavior:

```powershell
python benchmark.py --tasks 100 --seed 42
```

This behaves like the old project.

### Azure mode

Dataset-backed behavior:

```powershell
python benchmark.py --azure --azure-path vmtable.csv.gz --tasks 100 --seed 42
```

This uses Azure trace data for task generation while keeping the rest of the project unchanged.

## 13. Important Implementation Caveats

There are a few things to understand clearly about today's integration.

### The dataset is real, but the project abstraction is still simplified

The project still expects:
- one compact `load`
- one compact `energy_cost`
- one discrete `priority`
- one deadline slot

Azure gives richer operational data, so some translation was necessary.

### Priority is only partly native

If the dataset does not expose a clean scheduler-style priority column, we infer priority from:
- category labels
- or fallback weighted mapping

So the timing is real, but the urgency class is still partially derived.

### Energy cost is still modeled

The project still computes `energy_cost` rather than reading it directly from Azure.

So after today's work:
- arrival timing is Azure-based
- lifetime/deadline is Azure-based
- VM identity is Azure-based
- CPU/resource sizing is Azure-based
- energy cost remains a project-level derived feature

## 14. Summary of Today's Contribution

In plain language, today's work did the following:

- replaced the workload input path from purely random generation to optional Azure-based generation
- kept the rest of the project architecture unchanged
- added a robust Azure loader that can handle a large file without loading all of it
- added fallback behavior so the project never becomes unusable
- discovered and fixed a real schema problem in the downloaded Azure file
- verified the implementation with a successful benchmark run using `vmtable.csv.gz`

## 15. Short Readable Summary

Before today, this project scheduled synthetic cloud tasks. Today, Azure VM trace data from the 2019 public Azure dataset was integrated into the workload generator so that tasks can now be built from real cloud trace records. The key new function is `load_azure_tasks()`, which reads `vmtable.csv.gz` in chunks, normalizes real timestamps into the project's 96-slot day, converts VM lifetimes into deadlines, maps category or priority information into the project's three priority levels, scales core/CPU information into the project's `load` field, derives `energy_cost`, and returns scheduler-compatible `Task` objects. During implementation, the real Azure V2 file turned out to be headerless, which caused an initial schema mismatch; this was solved by adding automatic detection and a fixed 11-column Azure V2 schema mapping. The benchmark now supports `--azure` and `--azure-path`, and the project has been verified to run successfully on real Azure tasks without modifying the solar model, carbon model, or scheduler implementations.
