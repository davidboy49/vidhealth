import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime, date, timedelta
import plotly.graph_objects as go
import sys
import math

# Add parent dir to path to import db
sys.path.append(str(Path(__file__).parent.parent))
import db
from recovery_predictor import RecoveryPredictor

st.set_page_config(page_title="My Health", page_icon="⚡", layout="wide")

# ---------- THEME CONFIGURATION (SHADCN STYLING) ----------
# FIRST PRIORITY: Default to Light mode
if "theme" not in st.session_state:
    st.session_state.theme = "light"

# Apply CSS variables matching Shadcn UI design tokens
if st.session_state.theme == "dark":
    # Zinc Dark Palette
    bg_base = "#09090b"            # zinc-950
    bg_card = "#09090b"            # zinc-950
    text_primary = "#fafafa"       # zinc-50
    text_muted = "#a1a1aa"          # zinc-400
    border = "#27272a"             # zinc-800
    bg_muted = "#18181b"           # zinc-900
    accent_color = "#3f3f46"       # zinc-700
    plotly_template = "plotly_dark"
    grid_color = "#27272a"
else:
    # Zinc Light Palette (Default First Priority)
    bg_base = "#ffffff"            # white
    bg_card = "#ffffff"            # white
    text_primary = "#09090b"       # zinc-950
    text_muted = "#71717a"          # zinc-500
    border = "#e4e4e7"             # zinc-200
    bg_muted = "#f4f4f5"           # zinc-100
    accent_color = "#e4e4e7"       # zinc-200
    plotly_template = "plotly_white"
    grid_color = "#f4f4f5"

# Inject Stylesheet at the very beginning
st.markdown(f"""
<style>
    /* CSS Variables Setup */
    :root {{
        --background: {bg_base};
        --card: {bg_card};
        --card-foreground: {text_primary};
        --foreground: {text_primary};
        --muted: {bg_muted};
        --muted-foreground: {text_muted};
        --border: {border};
    }}

    /* Global Overrides */
    .main, .stApp {{
        background-color: var(--background) !important;
        color: var(--foreground) !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
    }}
    
    h1, h2, h3, h4, h5, h6, p, span, label, div {{
        color: var(--foreground);
    }}
    
    hr {{
        border-color: var(--border) !important;
    }}

    /* Hide Streamlit default headers completely to avoid sticky color mismatches */
    header[data-testid="stHeader"] {{
        display: none !important;
    }}
    
    div[data-testid="stDecoration"] {{
        display: none !important;
    }}
    
    div.block-container {{
        padding-top: 2rem !important;
        background-color: var(--background) !important;
    }}
    
    div[data-testid="stToolbar"] {{
        color: var(--foreground) !important;
    }}

    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}

    /* Loading overlay */
    .loader-overlay {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background-color: var(--background);
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        z-index: 999999;
        gap: 16px;
    }}
    .loader-spinner {{
        width: 40px;
        height: 40px;
        border: 3px solid var(--border);
        border-top: 3px solid var(--foreground);
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }}
    @keyframes spin {{
        0% {{ transform: rotate(0deg); }}
        100% {{ transform: rotate(360deg); }}
    }}

    /* Shadcn Card Component */
    .shadcn-card {{
        background-color: var(--card);
        color: var(--card-foreground);
        border-radius: 8px;
        border: 1px solid var(--border);
        padding: 24px 24px 12px 24px;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
        display: flex;
        flex-direction: column;
        gap: 6px;
        animation: fadeIn 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    }}
    .shadcn-card-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 2px;
    }}
    .shadcn-card-title {{
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--muted-foreground);
    }}
    .shadcn-card-value {{
        font-size: 1.875rem;
        font-weight: 700;
        letter-spacing: -0.05em;
        line-height: 1.25;
        color: var(--card-foreground);
    }}
    .shadcn-card-description {{
        font-size: 0.75rem;
        color: var(--muted-foreground);
        margin-bottom: 8px;
    }}

    /* Shadcn Callout / Alert Component */
    .shadcn-alert {{
        background-color: var(--card);
        color: var(--foreground);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 16px;
        display: flex;
        flex-direction: column;
        gap: 4px;
        margin-bottom: 16px;
    }}

    /* Target Streamlit tab buttons to look like Shadcn Tabs */
    div[data-baseweb="tab-list"] {{
        background-color: var(--muted) !important;
        border-radius: 8px !important;
        padding: 4px !important;
        gap: 4px !important;
        border: 1px solid var(--border) !important;
        width: fit-content !important;
        margin-bottom: 24px !important;
    }}
    button[data-baseweb="tab"] {{
        border-radius: 6px !important;
        color: var(--muted-foreground) !important;
        background-color: transparent !important;
        padding: 6px 12px !important;
        font-size: 0.875rem !important;
        font-weight: 500 !important;
        border: none !important;
        transition: all 0.2s ease !important;
    }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        background-color: var(--card) !important;
        color: var(--card-foreground) !important;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px -1px rgba(0, 0, 0, 0.1) !important;
    }}
    div[data-baseweb="tab-highlight-bar"] {{
        display: none !important;
    }}

    /* Style Streamlit Native Buttons to match Shadcn Outline variant */
    div.stButton > button {{
        border: 1px solid var(--border) !important;
        background-color: var(--card) !important;
        color: var(--card-foreground) !important;
        border-radius: 6px !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
        padding: 6px 12px !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05) !important;
    }}
    div.stButton > button:hover {{
        background-color: var(--muted) !important;
        border-color: var(--border) !important;
        color: var(--card-foreground) !important;
    }}
    div.stButton > button:active {{
        background-color: var(--card) !important;
    }}

    /* Clean Slider Handles */
    div[role="slider"] {{
        background-color: var(--card) !important;
        border: 2px solid var(--foreground) !important;
        box-shadow: 0 2px 4px 0 rgba(0, 0, 0, 0.1) !important;
    }}
    
    /* Inline Lucide styling */
    .lucide-icon {{
        display: inline-block;
        vertical-align: middle;
        color: var(--muted-foreground);
    }}
    .lucide-icon-active {{
        display: inline-block;
        vertical-align: middle;
        color: var(--foreground);
    }}

    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(6px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
</style>
""", unsafe_allow_html=True)

# ---------- INLINE LUCIDE ICONS (SVG) ----------
LUCIDE_ACTIVITY = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide-icon"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>'
LUCIDE_MOON = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide-icon"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg>'
LUCIDE_HEART = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide-icon"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/></svg>'
LUCIDE_FLAME = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide-icon"><path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/></svg>'
LUCIDE_BATTERY = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide-icon"><rect width="16" height="10" x="2" y="7" rx="2" ry="2"/><line x1="22" x2="22" y1="11" y2="13"/></svg>'
LUCIDE_WIND = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide-icon"><path d="M12.8 19.6A2 2 0 1 0 14 16H2"/><path d="M17.5 8.02A3 3 0 1 1 20 13H4"/><path d="M9.5 4.5A2.5 2.5 0 1 1 12 7H2"/></svg>'
LUCIDE_DUMBBELL = '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide-icon-active" style="margin-right:8px;"><path d="m6.5 6.5 11 11"/><path d="m21 21-1.5-1.5"/><path d="m3 3 1.5 1.5"/><path d="m18.5 5.5 3 3-1.5 1.5-3-3Z"/><path d="m5.5 18.5 3 3-1.5 1.5-3-3Z"/><path d="M7 5 5 7"/><path d="m19 17 2 2"/></svg>'
LUCIDE_SPARKLES = '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide-icon-active" style="margin-right:8px;"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/></svg>'
LUCIDE_ALERT_TRIANGLE = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide-icon-active" style="margin-right:8px;"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" x2="12" y1="9" y2="13"/><line x1="12" x2="12.01" y1="17" y2="17"/></svg>'

LUCIDE_DATABASE = '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide-icon-active" style="margin-right:8px;"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.66 4.03 3 9 3s9-1.34 9-3V5"/><path d="M3 12c0 1.66 4.03 3 9 3s9-1.34 9-3"/></svg>'
LUCIDE_SEARCH = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide-icon"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>'
LUCIDE_DOWNLOAD = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide-icon"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/></svg>'

# Get last sync time
db_path = Path(__file__).parent.parent / "health.db"
last_sync_str = "Never"
if db_path.exists():
    mtime = db_path.stat().st_mtime
    last_sync_str = datetime.fromtimestamp(mtime).strftime("%b %d, %H:%M")

# Header Row (now inherits correct variables)
cols_header = st.columns([7, 1.5, 1])
with cols_header[0]:
    st.markdown(f"""
        <div style="margin-bottom: 20px;">
            <h1 style="font-size: 2rem; font-weight: 800; letter-spacing: -0.05em; margin: 0;">My Health</h1>
            <p style="font-size: 0.875rem; color: var(--muted-foreground); margin: 2px 0 0 0;">
                Personal biometric tracking & training recommendations &bull; Last synced: {last_sync_str}
            </p>
        </div>
    """, unsafe_allow_html=True)
with cols_header[1]:
    sync_clicked = st.button(
        "Sync Garmin",
        type="primary",
        use_container_width=True,
        help="Fetch today's latest Garmin metrics and update the dashboard.",
    )
with cols_header[2]:
    if st.button(
        "Light" if st.session_state.theme == "dark" else "Dark",
        use_container_width=True,
        help="Switch dashboard theme.",
    ):
        st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
        st.rerun()

sync_error = None
if sync_clicked:
    try:
        with st.spinner("Syncing Garmin data..."):
            from sync import sync_latest

            sync_result = sync_latest()
        st.session_state["garmin_sync_notice"] = sync_result
        st.rerun()
    except ValueError as exc:
        sync_error = str(exc)
    except Exception as exc:
        sync_error = f"Garmin sync failed: {exc}"

if sync_error:
    st.error(sync_error)

sync_notice = st.session_state.pop("garmin_sync_notice", None)
if sync_notice:
    source_count = len(sync_notice["sources"])
    warning_count = sync_notice["warning_count"]
    warning_suffix = f" ({warning_count} endpoint warnings)" if warning_count else ""
    st.success(
        f"Garmin data synced for {sync_notice['date']} from "
        f"{source_count} data sources{warning_suffix}."
    )
# ---------- INITIAL LOADING SCREEN ----------
loader = st.empty()
with loader.container():
    st.markdown("""
    <div class="loader-overlay">
        <div class="loader-spinner"></div>
        <div style="font-size: 0.875rem; font-weight: 500; color: var(--muted-foreground); letter-spacing: 0.05em; text-transform: uppercase;">Loading biometrics...</div>
    </div>
    """, unsafe_allow_html=True)



# ---------- DATA LOADING ----------
df = db.get_df(limit=30)

if df.empty:
    loader.empty()
    st.info("No health data synced yet. Run `python sync.py backfill 14` to fetch data.")
    st.stop()

# Ensure chronological order and get latest row
latest_df = df.iloc[-1]
latest_timestamp = pd.to_datetime(latest_df["date"], errors="coerce")
if pd.isna(latest_timestamp):
    loader.empty()
    st.error("The newest Garmin record has an invalid date and cannot be displayed.")
    st.stop()
latest_date = latest_timestamp.strftime("%Y-%m-%d")

# Clear initial loading screen once data is successfully parsed
loader.empty()

# ---------- SPARKLINE PLOTTER HELPER ----------
def make_sparkline(series, color):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(range(len(series))), y=series,
        mode="lines",
        line=dict(color=color, width=2),
        hoverinfo="none"
    ))
    fig.update_layout(
        template=None,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0),
        height=30,
        showlegend=False
    )
    return fig


def is_available(value):
    return value is not None and pd.notna(value)


def numeric_value(value, default=None):
    """Return a finite float for display/calculations, or a safe default."""
    if not is_available(value):
        return default
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return default
    return numeric if math.isfinite(numeric) else default


def format_int(value, missing="-"):
    numeric = numeric_value(value)
    return str(int(numeric)) if numeric is not None else missing


def format_float(value, digits=1, missing="-"):
    numeric = numeric_value(value)
    return f"{numeric:.{digits}f}" if numeric is not None else missing


def clean_text(value):
    if not is_available(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "nat", "<na>"} else text
# ---------- TABS (EMOJI-LESS PLAIN TEXT HEADERS) ----------
tab_today, tab_trends, tab_comp, tab_ai, tab_recovery, tab_data = st.tabs([
    "Today", 
    "Trends", 
    "Body Comp",
    "AI Insights", 
    "Recovery Forecast",
    "Data"
])


# ==================== TAB 1: TODAY'S SNAPSHOT ====================
with tab_today:
    # Training Readiness Callout Banner
    readiness = numeric_value(latest_df.get("training_readiness"))
    if readiness is not None:
        if readiness >= 80:
            border_indicator = "#10b981" # emerald-500
            qualifier = "Ready for high-intensity training"
        elif readiness >= 50:
            border_indicator = "#f59e0b" # amber-500
            qualifier = "Moderate strain recommended"
        else:
            border_indicator = "#ef4444" # red-500
            qualifier = "Active recovery or rest recommended"
            
        st.markdown(f"""
        <div style="background-color: var(--card); border: 1px solid var(--border); border-left: 4px solid {border_indicator}; border-radius: 8px; padding: 18px; margin-bottom: 24px; box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);">
            <div style="font-size: 0.75rem; color: var(--muted-foreground); text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600;">Training Readiness</div>
            <div style="display: flex; align-items: baseline; gap: 12px; margin-top: 4px;">
                <span style="font-size: 2.25rem; font-weight: 800; letter-spacing: -0.05em; color: var(--card-foreground);">{format_int(readiness)}/100</span>
                <span style="font-size: 0.875rem; font-weight: 500; color: var(--muted-foreground);">• {qualifier}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 5-Column Grid Layout for Biometric Cards with 7-Day Sparkline trends below them
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        hrv_val = numeric_value(latest_df.get("hrv_last_night"))
        st.markdown(f"""
        <div class="shadcn-card">
            <div class="shadcn-card-header">
                <span class="shadcn-card-title">HRV</span>
                {LUCIDE_ACTIVITY}
            </div>
            <div class="shadcn-card-value">{format_int(hrv_val, missing='—')}</div>
            <div class="shadcn-card-description">last night (ms)</div>
        </div>
        """, unsafe_allow_html=True)
        # 7-day sparkline
        hrv_series = df["hrv_last_night"].tail(7).bfill().ffill().tolist()
        if len(hrv_series) > 1:
            st.plotly_chart(make_sparkline(hrv_series, "#6366f1"), config={'displayModeBar': False}, use_container_width=True)

    with col2:
        sleep_val = numeric_value(latest_df.get("sleep_score"))
        st.markdown(f"""
        <div class="shadcn-card">
            <div class="shadcn-card-header">
                <span class="shadcn-card-title">Sleep</span>
                {LUCIDE_MOON}
            </div>
            <div class="shadcn-card-value">{format_int(sleep_val, missing='—')}</div>
            <div class="shadcn-card-description">quality score /100</div>
        </div>
        """, unsafe_allow_html=True)
        # 7-day sparkline
        sleep_series = df["sleep_score"].tail(7).bfill().ffill().tolist()
        if len(sleep_series) > 1:
            st.plotly_chart(make_sparkline(sleep_series, "#8b5cf6"), config={'displayModeBar': False}, use_container_width=True)

    with col3:
        hr_val = numeric_value(latest_df.get("resting_hr"))
        st.markdown(f"""
        <div class="shadcn-card">
            <div class="shadcn-card-header">
                <span class="shadcn-card-title">Resting HR</span>
                {LUCIDE_HEART}
            </div>
            <div class="shadcn-card-value">{format_int(hr_val, missing='—')}</div>
            <div class="shadcn-card-description">beats per min (bpm)</div>
        </div>
        """, unsafe_allow_html=True)
        # 7-day sparkline
        hrv_avg_series = df["resting_hr"].tail(7).bfill().ffill().tolist()
        if len(hrv_avg_series) > 1:
            st.plotly_chart(make_sparkline(hrv_avg_series, "#ef4444"), config={'displayModeBar': False}, use_container_width=True)

    with col4:
        stress_val = numeric_value(latest_df.get("stress_avg"))
        st.markdown(f"""
        <div class="shadcn-card">
            <div class="shadcn-card-header">
                <span class="shadcn-card-title">Stress</span>
                {LUCIDE_FLAME}
            </div>
            <div class="shadcn-card-value">{format_int(stress_val, missing='—')}</div>
            <div class="shadcn-card-description">daily average /100</div>
        </div>
        """, unsafe_allow_html=True)
        # 7-day sparkline
        stress_series = df["stress_avg"].tail(7).bfill().ffill().tolist()
        if len(stress_series) > 1:
            st.plotly_chart(make_sparkline(stress_series, "#f59e0b"), config={'displayModeBar': False}, use_container_width=True)

    with col5:
        bb_val = numeric_value(latest_df.get("bb_min"))
        st.markdown(f"""
        <div class="shadcn-card">
            <div class="shadcn-card-header">
                <span class="shadcn-card-title">Body Battery</span>
                {LUCIDE_BATTERY}
            </div>
            <div class="shadcn-card-value">{format_int(bb_val, missing='—')}</div>
            <div class="shadcn-card-description">lowest level today</div>
        </div>
        """, unsafe_allow_html=True)
        # 7-day sparkline
        bb_series = df["bb_min"].tail(7).bfill().ffill().tolist()
        if len(bb_series) > 1:
            st.plotly_chart(make_sparkline(bb_series, "#10b981"), config={'displayModeBar': False}, use_container_width=True)

    st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)

    # Dynamic Workout split suggestions & Coach's Verdict
    col_gym, col_coach = st.columns([6, 4])
    
    with col_gym:
        st.markdown(f"<h3 style='font-size: 1.25rem; font-weight: 700; letter-spacing: -0.02em; margin-bottom: 12px; display: flex; align-items: center;'>{LUCIDE_DUMBBELL} Dynamic Gym Recommendation</h3>", unsafe_allow_html=True)
        
        # Calculate readiness fallback
        computed_readiness = readiness
        if computed_readiness is None:
            computed_readiness = 50
            if hrv_val and latest_df.get("hrv_weekly_avg"):
                ratio = hrv_val / latest_df["hrv_weekly_avg"]
                if ratio < 0.85: computed_readiness -= 15
                elif ratio > 1.05: computed_readiness += 15
            if sleep_val:
                computed_readiness += (sleep_val - 70) * 0.5
            if stress_val:
                computed_readiness -= (stress_val - 35) * 0.4
            computed_readiness = max(10, min(100, computed_readiness))

        day_name = latest_timestamp.strftime("%A")
        split_suggestions = {
            "Monday": ("Pull Day (Back & Biceps)", ["Deadlifts: 3 sets x 5 reps", "Pull-ups: 3 sets x max", "Barbell Rows: 3 sets x 8 reps", "Hammer Curls: 3 sets x 12 reps"]),
            "Tuesday": ("Push Day (Chest, Shoulders, Triceps)", ["Bench Press: 3 sets x 5 reps", "Overhead Press: 3 sets x 8 reps", "Incline Dumbbell Flyes: 3 sets x 10 reps", "Tricep Pushdowns: 3 sets x 12 reps"]),
            "Wednesday": ("Active Recovery / Core", ["Planks: 3 sets x 1 min", "Hanging Leg Raises: 3 sets x 15 reps", "Zone 2 Cardio: 30 mins (keep HR under 135)"]),
            "Thursday": ("Leg Day (Quads, Hamstrings, Calves)", ["Squats: 3 sets x 5 reps", "Romanian Deadlifts: 3 sets x 10 reps", "Leg Press: 3 sets x 12 reps", "Calf Raises: 4 sets x 15 reps"]),
            "Friday": ("Arms & Core Focus", ["Bicep Curls: 3 sets x 10 reps", "Skull Crushers: 3 sets x 10 reps", "Cable Woodchops: 3 sets x 15 reps", "Zone 2 Cardio: 20 mins"]),
            "Saturday": ("Full Body Conditioning", ["Kettlebell Swings: 4 sets x 15 reps", "Thrusters: 3 sets x 10 reps", "Farmer Walks: 4 sets x 50m", "Rowing Machine: 15 mins HIIT"]),
            "Sunday": ("Rest / Restorative Yoga", ["Deep stretching: 20 mins", "Foam rolling", "Light walk: 30 mins"])
        }
        
        workout_name, movements = split_suggestions.get(day_name, ("Cardio & Core", ["Zone 2 Cardio: 45 mins", "Core"]))
        
        # Adjust movements based on readiness
        if computed_readiness >= 80:
            intensity_badge = "emerald"
            intensity_label = "Optimal Condition (RPE 9)"
            adjusted_movements = movements
        elif computed_readiness >= 55:
            intensity_badge = "amber"
            intensity_label = "Good Condition (RPE 7-8)"
            adjusted_movements = movements
        elif computed_readiness >= 40:
            intensity_badge = "amber"
            intensity_label = "Fatigued (Active Recovery)"
            adjusted_movements = [m.replace("3 sets", "2 sets").replace("4 sets", "2 sets") for m in movements]
            if "Squats" in workout_name or "Deadlifts" in workout_name:
                adjusted_movements = ["Goblet Squats (Light): 2 sets x 12 reps", "Leg Curls: 2 sets x 12 reps", "Cossack Squats: 2 sets x 10 reps"]
                workout_name = "Modified Light Leg Day"
        else:
            intensity_badge = "red"
            intensity_label = "Rest Protocol (HRV low)"
            adjusted_movements = ["Restorative stretching: 20 mins", "Deep diaphragmatic breathing: 10 mins", "Light walk: 20 mins"]
            workout_name = "Rest & HRV Recovery Protocol"
            
        st.markdown(f"""
        <div class="shadcn-card" style="padding: 24px;">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
                <div style="font-size: 1.125rem; font-weight: 700; letter-spacing: -0.02em;">{workout_name}</div>
                <span style="font-size: 0.75rem; font-weight: 600; padding: 2px 8px; border-radius: 4px; border: 1px solid var(--border); background-color: var(--muted); color: var(--foreground);">{intensity_label}</span>
            </div>
            <div style="font-weight: 600; font-size: 0.75rem; color: var(--muted-foreground); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px;">Target Movements</div>
            <div style="display: flex; flex-direction: column; gap: 8px;">
                {"".join(f"<div style='font-size: 0.875rem; padding: 8px 12px; border-radius: 6px; background-color: var(--muted); border: 1px solid var(--border);'>{m}</div>" for m in adjusted_movements)}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    with col_coach:
        st.markdown(f"<h3 style='font-size: 1.25rem; font-weight: 700; letter-spacing: -0.02em; margin-bottom: 12px; display: flex; align-items: center;'>{LUCIDE_ALERT_TRIANGLE} Biometric Verdict</h3>", unsafe_allow_html=True)
        
        verdict_lines = []
        if hrv_val and hrv_val < 50:
            verdict_lines.append("HRV is suppressed: Autonomic nervous system shows stress. Recovery focus recommended.")
        elif hrv_val and latest_df.get("hrv_weekly_avg") and hrv_val < latest_df["hrv_weekly_avg"] * 0.9:
            verdict_lines.append("HRV is below baseline: Suppressed recovery rate. Limit cardiovascular loading.")
            
        if sleep_val and sleep_val < 70:
            verdict_lines.append("Sleep score sub-optimal: Sleep debt accumulated. Target 8h bedtime tonight.")
            
        if hr_val and latest_df.get("hrv_weekly_avg") and hr_val > 75:
            verdict_lines.append("Elevated Resting HR: Overtraining or potential immune response incoming.")
            
        if stress_val and stress_val > 55:
            verdict_lines.append("High Stress Average: Elevated sympathetic output. Diaphragmatic breathing recommended.")
            
        if bb_val is not None and bb_val < 30:
            verdict_lines.append("Low Energy Reserve: Body battery depleted. Deload planned volume.")

        if not verdict_lines:
            verdict_lines.append("Outstanding biometrics: Full parasympathetic recovery. Cleared for maximum loading.")

        # Display clean layout with colored left borders instead of emojis
        st.markdown(f"""
        <div class="shadcn-card" style="padding: 24px; gap: 12px; border-left: 4px solid var(--border);">
            {"".join(f"<div style='font-size: 0.875rem; line-height: 1.5; padding-left: 8px;'>{v}</div>" for v in verdict_lines)}
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom: 16px;'></div>", unsafe_allow_html=True)

        # Weekly Strain vs Recovery Balance progress bar
        weekly_stress = df["stress_avg"].tail(7).mean() or 30
        weekly_sleep = df["sleep_score"].tail(7).mean() or 75
        weekly_hrv_avg = df["hrv_last_night"].tail(7).mean() or 55
        weekly_readiness = df["training_readiness"].tail(7).mean() or 60
        
        strain_score = weekly_stress * 0.6 + (100 - weekly_sleep) * 0.4
        target_hrv = latest_df.get("hrv_weekly_avg") or 60
        hrv_ratio = min(1.2, hrv_val / target_hrv) if hrv_val and target_hrv else 1.0
        recovery_score = weekly_readiness * 0.6 + (hrv_ratio * 40)
        
        tot = strain_score + recovery_score
        strain_pct = (strain_score / tot) * 100 if tot > 0 else 50
        rec_pct = 100 - strain_pct

        st.markdown(f"""
        <div class="shadcn-card" style="padding: 18px; border-left: 4px solid var(--border);">
            <div style="font-size: 0.75rem; color: var(--muted-foreground); text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; margin-bottom: 8px;">Weekly Strain vs Recovery Balance</div>
            <div style="display: flex; height: 10px; border-radius: 5px; overflow: hidden; background-color: var(--muted); border: 1px solid var(--border);">
                <div style="width: {rec_pct:.1f}%; background-color: #10b981;"></div>
                <div style="width: {strain_pct:.1f}%; background-color: #ef4444;"></div>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 0.75rem; margin-top: 6px; font-weight: 500;">
                <span style="color: #10b981;">Recovery ({rec_pct:.0f}%)</span>
                <span style="color: #ef4444;">Strain ({strain_pct:.0f}%)</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ==================== TAB 2: TREND ANALYSIS ====================
with tab_trends:
    st.markdown("<h3 style='font-size: 1.25rem; font-weight: 700; letter-spacing: -0.02em; margin-bottom: 6px;'>Biometric Trends</h3>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 0.875rem; color: var(--muted-foreground); margin: 0 0 16px 0;'>Track direction, compare against broad wellness reference ranges, and spot improvement opportunities.</p>", unsafe_allow_html=True)

    trend_all_df = db.get_df(limit=None).copy()
    trend_all_df["date"] = pd.to_datetime(trend_all_df["date"], errors="coerce")
    trend_all_df = trend_all_df.dropna(subset=["date"]).sort_values("date")

    if len(trend_all_df) > 1:
        range_col, focus_col = st.columns([2, 3])
        with range_col:
            trend_range = st.selectbox("Time range", ["30 days", "90 days", "180 days", "All"], index=0)
        with focus_col:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            st.caption("Reference bands are broad adult wellness ranges, not diagnostic thresholds. Personal baseline matters most for HRV and recovery metrics.")

        if trend_range == "All":
            trend_df = trend_all_df.copy()
        else:
            days = int(trend_range.split()[0])
            cutoff = trend_all_df["date"].max() - pd.Timedelta(days=days - 1)
            trend_df = trend_all_df[trend_all_df["date"] >= cutoff].copy()

        if len(trend_df) < 2:
            st.info("Not enough records in this range, so Trends is showing all available history.")
            trend_df = trend_all_df.copy()

        def metric_mean(frame, col):
            return frame[col].mean() if col in frame.columns and frame[col].notna().any() else None

        def metric_latest(frame, col):
            if col not in frame.columns or frame[col].dropna().empty:
                return None
            return frame[col].dropna().iloc[-1]

        def fmt_value(value, suffix="", decimals=0):
            if value is None or pd.isna(value):
                return "-"
            if decimals == 0:
                return f"{value:.0f}{suffix}"
            return f"{value:.{decimals}f}{suffix}"

        def clamp(value, low=0, high=100):
            if value is None or pd.isna(value):
                return None
            return max(low, min(high, value))

        latest_hrv = metric_latest(trend_df, "hrv_last_night")
        latest_hrv_base = metric_latest(trend_df, "hrv_weekly_avg") or metric_mean(trend_df.tail(7), "hrv_last_night")
        latest_sleep = metric_latest(trend_df, "sleep_score")
        latest_rhr = metric_latest(trend_df, "resting_hr")
        latest_stress = metric_latest(trend_df, "stress_avg")
        latest_bb = metric_latest(trend_df, "bb_min")
        latest_readiness = metric_latest(trend_df, "training_readiness")

        recovery_parts = []
        if latest_hrv is not None and latest_hrv_base and latest_hrv_base > 0:
            recovery_parts.append(clamp((latest_hrv / latest_hrv_base) * 100))
        if latest_sleep is not None:
            recovery_parts.append(clamp(latest_sleep))
        if latest_stress is not None:
            recovery_parts.append(clamp(100 - latest_stress))
        if latest_bb is not None:
            recovery_parts.append(clamp(latest_bb))
        if latest_readiness is not None:
            recovery_parts.append(clamp(latest_readiness))
        recovery_index = sum(recovery_parts) / len(recovery_parts) if recovery_parts else None

        hrv_delta = latest_hrv - latest_hrv_base if latest_hrv is not None and latest_hrv_base is not None else None
        avg_sleep_hours = metric_mean(trend_df, "sleep_duration")
        avg_sleep_hours = avg_sleep_hours / 3600 if avg_sleep_hours is not None else None
        sleep_debt = max(0, 7 - avg_sleep_hours) if avg_sleep_hours is not None else None
        avg_rhr = metric_mean(trend_df, "resting_hr")

        st.markdown("""
        <style>
        .trend-card-row { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-bottom: 16px; }
        .trend-mini-card { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 14px 16px; }
        .trend-mini-label { color: var(--muted-foreground); font-size: 0.72rem; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase; }
        .trend-mini-value { color: var(--foreground); font-size: 1.35rem; font-weight: 800; line-height: 1.25; margin-top: 3px; }
        .trend-mini-sub { color: var(--muted-foreground); font-size: 0.78rem; margin-top: 2px; }
        .reference-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin: 10px 0 18px 0; }
        .reference-card { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 14px; border-left: 4px solid var(--border); }
        .reference-title { font-size: 0.78rem; color: var(--muted-foreground); text-transform: uppercase; letter-spacing: 0.05em; font-weight: 700; }
        .reference-value { font-size: 1rem; font-weight: 800; margin-top: 4px; }
        .reference-note { font-size: 0.78rem; color: var(--muted-foreground); margin-top: 4px; line-height: 1.4; }
        @media (max-width: 900px) { .trend-card-row, .reference-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
        @media (max-width: 520px) { .trend-card-row, .reference-grid { grid-template-columns: 1fr; } }
        </style>
        """, unsafe_allow_html=True)

        hrv_delta_label = fmt_value(hrv_delta, " ms") if hrv_delta is not None else "-"
        hrv_delta_sub = "vs current 7-day baseline" if hrv_delta is not None else "needs HRV baseline"
        sleep_debt_label = fmt_value(sleep_debt, "h", 1) if sleep_debt is not None else "-"
        rhr_label = fmt_value(avg_rhr, " bpm")

        st.markdown(f"""
        <div class="trend-card-row">
            <div class="trend-mini-card"><div class="trend-mini-label">Recovery Index</div><div class="trend-mini-value">{fmt_value(recovery_index, '/100')}</div><div class="trend-mini-sub">latest blended recovery signal</div></div>
            <div class="trend-mini-card"><div class="trend-mini-label">HRV Delta</div><div class="trend-mini-value">{hrv_delta_label}</div><div class="trend-mini-sub">{hrv_delta_sub}</div></div>
            <div class="trend-mini-card"><div class="trend-mini-label">Sleep Debt</div><div class="trend-mini-value">{sleep_debt_label}</div><div class="trend-mini-sub">avg shortfall from 7h target</div></div>
            <div class="trend-mini-card"><div class="trend-mini-label">Avg Resting HR</div><div class="trend-mini-value">{rhr_label}</div><div class="trend-mini-sub">selected range average</div></div>
        </div>
        """, unsafe_allow_html=True)

        # Create derived trend series.
        derived_df = trend_df.copy()
        derived_df["hrv_baseline"] = derived_df["hrv_weekly_avg"] if "hrv_weekly_avg" in derived_df.columns else pd.NA
        if "hrv_last_night" in derived_df.columns:
            derived_df["hrv_baseline"] = derived_df["hrv_baseline"].fillna(derived_df["hrv_last_night"].rolling(7, min_periods=2).mean())
            derived_df["hrv_delta"] = derived_df["hrv_last_night"] - derived_df["hrv_baseline"]
        score_components = []
        if "hrv_last_night" in derived_df.columns:
            score_components.append(((derived_df["hrv_last_night"] / derived_df["hrv_baseline"]) * 100).clip(0, 100))
        if "sleep_score" in derived_df.columns:
            score_components.append(derived_df["sleep_score"].clip(0, 100))
        if "stress_avg" in derived_df.columns:
            score_components.append((100 - derived_df["stress_avg"]).clip(0, 100))
        if "bb_min" in derived_df.columns:
            score_components.append(derived_df["bb_min"].clip(0, 100))
        if "training_readiness" in derived_df.columns:
            score_components.append(derived_df["training_readiness"].clip(0, 100))
        if score_components:
            derived_df["recovery_index"] = pd.concat(score_components, axis=1).mean(axis=1)

        reference_items = []
        if avg_rhr is not None:
            if avg_rhr < 60:
                rhr_status = "Athletic/low"
                rhr_color = "#10b981"
            elif avg_rhr <= 100:
                rhr_status = "Within adult range"
                rhr_color = "#10b981"
            else:
                rhr_status = "Above adult range"
                rhr_color = "#ef4444"
            reference_items.append(("Resting HR", rhr_status, "Adult reference: 60-100 bpm; trained athletes may be lower.", rhr_color))
        if avg_sleep_hours is not None:
            sleep_status = "On target" if avg_sleep_hours >= 7 else "Below 7h target"
            sleep_color = "#10b981" if avg_sleep_hours >= 7 else "#f59e0b"
            reference_items.append(("Sleep Duration", sleep_status, f"Average: {avg_sleep_hours:.1f}h. Adult guidance commonly starts at 7h/night.", sleep_color))
        spo2_avg = metric_mean(trend_df, "spo2_avg")
        if spo2_avg is not None:
            spo2_status = "Typical" if spo2_avg >= 95 else "Watch trend"
            spo2_color = "#10b981" if spo2_avg >= 95 else "#f59e0b"
            reference_items.append(("SpO2", spo2_status, f"Average: {spo2_avg:.1f}%. Typical pulse ox readings are often 95-100%.", spo2_color))
        resp_avg = metric_mean(trend_df, "respiration_avg")
        if resp_avg is not None:
            resp_status = "Typical" if 12 <= resp_avg <= 20 else "Outside common band"
            resp_color = "#10b981" if 12 <= resp_avg <= 20 else "#f59e0b"
            reference_items.append(("Respiration", resp_status, f"Average: {resp_avg:.1f}/min. Common adult resting band: 12-20/min.", resp_color))

        if reference_items:
            st.markdown("<h4 style='font-size: 1rem; font-weight: 700; letter-spacing: -0.01em; margin-top: 8px; margin-bottom: 8px;'>Reference Range Snapshot</h4>", unsafe_allow_html=True)
            st.markdown(f"""
            <div class="reference-grid">
                {''.join(f'<div class="reference-card" style="border-left-color: {color};"><div class="reference-title">{title}</div><div class="reference-value">{status}</div><div class="reference-note">{note}</div></div>' for title, status, note, color in reference_items)}
            </div>
            """, unsafe_allow_html=True)

        # Improvement trend: blended recovery index and HRV baseline deviation.
        if "recovery_index" in derived_df.columns and derived_df["recovery_index"].notna().any():
            fig_improve = go.Figure()
            fig_improve.add_trace(go.Scatter(
                x=derived_df["date"], y=derived_df["recovery_index"],
                mode="lines+markers", name="Recovery Index",
                line=dict(color="#2563eb", width=3), marker=dict(size=5)
            ))
            if "training_readiness" in derived_df.columns and derived_df["training_readiness"].notna().any():
                fig_improve.add_trace(go.Scatter(
                    x=derived_df["date"], y=derived_df["training_readiness"],
                    mode="lines", name="Training Readiness",
                    line=dict(color="#10b981", width=2, dash="dot")
                ))
            fig_improve.add_hrect(y0=75, y1=100, fillcolor="rgba(16,185,129,0.08)", line_width=0)
            fig_improve.add_hrect(y0=0, y1=50, fillcolor="rgba(239,68,68,0.06)", line_width=0)
            fig_improve.update_layout(
                template=plotly_template,
                title="Improvement Trend: Recovery Index",
                hovermode="x unified",
                yaxis=dict(title="Score", range=[0, 100], gridcolor=grid_color),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                height=320,
                margin=dict(l=40, r=40, t=40, b=30),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_improve, use_container_width=True)

        col_base, col_load = st.columns(2)
        with col_base:
            if "hrv_delta" in derived_df.columns and derived_df["hrv_delta"].notna().any():
                hrv_colors = ["#10b981" if val >= 0 else "#ef4444" for val in derived_df["hrv_delta"].fillna(0)]
                fig_hrv_delta = go.Figure()
                fig_hrv_delta.add_trace(go.Bar(
                    x=derived_df["date"], y=derived_df["hrv_delta"],
                    name="HRV vs Baseline", marker_color=hrv_colors
                ))
                fig_hrv_delta.add_hline(y=0, line_color=grid_color)
                fig_hrv_delta.update_layout(
                    template=plotly_template,
                    title="HRV Baseline Deviation",
                    yaxis=dict(title="ms vs baseline", gridcolor=grid_color),
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    height=280,
                    margin=dict(l=40, r=30, t=40, b=30),
                    showlegend=False
                )
                st.plotly_chart(fig_hrv_delta, use_container_width=True)

        with col_load:
            if "training_readiness" in trend_df.columns and trend_df["training_readiness"].notna().any():
                fig_load = go.Figure()
                fig_load.add_trace(go.Scatter(
                    x=trend_df["date"], y=trend_df["training_readiness"],
                    mode="lines+markers", name="Readiness",
                    line=dict(color="#10b981", width=2), marker=dict(size=4)
                ))
                if "stress_avg" in trend_df.columns and trend_df["stress_avg"].notna().any():
                    fig_load.add_trace(go.Bar(
                        x=trend_df["date"], y=trend_df["stress_avg"],
                        name="Stress Load", marker_color="rgba(245,158,11,0.45)"
                    ))
                fig_load.update_layout(
                    template=plotly_template,
                    title="Readiness vs Stress Load",
                    hovermode="x unified",
                    yaxis=dict(title="Score", range=[0, 100], gridcolor=grid_color),
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    height=280,
                    margin=dict(l=40, r=30, t=40, b=30),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_load, use_container_width=True)

        # Pie chart section.
        pie_left, pie_mid, pie_right = st.columns(3)
        with pie_left:
            sleep_cols = ["sleep_deep", "sleep_rem", "sleep_light", "sleep_awake"]
            if all(col in trend_df.columns for col in sleep_cols) and trend_df[sleep_cols].notna().any().any():
                sleep_values = [trend_df[col].mean() / 3600 for col in sleep_cols]
                fig_sleep_pie = go.Figure(data=[go.Pie(
                    labels=["Deep", "REM", "Light", "Awake"], values=sleep_values,
                    hole=0.52,
                    marker=dict(colors=["#1e1b4b", "#4f46e5", "#818cf8", "#d4d4d8"]),
                    textinfo="label+percent"
                )])
                fig_sleep_pie.update_layout(
                    template=plotly_template,
                    title="Average Sleep Mix",
                    height=290,
                    margin=dict(l=10, r=10, t=40, b=10),
                    showlegend=False,
                    paper_bgcolor="rgba(0,0,0,0)"
                )
                st.plotly_chart(fig_sleep_pie, use_container_width=True)
        with pie_mid:
            if recovery_index is not None:
                strain_index = max(0, 100 - recovery_index)
                fig_balance_pie = go.Figure(data=[go.Pie(
                    labels=["Recovery", "Strain"], values=[recovery_index, strain_index],
                    hole=0.58,
                    marker=dict(colors=["#10b981", "#ef4444"]),
                    textinfo="label+percent"
                )])
                fig_balance_pie.update_layout(
                    template=plotly_template,
                    title="Current Recovery Balance",
                    height=290,
                    margin=dict(l=10, r=10, t=40, b=10),
                    showlegend=False,
                    paper_bgcolor="rgba(0,0,0,0)"
                )
                st.plotly_chart(fig_balance_pie, use_container_width=True)
        with pie_right:
            readiness_source = derived_df["recovery_index"] if "recovery_index" in derived_df.columns else trend_df.get("training_readiness")
            if readiness_source is not None and readiness_source.notna().any():
                ready_days = int((readiness_source >= 75).sum())
                moderate_days = int(((readiness_source >= 50) & (readiness_source < 75)).sum())
                low_days = int((readiness_source < 50).sum())
                fig_days_pie = go.Figure(data=[go.Pie(
                    labels=["Ready", "Moderate", "Recovery Focus"], values=[ready_days, moderate_days, low_days],
                    hole=0.52,
                    marker=dict(colors=["#10b981", "#f59e0b", "#ef4444"]),
                    textinfo="label+percent"
                )])
                fig_days_pie.update_layout(
                    template=plotly_template,
                    title="Days by Recovery State",
                    height=290,
                    margin=dict(l=10, r=10, t=40, b=10),
                    showlegend=False,
                    paper_bgcolor="rgba(0,0,0,0)"
                )
                st.plotly_chart(fig_days_pie, use_container_width=True)

        # Chart 1: HRV vs Resting HR with adult reference band for resting HR.
        fig_hr = go.Figure()
        if "hrv_last_night" in trend_df.columns and trend_df["hrv_last_night"].notna().any():
            fig_hr.add_trace(go.Scatter(
                x=trend_df["date"], y=trend_df["hrv_last_night"],
                mode="lines+markers", name="HRV (ms)",
                line=dict(color="#6366f1", width=2),
                marker=dict(size=4)
            ))
        if "resting_hr" in trend_df.columns and trend_df["resting_hr"].notna().any():
            fig_hr.add_trace(go.Scatter(
                x=trend_df["date"], y=trend_df["resting_hr"],
                mode="lines+markers", name="Resting HR (bpm)",
                line=dict(color="#ef4444", width=2),
                marker=dict(size=4),
                yaxis="y2"
            ))
            fig_hr.add_hrect(y0=60, y1=100, yref="y2", fillcolor="rgba(16,185,129,0.06)", line_width=0)
        fig_hr.update_layout(
            template=plotly_template,
            title="HRV and Resting Heart Rate",
            hovermode="x unified",
            yaxis=dict(title="HRV (ms)", side="left", gridcolor=grid_color),
            yaxis2=dict(title="Resting HR (bpm)", overlaying="y", side="right", showgrid=False),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            height=300,
            margin=dict(l=40, r=40, t=40, b=30),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_hr, use_container_width=True)

        # Chart 2: Sleep Architecture Breakdown (Stacked Bar)
        if "sleep_deep" in trend_df.columns and trend_df["sleep_deep"].notna().any():
            fig_sleep_arch = go.Figure()
            deep_hrs = trend_df["sleep_deep"] / 3600.0
            rem_hrs = trend_df["sleep_rem"] / 3600.0
            light_hrs = trend_df["sleep_light"] / 3600.0
            awake_hrs = trend_df["sleep_awake"] / 3600.0
            total_sleep_hrs = trend_df["sleep_duration"] / 3600.0 if "sleep_duration" in trend_df.columns else deep_hrs + rem_hrs + light_hrs

            fig_sleep_arch.add_trace(go.Bar(x=trend_df["date"], y=deep_hrs, name="Deep Sleep", marker_color="#1e1b4b"))
            fig_sleep_arch.add_trace(go.Bar(x=trend_df["date"], y=rem_hrs, name="REM Sleep", marker_color="#4f46e5"))
            fig_sleep_arch.add_trace(go.Bar(x=trend_df["date"], y=light_hrs, name="Light Sleep", marker_color="#818cf8"))
            fig_sleep_arch.add_trace(go.Bar(x=trend_df["date"], y=awake_hrs, name="Awake Time", marker_color="#e4e4e7"))
            fig_sleep_arch.add_trace(go.Scatter(x=trend_df["date"], y=total_sleep_hrs.rolling(7, min_periods=2).mean(), name="7d Avg Total", line=dict(color="#111827", width=2), mode="lines"))
            fig_sleep_arch.add_hline(y=7, line_dash="dash", line_color="#10b981")

            fig_sleep_arch.update_layout(
                template=plotly_template,
                barmode="stack",
                title="Sleep Architecture and 7h Target",
                yaxis=dict(title="Duration (Hours)", gridcolor=grid_color),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                height=320,
                margin=dict(l=40, r=40, t=40, b=30),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_sleep_arch, use_container_width=True)

        # Chart 3: Stress vs Body Battery
        fig_stress = go.Figure()
        if "stress_avg" in trend_df.columns and trend_df["stress_avg"].notna().any():
            fig_stress.add_trace(go.Scatter(
                x=trend_df["date"], y=trend_df["stress_avg"],
                mode="lines+markers", name="Stress Avg",
                line=dict(color="#f59e0b", width=2),
                marker=dict(size=4)
            ))
            fig_stress.add_trace(go.Scatter(
                x=trend_df["date"], y=trend_df["stress_avg"].rolling(7, min_periods=2).mean(),
                mode="lines", name="Stress 7d Avg",
                line=dict(color="#b45309", width=2, dash="dot")
            ))
        if "bb_min" in trend_df.columns and trend_df["bb_min"].notna().any():
            fig_stress.add_trace(go.Scatter(
                x=trend_df["date"], y=trend_df["bb_min"],
                mode="lines+markers", name="Body Battery Min",
                line=dict(color="#10b981", width=2),
                marker=dict(size=4)
            ))
        fig_stress.update_layout(
            template=plotly_template,
            title="Stress Load and Body Battery",
            hovermode="x unified",
            yaxis=dict(title="Score (0-100)", side="left", range=[0, 100], gridcolor=grid_color),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            height=300,
            margin=dict(l=40, r=40, t=40, b=30),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_stress, use_container_width=True)

        col_left, col_right = st.columns(2)
        with col_left:
            if "sleep_score" in trend_df.columns and trend_df["sleep_score"].notna().any():
                fig_sleep = go.Figure()
                fig_sleep.add_trace(go.Bar(
                    x=trend_df["date"], y=trend_df["sleep_score"],
                    name="Sleep Score",
                    marker_color="#8b5cf6"
                ))
                fig_sleep.update_layout(
                    template=plotly_template,
                    title="Sleep Quality Score",
                    yaxis=dict(range=[0, 100], gridcolor=grid_color),
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    height=250,
                    margin=dict(l=40, r=40, t=30, b=30)
                )
                st.plotly_chart(fig_sleep, use_container_width=True)

        with col_right:
            if "steps" in trend_df.columns and trend_df["steps"].notna().any():
                fig_steps = go.Figure()
                fig_steps.add_trace(go.Bar(
                    x=trend_df["date"], y=trend_df["steps"],
                    name="Steps",
                    marker_color="#06b6d4"
                ))
                fig_steps.add_hline(y=8000, line_dash="dash", line_color="#f59e0b")
                fig_steps.update_layout(
                    template=plotly_template,
                    title="Daily Steps and 8k Target",
                    yaxis=dict(gridcolor=grid_color),
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    height=250,
                    margin=dict(l=40, r=40, t=30, b=30)
                )
                st.plotly_chart(fig_steps, use_container_width=True)

        # Pulse Ox & Respiration Chart
        if "spo2_avg" in trend_df.columns and trend_df["spo2_avg"].notna().any():
            fig_spo2 = go.Figure()
            fig_spo2.add_hrect(y0=95, y1=100, fillcolor="rgba(16,185,129,0.08)", line_width=0)
            fig_spo2.add_trace(go.Scatter(
                x=trend_df["date"], y=trend_df["spo2_avg"],
                mode="lines+markers", name="Pulse Ox (SpO2 %)",
                line=dict(color="#06b6d4", width=2),
                marker=dict(size=4)
            ))
            if "spo2_min" in trend_df.columns and trend_df["spo2_min"].notna().any():
                fig_spo2.add_trace(go.Scatter(
                    x=trend_df["date"], y=trend_df["spo2_min"],
                    mode="markers", name="SpO2 Min",
                    marker=dict(color="#ef4444", size=6)
                ))
            if "respiration_avg" in trend_df.columns and trend_df["respiration_avg"].notna().any():
                fig_spo2.add_trace(go.Scatter(
                    x=trend_df["date"], y=trend_df["respiration_avg"],
                    mode="lines+markers", name="Respiration (br/min)",
                    line=dict(color="#10b981", width=2),
                    marker=dict(size=4),
                    yaxis="y2"
                ))
            fig_spo2.update_layout(
                template=plotly_template,
                title="Pulse Ox, Min SpO2, and Respiration Rate",
                hovermode="x unified",
                yaxis=dict(title="SpO2 (%)", side="left", range=[80, 100], gridcolor=grid_color),
                yaxis2=dict(title="Breaths/min", overlaying="y", side="right", range=[10, 25], showgrid=False),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                height=300,
                margin=dict(l=40, r=40, t=40, b=30),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_spo2, use_container_width=True)

        # Automated Correlation Discovery Panel
        st.markdown("<h3 style='font-size: 1.125rem; font-weight: 700; letter-spacing: -0.02em; margin-top: 24px; margin-bottom: 12px;'>Biometric Correlation Insights</h3>", unsafe_allow_html=True)

        cols = ["hrv_last_night", "sleep_score", "resting_hr", "stress_avg", "steps", "training_readiness"]
        available_cols = [c for c in cols if c in trend_df.columns and trend_df[c].notna().sum() > 5]

        insights = []
        if len(available_cols) >= 2:
            corr_matrix = trend_df[available_cols].corr()
            if "hrv_last_night" in corr_matrix.index and "stress_avg" in corr_matrix.columns:
                val = corr_matrix.loc["hrv_last_night", "stress_avg"]
                if val < -0.35:
                    insights.append(f"Daytime stress averages and sleep recovery (HRV) are negatively correlated ({val:.2f}). Higher stress may be suppressing recovery.")
            if "hrv_last_night" in corr_matrix.index and "sleep_score" in corr_matrix.columns:
                val = corr_matrix.loc["hrv_last_night", "sleep_score"]
                if val > 0.35:
                    insights.append(f"Sleep score and overnight HRV show a positive correlation ({val:.2f}). Quality sleep appears to support autonomic recovery.")
            if "resting_hr" in corr_matrix.index and "hrv_last_night" in corr_matrix.columns:
                val = corr_matrix.loc["resting_hr", "hrv_last_night"]
                if val < -0.4:
                    insights.append(f"Resting HR and HRV are strongly inversely linked ({val:.2f}). Lower waking heart rate aligns with stronger parasympathetic recovery.")
            if "steps" in corr_matrix.index and "sleep_score" in corr_matrix.columns:
                val = corr_matrix.loc["steps", "sleep_score"]
                if val > 0.25:
                    insights.append(f"Higher step counts show a positive relationship ({val:.2f}) with sleep quality score in this range.")
            if "training_readiness" in corr_matrix.index and "stress_avg" in corr_matrix.columns:
                val = corr_matrix.loc["training_readiness", "stress_avg"]
                if val < -0.35:
                    insights.append(f"Training readiness falls as stress rises ({val:.2f}). Watch cumulative stress before harder sessions.")

        if not insights:
            insights.append("Still gathering enough variation to discover reliable correlations. Keep logging consistently.")

        st.markdown(f"""
        <div class="shadcn-card" style="padding: 20px; gap: 8px; border-left: 4px solid var(--border);">
            {''.join(f"<div style='font-size: 0.875rem; line-height: 1.5; padding: 4px 0;'>{ins}</div>" for ins in insights)}
        </div>
        """, unsafe_allow_html=True)

    else:
        st.info("Accumulating data. Wear watch consistently to show trend charts.")

# ==================== TAB 3: BODY COMPOSITION ====================
with tab_comp:
    st.markdown("<h3 style='font-size: 1.25rem; font-weight: 700; letter-spacing: -0.02em; margin-bottom: 16px;'>Body Composition Tracking</h3>", unsafe_allow_html=True)
    
    col_input, col_chart = st.columns([4, 8])
    
    with col_input:
        st.markdown("<div style='font-size: 0.875rem; font-weight: 600; margin-bottom: 8px;'>Log New Entry</div>", unsafe_allow_html=True)
        with st.form("body_comp_form", clear_on_submit=True):
            weight_input = st.number_input("Weight (kg)", 30.0, 200.0, 75.0, 0.1)
            fat_input = st.number_input("Body Fat (%)", 2.0, 50.0, 15.0, 0.1)
            waist_input = st.number_input("Waist (cm)", 40.0, 150.0, 80.0, 0.5)
            submit_comp = st.form_submit_button("Save Entry")
            if submit_comp:
                db.save_body_comp(date.today().strftime("%Y-%m-%d"), weight_input, fat_input, waist_input)
                st.success("Saved successfully!")
                st.rerun()
                
    comp_df = db.get_body_comp_df(limit=30)
    
    with col_chart:
        if not comp_df.empty:
            fig_comp = go.Figure()
            fig_comp.add_trace(go.Scatter(
                x=comp_df["date"], y=comp_df["weight"],
                mode="lines+markers", name="Weight (kg)",
                line=dict(color="#2563eb", width=2),
                marker=dict(size=4)
            ))
            if "body_fat" in comp_df.columns and comp_df["body_fat"].notna().any():
                fig_comp.add_trace(go.Scatter(
                    x=comp_df["date"], y=comp_df["body_fat"],
                    mode="lines+markers", name="Body Fat (%)",
                    line=dict(color="#db2777", width=2),
                    marker=dict(size=4),
                    yaxis="y2"
                ))
            fig_comp.update_layout(
                template=plotly_template,
                hovermode="x unified",
                yaxis=dict(title="Weight (kg)", side="left", gridcolor=grid_color),
                yaxis2=dict(title="Body Fat (%)", overlaying="y", side="right", showgrid=False),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                height=320,
                margin=dict(l=40, r=40, t=10, b=30),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_comp, use_container_width=True)
        else:
            st.markdown("""
            <div class="shadcn-card" style="padding: 24px; height: 320px; display: flex; justify-content: center; align-items: center; flex-direction: column;">
                <div style="font-weight: 600; font-size: 0.875rem;">No Data to Display</div>
                <p style="font-size: 0.875rem; color: var(--muted-foreground); margin-top: 4px; text-align: center;">
                    Log your daily weight and body fat % to generate composition trend lines.
                </p>
            </div>
            """, unsafe_allow_html=True)
            
    if not comp_df.empty:
        st.markdown("<h4 style='font-size: 1rem; font-weight: 700; letter-spacing: -0.01em; margin-top: 24px; margin-bottom: 12px;'>Logged Entries</h4>", unsafe_allow_html=True)
        styled_df = comp_df[["date", "weight", "body_fat", "waist"]].rename(columns={
            "date": "Date",
            "weight": "Weight (kg)",
            "body_fat": "Body Fat (%)",
            "waist": "Waist (cm)"
        }).sort_values(by="Date", ascending=False)
        st.dataframe(styled_df, hide_index=True, use_container_width=True)

# ==================== TAB 4: AI INSIGHTS ====================
with tab_ai:
    st.markdown(f"<h3 style='font-size: 1.25rem; font-weight: 700; letter-spacing: -0.02em; margin-bottom: 12px; display: flex; align-items: center;'>{LUCIDE_SPARKLES} AI Coach Biometric Insights</h3>", unsafe_allow_html=True)

    # Prefer the newly generated report in session state so the UI updates immediately.
    saved_ai_summary = clean_text(latest_df.get("ai_summary"))
    generated_ai_summary = clean_text(st.session_state.get("generated_ai_summary"))
    if saved_ai_summary and saved_ai_summary != generated_ai_summary:
        st.session_state["generated_ai_summary"] = saved_ai_summary
        generated_ai_summary = saved_ai_summary
    ai_summary = generated_ai_summary or saved_ai_summary

    if ai_summary:
        with st.container(border=True):
            st.markdown(ai_summary)
    else:
        st.markdown("""
        <div class="shadcn-card" style="padding: 24px;">
            <div style="font-weight: 600; font-size: 0.875rem;">No AI Summary Found</div>
            <p style="font-size: 0.875rem; color: var(--muted-foreground); margin-top: 4px;">
                You can generate a biometric coaching analysis from your SQLite database history on-demand using the button below.
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)
    if st.button("Generate On-Demand AI Report"):
        with st.spinner("AI Coach is compiling biometric analysis..."):
            try:
                from ai_coach import generate_weekly_report
                report = generate_weekly_report(days=7)
                cleaned_report = clean_text(report)
                if cleaned_report:
                    st.session_state["generated_ai_summary"] = cleaned_report
                    st.rerun()
                else:
                    st.error("AI Coach finished, but the generated report was empty. No summary was saved.")
            except Exception as e:
                st.error(
                    "AI Coach could not generate the report. "
                    f"Reason: {e}"
                )

    st.markdown("---")
    
    # Heuristic Flag Callouts (Emoji-free)
    st.markdown("<h4 style='font-size: 1rem; font-weight: 700; letter-spacing: -0.01em; margin-bottom: 12px;'>Biometric Anomalies Flagged</h4>", unsafe_allow_html=True)
    
    col_flag1, col_flag2 = st.columns(2)
    
    with col_flag1:
        # Alcohol
        sleep_stress = numeric_value(latest_df.get("stress_avg"))
        rhr = numeric_value(latest_df.get("resting_hr"))
        weekly_rhr = numeric_value(df["resting_hr"].mean())
        weekly_hrv = numeric_value(
            df["hrv_weekly_avg"].iloc[-1]
            if not df["hrv_weekly_avg"].empty
            else df["hrv_last_night"].mean()
        )
        
        is_alcohol = False
        if sleep_stress and sleep_stress > 45 and rhr and weekly_rhr and rhr > weekly_rhr + 6 and hrv_val and weekly_hrv and hrv_val < weekly_hrv * 0.82:
            is_alcohol = True
            
        if is_alcohol or latest_df.get("alcohol_logged") == 1:
            st.markdown(f"""
            <div class="shadcn-alert" style="border-left: 4px solid #ef4444;">
                <div style="font-weight: 700; color: #ef4444; font-size: 0.875rem;">Recovery Disruption Alert</div>
                <div style="font-size: 0.875rem; margin-top: 4px; line-height: 1.5;">
                    Metabolic strain detected (matching alcohol or immune activity):
                    <ul style="margin-left: 16px; margin-top: 4px;">
                        <li>Resting HR: {int(rhr)} bpm (+{int(rhr - weekly_rhr)} bpm over baseline)</li>
                        <li>HRV suppressed by {int((1 - hrv_val/weekly_hrv)*100)}% ({int(hrv_val)}ms vs {int(weekly_hrv)}ms)</li>
                    </ul>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="shadcn-alert" style="border-left: 4px solid #10b981;">
                <div style="font-weight: 700; color: #10b981; font-size: 0.875rem;">Recovery Balance Normal</div>
                <p style="font-size: 0.875rem; margin-top: 4px; line-height: 1.5; color: var(--muted-foreground);">
                    No systemic metabolic stress signatures detected. Autonomic recovery indicators remain inside typical baseline variance.
                </p>
            </div>
            """, unsafe_allow_html=True)

    with col_flag2:
        # Apnea
        spo2_min_val = numeric_value(latest_df.get("spo2_min"))
        resp_avg_val = numeric_value(latest_df.get("respiration_avg"))
        
        is_apnea = False
        if spo2_min_val and spo2_min_val < 90:
            is_apnea = True
            
        if is_apnea or latest_df.get("sleep_apnea_flag") == 1:
            st.markdown(f"""
            <div class="shadcn-alert" style="border-left: 4px solid #f59e0b;">
                <div style="font-weight: 700; color: #f59e0b; font-size: 0.875rem;">Sleep Desaturation Flagged</div>
                <div style="font-size: 0.875rem; margin-top: 4px; line-height: 1.5;">
                    Blood oxygen desaturation events occurred during sleep:
                    <ul style="margin-left: 16px; margin-top: 4px;">
                        <li>SpO2 minimum dropped to {int(spo2_min_val)}% (normal is >92%)</li>
                        <li>Respiration: {f"{resp_avg_val:.1f}" if resp_avg_val else "—"} breaths/min</li>
                    </ul>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="shadcn-alert" style="border-left: 4px solid #10b981;">
                <div style="font-weight: 700; color: #10b981; font-size: 0.875rem;">Oxygen Levels Stable</div>
                <p style="font-size: 0.875rem; margin-top: 4px; line-height: 1.5; color: var(--muted-foreground);">
                    No blood oxygen desaturation incidents registered during sleep. Overnight SpO2 values stayed stable.
                </p>
            </div>
            """, unsafe_allow_html=True)

# ==================== TAB 4: RECOVERY FORECAST ====================
with tab_recovery:
    st.markdown("<h3 style='font-size: 1.25rem; font-weight: 700; letter-spacing: -0.02em; margin-bottom: 8px;'>Athletic Recovery Forecast Model</h3>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 0.875rem; color: var(--muted-foreground); margin-bottom: 24px;'>Simulate sleeping hours and workout intensity to project nervous system recovery rate.</p>", unsafe_allow_html=True)
    
    current_hrv_val = hrv_val if hrv_val is not None else 50
    target_hrv_val = weekly_hrv if weekly_hrv is not None else 60
    deficit = target_hrv_val - current_hrv_val
    
    col_inputs, col_results = st.columns([4, 6])
    
    with col_inputs:
        st.markdown("<div style='font-size: 0.875rem; font-weight: 600; margin-bottom: 8px;'>Simulation Parameters</div>", unsafe_allow_html=True)
        sleep_forecast = st.slider("Projected sleep duration tonight (hours)", 5.0, 10.0, 8.0, 0.5)
        cardio_intensity = st.select_slider("Planned training load for tomorrow", options=["Rest Day", "Zone 2 (Light)", "Hypertrophy (Moderate)", "HIIT / Heavy (High)"])
        
    with col_results:
        # Call shared predictive recovery model
        prediction = RecoveryPredictor.predict_tomorrow(
            current_hrv=current_hrv_val,
            target_hrv=target_hrv_val,
            sleep_hours=sleep_forecast,
            workout_intensity=cardio_intensity
        )
        projected_hrv_tomorrow = prediction["projected_hrv_tomorrow"]
        days_needed = prediction["days_to_recovery"]
        
        recovery_day_str = "Tomorrow"
        if days_needed > 0:
            target_date_obj = date.today() + timedelta(days=days_needed)
            recovery_day_str = target_date_obj.strftime("%A, %b %d")
            
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.markdown(f"""
            <div class="shadcn-card" style="border-top: 3px solid #6366f1;">
                <div class="shadcn-card-header">
                    <span class="shadcn-card-title">Projected HRV Tomorrow</span>
                </div>
                <div class="shadcn-card-value">{int(projected_hrv_tomorrow)} ms</div>
                <div class="shadcn-card-description">Target: {int(target_hrv_val)} ms ({"-" if deficit > 0 else "+"}{abs(int(deficit))} ms diff)</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col_p2:
            status_text = "Fully Recovered" if days_needed == 0 else f"{days_needed} days"
            border_col = "#10b981" if days_needed == 0 else "#f59e0b"
            st.markdown(f"""
            <div class="shadcn-card" style="border-top: 3px solid {border_col};">
                <div class="shadcn-card-header">
                    <span class="shadcn-card-title">Estimated Recovery Date</span>
                </div>
                <div class="shadcn-card-value" style="font-size: 1.25rem; font-weight: 700; height: 38px; display: flex; align-items: center;">{recovery_day_str}</div>
                <div class="shadcn-card-description">Status: {status_text}</div>
            </div>
            """, unsafe_allow_html=True)
            
    # Render forecast chart
    forecast_dates = [date.today() + timedelta(days=i) for i in range(5)]
    forecast_values = [current_hrv_val, projected_hrv_tomorrow]
    for i in range(2, 5):
        forecast_values.append(min(120, forecast_values[-1] + 6.0))
            
    fig_forecast = go.Figure()
    fig_forecast.add_trace(go.Scatter(
        x=[d.strftime("%Y-%m-%d") for d in forecast_dates], y=forecast_values,
        mode="lines+markers+text", name="Projected HRV",
        text=[f"{int(v)}ms" for v in forecast_values],
        textposition="top center",
        line=dict(color="#6366f1", width=2, dash="dash"),
        marker=dict(size=6)
    ))
    fig_forecast.add_hline(y=target_hrv_val, line_dash="solid", line_color="#ef4444")
    fig_forecast.update_layout(
        template=plotly_template,
        title="5-Day HRV Projection",
        yaxis=dict(title="HRV (ms)", range=[30, 100], gridcolor=grid_color),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        height=280,
        margin=dict(l=40, r=40, t=40, b=30),
        showlegend=False
    )
    st.plotly_chart(fig_forecast, use_container_width=True)


# ==================== TAB 6: RECORDED DATA EXPLORER ====================
with tab_data:
    st.markdown(f"<h3 style='font-size: 1.25rem; font-weight: 700; letter-spacing: -0.02em; margin-bottom: 6px; display: flex; align-items: center;'>{LUCIDE_DATABASE} Recorded Data</h3>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 0.875rem; color: var(--muted-foreground); margin: 0 0 18px 0;'>Search, filter, inspect, and export the records stored in your local SQLite database.</p>", unsafe_allow_html=True)

    all_data_df = db.get_df(limit=None)

    if all_data_df.empty:
        st.markdown(f"""
        <div class="shadcn-alert" style="border-left: 4px solid #6366f1;">
            <div style="display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 0.875rem;">{LUCIDE_DATABASE} No recorded data found</div>
            <p style="font-size: 0.875rem; margin: 4px 0 0 0; line-height: 1.5; color: var(--muted-foreground);">
                The database is initialized, but daily_metrics has no rows yet. Run <code>python sync.py backfill 14</code> after configuring Garmin sync.
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        column_labels = {
            "date": "Date", "hrv_last_night": "HRV", "hrv_weekly_avg": "HRV 7d Avg",
            "hrv_status": "HRV Status", "sleep_score": "Sleep Score", "sleep_duration": "Sleep Duration",
            "sleep_deep": "Deep Sleep", "sleep_light": "Light Sleep", "sleep_rem": "REM Sleep",
            "sleep_awake": "Awake", "resting_hr": "Resting HR", "min_hr": "Min HR", "max_hr": "Max HR",
            "bb_max": "Battery Max", "bb_min": "Battery Min", "bb_charged": "Battery Charged", "bb_drained": "Battery Drained",
            "stress_avg": "Stress Avg", "stress_max": "Stress Max", "steps": "Steps",
            "floors": "Floors", "training_readiness": "Readiness", "spo2_avg": "SpO2 Avg",
            "spo2_min": "SpO2 Min", "respiration_avg": "Respiration Avg", "respiration_min": "Respiration Min",
            "workout_type": "Workout", "alcohol_logged": "Alcohol", "sleep_apnea_flag": "Sleep Apnea", "ai_summary": "AI Summary",
            "raw_json": "Raw JSON"
        }
        metric_groups = {
            "Essential": ["date", "training_readiness", "hrv_last_night", "sleep_score", "resting_hr", "stress_avg", "steps", "bb_min", "workout_type"],
            "Recovery": ["date", "training_readiness", "hrv_last_night", "hrv_weekly_avg", "hrv_status", "resting_hr", "stress_avg", "bb_max", "bb_min"],
            "Sleep": ["date", "sleep_score", "sleep_duration", "sleep_deep", "sleep_light", "sleep_rem", "sleep_awake", "spo2_avg", "spo2_min", "respiration_avg"],
            "Activity": ["date", "steps", "floors", "min_hr", "max_hr", "bb_charged", "bb_drained", "workout_type"],
            "Flags": ["date", "alcohol_logged", "sleep_apnea_flag", "spo2_min", "respiration_min", "stress_max", "ai_summary"],
            "All columns": [col for col in column_labels if col != "raw_json"],
        }

        data_df = all_data_df.copy()
        data_df["date"] = pd.to_datetime(data_df["date"], errors="coerce")
        data_df = data_df.dropna(subset=["date"])
        min_day = data_df["date"].min().date()
        max_day = data_df["date"].max().date()

        st.markdown("""
        <style>
        .data-card-row { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-bottom: 16px; }
        .data-mini-card { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 14px 16px; }
        .data-mini-label { color: var(--muted-foreground); font-size: 0.72rem; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase; }
        .data-mini-value { color: var(--foreground); font-size: 1.35rem; font-weight: 800; line-height: 1.25; margin-top: 3px; }
        .data-mini-sub { color: var(--muted-foreground); font-size: 0.78rem; margin-top: 2px; }
        div[data-testid="stDataFrame"] { border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
        @media (max-width: 900px) { .data-card-row { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
        @media (max-width: 520px) { .data-card-row { grid-template-columns: 1fr; } }
        </style>
        """, unsafe_allow_html=True)

        filters = st.container(border=True)
        with filters:
            search_col, date_col, group_col = st.columns([4, 3, 2])
            with search_col:
                search_term = st.text_input(
                    "Search records",
                    placeholder="Search date, status, workout, values, notes...",
                    help="Search is applied across every selected column after date filtering.",
                )
            with date_col:
                selected_range = st.date_input(
                    "Date range",
                    value=(min_day, max_day),
                    min_value=min_day,
                    max_value=max_day,
                )
            with group_col:
                metric_view = st.selectbox("Metric set", list(metric_groups.keys()), index=0)

            sort_col, row_col, extra_col = st.columns([2, 2, 5])
            with sort_col:
                sort_order = st.selectbox("Sort", ["Newest first", "Oldest first"], index=0)
            with row_col:
                row_limit = st.selectbox("Rows shown", [50, 100, 250, 500, "All"], index=1)
            with extra_col:
                optional_cols = [c for c in column_labels if c in data_df.columns and c not in metric_groups[metric_view] and c != "raw_json"]
                extra_cols = st.multiselect(
                    "Add columns",
                    optional_cols,
                    format_func=lambda c: column_labels.get(c, c),
                    placeholder="Choose additional fields",
                )

        include_raw_json = st.checkbox("Include raw JSON in table and export", value=False)

        selected_cols = [c for c in metric_groups[metric_view] if c in data_df.columns]
        selected_cols.extend([c for c in extra_cols if c not in selected_cols])
        if include_raw_json and "raw_json" in data_df.columns:
            selected_cols.append("raw_json")
        if "date" not in selected_cols:
            selected_cols.insert(0, "date")

        if isinstance(selected_range, tuple) and len(selected_range) == 2:
            start_day, end_day = selected_range
        else:
            start_day, end_day = min_day, max_day

        filtered_df = data_df[(data_df["date"].dt.date >= start_day) & (data_df["date"].dt.date <= end_day)].copy()
        filtered_df = filtered_df.sort_values("date", ascending=(sort_order == "Oldest first"))

        search_source = filtered_df[selected_cols].copy()
        if search_term.strip():
            normalized_query = search_term.strip()
            search_mask = search_source.astype(str).apply(
                lambda row: row.str.contains(normalized_query, case=False, na=False, regex=False).any(),
                axis=1,
            )
            filtered_df = filtered_df[search_mask]

        total_records = len(data_df)
        matched_records = len(filtered_df)
        export_df = filtered_df[selected_cols].copy()

        shown_df = export_df.copy()
        if row_limit != "All":
            shown_df = shown_df.head(int(row_limit))

        def seconds_to_duration(value):
            if pd.isna(value):
                return "-"
            value = int(value)
            hours = value // 3600
            minutes = (value % 3600) // 60
            return f"{hours}h {minutes}m"

        def format_for_display(frame):
            display = frame.copy()
            if "date" in display.columns:
                display["date"] = pd.to_datetime(display["date"]).dt.strftime("%Y-%m-%d")
            for duration_col in ["sleep_duration", "sleep_deep", "sleep_light", "sleep_rem", "sleep_awake"]:
                if duration_col in display.columns:
                    display[duration_col] = display[duration_col].apply(seconds_to_duration)
            for flag_col in ["alcohol_logged", "sleep_apnea_flag"]:
                if flag_col in display.columns:
                    display[flag_col] = display[flag_col].map({1: "Yes", 0: "No"}).fillna("-")
            for text_col in ["hrv_status", "workout_type", "ai_summary", "raw_json"]:
                if text_col in display.columns:
                    display[text_col] = display[text_col].fillna("-").replace("", "-")
            return display.rename(columns={col: column_labels.get(col, col) for col in display.columns})

        display_df = format_for_display(shown_df)
        date_span = f"{start_day:%b %d, %Y} to {end_day:%b %d, %Y}"
        avg_hrv = filtered_df["hrv_last_night"].mean() if "hrv_last_night" in filtered_df.columns else None
        avg_sleep = filtered_df["sleep_score"].mean() if "sleep_score" in filtered_df.columns else None
        total_steps = filtered_df["steps"].sum() if "steps" in filtered_df.columns else None
        avg_hrv_display = f"{avg_hrv:.0f} ms" if avg_hrv is not None and pd.notna(avg_hrv) else "-"
        total_steps_display = f"{int(total_steps):,}" if total_steps is not None and pd.notna(total_steps) else "-"

        st.markdown(f"""
        <div class="data-card-row">
            <div class="data-mini-card"><div class="data-mini-label">Matches</div><div class="data-mini-value">{matched_records:,}</div><div class="data-mini-sub">of {total_records:,} stored records</div></div>
            <div class="data-mini-card"><div class="data-mini-label">Date Window</div><div class="data-mini-value" style="font-size: 1rem;">{date_span}</div><div class="data-mini-sub">filtered from daily_metrics</div></div>
            <div class="data-mini-card"><div class="data-mini-label">Average HRV</div><div class="data-mini-value">{avg_hrv_display}</div><div class="data-mini-sub">visible result set</div></div>
            <div class="data-mini-card"><div class="data-mini-label">Total Steps</div><div class="data-mini-value">{total_steps_display}</div><div class="data-mini-sub">visible result set</div></div>
        </div>
        """, unsafe_allow_html=True)

        table_col, export_col = st.columns([7, 2])
        with table_col:
            st.markdown(f"<div style='font-size: 0.8125rem; color: var(--muted-foreground); margin-bottom: 8px;'>{LUCIDE_SEARCH} Showing {len(display_df):,} row{'s' if len(display_df) != 1 else ''}{' after search' if search_term.strip() else ''}</div>", unsafe_allow_html=True)
        with export_col:
            st.download_button(
                label="Export CSV",
                data=export_df.to_csv(index=False).encode("utf-8"),
                file_name=f"my_health_records_{date.today().isoformat()}.csv",
                mime="text/csv",
                use_container_width=True,
            )

        if display_df.empty:
            st.markdown("""
            <div class="shadcn-alert">
                <div style="font-weight: 700; font-size: 0.875rem;">No matching records</div>
                <p style="font-size: 0.875rem; margin: 4px 0 0 0; color: var(--muted-foreground);">Try a wider date range, fewer columns, or a broader search term.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
                height=520,
                column_config={
                    "Date": st.column_config.TextColumn("Date", help="Recorded metric date"),
                    "HRV": st.column_config.NumberColumn("HRV", help="Last night average HRV in ms", format="%d ms"),
                    "HRV 7d Avg": st.column_config.NumberColumn("HRV 7d Avg", format="%d ms"),
                    "Sleep Score": st.column_config.NumberColumn("Sleep Score", format="%d / 100"),
                    "Resting HR": st.column_config.NumberColumn("Resting HR", format="%d bpm"),
                    "Stress Avg": st.column_config.NumberColumn("Stress Avg", format="%d"),
                    "Readiness": st.column_config.NumberColumn("Readiness", format="%d / 100"),
                    "Steps": st.column_config.NumberColumn("Steps", format="%d"),
                    "SpO2 Avg": st.column_config.NumberColumn("SpO2 Avg", format="%.1f%%"),
                    "SpO2 Min": st.column_config.NumberColumn("SpO2 Min", format="%d%%"),
                    "Respiration Avg": st.column_config.NumberColumn("Respiration Avg", format="%.1f"),
                },
            )

        if avg_sleep is not None and pd.notna(avg_sleep):
            st.caption(f"Filtered average sleep score: {avg_sleep:.0f}/100")
