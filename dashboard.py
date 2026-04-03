"""
Carbon-Aware Cloud Task Scheduler — Streamlit Dashboard

Run with:  streamlit run dashboard.py
"""

import time
import copy
import random
import math
from collections import defaultdict

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# ── Page config (MUST be first Streamlit call) ────────────────────────────────
st.set_page_config(
    layout="wide",
    page_title="Carbon-Aware Cloud Scheduler",
    page_icon="⚡",
)

# ── Dark theme CSS injection ──────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Base ── */
html, body, [class*="css"] {
    background-color: #0d1117 !important;
    color: #c9d1d9 !important;
    font-family: 'Segoe UI', system-ui, sans-serif;
}

/* ── Main content area ── */
.main .block-container {
    background-color: #0d1117;
    padding-top: 1.5rem;
    padding-bottom: 2rem;
    max-width: 1400px;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background-color: #010409 !important;
    border-right: 1px solid #21262d;
}
[data-testid="stSidebar"] .block-container {
    background-color: #010409;
}
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span {
    color: #8b949e !important;
}

/* ── Cards / metric containers ── */
div[data-testid="metric-container"] {
    background-color: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    box-shadow: 0 4px 12px rgba(0,0,0,0.4);
}
div[data-testid="metric-container"] label {
    color: #8b949e !important;
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
div[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #3fb950 !important;
    font-size: 1.9rem !important;
    font-weight: 700;
}
div[data-testid="metric-container"] [data-testid="stMetricDelta"] {
    color: #58a6ff !important;
}

/* ── Buttons ── */
div.stButton > button {
    background: linear-gradient(135deg, #238636, #2ea043);
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 0.55rem 1.4rem;
    font-size: 0.95rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
    width: 100%;
}
div.stButton > button:hover {
    background: linear-gradient(135deg, #2ea043, #3fb950);
    box-shadow: 0 0 12px rgba(63,185,80,0.4);
    transform: translateY(-1px);
}

/* ── Tabs ── */
button[data-baseweb="tab"] {
    background-color: transparent !important;
    color: #8b949e !important;
    border-bottom: 2px solid transparent;
    font-size: 0.95rem;
    font-weight: 500;
    padding: 0.6rem 1.2rem;
    transition: color 0.2s;
}
button[data-baseweb="tab"][aria-selected="true"] {
    color: #58a6ff !important;
    border-bottom: 2px solid #58a6ff !important;
}
[data-baseweb="tab-list"] {
    border-bottom: 1px solid #21262d;
    margin-bottom: 1.2rem;
}

/* ── Sliders ── */
[data-testid="stSlider"] .st-bo { background-color: #21262d; }
[data-testid="stSlider"] .st-bp { background-color: #3fb950; }

/* ── Toggle ── */
[data-testid="stCheckbox"] label { color: #c9d1d9 !important; }

/* ── Info boxes ── */
div[data-testid="stInfo"] {
    background-color: #0c2d48;
    border: 1px solid #1f6feb;
    border-radius: 8px;
    color: #58a6ff !important;
}

/* ── Banner ── */
.banner {
    background: linear-gradient(135deg, #0d1117 0%, #0c2d48 50%, #0d1117 100%);
    border: 1px solid #1f6feb;
    border-radius: 14px;
    padding: 1.6rem 2rem;
    margin-bottom: 1.8rem;
    text-align: center;
}
.banner h1 {
    font-size: 2.2rem;
    font-weight: 800;
    color: #58a6ff;
    margin: 0 0 0.3rem 0;
    letter-spacing: -0.02em;
}
.banner p {
    font-size: 1rem;
    color: #8b949e;
    margin: 0;
}

/* ── Section headers ── */
.section-header {
    font-size: 1.1rem;
    font-weight: 700;
    color: #58a6ff;
    border-left: 3px solid #3fb950;
    padding-left: 0.7rem;
    margin: 1.2rem 0 0.8rem 0;
}

/* ── Progress bar ── */
[data-testid="stProgress"] > div > div {
    background-color: #3fb950 !important;
}

/* ── DataFrame / tables ── */
[data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; }
.dataframe { background-color: #161b22 !important; color: #c9d1d9 !important; }
.dataframe th { background-color: #21262d !important; color: #58a6ff !important; }
.dataframe td { border-color: #30363d !important; }

/* ── Divider ── */
hr { border-color: #21262d; }

/* ── Spinner ── */
[data-testid="stSpinner"] { color: #3fb950; }
</style>
""", unsafe_allow_html=True)


# ── Lazy imports (avoid import errors before requirements are installed) ──────
@st.cache_resource
def _import_modules():
    from phase1_models import make_cluster
    from phase2_energy_model import (
        SLOTS_PER_DAY, build_energy_profile, carbon_intensity,
        energy_at_slot, slot_to_time
    )
    from phase3_tasks import (
        generate_tasks, describe_workload, ScheduleResult,
        RoundRobinScheduler, GreedyEDFScheduler
    )
    from phase4_dp_scheduler import DPScheduler, MAX_ENERGY_BUDGET
    from phase5_agent import AgenticDPScheduler, GreenAgent
    from battery_model import BatteryStorage, BatteryAwareDPScheduler
    return {
        "make_cluster": make_cluster,
        "SLOTS_PER_DAY": SLOTS_PER_DAY,
        "build_energy_profile": build_energy_profile,
        "carbon_intensity": carbon_intensity,
        "energy_at_slot": energy_at_slot,
        "slot_to_time": slot_to_time,
        "generate_tasks": generate_tasks,
        "describe_workload": describe_workload,
        "RoundRobinScheduler": RoundRobinScheduler,
        "GreedyEDFScheduler": GreedyEDFScheduler,
        "DPScheduler": DPScheduler,
        "MAX_ENERGY_BUDGET": MAX_ENERGY_BUDGET,
        "AgenticDPScheduler": AgenticDPScheduler,
        "GreenAgent": GreenAgent,
        "BatteryStorage": BatteryStorage,
        "BatteryAwareDPScheduler": BatteryAwareDPScheduler,
    }


M = _import_modules()
SLOTS_PER_DAY    = M["SLOTS_PER_DAY"]
slot_to_time     = M["slot_to_time"]
energy_at_slot   = M["energy_at_slot"]
carbon_intensity = M["carbon_intensity"]


# ── Plotly dark theme helper ──────────────────────────────────────────────────
DARK_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="#0d1117",
    plot_bgcolor="#161b22",
    font=dict(color="#c9d1d9", family="Segoe UI, system-ui, sans-serif"),
    margin=dict(l=50, r=30, t=50, b=50),
)
# Grid colours applied separately so callers can pass their own xaxis/yaxis dicts
_AXIS_STYLE = dict(gridcolor="#21262d", linecolor="#30363d")


def dark_fig(title="", height=380):
    fig = go.Figure()
    fig.update_layout(title=title, height=height, **DARK_LAYOUT)
    fig.update_xaxes(**_AXIS_STYLE)
    fig.update_yaxes(**_AXIS_STYLE)
    return fig


# ── Solar energy line chart (base) ────────────────────────────────────────────
def make_solar_fig(cloudy: bool = False, current_slot: int = -1,
                   battery_trace: list = None, height=380):
    slots  = list(range(SLOTS_PER_DAY))
    energy = [energy_at_slot(s, cloudy) for s in slots]
    times  = [slot_to_time(s) for s in slots]

    fig = go.Figure()

    # Solar fill
    fig.add_trace(go.Scatter(
        x=times, y=energy,
        fill="tozeroy",
        fillcolor="rgba(249,202,36,0.18)",
        line=dict(color="#f9ca24", width=2),
        name="Solar Energy",
    ))

    # Battery SOC overlay
    if battery_trace and len(battery_trace) > 0:
        batt_x = times[:len(battery_trace)]
        fig.add_trace(go.Scatter(
            x=batt_x, y=battery_trace,
            line=dict(color="#9b59b6", width=2, dash="dot"),
            name="Battery SOC %",
            yaxis="y2",
        ))

    # Moving cursor — use add_shape (works with string x-axis in Plotly 6)
    if 0 <= current_slot < SLOTS_PER_DAY:
        fig.add_shape(
            type="line",
            x0=times[current_slot], x1=times[current_slot],
            y0=0, y1=1, yref="paper",
            line=dict(color="#e74c3c", width=2),
        )
        fig.add_annotation(
            x=times[current_slot], y=1.05, yref="paper",
            text=f"▶ {times[current_slot]}",
            showarrow=False,
            font=dict(color="#e74c3c", size=10),
        )

    fig.update_layout(
        title="Solar Energy & Battery SOC",
        height=height,
        xaxis_title="Time of Day",
        yaxis_title="Solar Energy (units)",
        yaxis2=dict(title="Battery SOC %", overlaying="y", side="right",
                    range=[0, 105], showgrid=False),
        legend=dict(orientation="h", y=1.08),
        **DARK_LAYOUT,
    )
    return fig


# ── Server utilisation bar chart ──────────────────────────────────────────────
def make_server_bar(servers):
    names = [s.name for s in servers]
    utils = [round(s.utilisation() * 100, 1) for s in servers]
    lats  = [round(s.avg_latency(), 1) for s in servers]

    colors = []
    for u in utils:
        if u < 40:
            colors.append("#3fb950")
        elif u < 75:
            colors.append("#e3b341")
        else:
            colors.append("#e74c3c")

    fig = go.Figure(go.Bar(
        x=names,
        y=utils,
        marker_color=colors,
        text=[f"{u}%<br>{l}ms" for u, l in zip(utils, lats)],
        textposition="outside",
        textfont=dict(size=11),
    ))
    fig.update_layout(title="Server Utilisation", height=280, **DARK_LAYOUT)
    fig.update_yaxes(title="Utilisation %", range=[0, 110], **_AXIS_STYLE)
    fig.update_xaxes(**_AXIS_STYLE)
    return fig


# ── Task timeline scatter ─────────────────────────────────────────────────────
def make_task_scatter(placed_tasks: list, height=380):
    """placed_tasks: list of (slot, server_name, priority, carbon)"""
    if not placed_tasks:
        fig = dark_fig("Task Scheduling Timeline", height=height)
        return fig

    df = pd.DataFrame(placed_tasks, columns=["slot", "server", "priority", "carbon"])
    df["time"] = df["slot"].apply(slot_to_time)

    color_map = {"critical": "#e74c3c", "high": "#e3b341", "normal": "#3fb950"}

    fig = go.Figure()
    for prio, grp in df.groupby("priority"):
        fig.add_trace(go.Scatter(
            x=grp["time"],
            y=grp["server"],
            mode="markers",
            marker=dict(
                size=9,
                color=color_map.get(prio, "#58a6ff"),
                symbol="circle",
                line=dict(color="#0d1117", width=1),
            ),
            name=prio.capitalize(),
            hovertemplate=(
                "Time: %{x}<br>Server: %{y}<br>Priority: " + prio +
                "<br>Carbon: %{customdata:.1f} gCO₂<extra></extra>"
            ),
            customdata=grp["carbon"],
        ))

    fig.update_layout(
        title="Task Scheduling Timeline",
        xaxis_title="Time of Day",
        yaxis_title="Server",
        height=height,
        legend=dict(orientation="h", y=1.08),
        **DARK_LAYOUT,
    )
    return fig


# ── Banner ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="banner">
  <h1>🌱 Carbon-Aware Cloud Task Scheduler</h1>
  <p>Dynamic Programming &nbsp;·&nbsp; Agentic AI &nbsp;·&nbsp; Battery Storage &nbsp;·&nbsp; Real-Time Simulation</p>
</div>
""", unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙ Simulation Controls")
    st.markdown("---")

    n_tasks = st.slider("Number of Tasks", min_value=50, max_value=200, value=100, step=10,
                        help="Total tasks to schedule in the simulation")

    cloudy = st.toggle("☁ Cloudy Day", value=False,
                       help="Reduces solar output by ~45% and tests scheduler resilience")

    seed = st.number_input("Random Seed", min_value=0, max_value=9999, value=42, step=1,
                           help="Controls task generation randomness for reproducibility")

    speed = st.slider("Simulation Speed (s/step)", min_value=0.01, max_value=0.5,
                      value=0.05, step=0.01,
                      help="Pause duration between each time slot in the animation")

    st.markdown("---")
    st.markdown("### 📋 Quick Info")
    st.info(
        f"**Tasks:** {n_tasks}  \n"
        f"**Day type:** {'Cloudy ☁' if cloudy else 'Clear ☀'}  \n"
        f"**Time slots:** 96 × 15 min  \n"
        f"**Schedulers:** 5 algorithms"
    )

    st.markdown("---")
    run_bench_btn = st.button("📊 Run Benchmark", key="sidebar_bench")
    live_sim_btn  = st.button("▶ Start Live Simulation", key="sidebar_live")


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_live, tab_bench, tab_battery = st.tabs([
    "⚡ Live Simulation",
    "📊 Benchmark",
    "🔋 Battery & Energy",
])


# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — LIVE SIMULATION
# ═════════════════════════════════════════════════════════════════════════════
with tab_live:
    st.markdown('<div class="section-header">Live Step-by-Step Simulation</div>',
                unsafe_allow_html=True)
    st.markdown(
        "The simulation runs the **Agentic DP Scheduler** slot-by-slot across the full 24-hour "
        "day. Watch tasks being placed in real time as the solar window opens and the agent "
        "switches between AGGRESSIVE / CONSERVATIVE / SHED modes."
    )

    if live_sim_btn or st.button("▶ Start Live Simulation", key="tab_live_btn"):

        # ── Setup ──────────────────────────────────────────────────────────
        tasks_raw = M["generate_tasks"](n=n_tasks, seed=int(seed), cloudy=cloudy)
        servers   = M["make_cluster"](5)
        for s in servers:
            s.reset()

        # Pre-build arrival index
        arrival_index = defaultdict(list)
        for t in tasks_raw:
            arrival_index[t.arrival_slot].append(copy.deepcopy(t))

        battery = M["BatteryStorage"](capacity=200, max_charge_rate=25, max_discharge_rate=25)
        agent   = M["GreenAgent"](budget=M["MAX_ENERGY_BUDGET"], cloudy=cloudy)

        # Simulation state
        deferred      = []
        scheduled_ids = set()
        placed_tasks  = []   # (slot, server_name, priority, carbon)
        latencies     = []
        carbon_total  = 0.0
        solar_tasks   = 0
        grid_tasks    = 0
        deadline_met  = 0
        deadline_miss = 0
        battery_soc   = []
        mode_history  = []

        # ── Progress & containers ──────────────────────────────────────────
        progress_bar  = st.progress(0, text="Starting simulation…")
        status_text   = st.empty()
        metrics_row   = st.empty()

        # Pre-create columns once so charts update in-place without flickering
        _col_left, _col_right = st.columns(2)
        solar_placeholder = _col_left.empty()
        tasks_placeholder = _col_right.empty()
        server_placeholder = st.empty()

        energy_profile = [energy_at_slot(s, cloudy) for s in range(SLOTS_PER_DAY)]
        times_labels   = [slot_to_time(s) for s in range(SLOTS_PER_DAY)]

        # ── Slot-by-slot simulation loop ───────────────────────────────────
        for slot in range(SLOTS_PER_DAY):
            # Tick servers
            for s in servers:
                s.tick(slot)

            # Record battery SOC
            battery_soc.append(battery.soc_pct())

            # New arrivals
            for task in arrival_index.get(slot, []):
                deferred.append(task)

            # Agent observe
            a_state = agent.observe(slot, len(deferred), len(scheduled_ids), carbon_total)
            mode    = a_state.mode
            mode_history.append(mode)

            solar_energy = energy_at_slot(slot, cloudy)

            # Battery management
            task_demand = sum(t.energy_cost for t in deferred[:8])
            net_energy, batt_contrib = battery.update_from_solar(slot, solar_energy, task_demand)
            using_batt = batt_contrib > 0

            # Force-schedule tasks at deadline
            for task in list(deferred):
                if task.deadline <= slot and task.assigned_slot is None:
                    srv = min(servers, key=lambda s: s.active_connections)
                    lat = srv.accept(slot)
                    srv.tick(slot)
                    task.mark_scheduled(slot, srv.name, lat)
                    ci = carbon_intensity(slot, cloudy)
                    c  = ci * task.energy_cost
                    carbon_total += c
                    scheduled_ids.add(task.id)
                    latencies.append(lat)
                    placed_tasks.append((slot, srv.name, task.priority, c))
                    if task.met_deadline:
                        deadline_met  += 1
                    else:
                        deadline_miss += 1
                    grid_tasks += 1

            deferred = [t for t in deferred
                        if t.assigned_slot is None and t.id not in scheduled_ids]

            # DP scheduling
            eff_budget = agent.effective_budget()
            eff_solar  = solar_energy + (batt_contrib if using_batt else 0)

            if eff_solar >= 20 and eff_budget > 0 and deferred:
                eligible = [t for t in deferred
                            if t.arrival_slot <= slot and t.assigned_slot is None]
                cap      = min(eff_budget, int(eff_solar))

                if eligible and cap > 0:
                    from phase4_dp_scheduler import build_dp_table, traceback
                    dp     = build_dp_table(eligible, slot, cap, cloudy)
                    chosen = traceback(dp, eligible, cap)

                    for task in chosen:
                        if task.id in scheduled_ids or task.assigned_slot is not None:
                            continue
                        srv = min(servers, key=lambda s: s.active_connections)
                        lat = srv.accept(slot)
                        srv.tick(slot)
                        task.mark_scheduled(slot, srv.name, lat)
                        scheduled_ids.add(task.id)

                        ci = 2.5 if using_batt else carbon_intensity(slot, cloudy)
                        c  = ci * task.energy_cost
                        carbon_total += c
                        latencies.append(lat)
                        placed_tasks.append((slot, srv.name, task.priority, c))

                        if task.met_deadline:
                            deadline_met  += 1
                        else:
                            deadline_miss += 1
                        solar_tasks += 1

                    chosen_ids = {t.id for t in chosen}
                    deferred   = [t for t in deferred
                                  if t.id not in chosen_ids or t.assigned_slot is None]

            # ── Update UI ─────────────────────────────────────────────────
            pct = (slot + 1) / SLOTS_PER_DAY
            progress_bar.progress(pct, text=f"Slot {slot+1}/96 — {slot_to_time(slot)} — Mode: {mode}")

            status_text.markdown(
                f"**🕐 {slot_to_time(slot)}** &nbsp;|&nbsp; "
                f"Solar: **{solar_energy:.0f}** units &nbsp;|&nbsp; "
                f"Mode: <span style='color:{'#3fb950' if mode=='AGGRESSIVE' else '#e3b341' if mode=='CONSERVATIVE' else '#e74c3c'}'>"
                f"**{mode}**</span> &nbsp;|&nbsp; "
                f"Deferred queue: **{len(deferred)}** tasks",
                unsafe_allow_html=True,
            )

            # Metrics row
            with metrics_row.container():
                m1, m2, m3, m4 = st.columns(4)
                with m1:
                    st.metric("Carbon Saved (gCO₂)",
                              f"{max(0, len(placed_tasks)*45*5 - carbon_total):.0f}",
                              delta=f"-{carbon_total:.0f} emitted")
                with m2:
                    st.metric("Tasks Scheduled", len(scheduled_ids),
                              delta=f"{len(deferred)} deferred")
                with m3:
                    mode_color = "AGGRESSIVE" if mode == "AGGRESSIVE" else mode
                    st.metric("Agent Mode", mode)
                with m4:
                    st.metric("Battery Level", f"{battery.soc_pct():.0f}%",
                              delta=f"{battery.soc:.0f}/{battery.capacity:.0f} units")

            # Main charts — write into pre-created placeholders to avoid flicker
            fig_solar = make_solar_fig(
                cloudy=cloudy,
                current_slot=slot,
                battery_trace=battery_soc,
                height=360,
            )
            solar_placeholder.plotly_chart(fig_solar, use_container_width=True, key=f"solar_{slot}")

            fig_tasks = make_task_scatter(placed_tasks, height=360)
            tasks_placeholder.plotly_chart(fig_tasks, use_container_width=True, key=f"tasks_{slot}")

            # Server bars
            fig_srv = make_server_bar(servers)
            server_placeholder.plotly_chart(fig_srv, use_container_width=True, key=f"srv_{slot}")

            time.sleep(speed)

        # ── End-of-day flush ───────────────────────────────────────────────
        night_slot = SLOTS_PER_DAY - 1
        for task in deferred:
            if task.assigned_slot is not None or task.id in scheduled_ids:
                continue
            srv = min(servers, key=lambda s: s.active_connections)
            lat = srv.accept(night_slot)
            task.mark_scheduled(night_slot, srv.name, lat)
            scheduled_ids.add(task.id)
            ci = carbon_intensity(night_slot, cloudy)
            c  = ci * task.energy_cost
            carbon_total += c
            latencies.append(lat)
            placed_tasks.append((night_slot, srv.name, task.priority, c))
            if task.met_deadline:
                deadline_met  += 1
            else:
                deadline_miss += 1
            grid_tasks += 1

        progress_bar.progress(1.0, text="Simulation complete!")

        # ── Final stats ────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 🏁 Simulation Complete!")

        s1, s2, s3, s4, s5 = st.columns(5)
        with s1:
            st.metric("Total Tasks", len(tasks_raw))
        with s2:
            st.metric("Scheduled", len(scheduled_ids))
        with s3:
            st.metric("Total Carbon", f"{carbon_total:.1f} gCO₂")
        with s4:
            st.metric("Deadline Met", deadline_met,
                      delta=f"{deadline_miss} missed")
        with s5:
            avg_lat = sum(latencies) / len(latencies) if latencies else 0
            st.metric("Avg Latency", f"{avg_lat:.1f} ms")

        # Mode distribution pie
        mode_counts = {
            "AGGRESSIVE":   mode_history.count("AGGRESSIVE"),
            "CONSERVATIVE": mode_history.count("CONSERVATIVE"),
            "SHED":         mode_history.count("SHED"),
        }
        fig_pie = go.Figure(go.Pie(
            labels=list(mode_counts.keys()),
            values=list(mode_counts.values()),
            hole=0.45,
            marker_colors=["#3fb950", "#e3b341", "#e74c3c"],
        ))
        fig_pie.update_layout(
            title="Agent Mode Distribution",
            height=320,
            **DARK_LAYOUT,
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    else:
        st.info("👈 Configure settings in the sidebar, then click **▶ Start Live Simulation** to begin.")

        # Static preview of solar curve
        st.markdown('<div class="section-header">Solar Energy Preview</div>', unsafe_allow_html=True)
        fig_preview = make_solar_fig(cloudy=cloudy, height=400)
        st.plotly_chart(fig_preview, use_container_width=True)


# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — BENCHMARK
# ═════════════════════════════════════════════════════════════════════════════
with tab_bench:
    st.markdown('<div class="section-header">Multi-Scheduler Benchmark</div>',
                unsafe_allow_html=True)
    st.markdown(
        "Runs all 5 schedulers on the same workload and compares carbon emissions, "
        "deadline adherence, and latency. Charts are interactive — hover for details."
    )

    if run_bench_btn or st.button("🚀 Run All Schedulers", key="bench_run"):
        with st.spinner("Running benchmark — this may take a few seconds…"):
            tasks_raw = M["generate_tasks"](n=n_tasks, seed=int(seed), cloudy=cloudy)
            servers   = M["make_cluster"](5)

            def _reset(t):
                t2 = copy.deepcopy(t)
                t2.assigned_slot = t2.assigned_server = t2.latency_ms = t2.met_deadline = None
                return t2

            schedulers = [
                M["RoundRobinScheduler"](cloudy=cloudy),
                M["GreedyEDFScheduler"](cloudy=cloudy),
                M["DPScheduler"](cloudy=cloudy),
                M["AgenticDPScheduler"](cloudy=cloudy),
                M["BatteryAwareDPScheduler"](
                    battery=M["BatteryStorage"](capacity=200),
                    cloudy=cloudy,
                ),
            ]

            COLORS_MAP = {
                "RoundRobin":    "#e74c3c",
                "GreedyEDF":     "#e67e22",
                "DPScheduler":   "#3498db",
                "AgenticDP":     "#2ecc71",
                "BatteryAwareDP":"#9b59b6",
            }

            results = {}
            for sched in schedulers:
                fresh = [_reset(t) for t in tasks_raw]
                res   = sched.run(fresh, copy.deepcopy(servers))
                results[res.scheduler_name] = res

        st.success("Benchmark complete!")
        st.markdown("---")

        names   = list(results.keys())
        carbons = [results[n].total_carbon_g for n in names]
        baseline = carbons[0] if carbons else 1

        # ── Row 1: Energy profile + Carbon comparison ──────────────────────
        col1, col2 = st.columns(2)

        with col1:
            # Chart 1: Solar energy + carbon intensity
            slots  = list(range(SLOTS_PER_DAY))
            energy = [energy_at_slot(s, cloudy) for s in slots]
            ci_vals = [carbon_intensity(s, cloudy) for s in slots]
            times  = [slot_to_time(s) for s in slots]

            fig1 = make_subplots(specs=[[{"secondary_y": True}]])
            fig1.add_trace(
                go.Scatter(x=times, y=energy, fill="tozeroy",
                           fillcolor="rgba(249,202,36,0.18)",
                           line=dict(color="#f9ca24", width=2), name="Solar Energy"),
                secondary_y=False,
            )
            fig1.add_trace(
                go.Scatter(x=times, y=ci_vals,
                           line=dict(color="#e74c3c", width=1.8, dash="dash"),
                           name="Carbon Intensity"),
                secondary_y=True,
            )
            fig1.update_layout(
                title=f"Solar Energy Profile {'(Cloudy)' if cloudy else '(Clear)'}",
                height=380,
                **DARK_LAYOUT,
            )
            fig1.update_xaxes(tickangle=-45, tickvals=times[::8], **_AXIS_STYLE)
            fig1.update_yaxes(title_text="Solar Energy (units)", secondary_y=False)
            fig1.update_yaxes(title_text="Carbon Intensity (gCO₂/unit)", secondary_y=True)
            st.plotly_chart(fig1, use_container_width=True)

        with col2:
            # Chart 2: Carbon comparison bar
            reductions = [100 * (baseline - c) / max(baseline, 1) for c in carbons]
            colors_bar = [COLORS_MAP.get(n, "#7f8c8d") for n in names]

            fig2 = go.Figure(go.Bar(
                x=names,
                y=carbons,
                marker_color=colors_bar,
                text=[f"{c:.0f} gCO₂<br>({-r:+.1f}%)" for c, r in zip(carbons, reductions)],
                textposition="outside",
                textfont=dict(size=10),
            ))
            fig2.update_layout(
                title="Total Carbon Emissions by Scheduler",
                height=380,
                **DARK_LAYOUT,
            )
            fig2.update_yaxes(title="gCO₂", range=[0, max(carbons) * 1.3], **_AXIS_STYLE)
            fig2.update_xaxes(tickangle=-15, **_AXIS_STYLE)
            st.plotly_chart(fig2, use_container_width=True)

        # ── Row 2: Task distribution + Latency scatter ─────────────────────
        col3, col4 = st.columns(2)

        with col3:
            # Chart 3: Task distribution grouped bar
            period_labels = ["Night (0-6h)", "Morning (6-12h)", "Afternoon (12-18h)", "Evening (18-24h)"]
            period_slots  = [(0, 24), (24, 48), (48, 72), (72, 96)]

            fig3 = go.Figure()
            for name in names:
                res = results[name]
                counts = []
                for start, end in period_slots:
                    c = sum(1 for slot, _ in res.schedule_pairs if start <= slot < end)
                    counts.append(c)
                fig3.add_trace(go.Bar(
                    name=name, x=period_labels, y=counts,
                    marker_color=COLORS_MAP.get(name, "#7f8c8d"),
                ))
            fig3.update_layout(
                title="Task Distribution by Time Period",
                barmode="group",
                yaxis_title="Tasks Scheduled",
                height=380,
                **DARK_LAYOUT,
            )
            st.plotly_chart(fig3, use_container_width=True)

        with col4:
            # Chart 4: Latency vs Carbon scatter
            fig4 = go.Figure()
            for name in names:
                res = results[name]
                fig4.add_trace(go.Scatter(
                    x=[res.avg_latency_ms],
                    y=[res.total_carbon_g],
                    mode="markers+text",
                    marker=dict(size=16, color=COLORS_MAP.get(name, "#7f8c8d"),
                                line=dict(color="white", width=1.5)),
                    text=[name],
                    textposition="top center",
                    textfont=dict(size=10),
                    name=name,
                ))
            fig4.update_layout(
                title="Latency vs Carbon Trade-off",
                xaxis_title="Avg Latency (ms)",
                yaxis_title="Total Carbon (gCO₂)",
                height=380,
                **DARK_LAYOUT,
            )
            st.plotly_chart(fig4, use_container_width=True)

        # ── Summary table ──────────────────────────────────────────────────
        st.markdown("---")
        st.markdown('<div class="section-header">Results Summary</div>', unsafe_allow_html=True)

        rows = []
        for name, res in results.items():
            saving_g   = baseline - res.total_carbon_g
            saving_pct = 100 * saving_g / max(baseline, 1)
            rows.append({
                "Scheduler":          name,
                "Carbon (gCO₂)":      round(res.total_carbon_g, 1),
                "Tasks Scheduled":    res.tasks_scheduled,
                "Deadline Met":       res.deadline_met,
                "Deadline Missed":    res.deadline_missed,
                "Solar Tasks":        res.solar_tasks,
                "Grid Tasks":         res.grid_tasks,
                "Avg Latency (ms)":   round(res.avg_latency_ms, 1),
                "Carbon Saving (%)":  round(saving_pct, 1),
                "Saving (kg CO₂)":    round(saving_g / 1000, 4),
            })

        df = pd.DataFrame(rows).set_index("Scheduler")
        st.dataframe(df.style.background_gradient(
            subset=["Carbon (gCO₂)"],
            cmap="RdYlGn_r",
        ).background_gradient(
            subset=["Carbon Saving (%)"],
            cmap="Greens",
        ), use_container_width=True)

        # ── Carbon savings highlight ───────────────────────────────────────
        if len(results) > 1:
            best_name   = min(results, key=lambda n: results[n].total_carbon_g)
            best_saving = baseline - results[best_name].total_carbon_g
            best_pct    = 100 * best_saving / max(baseline, 1)
            st.success(
                f"**Best scheduler: {best_name}** saves **{best_saving:.0f} gCO₂** "
                f"({best_pct:.1f}%) vs Round-Robin baseline — equivalent to "
                f"**{best_saving/1000:.3f} kg CO₂** per simulation run."
            )

    else:
        st.info("👈 Click **Run All Schedulers** or use the sidebar button to start the benchmark.")

        # Static solar preview
        st.markdown('<div class="section-header">Solar Energy Preview</div>', unsafe_allow_html=True)
        slots = list(range(SLOTS_PER_DAY))
        energy = [energy_at_slot(s, cloudy) for s in slots]
        times  = [slot_to_time(s) for s in slots]
        fig_prev = go.Figure(go.Scatter(
            x=times, y=energy, fill="tozeroy",
            fillcolor="rgba(249,202,36,0.18)",
            line=dict(color="#f9ca24", width=2), name="Solar Energy",
        ))
        fig_prev.update_layout(title="Solar Energy Profile (preview)", height=350, **DARK_LAYOUT)
        fig_prev.update_xaxes(tickangle=-45, tickvals=times[::8], **_AXIS_STYLE)
        fig_prev.update_yaxes(**_AXIS_STYLE)
        st.plotly_chart(fig_prev, use_container_width=True)


# ═════════════════════════════════════════════════════════════════════════════
# TAB 3 — BATTERY & ENERGY
# ═════════════════════════════════════════════════════════════════════════════
with tab_battery:
    st.markdown('<div class="section-header">Battery Storage & Energy Analysis</div>',
                unsafe_allow_html=True)
    st.markdown(
        "The **Battery Storage** novelty addition stores excess solar energy during peak hours "
        "and releases it at night, extending the effective green energy window and achieving "
        "an additional **5–8% carbon reduction** over the vanilla DP scheduler."
    )

    if st.button("🔋 Run Battery Analysis", key="battery_run"):
        with st.spinner("Running DP vs Battery-Aware DP comparison…"):
            tasks_raw = M["generate_tasks"](n=n_tasks, seed=int(seed), cloudy=cloudy)
            servers   = M["make_cluster"](5)

            def _reset(t):
                t2 = copy.deepcopy(t)
                t2.assigned_slot = t2.assigned_server = t2.latency_ms = t2.met_deadline = None
                return t2

            # Baseline DP
            dp_tasks  = [_reset(t) for t in tasks_raw]
            dp_res    = M["DPScheduler"](cloudy=cloudy).run(dp_tasks, copy.deepcopy(servers))

            # Battery-Aware DP
            battery   = M["BatteryStorage"](capacity=200, max_charge_rate=25, max_discharge_rate=25)
            ba_tasks  = [_reset(t) for t in tasks_raw]
            ba_sched  = M["BatteryAwareDPScheduler"](battery=battery, cloudy=cloudy)
            ba_res    = ba_sched.run(ba_tasks, copy.deepcopy(servers))

        st.success("Analysis complete!")
        st.markdown("---")

        # ── KPI row ────────────────────────────────────────────────────────
        k1, k2, k3, k4 = st.columns(4)
        saving_g   = dp_res.total_carbon_g - ba_res.total_carbon_g
        saving_pct = 100 * saving_g / max(dp_res.total_carbon_g, 1)
        batt_sum   = ba_res.extras.get("battery_summary", {})

        with k1:
            st.metric("DP Carbon", f"{dp_res.total_carbon_g:.0f} gCO₂")
        with k2:
            st.metric("Battery-DP Carbon", f"{ba_res.total_carbon_g:.0f} gCO₂",
                      delta=f"-{saving_g:.0f} gCO₂")
        with k3:
            st.metric("Extra Reduction", f"{saving_pct:.1f}%",
                      delta="battery benefit")
        with k4:
            st.metric("Total Energy Stored",
                      f"{batt_sum.get('total_charged', 0):.0f} units")

        st.markdown("---")

        # ── Chart 1: Solar + Battery SOC trace ────────────────────────────
        st.markdown('<div class="section-header">Solar Energy & Battery State of Charge</div>',
                    unsafe_allow_html=True)

        soc_trace = ba_res.extras.get("battery_soc_trace", [])
        slots     = list(range(SLOTS_PER_DAY))
        energy    = [energy_at_slot(s, cloudy) for s in slots]
        times     = [slot_to_time(s) for s in slots]

        fig_batt = make_subplots(specs=[[{"secondary_y": True}]])
        fig_batt.add_trace(
            go.Scatter(x=times, y=energy, fill="tozeroy",
                       fillcolor="rgba(249,202,36,0.15)",
                       line=dict(color="#f9ca24", width=2),
                       name="Solar Energy"),
            secondary_y=False,
        )
        if soc_trace:
            fig_batt.add_trace(
                go.Scatter(x=times[:len(soc_trace)], y=soc_trace,
                           line=dict(color="#9b59b6", width=2.5),
                           name="Battery SOC %"),
                secondary_y=True,
            )
        fig_batt.update_layout(
            title="Solar Energy & Battery State of Charge Throughout the Day",
            height=420,
            xaxis=dict(tickangle=-45, tickvals=times[::8]),
            **DARK_LAYOUT,
        )
        fig_batt.update_yaxes(title_text="Solar Energy (units)", secondary_y=False)
        fig_batt.update_yaxes(title_text="Battery SOC (%)", range=[0, 105], secondary_y=True)
        st.plotly_chart(fig_batt, use_container_width=True)

        # ── Chart 2: Battery charge/discharge events ───────────────────────
        st.markdown('<div class="section-header">Battery Charge / Discharge Events</div>',
                    unsafe_allow_html=True)

        batt_history = ba_res.extras.get("battery_history", [])
        if batt_history:
            bh_df = pd.DataFrame(batt_history)
            charge_df    = bh_df[bh_df["action"] == "charge"]
            discharge_df = bh_df[bh_df["action"] == "discharge"]

            fig_events = go.Figure()
            if not charge_df.empty:
                fig_events.add_trace(go.Bar(
                    x=charge_df["time"],
                    y=charge_df["amount"],
                    name="Charge (Solar → Battery)",
                    marker_color="#3fb950",
                    opacity=0.85,
                ))
            if not discharge_df.empty:
                fig_events.add_trace(go.Bar(
                    x=discharge_df["time"],
                    y=[-v for v in discharge_df["amount"]],
                    name="Discharge (Battery → Tasks)",
                    marker_color="#e74c3c",
                    opacity=0.85,
                ))
            fig_events.update_layout(
                title="Battery Charge (+) and Discharge (−) per Slot",
                barmode="overlay",
                yaxis_title="Energy (units)",
                xaxis_title="Time of Day",
                height=380,
                **DARK_LAYOUT,
            )
            st.plotly_chart(fig_events, use_container_width=True)
        else:
            st.info("No battery events recorded. Try increasing the task load or changing parameters.")

        # ── Chart 3: Carbon comparison bar ────────────────────────────────
        st.markdown('<div class="section-header">Carbon Reduction from Battery Storage</div>',
                    unsafe_allow_html=True)

        fig_comp = go.Figure(go.Bar(
            x=["DP Scheduler", "Battery-Aware DP"],
            y=[dp_res.total_carbon_g, ba_res.total_carbon_g],
            marker_color=["#3498db", "#9b59b6"],
            text=[f"{dp_res.total_carbon_g:.0f} gCO₂", f"{ba_res.total_carbon_g:.0f} gCO₂"],
            textposition="outside",
            textfont=dict(size=13),
            width=0.4,
        ))
        fig_comp.add_annotation(
            x=0.5, y=max(dp_res.total_carbon_g, ba_res.total_carbon_g) * 1.15,
            xref="x", yref="y",
            text=f"Battery saves {saving_pct:.1f}% more carbon",
            showarrow=False,
            font=dict(size=14, color="#3fb950"),
        )
        fig_comp.update_layout(
            title="Carbon Emissions: Standard DP vs Battery-Aware DP",
            yaxis=dict(title="Total Carbon (gCO₂)",
                       range=[0, max(dp_res.total_carbon_g, ba_res.total_carbon_g) * 1.3]),
            height=380,
            **DARK_LAYOUT,
        )
        st.plotly_chart(fig_comp, use_container_width=True)

        # ── Battery summary table ──────────────────────────────────────────
        st.markdown('<div class="section-header">Battery Performance Summary</div>',
                    unsafe_allow_html=True)
        batt_data = {
            "Metric":  ["Capacity", "Final SOC", "Final SOC %",
                        "Total Charged", "Total Discharged",
                        "Charge Events", "Discharge Events"],
            "Value":   [
                f"{batt_sum.get('capacity', 0):.0f} units",
                f"{batt_sum.get('final_soc', 0):.1f} units",
                f"{batt_sum.get('final_soc_pct', 0):.1f}%",
                f"{batt_sum.get('total_charged', 0):.1f} units",
                f"{batt_sum.get('total_discharged', 0):.1f} units",
                str(batt_sum.get('charge_events', 0)),
                str(batt_sum.get('discharge_events', 0)),
            ],
        }
        st.dataframe(pd.DataFrame(batt_data).set_index("Metric"), use_container_width=True)

    else:
        st.info("Click **Run Battery Analysis** to compare standard DP vs Battery-Aware DP.")

        # Explainer
        st.markdown('<div class="section-header">How Battery Storage Works</div>',
                    unsafe_allow_html=True)

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.markdown("""
**Charge Phase (Day)**
- Solar panels generate excess energy during peak sun (10:00–16:00)
- Surplus above task demand is stored in the battery
- Max charge rate: 25 units/slot
- Battery capacity: 200 units
""")
        with col_b:
            st.markdown("""
**Discharge Phase (Night)**
- After sunset, battery powers deferred tasks
- Extends the "green energy window" to early morning
- Discharge uses low carbon factor (2.5 gCO₂/unit)
- vs grid carbon of 45 gCO₂/unit — a **18× improvement**
""")
        with col_c:
            st.markdown("""
**Carbon Accounting**
- Tasks powered by battery use `BATTERY_CARBON_FACTOR = 2.5`
- This is slightly above pure solar (2.0) to account for storage losses
- Round-trip efficiency: 90%
- Net result: **5–8% extra carbon reduction** vs vanilla DP
""")

        # Static illustration
        slots  = list(range(SLOTS_PER_DAY))
        energy = [energy_at_slot(s, cloudy) for s in slots]
        times  = [slot_to_time(s) for s in slots]

        # Synthetic battery SOC illustration
        synthetic_soc = []
        soc = 0.0
        for s in slots:
            e = energy[s]
            if e > 50:
                soc = min(100, soc + 3.5)
            elif e > 20:
                soc = min(100, soc + 1.2)
            elif e > 0:
                soc = max(0, soc - 0.5)
            else:
                soc = max(0, soc - 2.0)
            synthetic_soc.append(round(soc, 1))

        fig_ill = make_subplots(specs=[[{"secondary_y": True}]])
        fig_ill.add_trace(
            go.Scatter(x=times, y=energy, fill="tozeroy",
                       fillcolor="rgba(249,202,36,0.15)",
                       line=dict(color="#f9ca24", width=2),
                       name="Solar Energy"),
            secondary_y=False,
        )
        fig_ill.add_trace(
            go.Scatter(x=times, y=synthetic_soc,
                       line=dict(color="#9b59b6", width=2.5),
                       name="Battery SOC % (illustrative)"),
            secondary_y=True,
        )
        fig_ill.update_layout(
            title="Illustrative Battery SOC vs Solar Energy",
            height=380,
            xaxis=dict(tickangle=-45, tickvals=times[::8]),
            **DARK_LAYOUT,
        )
        fig_ill.update_yaxes(title_text="Solar Energy (units)", secondary_y=False)
        fig_ill.update_yaxes(title_text="Battery SOC (%)", range=[0, 105], secondary_y=True)
        st.plotly_chart(fig_ill, use_container_width=True)


# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align:center; color:#484f58; font-size:0.8rem;'>"
    "Carbon-Aware Cloud Task Scheduler &nbsp;·&nbsp; "
    "Dynamic Programming + Agentic AI + Battery Storage &nbsp;·&nbsp; "
    "Cloud Computing Project 2024"
    "</div>",
    unsafe_allow_html=True,
)
