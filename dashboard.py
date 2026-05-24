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
    page_title="Green Cloud Scheduler",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session state routing ─────────────────────────────────────────────────────
if "show_dashboard" not in st.session_state:
    st.session_state.show_dashboard = False

if not st.session_state.show_dashboard:
    # Hide Streamlit chrome on landing page
    st.markdown("""
<style>
header[data-testid="stHeader"] { display: none; }
footer { display: none; }
.block-container { padding-top: 0 !important; padding-bottom: 0 !important;
                   max-width: 100% !important; padding-left: 0 !important;
                   padding-right: 0 !important; }
[data-testid="stAppViewContainer"] { background: #0d1117; }
div.stButton > button {
    background-color: #21262d; color: #cdd9e5;
    border: 1px solid #30363d; border-radius: 6px;
    padding: 0.55rem 1.4rem; font-size: 0.95rem; font-weight: 500;
    cursor: pointer; transition: border-color 0.15s ease, color 0.15s ease;
    width: 100%;
}
div.stButton > button:hover {
    border-color: #2ea043; color: #2ea043; background-color: #21262d;
}
</style>
""", unsafe_allow_html=True)

    import streamlit.components.v1 as _stc_lp
    _stc_lp.html("""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
*{margin:0;padding:0;box-sizing:border-box}
html,body{width:100%;height:680px;background:#0d1117;overflow:hidden}
canvas{position:absolute;top:0;left:0;width:100%;height:100%;display:block}
.ov{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
    text-align:center;max-width:680px;width:90%;pointer-events:none;user-select:none}
.lp-sm{font-size:10px;letter-spacing:3px;color:#2ea043;
        font-family:system-ui,-apple-system,sans-serif;font-weight:500;margin-bottom:16px}
.lp-h1{font-size:36px;font-weight:600;color:#cdd9e5;
        font-family:system-ui,-apple-system,sans-serif;line-height:1.2;margin-bottom:12px}
.lp-sub{font-size:14px;color:#768390;line-height:1.6;max-width:520px;
        margin:0 auto 28px auto;font-family:system-ui,-apple-system,sans-serif}
.lp-badges{display:flex;flex-wrap:wrap;justify-content:center;gap:8px;margin-bottom:48px}
.lp-badge{background:transparent;border:1px solid #30363d;color:#768390;font-size:11px;
          padding:4px 12px;border-radius:20px;font-family:system-ui,-apple-system,sans-serif}
.lp-div{width:40px;height:1px;background:#30363d;margin:0 auto 32px auto}
.lp-devlbl{font-size:10px;letter-spacing:2px;color:#4a5260;font-weight:500;
            margin-bottom:20px;font-family:system-ui,-apple-system,sans-serif}
.lp-devrow{display:flex;flex-direction:row;gap:12px;overflow-x:auto;padding-bottom:8px;
           justify-content:center;max-width:600px;margin:0 auto;
           scrollbar-width:none;pointer-events:all}
.lp-devrow::-webkit-scrollbar{display:none}
.lp-card{width:130px;flex-shrink:0;background:#161b22;border:1px solid #30363d;
         border-radius:8px;padding:14px 12px;text-align:center}
.lp-av{width:36px;height:36px;border-radius:50%;background:#21262d;
       border:1px solid #30363d;margin:0 auto 10px auto;display:flex;
       align-items:center;justify-content:center;font-size:13px;color:#2ea043;
       font-weight:500;font-family:system-ui,-apple-system,sans-serif}
.lp-dn{font-size:12px;color:#cdd9e5;font-weight:500;margin-bottom:3px;
       font-family:system-ui,sans-serif}
.lp-dr{font-size:10px;color:#768390;font-family:system-ui,sans-serif}
</style></head>
<body>
<canvas id="lpc"></canvas>
<div class="ov">
  <div class="lp-sm">CLOUD COMPUTING PROJECT</div>
  <div class="lp-h1">Carbon-Aware Cloud Scheduler</div>
  <div class="lp-sub">Scheduling cloud workloads intelligently across renewable energy windows
    to minimise carbon emissions without missing deadlines.</div>
  <div class="lp-badges">
    <span class="lp-badge">Dynamic Programming</span>
    <span class="lp-badge">P2C Load Balancing</span>
    <span class="lp-badge">Agentic AI</span>
    <span class="lp-badge">Battery Aware</span>
  </div>
  <div class="lp-div"></div>
  <div class="lp-devlbl">DEVELOPED BY</div>
  <div class="lp-devrow">
    <div class="lp-card"><div class="lp-av">D</div>
      <div class="lp-dn">Dhimant Kulkarni</div><div class="lp-dr">Developer 1</div></div>
    <div class="lp-card"><div class="lp-av">N</div>
      <div class="lp-dn">Noel Tom</div><div class="lp-dr">Developer 2</div></div>
    <div class="lp-card"><div class="lp-av">S</div>
      <div class="lp-dn">Shravan Sathiyanarayanan</div><div class="lp-dr">Developer 3</div></div>
    <div class="lp-card"><div class="lp-av">J</div>
      <div class="lp-dn">Jnanasagara Srinivasa</div><div class="lp-dr">Developer 4</div></div>
  </div>
</div>
<script>
(function(){
  var c=document.getElementById('lpc'),ctx=c.getContext('2d');
  var DS=3,GAP=20,RAD=100,BC=[28,33,40],AC=[46,160,67];
  var ripples=[],mouse={x:-9999,y:-9999};
  function resize(){c.width=c.offsetWidth||window.innerWidth;c.height=c.offsetHeight||680;}
  resize();window.addEventListener('resize',resize);
  window.addEventListener('mousemove',function(e){
    var r=c.getBoundingClientRect();mouse.x=e.clientX-r.left;mouse.y=e.clientY-r.top;});
  window.addEventListener('click',function(e){
    var r=c.getBoundingClientRect();
    ripples.push({x:e.clientX-r.left,y:e.clientY-r.top,t:0,max:60});});
  function lerp(a,b,t){return a+(b-a)*t;}
  function draw(){
    ctx.fillStyle='#0d1117';ctx.fillRect(0,0,c.width,c.height);
    var step=DS+GAP;
    for(var rx=DS;rx<c.width;rx+=step){
      for(var ry=DS;ry<c.height;ry+=step){
        var dx=rx-mouse.x,dy=ry-mouse.y;
        var dist=Math.sqrt(dx*dx+dy*dy);
        var mf=Math.max(0,1-dist/RAD),rf=0;
        for(var i=0;i<ripples.length;i++){
          var rp=ripples[i];
          var rdx=rx-rp.x,rdy=ry-rp.y;
          var rd=Math.sqrt(rdx*rdx+rdy*rdy);
          var wr=rp.t*10,ww=55,wd=Math.abs(rd-wr);
          if(wd<ww){var wf=(1-wd/ww)*(1-rp.t/rp.max);rf=Math.max(rf,wf);}
        }
        var t=Math.min(1,mf+rf);
        var r=Math.round(lerp(BC[0],AC[0],t));
        var g=Math.round(lerp(BC[1],AC[1],t));
        var b=Math.round(lerp(BC[2],AC[2],t));
        ctx.fillStyle='rgb('+r+','+g+','+b+')';
        ctx.beginPath();ctx.arc(rx,ry,DS/2,0,Math.PI*2);ctx.fill();
      }
    }
    ripples=ripples.filter(function(rp){rp.t++;return rp.t<rp.max;});
    requestAnimationFrame(draw);
  }
  draw();
})();
</script>
</body></html>""", height=680, scrolling=False)

    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        if st.button("Enter Dashboard", use_container_width=True):
            st.session_state.show_dashboard = True
            st.rerun()

    st.stop()

# ── Theme helpers (dark / light mode) ─────────────────────────────────────────

def _inject_theme(light_mode: bool = False):
    """Inject full CSS for the active colour palette."""
    if light_mode:
        # ── Light palette ──────────────────────────────────────────────────
        bg_page            = "#f0f4f8"
        bg_sidebar         = "#ffffff"
        metric_bg          = "rgba(255,255,255,0.88)"
        metric_border      = "rgba(0,0,0,0.07)"
        metric_shadow      = "0 8px 32px 0 rgba(0,0,0,0.06)"
        metric_hover_bdr   = "rgba(5,150,105,0.35)"
        metric_hover_shd   = "0 12px 40px rgba(5,150,105,0.10)"
        metric_value       = "#059669"
        metric_label       = "#475569"
        metric_delta       = "#64748b"
        text_primary       = "#0f172a"
        text_muted         = "#475569"
        border             = "rgba(0,0,0,0.08)"
        accent             = "#059669"
        accent2            = "#2563eb"
        btn_bg             = "linear-gradient(135deg,#ffffff 0%,#f8fafc 100%)"
        btn_hover_bg       = "linear-gradient(135deg,#f0fdf4 0%,#f8fafc 100%)"
        btn_color          = "#0f172a"
        btn_border         = "rgba(0,0,0,0.10)"
        tab_inactive       = "#64748b"
        tab_hover          = "#0f172a"
        tab_border_btm     = "rgba(0,0,0,0.08)"
        scrollbar_track    = "#f0f4f8"
        scrollbar_thumb    = "#cbd5e1"
        scrollbar_thumb_hv = "#94a3b8"
        alert_bg           = "rgba(255,255,255,0.65)"
        alert_border       = "rgba(0,0,0,0.08)"
        alert_color        = "#475569"
        alert_div          = "#0f172a"
        input_bg           = "#ffffff"
        input_border       = "rgba(0,0,0,0.10)"
        input_color        = "#0f172a"
        slider_track       = "#e2e8f0"
        slider_fill        = "#059669"
        hr_color           = "rgba(0,0,0,0.08)"
        sb_title           = "#059669"
        sb_sub             = "#94a3b8"
        sb_label           = "#475569"
        badge_bg           = "#f8fafc"
        badge_border       = "rgba(0,0,0,0.08)"
        badge_blue         = "#2563eb"
        sc_bg              = "rgba(255,255,255,0.70)"
        sc_border          = "rgba(0,0,0,0.06)"
        df_bg              = "#ffffff"
        df_th_bg           = "#f8fafc"
        df_th_color        = "#475569"
        df_td_border       = "#f1f5f9"
        chart_glass_bg     = "rgba(255,255,255,0.80)"
        chart_glass_bdr    = "rgba(0,0,0,0.08)"
        chart_glass_shd    = "0 4px 28px rgba(0,0,0,0.07)"
        check_label        = "#0f172a"
    else:
        # ── Dark palette ───────────────────────────────────────────────────
        bg_page            = "#07090e"
        bg_sidebar         = "#0b0f19"
        metric_bg          = "rgba(13,18,30,0.72)"
        metric_border      = "rgba(255,255,255,0.05)"
        metric_shadow      = "0 8px 32px 0 rgba(0,0,0,0.30)"
        metric_hover_bdr   = "rgba(16,185,129,0.40)"
        metric_hover_shd   = "0 12px 40px rgba(16,185,129,0.10)"
        metric_value       = "#10b981"
        metric_label       = "#94a3b8"
        metric_delta       = "#64748b"
        text_primary       = "#f1f5f9"
        text_muted         = "#94a3b8"
        border             = "rgba(255,255,255,0.07)"
        accent             = "#10b981"
        accent2            = "#3b82f6"
        btn_bg             = "linear-gradient(135deg,#101625 0%,#0b0f19 100%)"
        btn_hover_bg       = "linear-gradient(135deg,#0b0f19 0%,#101625 100%)"
        btn_color          = "#e2e8f0"
        btn_border         = "rgba(255,255,255,0.06)"
        tab_inactive       = "#64748b"
        tab_hover          = "#cbd5e1"
        tab_border_btm     = "rgba(255,255,255,0.05)"
        scrollbar_track    = "#07090e"
        scrollbar_thumb    = "#1e293b"
        scrollbar_thumb_hv = "#334155"
        alert_bg           = "rgba(15,23,42,0.45)"
        alert_border       = "rgba(255,255,255,0.05)"
        alert_color        = "#94a3b8"
        alert_div          = "#cbd5e1"
        input_bg           = "#0b0f19"
        input_border       = "rgba(255,255,255,0.05)"
        input_color        = "#f1f5f9"
        slider_track       = "#1e293b"
        slider_fill        = "#10b981"
        hr_color           = "rgba(255,255,255,0.05)"
        sb_title           = "#10b981"
        sb_sub             = "#64748b"
        sb_label           = "#94a3b8"
        badge_bg           = "#0b0f19"
        badge_border       = "rgba(255,255,255,0.05)"
        badge_blue         = "#3b82f6"
        sc_bg              = "rgba(13,18,30,0.50)"
        sc_border          = "rgba(255,255,255,0.04)"
        df_bg              = "#0b0f19"
        df_th_bg           = "#101625"
        df_th_color        = "#94a3b8"
        df_td_border       = "#101625"
        chart_glass_bg     = "rgba(13,18,30,0.58)"
        chart_glass_bdr    = "rgba(255,255,255,0.07)"
        chart_glass_shd    = "0 4px 24px rgba(0,0,0,0.22)"
        check_label        = "#f1f5f9"

    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Outfit:wght@300;400;500;600;700&display=swap');

/* ── Base ── */
html, body, [class*="css"] {{
    background-color: {bg_page} !important;
    color: {text_primary} !important;
    font-family: 'Outfit', -apple-system, sans-serif;
}}

/* ── Scrollbar ── */
::-webkit-scrollbar {{ width: 6px; height: 6px; }}
::-webkit-scrollbar-track {{ background: {scrollbar_track}; }}
::-webkit-scrollbar-thumb {{ background: {scrollbar_thumb}; border-radius: 4px; }}
::-webkit-scrollbar-thumb:hover {{ background: {scrollbar_thumb_hv}; }}

/* ── Main content area ── */
.main .block-container {{
    background-color: {bg_page};
    padding-top: 1.5rem;
    padding-bottom: 3rem;
    max-width: 1440px;
}}

/* ── Sidebar ── */
[data-testid="stSidebar"] {{
    background-color: {bg_sidebar} !important;
    border-right: 1px solid {border};
}}
[data-testid="stSidebar"] .block-container {{
    background-color: {bg_sidebar};
    padding-top: 2rem;
}}
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span {{
    color: {sb_label} !important;
    font-family: 'Space Grotesk', sans-serif;
    font-size: 0.85rem;
}}

/* Sidebar collapse/expand control */
[data-testid="stExpandSidebarButton"],
[data-testid="stSidebar"] button[kind="header"],
[data-testid="stSidebar"] button[kind="headerNoPadding"],
[data-testid="stSidebar"] button[aria-label*="sidebar" i] {{
    width: 36px !important;
    height: 36px !important;
    min-width: 36px !important;
    padding: 0 !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    color: transparent !important;
    font-size: 0 !important;
    overflow: hidden !important;
}}
[data-testid="stExpandSidebarButton"] *,
[data-testid="stSidebar"] button[kind="header"] *,
[data-testid="stSidebar"] button[kind="headerNoPadding"] *,
[data-testid="stSidebar"] button[aria-label*="sidebar" i] * {{
    opacity: 0 !important;
    width: 0 !important;
    min-width: 0 !important;
}}
[data-testid="stExpandSidebarButton"]::before,
[data-testid="stSidebar"] button[kind="header"]::before,
[data-testid="stSidebar"] button[kind="headerNoPadding"]::before,
[data-testid="stSidebar"] button[aria-label*="sidebar" i]::before {{
    content: "";
    width: 18px;
    height: 2px;
    border-radius: 999px;
    background: {sb_label};
    box-shadow: 0 -6px 0 {sb_label}, 0 6px 0 {sb_label};
    display: block;
    flex: 0 0 auto;
}}

/* ── Metric cards ── */
div[data-testid="metric-container"] {{
    background: {metric_bg} !important;
    border: 1px solid {metric_border} !important;
    border-radius: 14px !important;
    padding: 1.3rem 1.5rem !important;
    box-shadow: {metric_shadow} !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
    position: relative;
    overflow: hidden;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}}
div[data-testid="metric-container"]:hover {{
    border-color: {metric_hover_bdr} !important;
    box-shadow: {metric_hover_shd} !important;
    transform: translateY(-2px);
}}
div[data-testid="metric-container"] label {{
    font-family: 'Space Grotesk', sans-serif;
    color: {metric_label} !important;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}}
div[data-testid="metric-container"] [data-testid="stMetricValue"] {{
    color: {metric_value} !important;
    font-size: 1.9rem !important;
    font-weight: 700;
    font-family: 'Space Grotesk', sans-serif;
    margin-top: 0.35rem;
}}
div[data-testid="metric-container"] [data-testid="stMetricDelta"] {{
    color: {metric_delta} !important;
    font-size: 0.85rem;
    font-weight: 500;
}}

/* ── Buttons ── */
div.stButton > button {{
    background: {btn_bg} !important;
    color: {btn_color} !important;
    border: 1px solid {btn_border} !important;
    border-radius: 8px !important;
    padding: 0.65rem 1.4rem !important;
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    cursor: pointer !important;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
    width: 100%;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
}}
div.stButton > button:hover {{
    border-color: {accent} !important;
    color: {accent} !important;
    background: {btn_hover_bg} !important;
    box-shadow: 0 4px 20px rgba(5,150,105,0.18) !important;
    transform: translateY(-1px);
}}

/* ── Tabs ── */
button[data-baseweb="tab"] {{
    background-color: transparent !important;
    color: {tab_inactive} !important;
    font-family: 'Space Grotesk', sans-serif;
    border-bottom: 2px solid transparent;
    font-size: 0.9rem;
    font-weight: 600;
    padding: 0.7rem 1.5rem;
    letter-spacing: 0.04em;
    transition: all 0.2s ease-in-out;
}}
button[data-baseweb="tab"]:hover {{ color: {tab_hover} !important; }}
button[data-baseweb="tab"][aria-selected="true"] {{
    color: {accent} !important;
    border-bottom: 2px solid {accent} !important;
}}
[data-baseweb="tab-list"] {{
    border-bottom: 1px solid {tab_border_btm};
    margin-bottom: 1.8rem;
}}

/* ── Input fields ── */
input, textarea, select,
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {{
    background-color: {input_bg} !important;
    border: 1px solid {input_border} !important;
    color: {input_color} !important;
    border-radius: 8px !important;
}}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus {{ border-color: {accent} !important; }}

/* ── Sliders ── */
[data-testid="stSlider"] .st-bo {{ background-color: {slider_track}; }}
[data-testid="stSlider"] .st-bp {{ background-color: {accent}; }}

/* ── Toggle / checkbox ── */
[data-testid="stCheckbox"] label {{ color: {check_label} !important; }}
div[data-testid="stToggleCollector"] label {{ color: {check_label} !important; }}

/* ── Info / status boxes ── */
div[data-testid="stAlert"] {{
    background: {alert_bg} !important;
    border: 1px solid {alert_border} !important;
    border-radius: 10px !important;
    color: {alert_color} !important;
}}
div[data-testid="stAlert"] div {{ color: {alert_div} !important; }}

/* ── Section headers ── */
.section-header {{
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.25rem;
    font-weight: 600;
    background: linear-gradient(90deg, {accent} 0%, {accent2} 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    border-left: 4px solid {accent};
    padding-left: 0.8rem;
    margin: 1.8rem 0 1.2rem 0;
    letter-spacing: 0.02em;
}}

/* ── Progress bar ── */
[data-testid="stProgress"] > div > div {{
    background: linear-gradient(90deg, {accent}, {accent2}) !important;
}}

/* ── DataFrame / tables ── */
[data-testid="stDataFrame"] {{
    border-radius: 8px; overflow: hidden; border: 1px solid {border};
}}
.dataframe {{ background-color: {df_bg} !important; color: {text_primary} !important; }}
.dataframe th {{ background-color: {df_th_bg} !important; color: {df_th_color} !important; font-weight: 600; }}
.dataframe td {{ border-color: {df_td_border} !important; }}

/* ── Divider ── */
hr {{ border-color: {hr_color}; margin: 1.8rem 0; }}

/* ── Spinner ── */
[data-testid="stSpinner"] {{ color: {accent}; }}

/* ── Sidebar branding ── */
.sidebar-brand {{ padding: 0.4rem 0 1.2rem 0; }}
.sidebar-brand .sb-title {{
    font-family: 'Space Grotesk', sans-serif;
    font-size: 17px; font-weight: 700;
    color: {sb_title}; display: block;
    letter-spacing: 0.04em;
}}
.sidebar-brand .sb-sub {{
    font-family: 'Outfit', sans-serif; font-size: 10px;
    color: {sb_sub}; display: block; margin-top: 5px;
    text-transform: uppercase; letter-spacing: 0.08em;
}}

/* ── Custom Badges ── */
.status-badge {{
    background-color: {badge_bg};
    border: 1px solid {badge_border};
    padding: 0.3rem 0.75rem; border-radius: 6px;
    font-family: monospace; font-weight: 600; color: {accent};
}}
.status-badge-blue {{
    background-color: {badge_bg};
    border: 1px solid {badge_border};
    padding: 0.3rem 0.75rem; border-radius: 6px;
    font-family: monospace; font-weight: 600; color: {badge_blue};
}}
.status-container {{
    display: flex; gap: 1rem; flex-wrap: wrap; align-items: center;
    background: {sc_bg}; border: 1px solid {sc_border};
    padding: 0.8rem 1.2rem; border-radius: 8px; margin-bottom: 1rem;
}}

/* ── Glassmorphic chart panel ── */
[data-testid="stPlotlyChart"] {{
    background: {chart_glass_bg} !important;
    border: 1px solid {chart_glass_bdr} !important;
    border-radius: 16px !important;
    padding: 0.9rem 0.75rem !important;
    backdrop-filter: blur(10px) !important;
    -webkit-backdrop-filter: blur(10px) !important;
    box-shadow: {chart_glass_shd} !important;
    margin-bottom: 0.75rem !important;
}}
</style>
""", unsafe_allow_html=True)


def _get_chart_theme(light_mode: bool = False):
    """Return (layout_dict, axis_style_dict) tuned for the active palette."""
    if light_mode:
        layout = dict(
            template="plotly_white",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(
                color="#1e293b",
                family="'Space Grotesk', 'Outfit', -apple-system, sans-serif",
            ),
            margin=dict(l=50, r=30, t=50, b=50),
        )
        axis = dict(
            gridcolor="rgba(0,0,0,0.07)",
            linecolor="rgba(0,0,0,0.14)",
            zerolinecolor="rgba(0,0,0,0.14)",
        )
    else:
        layout = dict(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(
                color="#cbd5e1",
                family="'Space Grotesk', 'Outfit', -apple-system, sans-serif",
            ),
            margin=dict(l=50, r=30, t=50, b=50),
        )
        axis = dict(
            gridcolor="rgba(255,255,255,0.05)",
            linecolor="rgba(255,255,255,0.08)",
            zerolinecolor="rgba(255,255,255,0.08)",
        )
    return layout, axis


# ── Initial theme injection (uses session state from previous run) ─────────────
_lm_init = st.session_state.get("theme_toggle", False)
_inject_theme(_lm_init)



# ── Lazy imports (avoid import errors before requirements are installed) ──────
@st.cache_resource
def _import_modules():
    from phase1_models import make_cluster
    from phase2_energy_model import (
        SLOTS_PER_DAY, build_energy_profile, carbon_intensity,
        energy_at_slot, slot_to_time,
        load_solar_dataset, activate_solar_day, deactivate_solar_dataset
    )
    from phase3_tasks import (
        generate_tasks, load_azure_tasks, describe_workload, ScheduleResult,
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
        "load_solar_dataset": load_solar_dataset,
        "activate_solar_day": activate_solar_day,
        "deactivate_solar_dataset": deactivate_solar_dataset,
        "generate_tasks": generate_tasks,
        "load_azure_tasks": load_azure_tasks,
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


def _load_tasks_for_dashboard(use_azure: bool, azure_path: str, n_tasks: int, seed: int, cloudy: bool):
    """Load workload for the dashboard, falling back to synthetic if Azure load fails."""
    if use_azure:
        try:
            return M["load_azure_tasks"](filepath=azure_path, n=n_tasks, seed=int(seed))
        except (FileNotFoundError, ValueError, pd.errors.EmptyDataError) as exc:
            st.error(f"Azure dataset could not be loaded: {exc}. Falling back to synthetic workload.")
    return M["generate_tasks"](n=n_tasks, seed=int(seed), cloudy=cloudy)


# ── Plotly theme helpers (rebound after sidebar toggle is read) ───────────────
# Defaults match dark mode; overridden after the sidebar block.
DARK_LAYOUT, _AXIS_STYLE = _get_chart_theme(False)


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

    # Solar fill - sleeker emerald/teal gradient look
    fig.add_trace(go.Scatter(
        x=times, y=energy,
        fill="tozeroy",
        fillcolor="rgba(16,185,129,0.08)",
        line=dict(color="#10b981", width=2.5),
        name="Solar Energy",
    ))

    # Battery SOC overlay - sleeker electric violet
    if battery_trace and len(battery_trace) > 0:
        batt_x = times[:len(battery_trace)]
        fig.add_trace(go.Scatter(
            x=batt_x, y=battery_trace,
            line=dict(color="#8b5cf6", width=2.5, dash="dot"),
            name="Battery SOC %",
            yaxis="y2",
        ))

    # Moving cursor — use add_shape (works with string x-axis in Plotly 6)
    if 0 <= current_slot < SLOTS_PER_DAY:
        fig.add_shape(
            type="line",
            x0=times[current_slot], x1=times[current_slot],
            y0=0, y1=1, yref="paper",
            line=dict(color="#f43f5e", width=2),
        )
        fig.add_annotation(
            x=times[current_slot], y=1.05, yref="paper",
            text=f"Slot: {times[current_slot]}",
            showarrow=False,
            font=dict(color="#f43f5e", size=10, family="'Space Grotesk', sans-serif"),
        )

    fig.update_layout(
        title="Solar Energy & Battery SOC",
        height=height,
        xaxis_title="Time of Day",
        yaxis_title="Solar Energy (units)",
        yaxis2=dict(title="Battery SOC %", overlaying="y", side="right",
                    range=[0, 105], showgrid=False,
                    linecolor=_AXIS_STYLE["linecolor"]),
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
            colors.append("#10b981") # Sleek emerald low load
        elif u < 75:
            colors.append("#f59e0b") # Warning amber medium load
        else:
            colors.append("#ef4444") # Modern rose high load

    fig = go.Figure(go.Bar(
        x=names,
        y=utils,
        marker=dict(
            color=colors,
            line=dict(width=1, color="rgba(255,255,255,0.06)")
        ),
        text=[f"{u}%<br>{l}ms" for u, l in zip(utils, lats)],
        textposition="outside",
        textfont=dict(size=10, family="'Space Grotesk', sans-serif"),
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

    color_map = {"critical": "#ef4444", "high": "#f59e0b", "normal": "#10b981"}

    fig = go.Figure()
    for prio, grp in df.groupby("priority"):
        fig.add_trace(go.Scatter(
            x=grp["time"],
            y=grp["server"],
            mode="markers",
            marker=dict(
                size=9,
                color=color_map.get(prio, "#3b82f6"),
                symbol="circle",
                line=dict(color="#07090e", width=1.2),
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


# ── Dot-grid canvas header ────────────────────────────────────────────────────
import streamlit.components.v1 as _stc
_stc.html("""
<div style="position:relative;width:100%;height:220px;overflow:hidden;
            border-bottom:1px solid #30363d;margin-bottom:24px;background:#0d1117">
  <canvas id="gc-canvas" style="position:absolute;top:0;left:0;width:100%;height:100%;
                                 display:block;"></canvas>
  <div style="position:absolute;top:0;left:0;width:100%;height:100%;
              display:flex;flex-direction:column;align-items:center;
              justify-content:center;pointer-events:none;user-select:none">
    <div style="font-size:22px;font-weight:500;color:#cdd9e5;
                font-family:system-ui,-apple-system,sans-serif;letter-spacing:-0.01em">
      Carbon-Aware Cloud Scheduler
    </div>
    <div style="font-size:13px;color:#768390;margin-top:6px;
                font-family:system-ui,-apple-system,sans-serif">
      Scheduling cloud workloads across renewable energy windows
    </div>
    <div style="display:flex;gap:8px;margin-top:14px">
      <span style="background:#21262d;border:1px solid #30363d;color:#768390;
                   font-size:11px;padding:3px 10px;border-radius:12px;
                   font-family:system-ui,-apple-system,sans-serif">Dynamic Programming</span>
      <span style="background:#21262d;border:1px solid #30363d;color:#768390;
                   font-size:11px;padding:3px 10px;border-radius:12px;
                   font-family:system-ui,-apple-system,sans-serif">P2C Load Balancing</span>
      <span style="background:#21262d;border:1px solid #30363d;color:#768390;
                   font-size:11px;padding:3px 10px;border-radius:12px;
                   font-family:system-ui,-apple-system,sans-serif">Agentic AI</span>
      <span style="background:#21262d;border:1px solid #30363d;color:#768390;
                   font-size:11px;padding:3px 10px;border-radius:12px;
                   font-family:system-ui,-apple-system,sans-serif">Battery Aware</span>    
    </div>
  </div>
</div>
<script>
(function(){
  var canvas = document.getElementById('gc-canvas');
  if (!canvas) return;
  var ctx = canvas.getContext('2d');
  var DOT_SIZE = 4;
  var GAP = 22;
  var RADIUS = 90;
  var BASE_COLOR = [28, 33, 40];
  var ACTIVE_COLOR = [46, 160, 67];
  var ripples = [];
  var mouse = {x: -9999, y: -9999};

  function resize() {
    canvas.width  = canvas.offsetWidth  || 800;
    canvas.height = canvas.offsetHeight || 220;
  }
  resize();
  window.addEventListener('resize', resize);

  canvas.addEventListener('mousemove', function(e) {
    var r = canvas.getBoundingClientRect();
    mouse.x = e.clientX - r.left;
    mouse.y = e.clientY - r.top;
  });
  canvas.addEventListener('mouseleave', function() {
    mouse.x = -9999; mouse.y = -9999;
  });
  canvas.addEventListener('click', function(e) {
    var r = canvas.getBoundingClientRect();
    ripples.push({x: e.clientX - r.left, y: e.clientY - r.top,
                  t: 0, maxT: 55});
  });

  function lerp(a, b, t) { return a + (b - a) * t; }
  function easeOut(t) { return 1 - Math.pow(1 - t, 2); }

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    var step = DOT_SIZE + GAP;
    var now = Date.now();

    for (var rx = DOT_SIZE; rx < canvas.width; rx += step) {
      for (var ry = DOT_SIZE; ry < canvas.height; ry += step) {
        // Mouse proximity factor
        var dx = rx - mouse.x;
        var dy = ry - mouse.y;
        var dist = Math.sqrt(dx*dx + dy*dy);
        var mouseFactor = Math.max(0, 1 - dist / RADIUS);

        // Ripple factor (take max of all active ripples)
        var rippleFactor = 0;
        for (var i = 0; i < ripples.length; i++) {
          var rp = ripples[i];
          var rdx = rx - rp.x;
          var rdy = ry - rp.y;
          var rdist = Math.sqrt(rdx*rdx + rdy*rdy);
          var waveRadius = rp.t * 9;
          var waveWidth  = 50;
          var waveDist = Math.abs(rdist - waveRadius);
          if (waveDist < waveWidth) {
            var waveFactor = (1 - waveDist / waveWidth) * (1 - rp.t / rp.maxT);
            rippleFactor = Math.max(rippleFactor, waveFactor);
          }
        }

        var t = Math.min(1, mouseFactor + rippleFactor);
        var r = Math.round(lerp(BASE_COLOR[0], ACTIVE_COLOR[0], t));
        var g = Math.round(lerp(BASE_COLOR[1], ACTIVE_COLOR[1], t));
        var b = Math.round(lerp(BASE_COLOR[2], ACTIVE_COLOR[2], t));

        ctx.fillStyle = 'rgb('+r+','+g+','+b+')';
        ctx.beginPath();
        ctx.arc(rx, ry, DOT_SIZE / 2, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    // Advance + prune ripples
    ripples = ripples.filter(function(rp) {
      rp.t++;
      return rp.t < rp.maxT;
    });

    requestAnimationFrame(draw);
  }
  draw();
})();
</script>
""", height=228, scrolling=False)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
<div class="sidebar-brand">
  <span class="sb-title">Green Cloud Scheduler</span>
  <span class="sb-sub">Carbon-Aware Task Scheduling</span>
</div>
""", unsafe_allow_html=True)

    # ── Light / Dark mode toggle ───────────────────────────────────────────
    if st.button("HOME PAGE", key="sidebar_home", use_container_width=True):
        st.session_state.show_dashboard = False
        st.rerun()

    light_mode = st.toggle(
        "Light Mode",
        key="theme_toggle",
        help="Switch between dark (default) and light colour palette",
    )
    st.divider()
    st.markdown("## Simulation Controls")
    st.markdown("---")

    n_tasks = st.slider("Number of Tasks", min_value=50, max_value=200, value=100, step=10,
                        help="Total tasks to schedule in the simulation")

    cloudy = st.toggle("Simulate Overcast Weather", value=False,
                       help="Reduces solar output by ~45% and tests scheduler resilience")

    use_solar_dataset = st.checkbox("Enable Historical Solar Feed", value=False,
                                    help="Use real weather radiation data instead of synthetic profile")
    solar_date = "2016-09-29"
    if use_solar_dataset:
        try:
            available_dates = M["load_solar_dataset"]("SolarPrediction.csv")
            default_idx = available_dates.index("2016-09-29") if "2016-09-29" in available_dates else 0
            solar_date = st.selectbox("Select Date", available_dates, index=default_idx,
                                      help="Select a date from the HI-SEAS weather dataset")
            M["activate_solar_day"](solar_date, "SolarPrediction.csv")
        except Exception as e:
            st.error(f"Failed to load solar dataset: {e}")
            use_solar_dataset = False
            M["deactivate_solar_dataset"]()
    else:
        M["deactivate_solar_dataset"]()

    seed = st.number_input("Random Seed", min_value=0, max_value=9999, value=42, step=1,
                           help="Controls task generation randomness for reproducibility")

    speed = st.slider("Simulation Speed (s/step)", min_value=0.01, max_value=0.5,
                      value=0.05, step=0.01,
                      help="Pause duration between each time slot in the animation")

    use_azure = st.checkbox("Use Azure Dataset", value=False)
    azure_path = "vmtable.csv.gz"
    if use_azure:
        azure_path = st.text_input("Path to vmtable.csv.gz", value="vmtable.csv.gz")

    st.markdown("---")
    st.markdown("### System Parameters")
    st.info(
        f"**Tasks:** {n_tasks}  \n"
        f"**Solar Feed:** {f'Historical ({solar_date})' if use_solar_dataset else ('Cloudy (Overcast)' if cloudy else 'Clear Sky')}  \n"
        f"**Time Slots:** 96 × 15 min  \n"
        f"**Schedulers:** 5 Algorithms"
    )

    st.caption(
        "Workload source: Azure vmtable (real traces)"
        if use_azure else
        "Workload source: Synthetic (simulated)"
    )
    st.markdown('---')
    run_bench_btn = st.button("RUN BENCHMARK ENGINE", key="sidebar_bench")
    live_sim_btn  = st.button("LAUNCH LIVE SIMULATION", key="sidebar_live")


# ── Apply theme based on toggle ────────────────────────────────────────────────
# light_mode is set by the sidebar toggle above; rebind globals so all chart
# builders (make_solar_fig, make_server_bar, etc.) use the correct palette.
DARK_LAYOUT, _AXIS_STYLE = _get_chart_theme(light_mode)
_inject_theme(light_mode)   # second call overrides the early init above

# ── Tabs ──────────────────────────────────────────────────────────────────────
solar_desc = f"Real-World Solar ({solar_date})" if use_solar_dataset else ("Cloudy Solar" if cloudy else "Clear Solar")
st.info(
    f"**Workload Trace:** {'Azure VM trace (real)' if use_azure else 'Synthetic (simulated)'} &nbsp;|&nbsp; "
    f"**Active Solar Supply:** {solar_desc}"
)

tab_live, tab_bench, tab_battery = st.tabs([
    "LIVE SIMULATION ENGINE",
    "COMPARATIVE BENCHMARK",
    "BATTERY & STORAGE ANALYSIS",
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

    if live_sim_btn or st.button("LAUNCH LIVE SIMULATION", key="tab_live_btn"):

        # ── Setup ──────────────────────────────────────────────────────────
        tasks_raw = _load_tasks_for_dashboard(
            use_azure=use_azure,
            azure_path=azure_path,
            n_tasks=n_tasks,
            seed=int(seed),
            cloudy=cloudy,
        )
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
        chart_update_interval = 4

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
            progress_bar.progress(pct, text=f"Simulation running... Slot {slot+1}/96 — {slot_to_time(slot)}")

            status_text.markdown(
                f"<div class='status-container'>"
                f"<span class='status-badge-blue'>TIME: {slot_to_time(slot)}</span>"
                f"<span class='status-badge'>SOLAR ENERGY: {solar_energy:.0f} u</span>"
                f"&nbsp;&nbsp;&bull;&nbsp;&nbsp;Agent State: <span style='font-weight:700; color:{'#10b981' if mode=='AGGRESSIVE' else '#f59e0b' if mode=='CONSERVATIVE' else '#ef4444'}'>{mode}</span>"
                f"&nbsp;&nbsp;&bull;&nbsp;&nbsp;Workload Queue: <strong>{len(deferred)}</strong> deferred tasks"
                f"</div>",
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

            # Refresh heavy charts every few slots to reduce flicker in Streamlit.
            should_refresh_charts = (
                slot == 0
                or (slot + 1) % chart_update_interval == 0
                or slot == SLOTS_PER_DAY - 1
            )
            if should_refresh_charts:
                fig_solar = make_solar_fig(
                    cloudy=cloudy,
                    current_slot=slot,
                    battery_trace=battery_soc,
                    height=360,
                )
                solar_placeholder.plotly_chart(
                    fig_solar,
                    width="stretch",
                    key=f"live_solar_chart_{slot}",
                )

                fig_tasks = make_task_scatter(placed_tasks, height=360)
                tasks_placeholder.plotly_chart(
                    fig_tasks,
                    width="stretch",
                    key=f"live_tasks_chart_{slot}",
                )

                fig_srv = make_server_bar(servers)
                server_placeholder.plotly_chart(
                    fig_srv,
                    width="stretch",
                    key=f"live_server_chart_{slot}",
                )

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

        progress_bar.progress(1.0, text="Evaluation complete.")

        # ── Final stats ────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### Simulation Run Complete")

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
            marker_colors=["#10b981", "#f59e0b", "#ef4444"],
        ))
        fig_pie.update_layout(
            title="Agent Mode Distribution",
            height=320,
            **DARK_LAYOUT,
        )
        st.plotly_chart(fig_pie, width="stretch")

    else:
        st.info("Configure the parameters in the sidebar control panel and click 'Launch Live Simulation' to start the execution.")

        # Static preview of solar curve
        st.markdown('<div class="section-header">Solar Energy Preview</div>', unsafe_allow_html=True)
        fig_preview = make_solar_fig(cloudy=cloudy, height=400)
        st.plotly_chart(fig_preview, width="stretch")


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

    if run_bench_btn or st.button("RUN SCHEDULER EVALUATIONS", key="bench_run"):
        with st.spinner("Running benchmark — this may take a few seconds…"):
            tasks_raw = _load_tasks_for_dashboard(
                use_azure=use_azure,
                azure_path=azure_path,
                n_tasks=n_tasks,
                seed=int(seed),
                cloudy=cloudy,
            )
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
                "RoundRobin":    "#ef4444",
                "GreedyEDF":     "#f59e0b",
                "DPScheduler":   "#3b82f6",
                "AgenticDP":     "#10b981",
                "BatteryAwareDP":"#8b5cf6",
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
                           fillcolor="rgba(16,185,129,0.08)",
                           line=dict(color="#10b981", width=2.5), name="Solar Energy"),
                secondary_y=False,
            )
            fig1.add_trace(
                go.Scatter(x=times, y=ci_vals,
                           line=dict(color="#ef4444", width=1.8, dash="dash"),
                           name="Carbon Intensity"),
                secondary_y=True,
            )
            solar_title = f"Solar Energy Profile - Real-world Dataset ({solar_date})" if use_solar_dataset else f"Solar Energy Profile {'(Cloudy)' if cloudy else '(Clear)'}"
            fig1.update_layout(
                title=solar_title,
                height=380,
                **DARK_LAYOUT,
            )
            fig1.update_xaxes(tickangle=-45, tickvals=times[::8], **_AXIS_STYLE)
            fig1.update_yaxes(title_text="Solar Energy (units)", secondary_y=False)
            fig1.update_yaxes(title_text="Carbon Intensity (gCO₂/unit)", secondary_y=True)
            st.plotly_chart(fig1, width="stretch")

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
            st.plotly_chart(fig2, width="stretch")

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
            st.plotly_chart(fig3, width="stretch")

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
            st.plotly_chart(fig4, width="stretch")

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
        ), width="stretch")

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
        st.info("Click RUN SCHEDULER EVALUATIONS or use the sidebar button to start the benchmark.")

        # Static solar preview
        st.markdown('<div class="section-header">Solar Energy Preview</div>', unsafe_allow_html=True)
        slots = list(range(SLOTS_PER_DAY))
        energy = [energy_at_slot(s, cloudy) for s in slots]
        times  = [slot_to_time(s) for s in slots]
        fig_prev = go.Figure(go.Scatter(
            x=times, y=energy, fill="tozeroy",
            fillcolor="rgba(16,185,129,0.08)",
            line=dict(color="#10b981", width=2.5), name="Solar Energy",
        ))
        preview_title = f"Solar Energy Profile (Real-world preview - {solar_date})" if use_solar_dataset else f"Solar Energy Profile (preview - {'Cloudy' if cloudy else 'Clear'})"
        fig_prev.update_layout(title=preview_title, height=350, **DARK_LAYOUT)
        fig_prev.update_xaxes(tickangle=-45, tickvals=times[::8], **_AXIS_STYLE)
        fig_prev.update_yaxes(**_AXIS_STYLE)
        st.plotly_chart(fig_prev, width="stretch")


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

    if st.button("RUN BATTERY PERFORMANCE ANALYSIS", key="battery_run"):
        with st.spinner("Running DP vs Battery-Aware DP comparison…"):
            tasks_raw = _load_tasks_for_dashboard(
                use_azure=use_azure,
                azure_path=azure_path,
                n_tasks=n_tasks,
                seed=int(seed),
                cloudy=cloudy,
            )
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
                       fillcolor="rgba(16,185,129,0.08)",
                       line=dict(color="#10b981", width=2.5),
                       name="Solar Energy"),
            secondary_y=False,
        )
        if soc_trace:
            fig_batt.add_trace(
                go.Scatter(x=times[:len(soc_trace)], y=soc_trace,
                           line=dict(color="#8b5cf6", width=2.5),
                           name="Battery SOC %"),
                secondary_y=True,
            )
        fig_batt.update_layout(
            title="Solar Energy & Battery State of Charge Throughout the Day",
            height=420,
            xaxis=dict(tickangle=-45, tickvals=times[::8]),
            **DARK_LAYOUT,
        )
        fig_batt.update_xaxes(**_AXIS_STYLE)
        fig_batt.update_yaxes(title_text="Solar Energy (units)", secondary_y=False, **_AXIS_STYLE)
        fig_batt.update_yaxes(title_text="Battery SOC (%)", range=[0, 105], secondary_y=True, showgrid=False, linecolor=_AXIS_STYLE["linecolor"])
        st.plotly_chart(fig_batt, width="stretch")

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
                    marker_color="#10b981",
                    opacity=0.85,
                ))
            if not discharge_df.empty:
                fig_events.add_trace(go.Bar(
                    x=discharge_df["time"],
                    y=[-v for v in discharge_df["amount"]],
                    name="Discharge (Battery → Tasks)",
                    marker_color="#ef4444",
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
            fig_events.update_xaxes(**_AXIS_STYLE)
            fig_events.update_yaxes(**_AXIS_STYLE)
            st.plotly_chart(fig_events, width="stretch")
        else:
            st.info("No battery events recorded. Try increasing the task load or changing parameters.")

        # ── Chart 3: Carbon comparison bar ────────────────────────────────
        st.markdown('<div class="section-header">Carbon Reduction from Battery Storage</div>',
                    unsafe_allow_html=True)

        fig_comp = go.Figure(go.Bar(
            x=["DP Scheduler", "Battery-Aware DP"],
            y=[dp_res.total_carbon_g, ba_res.total_carbon_g],
            marker_color=["#3b82f6", "#8b5cf6"],
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
            font=dict(size=14, color="#10b981", family="'Space Grotesk', sans-serif"),
        )
        fig_comp.update_layout(
            title="Carbon Emissions: Standard DP vs Battery-Aware DP",
            yaxis=dict(title="Total Carbon (gCO₂)",
                       range=[0, max(dp_res.total_carbon_g, ba_res.total_carbon_g) * 1.3]),
            height=380,
            **DARK_LAYOUT,
        )
        fig_comp.update_xaxes(**_AXIS_STYLE)
        fig_comp.update_yaxes(**_AXIS_STYLE)
        st.plotly_chart(fig_comp, width="stretch")

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
        st.dataframe(pd.DataFrame(batt_data).set_index("Metric"), width="stretch")

    else:
        st.info("Click RUN BATTERY PERFORMANCE ANALYSIS to compare standard DP vs Battery-Aware DP.")

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
                       fillcolor="rgba(16,185,129,0.08)",
                       line=dict(color="#10b981", width=2.5),
                       name="Solar Energy"),
            secondary_y=False,
        )
        fig_ill.add_trace(
            go.Scatter(x=times, y=synthetic_soc,
                       line=dict(color="#8b5cf6", width=2.5),
                       name="Battery SOC % (illustrative)"),
            secondary_y=True,
        )
        fig_ill.update_layout(
            title="Illustrative Battery SOC vs Solar Energy",
            height=380,
            xaxis=dict(tickangle=-45, tickvals=times[::8]),
            **DARK_LAYOUT,
        )
        fig_ill.update_xaxes(**_AXIS_STYLE)
        fig_ill.update_yaxes(title_text="Solar Energy (units)", secondary_y=False, **_AXIS_STYLE)
        fig_ill.update_yaxes(title_text="Battery SOC (%)", range=[0, 105], secondary_y=True, showgrid=False, linecolor=_AXIS_STYLE["linecolor"])
        st.plotly_chart(fig_ill, width="stretch")


# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="margin-top:48px;padding-top:16px;border-top:1px solid #30363d;
            text-align:center;color:#4a5260;font-size:11px">
    Green Cloud Scheduler &nbsp;·&nbsp; Carbon-Aware Task Scheduling
    &nbsp;·&nbsp; Cloud Computing Project
</div>
""", unsafe_allow_html=True)
