import streamlit as st
import json
import pandas as pd
from pathlib import Path
from datetime import datetime, date, timedelta
import plotly.graph_objects as go
import plotly.express as px

# ---------- CONFIG ----------
DATA_DIR = Path(__file__).parent.parent / "data"
st.set_page_config(page_title="Hermes Health", page_icon="📊", layout="wide")

# ---------- STYLE ----------
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .stApp { background-color: #0e1117; }
    .metric-card {
        background: #1a1d23;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #2d3139;
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        color: #ffffff;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #8b8d92;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .verdict-card {
        background: linear-gradient(135deg, #1a1d23 0%, #0e1117 100%);
        border-radius: 16px;
        padding: 24px;
        border: 1px solid #2d3139;
    }
    hr { border-color: #2d3139; }
</style>
""", unsafe_allow_html=True)

# ---------- DATA LOADING ----------
def load_data(days=14):
    records = []
    today = date.today()
    for i in range(days):
        d = today - timedelta(days=i)
        p = DATA_DIR / f"{d.isoformat()}.json"
        if p.exists():
            with open(p) as f:
                records.append(json.load(f))
    records.sort(key=lambda r: r["date"])
    return records

records = load_data(14)

# ---------- TITLE ----------
st.title("🏋️ Hermes Health Dashboard")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC+7")

# ---------- DATA PREP ----------
df_list = []
for r in records:
    row = {"date": r["date"]}
    
    # HRV
    hrv = r.get("hrv", {})
    if isinstance(hrv, dict):
        row["hrv_weekly_avg"] = hrv.get("weeklyAvg") or hrv.get("weekly_avg")
        row["hrv_last_night"] = hrv.get("lastNightAvg") or hrv.get("last_night_avg")
    
    # Sleep
    sleep = r.get("sleep", {})
    daily = sleep.get("dailySleepDTO", {}) if isinstance(sleep, dict) else {}
    if isinstance(daily, dict):
        ss = daily.get("sleepScores", {})
        row["sleep_score"] = ss.get("overall", {}).get("value") if isinstance(ss, dict) else None
        row["sleep_duration"] = daily.get("sleepTime")
        row["deep_sleep"] = daily.get("deepSleepSeconds")
        row["light_sleep"] = daily.get("lightSleepSeconds")
        row["rem_sleep"] = daily.get("remSleepSeconds")
        row["awake"] = daily.get("awakeSleepSeconds")
    
    # HR
    hr = r.get("heart_rate", {})
    if isinstance(hr, dict):
        row["resting_hr"] = hr.get("restingHeartRate")
        row["min_hr"] = hr.get("minHeartRate")
        row["max_hr"] = hr.get("maxHeartRate")
    
    # Body Battery
    bb = r.get("body_battery", [])
    if isinstance(bb, list) and len(bb) > 0:
        b = bb[0]
        row["bb_max"] = b.get("bodyBatteryMax") or b.get("max")
        row["bb_min"] = b.get("bodyBatteryMin") or b.get("min")
        row["bb_drained"] = b.get("drained")
        row["bb_charged"] = b.get("charged")
    
    # Stress
    stress = r.get("stress", {})
    if isinstance(stress, dict):
        row["stress_avg"] = stress.get("avgStressLevel")
        row["stress_max"] = stress.get("maxStressLevel")
    
    # Steps
    steps = r.get("steps", {})
    if isinstance(steps, dict):
        row["steps"] = steps.get("totalSteps")
    
    # Training Readiness
    tr = r.get("training_readiness", {})
    if isinstance(tr, dict):
        rq = tr.get("readinessQualifier", {})
        if isinstance(rq, dict):
            row["readiness"] = rq.get("readinessScore")
    
    df_list.append(row)

df = pd.DataFrame(df_list)

# ---------- METRICS ROW ----------
st.markdown("### 📈 Today's Snapshot")

if not records:
    st.info("No data yet. Wear your Fenix 7X and data will appear in 7+ days.")
    st.stop()

latest = records[-1] if records else {}
latest_df = df.iloc[-1] if not df.empty else {}

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    hrv_val = latest_df.get("hrv_last_night", "")
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">HRV</div>
        <div class="metric-value">{hrv_val if hrv_val else '—'}</div>
        <div style="color:#8b8d92;font-size:0.8rem;">ms</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    sleep_val = latest_df.get("sleep_score", "")
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Sleep Score</div>
        <div class="metric-value">{int(sleep_val) if sleep_val else '—'}</div>
        <div style="color:#8b8d92;font-size:0.8rem;">/100</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    hr_val = latest_df.get("resting_hr", "")
    color = "#ff4b4b" if hr_val and hr_val > 80 else "#00cc66"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Resting HR</div>
        <div class="metric-value" style="color:{color}">{int(hr_val) if hr_val else '—'}</div>
        <div style="color:#8b8d92;font-size:0.8rem;">bpm</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    stress_val = latest_df.get("stress_avg", "")
    color = "#ff4b4b" if stress_val and stress_val > 60 else "#ffaa00" if stress_val and stress_val > 40 else "#00cc66"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Stress</div>
        <div class="metric-value" style="color:{color}">{int(stress_val) if stress_val else '—'}</div>
        <div style="color:#8b8d92;font-size:0.8rem;">avg</div>
    </div>
    """, unsafe_allow_html=True)

with col5:
    bb_val = latest_df.get("bb_min", "")
    color = "#ff4b4b" if bb_val and bb_val < 30 else "#ffaa00" if bb_val and bb_val < 50 else "#00cc66"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Body Battery</div>
        <div class="metric-value" style="color:{color}">{int(bb_val) if bb_val else '—'}</div>
        <div style="color:#8b8d92;font-size:0.8rem;">lowest today</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ---------- CHARTS ----------
st.markdown("### 📉 Trends")

if len(df) > 1:
    # HRV + Resting HR
    fig_hr = go.Figure()
    
    if "hrv_last_night" in df.columns and df["hrv_last_night"].notna().any():
        fig_hr.add_trace(go.Scatter(
            x=df["date"], y=df["hrv_last_night"].astype(float),
            mode="lines+markers", name="HRV (ms)",
            line=dict(color="#636efa", width=3),
            marker=dict(size=8)
        ))
    
    if "resting_hr" in df.columns and df["resting_hr"].notna().any():
        fig_hr.add_trace(go.Scatter(
            x=df["date"], y=df["resting_hr"].astype(float),
            mode="lines+markers", name="Resting HR (bpm)",
            line=dict(color="#ff4b4b", width=3),
            marker=dict(size=8),
            yaxis="y2"
        ))
    
    fig_hr.update_layout(
        template="plotly_dark",
        title="HRV vs Resting Heart Rate",
        hovermode="x unified",
        yaxis=dict(title="HRV (ms)", side="left"),
        yaxis2=dict(title="Resting HR (bpm)", overlaying="y", side="right"),
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
        height=400
    )
    
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig_hr, use_container_width=True)
    
    # Stress + Body Battery
    fig_stress = go.Figure()
    
    if "stress_avg" in df.columns and df["stress_avg"].notna().any():
        fig_stress.add_trace(go.Scatter(
            x=df["date"], y=df["stress_avg"].astype(float),
            mode="lines+markers", name="Stress (avg)",
            line=dict(color="#ff9800", width=3),
            marker=dict(size=8),
            fill="tozeroy"
        ))
    
    if "bb_min" in df.columns and df["bb_min"].notna().any():
        fig_stress.add_trace(go.Scatter(
            x=df["date"], y=df["bb_min"].astype(float),
            mode="lines+markers", name="Body Battery (low)",
            line=dict(color="#4caf50", width=3),
            marker=dict(size=8),
            yaxis="y2"
        ))
    
    fig_stress.update_layout(
        template="plotly_dark",
        title="Stress vs Body Battery",
        hovermode="x unified",
        yaxis=dict(title="Stress", side="left", range=[0, 100]),
        yaxis2=dict(title="Body Battery", overlaying="y", side="right", range=[0, 100]),
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
        height=400
    )
    
    with col2:
        st.plotly_chart(fig_stress, use_container_width=True)
    
    # Sleep score
    if "sleep_score" in df.columns and df["sleep_score"].notna().any():
        fig_sleep = go.Figure()
        fig_sleep.add_trace(go.Bar(
            x=df["date"], y=df["sleep_score"].astype(float),
            name="Sleep Score",
            marker_color="#9c27b0"
        ))
        fig_sleep.update_layout(
            template="plotly_dark",
            title="Sleep Quality",
            hovermode="x unified",
            plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
            height=300
        )
        st.plotly_chart(fig_sleep, use_container_width=True)
    
    # Steps
    if "steps" in df.columns and df["steps"].notna().any():
        fig_steps = go.Figure()
        fig_steps.add_trace(go.Bar(
            x=df["date"], y=df["steps"].astype(float),
            name="Steps",
            marker_color="#00bcd4"
        ))
        fig_steps.add_hline(y=8000, line_dash="dash", line_color="#ff9800",
                           annotation_text="Goal: 8,000")
        fig_steps.update_layout(
            template="plotly_dark",
            title="Daily Steps",
            hovermode="x unified",
            plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
            height=300
        )
        st.plotly_chart(fig_steps, use_container_width=True)

else:
    st.info("More data needed. Keep wearing the watch and check back in a few days.")

# ---------- VERDICT ----------
st.markdown("---")
st.markdown("### 🧠 Coach's Verdict")

verdict_lines = []

if latest_df.get("hrv_last_night") and latest_df["hrv_last_night"] < 50:
    verdict_lines.append("⚠️ **HRV low** — your nervous system is stressed. Recovery day.")
elif not latest_df.get("hrv_last_night"):
    verdict_lines.append("⏳ **HRV calibrating** — need 7+ days of sleep data.")

if latest_df.get("sleep_score") and latest_df["sleep_score"] < 70:
    verdict_lines.append("⚠️ **Sleep quality poor** — prioritize 8 hours tonight. Screens off early.")
elif latest_df.get("sleep_score"):
    verdict_lines.append(f"✅ **Sleep score {int(latest_df['sleep_score'])}** — decent recovery.")

if latest_df.get("resting_hr") and latest_df["resting_hr"] > 75:
    verdict_lines.append(f"⚠️ **Resting HR elevated ({int(latest_df['resting_hr'])} bpm)** — high stress or poor recovery.")
    
if latest_df.get("stress_avg") and latest_df["stress_avg"] > 60:
    verdict_lines.append(f"⚠️ **Stress high ({int(latest_df['stress_avg'])} avg)** — your body is in fight mode. Cold plunge + breathwork recommended.")

if latest_df.get("bb_min") is not None:
    if latest_df["bb_min"] < 30:
        verdict_lines.append(f"⚠️ **Body Battery critically low ({int(latest_df['bb_min'])})** — you're running on fumes. Rest tonight.")
    elif latest_df["bb_min"] < 50:
        verdict_lines.append(f"⚠️ **Body Battery drained ({int(latest_df['bb_min'])})** — moderate energy used today.")
    else:
        verdict_lines.append(f"✅ **Body Battery {int(latest_df['bb_min'])}** — good energy reserve.")

if not verdict_lines:
    verdict_lines.append("📡 No verdict yet. Wear the watch for 7+ days.")

st.markdown(f"""
<div class="verdict-card">
    {"".join(f"<p>{v}</p>" for v in verdict_lines)}
</div>
""", unsafe_allow_html=True)

# ---------- RAW DATA ----------
with st.expander("📦 Raw Data (last 7 days)"):
    if not df.empty:
        st.dataframe(df.tail(7), use_container_width=True)
    else:
        st.write("No data yet.")
