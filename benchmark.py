"""
Phase 6: Benchmark Runner

Runs all schedulers on the same workload and produces comparative charts.
Outputs 4 matplotlib figures to the outputs/ directory.
"""

import os
import copy
import math
import random

import matplotlib
matplotlib.use("Agg")   # non-interactive backend for server/CI use
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np

from phase1_models import Task, Server, make_cluster
from phase2_energy_model import (
    SLOTS_PER_DAY, build_energy_profile, carbon_intensity,
    energy_at_slot, slot_to_time, carbon_array, energy_array
)
from phase3_tasks import generate_tasks, describe_workload, ScheduleResult
from phase3_tasks import RoundRobinScheduler, GreedyEDFScheduler
from phase4_dp_scheduler import DPScheduler, MAX_ENERGY_BUDGET
from phase5_agent import AgenticDPScheduler
from battery_model import BatteryStorage, BatteryAwareDPScheduler


# ── Output directory ──────────────────────────────────────────────────────────
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ── Colour palette ────────────────────────────────────────────────────────────
COLORS = {
    "RoundRobin":   "#e74c3c",
    "GreedyEDF":    "#e67e22",
    "DPScheduler":  "#3498db",
    "AgenticDP":    "#2ecc71",
    "BatteryAwareDP": "#9b59b6",
}

STYLE = {
    "figure.facecolor": "#1a1a2e",
    "axes.facecolor":   "#16213e",
    "axes.edgecolor":   "#0f3460",
    "axes.labelcolor":  "#e0e0e0",
    "xtick.color":      "#e0e0e0",
    "ytick.color":      "#e0e0e0",
    "text.color":       "#e0e0e0",
    "grid.color":       "#0f3460",
    "legend.facecolor": "#16213e",
    "legend.edgecolor": "#0f3460",
}


def apply_style():
    for k, v in STYLE.items():
        plt.rcParams[k] = v
    plt.rcParams["font.family"] = "DejaVu Sans"


# ── Run all schedulers ────────────────────────────────────────────────────────

def run_all(n_tasks: int = 100, seed: int = 42, cloudy: bool = False):
    """Run all schedulers on an identical workload and return results dict."""
    tasks   = generate_tasks(n=n_tasks, seed=seed, cloudy=cloudy)
    servers = make_cluster(5)

    schedulers = [
        RoundRobinScheduler(cloudy=cloudy),
        GreedyEDFScheduler(cloudy=cloudy),
        DPScheduler(cloudy=cloudy),
        AgenticDPScheduler(cloudy=cloudy),
        BatteryAwareDPScheduler(
            battery=BatteryStorage(capacity=200, max_charge_rate=25, max_discharge_rate=25),
            cloudy=cloudy,
        ),
    ]

    results = {}
    for sched in schedulers:
        # Give each scheduler a fresh copy of tasks (reset assigned fields)
        fresh_tasks = [copy.deepcopy(t) for t in tasks]
        fresh_tasks = [_reset_task(t) for t in fresh_tasks]
        res = sched.run(fresh_tasks, copy.deepcopy(servers))
        results[res.scheduler_name] = res
        print(res.summary())

    return results, tasks, describe_workload(tasks)


def _reset_task(task: Task) -> Task:
    task.assigned_slot   = None
    task.assigned_server = None
    task.latency_ms      = None
    task.met_deadline    = None
    return task


# ── Chart 1: Solar Energy Curve + Carbon Intensity ───────────────────────────

def chart_energy_profile(cloudy: bool = False, save: bool = True) -> str:
    apply_style()
    slots  = list(range(SLOTS_PER_DAY))
    energy = build_energy_profile(cloudy)
    ci     = [carbon_intensity(s, cloudy) for s in slots]
    times  = [slot_to_time(s) for s in slots]

    fig, ax1 = plt.subplots(figsize=(12, 5))
    ax2 = ax1.twinx()

    ax1.fill_between(slots, energy, alpha=0.35, color="#f9ca24", label="Solar Energy")
    ax1.plot(slots, energy, color="#f9ca24", lw=2)
    ax2.plot(slots, ci, color="#e74c3c", lw=1.8, linestyle="--", label="Carbon Intensity")

    ax1.set_xlabel("Time of Day")
    ax1.set_ylabel("Solar Energy (units)", color="#f9ca24")
    ax2.set_ylabel("Carbon Intensity (gCO₂/unit)", color="#e74c3c")

    tick_slots = list(range(0, SLOTS_PER_DAY, 8))
    ax1.set_xticks(tick_slots)
    ax1.set_xticklabels([slot_to_time(s) for s in tick_slots], rotation=45, ha="right")

    title = f"Solar Energy Profile {'(Cloudy)' if cloudy else '(Clear Day)'}"
    ax1.set_title(title, fontsize=14, pad=12)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")
    ax1.grid(True, alpha=0.3)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "chart1_energy_profile.png")
    if save:
        fig.savefig(path, dpi=150, bbox_inches="tight")
        print(f"Saved: {path}")
    plt.close(fig)
    return path


# ── Chart 2: Total Carbon by Scheduler ───────────────────────────────────────

def chart_carbon_comparison(results: dict, save: bool = True) -> str:
    apply_style()
    names   = list(results.keys())
    carbons = [results[n].total_carbon_g for n in names]
    colors  = [COLORS.get(n, "#7f8c8d") for n in names]

    # Baseline = RoundRobin carbon
    baseline = carbons[0] if carbons else 1

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_xticks(range(len(names)))
    bars = ax.bar(names, carbons, color=colors, edgecolor="#0f3460", linewidth=1.2, width=0.6)

    for bar, carbon, name in zip(bars, carbons, names):
        reduction = 100 * (baseline - carbon) / max(baseline, 1)
        label = f"{carbon:.0f} gCO₂"
        if reduction > 0:
            label += f"\n(-{reduction:.1f}%)"
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 5,
            label,
            ha="center", va="bottom", fontsize=9, color="#e0e0e0"
        )

    ax.set_ylabel("Total Carbon Emissions (gCO₂)")
    ax.set_title("Carbon Emissions by Scheduler", fontsize=14, pad=12)
    ax.set_xticklabels(names, rotation=15, ha="right")
    ax.grid(True, axis="y", alpha=0.3)
    ax.set_ylim(0, max(carbons) * 1.25)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "chart2_carbon_comparison.png")
    if save:
        fig.savefig(path, dpi=150, bbox_inches="tight")
        print(f"Saved: {path}")
    plt.close(fig)
    return path


# ── Chart 3: Task Distribution Across Time Periods ────────────────────────────

def chart_task_distribution(results: dict, save: bool = True) -> str:
    apply_style()
    names   = list(results.keys())
    periods = ["Night\n(00-06)", "Morning\n(06-12)", "Afternoon\n(12-18)", "Evening\n(18-24)"]
    period_slots = [(0, 24), (24, 48), (48, 72), (72, 96)]

    data = {}
    for name, res in results.items():
        counts = []
        for start, end in period_slots:
            c = sum(1 for slot, _ in res.schedule_pairs if start <= slot < end)
            counts.append(c)
        data[name] = counts

    x     = np.arange(len(periods))
    width = 0.15
    fig, ax = plt.subplots(figsize=(12, 6))

    for i, name in enumerate(names):
        offset = (i - len(names) / 2 + 0.5) * width
        bars = ax.bar(x + offset, data[name], width=width,
                      label=name, color=COLORS.get(name, "#7f8c8d"),
                      edgecolor="#0f3460", linewidth=0.8)

    ax.set_xticks(x)
    ax.set_xticklabels(periods)
    ax.set_ylabel("Tasks Scheduled")
    ax.set_title("Task Distribution Across Time Periods", fontsize=14, pad=12)
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, axis="y", alpha=0.3)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "chart3_task_distribution.png")
    if save:
        fig.savefig(path, dpi=150, bbox_inches="tight")
        print(f"Saved: {path}")
    plt.close(fig)
    return path


# ── Chart 4: Latency vs Carbon Scatter ───────────────────────────────────────

def chart_latency_vs_carbon(results: dict, save: bool = True) -> str:
    apply_style()
    fig, ax = plt.subplots(figsize=(9, 6))

    for name, res in results.items():
        ax.scatter(
            res.avg_latency_ms,
            res.total_carbon_g,
            s=180,
            color=COLORS.get(name, "#7f8c8d"),
            label=name,
            edgecolors="white",
            linewidths=1.2,
            zorder=5,
        )
        ax.annotate(
            name,
            (res.avg_latency_ms, res.total_carbon_g),
            textcoords="offset points",
            xytext=(8, 4),
            fontsize=8,
            color="#e0e0e0",
        )

    ax.set_xlabel("Average Latency (ms)")
    ax.set_ylabel("Total Carbon Emissions (gCO₂)")
    ax.set_title("Latency vs Carbon Trade-off", fontsize=14, pad=12)
    ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, "chart4_latency_vs_carbon.png")
    if save:
        fig.savefig(path, dpi=150, bbox_inches="tight")
        print(f"Saved: {path}")
    plt.close(fig)
    return path


# ── Summary table ─────────────────────────────────────────────────────────────

def print_summary_table(results: dict, workload_info: dict):
    print("\n" + "=" * 90)
    print(f"{'Scheduler':<20} {'Carbon(gCO2)':>12} {'Tasks':>8} {'DeadMet':>8} "
          f"{'Solar':>8} {'Grid':>8} {'AvgLat(ms)':>12}")
    print("-" * 90)
    for name, res in results.items():
        print(f"{name:<20} {res.total_carbon_g:>12.1f} {res.tasks_scheduled:>8} "
              f"{res.deadline_met:>8} {res.solar_tasks:>8} {res.grid_tasks:>8} "
              f"{res.avg_latency_ms:>12.1f}")
    print("=" * 90)

    # Carbon savings vs RoundRobin baseline
    if "RoundRobin" in results:
        baseline = results["RoundRobin"].total_carbon_g
        print("\nCarbon savings vs RoundRobin baseline:")
        for name, res in results.items():
            saving_g   = baseline - res.total_carbon_g
            saving_pct = 100 * saving_g / max(baseline, 1)
            kg_saved   = saving_g / 1000.0
            print(f"  {name:<20}: {saving_g:>+8.1f} gCO2 ({saving_pct:+.1f}%) = {kg_saved:.3f} kg CO2")
    print()


# ── Main entry point ──────────────────────────────────────────────────────────

def run_benchmark(n_tasks: int = 100, seed: int = 42, cloudy: bool = False):
    print(f"\n{'='*60}")
    print(f"  Carbon-Aware Cloud Scheduler Benchmark")
    print(f"  Tasks={n_tasks}, Seed={seed}, Cloudy={cloudy}")
    print(f"{'='*60}\n")

    results, tasks, workload = run_all(n_tasks=n_tasks, seed=seed, cloudy=cloudy)
    print_summary_table(results, workload)

    print("Generating charts...")
    p1 = chart_energy_profile(cloudy=cloudy)
    p2 = chart_carbon_comparison(results)
    p3 = chart_task_distribution(results)
    p4 = chart_latency_vs_carbon(results)

    print(f"\nAll charts saved to: {OUTPUT_DIR}")
    return results, [p1, p2, p3, p4]


if __name__ == "__main__":
    run_benchmark(n_tasks=100, seed=42, cloudy=False)
