import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime, date, timedelta
import plotly.graph_objects as go
import sys

# Add parent dir to path to import db
sys.path.append(str(Path(__file__).parent.parent))
import db
from recovery_predictor import RecoveryPredictor

st.set_page_config(page_title="Hermes Health", page_icon="⚡", layout="wide")

# ---------- THEME CONFIGURATION (SHADCN STYLING) ----------
# FIRST PRIORITY: Default to Light mode
if "theme" not in st.session_state:
    st.session_state.theme = "light"

# Header Row
cols_header = st.columns([9, 1])
with cols_header[0]:
    st.markdown("""
        <div style="margin-bottom: 20px;">
            <h1 style="font-size: 2rem; font-weight: 800; letter-spacing: -0.05em; margin: 0;">Hermes Health</h1>
            <p style="font-size: 0.875rem; color: var(--muted-foreground); margin: 2px 0 0 0;">Personal biometric tracking & training recommendations</p>
        </div>
    """, unsafe_allow_html=True)
with cols_header[1]:
    if st.button("☀️ Light" if st.session_state.theme == "dark" else "🌙 Dark"):
        st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
        st.rerun()

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

# ---------- SIDEBAR COMPOSITION FORM ----------
st.sidebar.markdown("<h3 style='font-size: 1.125rem; font-weight: 700; letter-spacing: -0.02em;'>Log Metrics</h3>", unsafe_allow_html=True)
with st.sidebar.form("body_comp_form", clear_on_submit=True):
    weight_input = st.number_input("Weight (kg)", 30.0, 200.0, 75.0, 0.1)
    fat_input = st.number_input("Body Fat (%)", 2.0, 50.0, 15.0, 0.1)
    waist_input = st.number_input("Waist (cm)", 40.0, 150.0, 80.0, 0.5)
    submit_comp = st.form_submit_button("Save Entry")
    if submit_comp:
        db.save_body_comp(date.today().strftime("%Y-%m-%d"), weight_input, fat_input, waist_input)
        st.sidebar.success("Saved successfully!")
        st.rerun()

# ---------- INITIAL LOADING SCREEN ----------
loader = st.empty()
with loader.container():
    st.markdown("""
    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 80vh; gap: 16px;">
        <div style="width: 40px; height: 40px; border: 3px solid var(--border); border-top: 3px solid var(--foreground); border-radius: 50%; animation: spin 1s linear infinite;"></div>
        <div style="font-size: 0.875rem; font-weight: 500; color: var(--muted-foreground); letter-spacing: 0.05em; text-transform: uppercase;">Loading biometrics...</div>
    </div>
    <style>
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
    """, unsafe_allow_html=True)

# ---------- DATA LOADING ----------
df = db.get_df(limit=30)

if df.empty:
    loader.empty()
    st.info("No health data synced yet. Run `python sync.py backfill 14` to fetch data.")
    st.stop()

# Ensure chronological order and get latest row
latest_df = df.iloc[-1]
latest_date = latest_df["date"]

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

# ---------- TABS (EMOJI-LESS PLAIN TEXT HEADERS) ----------
tab_today, tab_trends, tab_comp, tab_ai, tab_recovery = st.tabs([
    "Today", 
    "Trends", 
    "Body Comp",
    "AI Insights", 
    "Recovery Forecast"
])


# ==================== TAB 1: TODAY'S SNAPSHOT ====================
with tab_today:
    # Training Readiness Callout Banner
    readiness = latest_df.get("training_readiness")
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
                <span style="font-size: 2.25rem; font-weight: 800; letter-spacing: -0.05em; color: var(--card-foreground);">{int(readiness)}/100</span>
                <span style="font-size: 0.875rem; font-weight: 500; color: var(--muted-foreground);">• {qualifier}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 5-Column Grid Layout for Biometric Cards with 7-Day Sparkline trends below them
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        hrv_val = latest_df.get("hrv_last_night")
        st.markdown(f"""
        <div class="shadcn-card">
            <div class="shadcn-card-header">
                <span class="shadcn-card-title">HRV</span>
                {LUCIDE_ACTIVITY}
            </div>
            <div class="shadcn-card-value">{int(hrv_val) if hrv_val else '—'}</div>
            <div class="shadcn-card-description">last night (ms)</div>
        </div>
        """, unsafe_allow_html=True)
        # 7-day sparkline
        hrv_series = df["hrv_last_night"].tail(7).bfill().ffill().tolist()
        if len(hrv_series) > 1:
            st.plotly_chart(make_sparkline(hrv_series, "#6366f1"), config={'displayModeBar': False}, use_container_width=True)

    with col2:
        sleep_val = latest_df.get("sleep_score")
        st.markdown(f"""
        <div class="shadcn-card">
            <div class="shadcn-card-header">
                <span class="shadcn-card-title">Sleep</span>
                {LUCIDE_MOON}
            </div>
            <div class="shadcn-card-value">{int(sleep_val) if sleep_val else '—'}</div>
            <div class="shadcn-card-description">quality score /100</div>
        </div>
        """, unsafe_allow_html=True)
        # 7-day sparkline
        sleep_series = df["sleep_score"].tail(7).bfill().ffill().tolist()
        if len(sleep_series) > 1:
            st.plotly_chart(make_sparkline(sleep_series, "#8b5cf6"), config={'displayModeBar': False}, use_container_width=True)

    with col3:
        hr_val = latest_df.get("resting_hr")
        st.markdown(f"""
        <div class="shadcn-card">
            <div class="shadcn-card-header">
                <span class="shadcn-card-title">Resting HR</span>
                {LUCIDE_HEART}
            </div>
            <div class="shadcn-card-value">{int(hr_val) if hr_val else '—'}</div>
            <div class="shadcn-card-description">beats per min (bpm)</div>
        </div>
        """, unsafe_allow_html=True)
        # 7-day sparkline
        hrv_avg_series = df["resting_hr"].tail(7).bfill().ffill().tolist()
        if len(hrv_avg_series) > 1:
            st.plotly_chart(make_sparkline(hrv_avg_series, "#ef4444"), config={'displayModeBar': False}, use_container_width=True)

    with col4:
        stress_val = latest_df.get("stress_avg")
        st.markdown(f"""
        <div class="shadcn-card">
            <div class="shadcn-card-header">
                <span class="shadcn-card-title">Stress</span>
                {LUCIDE_FLAME}
            </div>
            <div class="shadcn-card-value">{int(stress_val) if stress_val else '—'}</div>
            <div class="shadcn-card-description">daily average /100</div>
        </div>
        """, unsafe_allow_html=True)
        # 7-day sparkline
        stress_series = df["stress_avg"].tail(7).bfill().ffill().tolist()
        if len(stress_series) > 1:
            st.plotly_chart(make_sparkline(stress_series, "#f59e0b"), config={'displayModeBar': False}, use_container_width=True)

    with col5:
        bb_val = latest_df.get("bb_min")
        st.markdown(f"""
        <div class="shadcn-card">
            <div class="shadcn-card-header">
                <span class="shadcn-card-title">Body Battery</span>
                {LUCIDE_BATTERY}
            </div>
            <div class="shadcn-card-value">{int(bb_val) if bb_val is not None else '—'}</div>
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

        day_name = datetime.strptime(latest_date, "%Y-%m-%d").strftime("%A")
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
    st.markdown("<h3 style='font-size: 1.25rem; font-weight: 700; letter-spacing: -0.02em; margin-bottom: 16px;'>Biometric Trends (30 Days)</h3>", unsafe_allow_html=True)
    
    if len(df) > 1:
        # Chart 1: HRV vs Resting HR
        fig_hr = go.Figure()
        if "hrv_last_night" in df.columns and df["hrv_last_night"].notna().any():
            fig_hr.add_trace(go.Scatter(
                x=df["date"], y=df["hrv_last_night"],
                mode="lines+markers", name="HRV (ms)",
                line=dict(color="#6366f1", width=2), # indigo-500
                marker=dict(size=4)
            ))
        if "resting_hr" in df.columns and df["resting_hr"].notna().any():
            fig_hr.add_trace(go.Scatter(
                x=df["date"], y=df["resting_hr"],
                mode="lines+markers", name="Resting HR (bpm)",
                line=dict(color="#ef4444", width=2), # red-500
                marker=dict(size=4),
                yaxis="y2"
            ))
        fig_hr.update_layout(
            template=plotly_template,
            hovermode="x unified",
            yaxis=dict(title="HRV (ms)", side="left", gridcolor=grid_color),
            yaxis2=dict(title="Resting HR (bpm)", overlaying="y", side="right", showgrid=False),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            height=300,
            margin=dict(l=40, r=40, t=10, b=30),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_hr, use_container_width=True)

        # Chart 2: Sleep Architecture Breakdown (Stacked Bar)
        if "sleep_deep" in df.columns and df["sleep_deep"].notna().any():
            fig_sleep_arch = go.Figure()
            deep_hrs = df["sleep_deep"] / 3600.0
            rem_hrs = df["sleep_rem"] / 3600.0
            light_hrs = df["sleep_light"] / 3600.0
            awake_hrs = df["sleep_awake"] / 3600.0
            
            fig_sleep_arch.add_trace(go.Bar(x=df["date"], y=deep_hrs, name="Deep Sleep", marker_color="#1e1b4b"))
            fig_sleep_arch.add_trace(go.Bar(x=df["date"], y=rem_hrs, name="REM Sleep", marker_color="#4f46e5"))
            fig_sleep_arch.add_trace(go.Bar(x=df["date"], y=light_hrs, name="Light Sleep", marker_color="#818cf8"))
            fig_sleep_arch.add_trace(go.Bar(x=df["date"], y=awake_hrs, name="Awake Time", marker_color="#e4e4e7"))
            
            fig_sleep_arch.update_layout(
                template=plotly_template,
                barmode="stack",
                title="Overnight Sleep Architecture Breakdown",
                yaxis=dict(title="Duration (Hours)", gridcolor=grid_color),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                height=300,
                margin=dict(l=40, r=40, t=40, b=30),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_sleep_arch, use_container_width=True)

        # Chart 3: Stress vs Body Battery
        fig_stress = go.Figure()
        if "stress_avg" in df.columns and df["stress_avg"].notna().any():
            fig_stress.add_trace(go.Scatter(
                x=df["date"], y=df["stress_avg"],
                mode="lines+markers", name="Stress Avg",
                line=dict(color="#f59e0b", width=2), # amber-500
                marker=dict(size=4)
            ))
        if "bb_min" in df.columns and df["bb_min"].notna().any():
            fig_stress.add_trace(go.Scatter(
                x=df["date"], y=df["bb_min"],
                mode="lines+markers", name="Body Battery Min",
                line=dict(color="#10b981", width=2), # emerald-500
                marker=dict(size=4)
            ))
        fig_stress.update_layout(
            template=plotly_template,
            hovermode="x unified",
            yaxis=dict(title="Score (0-100)", side="left", range=[0, 100], gridcolor=grid_color),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            height=300,
            margin=dict(l=40, r=40, t=10, b=30),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_stress, use_container_width=True)

        col_left, col_right = st.columns(2)
        
        with col_left:
            if "sleep_score" in df.columns and df["sleep_score"].notna().any():
                fig_sleep = go.Figure()
                fig_sleep.add_trace(go.Bar(
                    x=df["date"], y=df["sleep_score"],
                    name="Sleep Score",
                    marker_color="#8b5cf6" # violet-500
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
            if "steps" in df.columns and df["steps"].notna().any():
                fig_steps = go.Figure()
                fig_steps.add_trace(go.Bar(
                    x=df["date"], y=df["steps"],
                    name="Steps",
                    marker_color="#06b6d4" # cyan-500
                ))
                fig_steps.add_hline(y=8000, line_dash="dash", line_color="#f59e0b")
                fig_steps.update_layout(
                    template=plotly_template,
                    title="Daily Steps",
                    yaxis=dict(gridcolor=grid_color),
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    height=250,
                    margin=dict(l=40, r=40, t=30, b=30)
                )
                st.plotly_chart(fig_steps, use_container_width=True)

        # Pulse Ox & Respiration Chart
        if "spo2_avg" in df.columns and df["spo2_avg"].notna().any():
            fig_spo2 = go.Figure()
            fig_spo2.add_trace(go.Scatter(
                x=df["date"], y=df["spo2_avg"],
                mode="lines+markers", name="Pulse Ox (SpO2 %)",
                line=dict(color="#06b6d4", width=2),
                marker=dict(size=4)
            ))
            if "respiration_avg" in df.columns and df["respiration_avg"].notna().any():
                fig_spo2.add_trace(go.Scatter(
                    x=df["date"], y=df["respiration_avg"],
                    mode="lines+markers", name="Respiration (br/min)",
                    line=dict(color="#10b981", width=2),
                    marker=dict(size=4),
                    yaxis="y2"
                ))
            fig_spo2.update_layout(
                template=plotly_template,
                title="Pulse Ox (SpO2) & Respiration rate",
                hovermode="x unified",
                yaxis=dict(title="SpO2 (%)", side="left", range=[80, 100], gridcolor=grid_color),
                yaxis2=dict(title="Breaths/min", overlaying="y", side="right", range=[10, 25], showgrid=False),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                height=280,
                margin=dict(l=40, r=40, t=40, b=30),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_spo2, use_container_width=True)



        # Automated Correlation Discovery Panel
        st.markdown("<h3 style='font-size: 1.125rem; font-weight: 700; letter-spacing: -0.02em; margin-top: 24px; margin-bottom: 12px;'>Biometric Correlation Insights</h3>", unsafe_allow_html=True)
        
        # Pearson correlations calculator
        cols = ["hrv_last_night", "sleep_score", "resting_hr", "stress_avg", "steps", "training_readiness"]
        available_cols = [c for c in cols if c in df.columns and df[c].notna().sum() > 5]
        
        insights = []
        if len(available_cols) >= 2:
            corr_matrix = df[available_cols].corr()
            
            if "hrv_last_night" in corr_matrix.index and "stress_avg" in corr_matrix.columns:
                val = corr_matrix.loc["hrv_last_night", "stress_avg"]
                if val < -0.35:
                    insights.append(f"Daytime stress averages and sleep recovery (HRV) are negatively correlated ({val:.2f}). Higher stress directly suppresses your sleep recovery.")
            if "hrv_last_night" in corr_matrix.index and "sleep_score" in corr_matrix.columns:
                val = corr_matrix.loc["hrv_last_night", "sleep_score"]
                if val > 0.35:
                    insights.append(f"Sleep score and overnight HRV show a positive correlation ({val:.2f}). Deep quality sleep directly charges autonomic recovery.")
            if "resting_hr" in corr_matrix.index and "hrv_last_night" in corr_matrix.columns:
                val = corr_matrix.loc["resting_hr", "hrv_last_night"]
                if val < -0.4:
                    insights.append(f"Resting HR and HRV are strongly inversely linked ({val:.2f}). A lower waking heart rate signifies peak parasympathetic recovery.")
            if "steps" in corr_matrix.index and "sleep_score" in corr_matrix.columns:
                val = corr_matrix.loc["steps", "sleep_score"]
                if val > 0.25:
                    insights.append(f"Higher daily step counts show a positive relationship ({val:.2f}) with sleep quality score. Physical output helps you sleep deeper.")
        
        if not insights:
            insights.append("Still gathering data to discover correlation insights. Keep logging consistency.")
            
        st.markdown(f"""
        <div class="shadcn-card" style="padding: 20px; gap: 8px; border-left: 4px solid var(--border);">
            {"".join(f"<div style='font-size: 0.875rem; line-height: 1.5; padding: 4px 0;'>• {ins}</div>" for ins in insights)}
        </div>
        """, unsafe_allow_html=True)

    else:
        st.info("Accumulating data. Wear watch consistently to show trend charts.")

# ==================== TAB 3: BODY COMPOSITION ====================
with tab_comp:
    st.markdown("<h3 style='font-size: 1.25rem; font-weight: 700; letter-spacing: -0.02em; margin-bottom: 16px;'>Body Composition Tracking</h3>", unsafe_allow_html=True)
    
    comp_df = db.get_body_comp_df(limit=30)
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
        
        # Display body comp logs in a table
        st.markdown("<h4 style='font-size: 1rem; font-weight: 700; letter-spacing: -0.01em; margin-top: 24px; margin-bottom: 12px;'>Logged Entries</h4>", unsafe_allow_html=True)
        styled_df = comp_df[["date", "weight", "body_fat", "waist"]].rename(columns={
            "date": "Date",
            "weight": "Weight (kg)",
            "body_fat": "Body Fat (%)",
            "waist": "Waist (cm)"
        }).sort_values(by="Date", ascending=False)
        st.dataframe(styled_df, hide_index=True, use_container_width=True)
    else:
        st.markdown("""
        <div class="shadcn-card" style="padding: 24px;">
            <div style="font-weight: 600; font-size: 0.875rem;">No Entries Logged Yet</div>
            <p style="font-size: 0.875rem; color: var(--muted-foreground); margin-top: 4px;">
                Log your weight, body fat %, and waist size in the sidebar to start tracking composition trends.
            </p>
        </div>
        """, unsafe_allow_html=True)

# ==================== TAB 4: AI INSIGHTS ====================
with tab_ai:
    st.markdown(f"<h3 style='font-size: 1.25rem; font-weight: 700; letter-spacing: -0.02em; margin-bottom: 12px; display: flex; align-items: center;'>{LUCIDE_SPARKLES} Gemini AI Biometric Insights</h3>", unsafe_allow_html=True)
    
    # Weekly AI Summary Display
    ai_summary = latest_df.get("ai_summary")
    
    if ai_summary:
        st.markdown(f"""
        <div class="shadcn-card" style="padding: 24px; line-height: 1.6; font-size: 0.95rem;">
            {ai_summary}
        </div>
        """, unsafe_allow_html=True)
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
        with st.spinner("Gemini is compiling biometric analysis..."):
            try:
                from ai_coach import generate_weekly_report
                report = generate_weekly_report(days=7)
                st.rerun()
            except Exception as e:
                st.error(f"Error compiling Gemini report: {e}")

    st.markdown("---")
    
    # Heuristic Flag Callouts (Emoji-free)
    st.markdown("<h4 style='font-size: 1rem; font-weight: 700; letter-spacing: -0.01em; margin-bottom: 12px;'>Biometric Anomalies Flagged</h4>", unsafe_allow_html=True)
    
    col_flag1, col_flag2 = st.columns(2)
    
    with col_flag1:
        # Alcohol
        sleep_stress = latest_df.get("stress_avg")
        rhr = latest_df.get("resting_hr")
        weekly_rhr = df["resting_hr"].mean()
        weekly_hrv = df["hrv_weekly_avg"].iloc[-1] if not df["hrv_weekly_avg"].empty else df["hrv_last_night"].mean()
        
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
        spo2_min_val = latest_df.get("spo2_min")
        resp_avg_val = latest_df.get("respiration_avg")
        
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
    
    current_hrv_val = hrv_val or 50
    target_hrv_val = weekly_hrv or 60
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
