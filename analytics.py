#!/usr/bin/env python3
"""
Advanced Biometric Intelligence & Analytics Module
Provides:
- HRV Baseline Banding (rolling normal range +/- 0.75 SD)
- Biomarker Correlation Matrix
- Sleep Architecture Disruption Index
- Unholy Habit Impact Quantification
"""

import numpy as np
import pandas as pd
import db


def calculate_hrv_baseline(df: pd.DataFrame, window: int = 28) -> pd.DataFrame:
    """
    Computes personalized HRV baseline bands:
    - baseline_mean: rolling 28-day mean of HRV
    - baseline_sd: rolling 28-day standard deviation
    - band_lower: baseline_mean - (0.75 * baseline_sd)
    - band_upper: baseline_mean + (0.75 * baseline_sd)
    - status: 'Suppressed' (below lower), 'Balanced' (within band), 'Elevated' (above upper)
    """
    if df.empty or "hrv_last_night" not in df.columns:
        return df

    df_calc = df.copy()
    df_calc["hrv_numeric"] = pd.to_numeric(df_calc["hrv_last_night"], errors="coerce")

    # Rolling window stats (min_periods 3 to handle initial ramp-up)
    df_calc["hrv_baseline_mean"] = df_calc["hrv_numeric"].rolling(window=window, min_periods=3).mean()
    df_calc["hrv_baseline_sd"] = df_calc["hrv_numeric"].rolling(window=window, min_periods=3).std().fillna(4.0)

    # Calculate baseline normal bands (+/- 0.75 SD)
    df_calc["hrv_band_lower"] = (df_calc["hrv_baseline_mean"] - 0.75 * df_calc["hrv_baseline_sd"]).round(1)
    df_calc["hrv_band_upper"] = (df_calc["hrv_baseline_mean"] + 0.75 * df_calc["hrv_baseline_sd"]).round(1)
    df_calc["hrv_severe_lower"] = (df_calc["hrv_baseline_mean"] - 1.5 * df_calc["hrv_baseline_sd"]).round(1)

    # Classify daily HRV status
    def classify_hrv(row):
        val = row["hrv_numeric"]
        lower = row["hrv_band_lower"]
        upper = row["hrv_band_upper"]
        if pd.isna(val) or pd.isna(lower):
            return "Calibrating"
        if val < row["hrv_severe_lower"]:
            return "Severe Suppression"
        if val < lower:
            return "Suppressed"
        if val > upper:
            return "Elevated (Parasympathetic)"
        return "Balanced"

    df_calc["hrv_band_status"] = df_calc.apply(classify_hrv, axis=1)
    return df_calc


def calculate_sleep_disruption_index(row: dict | pd.Series) -> dict:
    """
    Computes a Sleep Architecture Disruption Score (0 = Optimal, 100 = Severe Disruption).
    Evaluates:
    - Deep sleep ratio (optimal >= 15%)
    - REM sleep ratio (optimal >= 20%)
    - Awake interruption ratio (optimal <= 10%)
    - Overnight average stress (optimal <= 20)
    """
    duration = float(row.get("sleep_duration") or 0)
    deep = float(row.get("sleep_deep") or 0)
    rem = float(row.get("sleep_rem") or 0)
    awake = float(row.get("sleep_awake") or 0)
    stress_avg = float(row.get("stress_avg") or 20)

    if duration <= 0:
        return {
            "score": None,
            "category": "No Sleep Data",
            "deep_pct": 0,
            "rem_pct": 0,
            "awake_pct": 0,
            "drivers": []
        }

    deep_pct = (deep / duration) * 100.0
    rem_pct = (rem / duration) * 100.0
    awake_pct = (awake / duration) * 100.0

    penalty = 0.0
    drivers = []

    # Deep Sleep penalty
    if deep_pct < 10.0:
        penalty += 25.0
        drivers.append("Low Deep Sleep (<10%)")
    elif deep_pct < 15.0:
        penalty += 12.0
        drivers.append("Suboptimal Deep Sleep (<15%)")

    # REM Sleep penalty
    if rem_pct < 15.0:
        penalty += 20.0
        drivers.append("Low REM Sleep (<15%)")
    elif rem_pct < 20.0:
        penalty += 10.0
        drivers.append("Suboptimal REM Sleep (<20%)")

    # Awake Time penalty
    if awake_pct > 18.0:
        penalty += 25.0
        drivers.append("Frequent Nighttime Awakenings (>18%)")
    elif awake_pct > 12.0:
        penalty += 12.0
        drivers.append("Elevated Awake Time (>12%)")

    # Overnight Stress penalty
    if stress_avg > 35.0:
        penalty += 30.0
        drivers.append("High Overnight Sympathetic Stress (>35)")
    elif stress_avg > 25.0:
        penalty += 15.0
        drivers.append("Moderate Overnight Stress (>25)")

    disruption_score = min(100.0, max(0.0, penalty))
    
    if disruption_score <= 15:
        category = "Restorative"
    elif disruption_score <= 35:
        category = "Mild Disruption"
    elif disruption_score <= 60:
        category = "Moderate Disruption"
    else:
        category = "High Disruption"

    return {
        "score": round(disruption_score, 1),
        "category": category,
        "deep_pct": round(deep_pct, 1),
        "rem_pct": round(rem_pct, 1),
        "awake_pct": round(awake_pct, 1),
        "drivers": drivers
    }


def calculate_correlation_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates Pearson correlation matrix across biometric metrics and habit markers.
    """
    if df.empty:
        return pd.DataFrame()

    candidate_cols = [
        "hrv_last_night",
        "sleep_score",
        "sleep_duration",
        "sleep_deep",
        "sleep_rem",
        "resting_hr",
        "bb_max",
        "bb_drained",
        "stress_avg",
        "steps",
        "alcohol_logged"
    ]

    available_cols = [c for c in candidate_cols if c in df.columns]
    df_subset = df[available_cols].copy()

    for col in available_cols:
        df_subset[col] = pd.to_numeric(df_subset[col], errors="coerce")

    # Drop columns that have all NaNs or zero variance
    valid_cols = [c for c in available_cols if df_subset[c].dropna().nunique() > 1]
    if len(valid_cols) < 2:
        return pd.DataFrame()

    # Convert sleep seconds to hours for cleaner display
    if "sleep_duration" in valid_cols:
        df_subset["sleep_duration"] = df_subset["sleep_duration"] / 3600.0
    if "sleep_deep" in valid_cols:
        df_subset["sleep_deep"] = df_subset["sleep_deep"] / 3600.0
    if "sleep_rem" in valid_cols:
        df_subset["sleep_rem"] = df_subset["sleep_rem"] / 3600.0

    friendly_names = {
        "hrv_last_night": "HRV (ms)",
        "sleep_score": "Sleep Score",
        "sleep_duration": "Sleep (hrs)",
        "sleep_deep": "Deep Sleep (hrs)",
        "sleep_rem": "REM Sleep (hrs)",
        "resting_hr": "Resting HR",
        "bb_max": "Body Battery Peak",
        "bb_drained": "Body Battery Drained",
        "stress_avg": "Avg Stress",
        "steps": "Steps",
        "alcohol_logged": "Alcohol Logged"
    }

    df_renamed = df_subset[valid_cols].rename(columns=friendly_names)
    corr = df_renamed.corr(method="pearson").round(2)
    return corr


def analyze_habit_impact(df_metrics: pd.DataFrame, df_logs: pd.DataFrame | None = None) -> dict:
    """
    Analyzes the quantitative impact of logged habits (Alcohol, Late Meal, etc.) on recovery metrics.
    Compares:
    - HRV change
    - Resting HR change
    - Sleep score change
    """
    if df_metrics.empty:
        return {"has_data": False, "summary": "No metrics available."}

    df = df_metrics.copy()
    df["hrv_last_night"] = pd.to_numeric(df["hrv_last_night"], errors="coerce")
    df["resting_hr"] = pd.to_numeric(df["resting_hr"], errors="coerce")
    df["sleep_score"] = pd.to_numeric(df["sleep_score"], errors="coerce")

    # Aggregate unholy habits per date from activity_logs if provided
    if df_logs is not None and not df_logs.empty:
        unholy = df_logs[df_logs["category"] == "unholy_habit"]
        unholy_dates = set(unholy["date"].unique())
        alcohol_dates = set(unholy[unholy["tag"] == "alcohol"]["date"].unique())
        df["has_unholy_habit"] = df["date"].isin(unholy_dates).astype(int)
        df["has_alcohol"] = df["date"].isin(alcohol_dates) | (df.get("alcohol_logged", 0) == 1)
    else:
        df["has_alcohol"] = (df.get("alcohol_logged", 0) == 1)
        df["has_unholy_habit"] = df["has_alcohol"].astype(int)

    # Analyze Alcohol impact
    alcohol_group = df[df["has_alcohol"] == True]
    clean_group = df[df["has_alcohol"] == False]

    results = {
        "has_data": True,
        "total_days": len(df),
        "alcohol_days": len(alcohol_group),
        "clean_days": len(clean_group),
        "alcohol_impact": None
    }

    if len(alcohol_group) >= 1 and len(clean_group) >= 1:
        alc_hrv = alcohol_group["hrv_last_night"].mean()
        clean_hrv = clean_group["hrv_last_night"].mean()
        delta_hrv = alc_hrv - clean_hrv if (pd.notna(alc_hrv) and pd.notna(clean_hrv)) else None

        alc_rhr = alcohol_group["resting_hr"].mean()
        clean_rhr = clean_group["resting_hr"].mean()
        delta_rhr = alc_rhr - clean_rhr if (pd.notna(alc_rhr) and pd.notna(clean_rhr)) else None

        alc_sleep = alcohol_group["sleep_score"].mean()
        clean_sleep = clean_group["sleep_score"].mean()
        delta_sleep = alc_sleep - clean_sleep if (pd.notna(alc_sleep) and pd.notna(clean_sleep)) else None

        results["alcohol_impact"] = {
            "alcohol_hrv": round(alc_hrv, 1) if pd.notna(alc_hrv) else None,
            "clean_hrv": round(clean_hrv, 1) if pd.notna(clean_hrv) else None,
            "delta_hrv": round(delta_hrv, 1) if delta_hrv is not None else None,
            "alcohol_rhr": round(alc_rhr, 1) if pd.notna(alc_rhr) else None,
            "clean_rhr": round(clean_rhr, 1) if pd.notna(clean_rhr) else None,
            "delta_rhr": round(delta_rhr, 1) if delta_rhr is not None else None,
            "alcohol_sleep": round(alc_sleep, 1) if pd.notna(alc_sleep) else None,
            "clean_sleep": round(clean_sleep, 1) if pd.notna(clean_sleep) else None,
            "delta_sleep": round(delta_sleep, 1) if delta_sleep is not None else None,
        }

    return results


# =========================================================================
# EXACT-MOMENT SpO2 DESATURATION & CLINICAL RESPIRATORY INTELLIGENCE
# =========================================================================

def detect_exact_desaturation_events(epochs_data: list[dict] | pd.DataFrame) -> list[dict]:
    """
    Detects discrete, exact-moment oxygen desaturation events from high-resolution SpO2 time-series.
    
    Clinical Criteria (AASM / Polysomnography Standard):
    - A desaturation event is flagged when SpO2 drops >= 3% from the rolling baseline,
      or whenever SpO2 dips below 90%.
    - Pinpoints:
      * start_time (HH:MM:SS) - exact moment the drop began
      * nadir_time (HH:MM:SS) - exact moment the lowest SpO2 occurred
      * end_time (HH:MM:SS)   - exact moment SpO2 recovered towards baseline
      * nadir_spo2            - lowest SpO2 reached (%)
      * baseline_spo2         - pre-event baseline SpO2 (%)
      * drop_magnitude        - drop depth (baseline - nadir)
      * duration_seconds      - duration from onset to recovery
      * sleep_stage           - REM, Deep, Light, Awake, etc.
      * respiration_rate      - breaths per minute at nadir
      * severity              - 'CRITICAL' (<85%), 'WARNING' (<90%), 'MILD' (>=90%)
    """
    if epochs_data is None:
        return []

    if isinstance(epochs_data, pd.DataFrame):
        if epochs_data.empty:
            return []
        records = epochs_data.to_dict("records")
    else:
        records = list(epochs_data)

    if not records:
        return []

    # Sort chronologically by timestamp or time_str
    records = sorted(records, key=lambda x: (x.get("date", ""), str(x.get("time_str", ""))))

    events = []
    in_event = False
    event_start_idx = 0
    baseline_val = float(records[0].get("spo2_value") or 96.0)

    # Rolling baseline window (last 10-15 valid readings)
    recent_values = []

    for i, rec in enumerate(records):
        val = rec.get("spo2_value")
        if val is None or pd.isna(val):
            continue
        val = float(val)

        # Update rolling baseline when not in an active desaturation
        if not in_event:
            recent_values.append(val)
            if len(recent_values) > 15:
                recent_values.pop(0)
            baseline_val = float(np.median(recent_values)) if recent_values else val

        # Criteria for drop start: drop >= 3% from baseline OR absolute dip < 90%
        drop_from_base = baseline_val - val
        is_desaturating = (drop_from_base >= 3.0) or (val < 90.0)

        if is_desaturating and not in_event:
            # Drop started!
            in_event = True
            event_start_idx = max(0, i - 1)
            event_records = [records[event_start_idx], rec]
        elif in_event:
            event_records.append(rec)
            # Recovery condition: returned to within 1.5% of baseline or >= 95%
            recovered = (val >= baseline_val - 1.5) or (val >= 95.0)
            is_last = (i == len(records) - 1)

            if recovered or is_last:
                # Event ended - compute metrics
                in_event = False
                nadir_rec = min(event_records, key=lambda r: float(r.get("spo2_value") or 100))
                nadir_val = int(nadir_rec.get("spo2_value") or 0)
                nadir_time = str(nadir_rec.get("time_str") or "")
                start_time = str(event_records[0].get("time_str") or "")
                end_time = str(rec.get("time_str") or "")

                # Estimate duration in seconds
                start_ts = event_records[0].get("timestamp")
                end_ts = rec.get("timestamp")
                if start_ts and end_ts and isinstance(start_ts, (int, float)) and isinstance(end_ts, (int, float)):
                    # Handle if timestamps are in ms vs s
                    ts_diff = end_ts - start_ts
                    duration_s = int(ts_diff / 1000) if ts_diff > 10000 else int(ts_diff)
                    duration_s = max(15, min(600, duration_s))
                else:
                    duration_s = max(20, len(event_records) * 30)

                drop_mag = round(baseline_val - nadir_val, 1)

                if nadir_val < 85:
                    severity = "CRITICAL"
                elif nadir_val < 90:
                    severity = "WARNING"
                else:
                    severity = "MILD"

                stage = nadir_rec.get("sleep_stage") or event_records[0].get("sleep_stage") or "Sleep"
                resp = nadir_rec.get("respiration_rate")

                events.append({
                    "date": rec.get("date", ""),
                    "start_time": start_time,
                    "nadir_time": nadir_time,
                    "end_time": end_time,
                    "duration_seconds": int(duration_s),
                    "baseline_spo2": round(baseline_val, 1),
                    "nadir_spo2": int(nadir_val),
                    "drop_magnitude": float(drop_mag),
                    "sleep_stage": str(stage).capitalize(),
                    "respiration_rate": round(float(resp), 1) if resp and pd.notna(resp) else None,
                    "severity": severity,
                    "event_type": "DESATURATION"
                })

    return events


def calculate_oxygen_desaturation_index(events: list[dict], sleep_duration_seconds: float | int | None) -> dict:
    """
    Computes the Oxygen Desaturation Index (ODI = events / sleep hours).
    Benchmarked against American Academy of Sleep Medicine (AASM) standards:
    - Normal: < 5 events/hour
    - Mild Sleep Apnea: 5 - 14.9 events/hour
    - Moderate Sleep Apnea: 15 - 29.9 events/hour
    - Severe Sleep Apnea: >= 30 events/hour
    """
    event_count = len(events)
    if not sleep_duration_seconds or sleep_duration_seconds <= 0:
        sleep_hours = 7.0  # default assumption if missing
    else:
        sleep_hours = float(sleep_duration_seconds) / 3600.0

    sleep_hours = max(1.0, sleep_hours)
    odi_score = round(event_count / sleep_hours, 1)

    if odi_score < 5.0:
        classification = "Normal"
        status_color = "#10b981"  # emerald-500
        description = "Minimal or normal nocturnal desaturations (<5/hr)."
    elif odi_score < 15.0:
        classification = "Mild Apnea Risk"
        status_color = "#f59e0b"  # amber-500
        description = "Mild oxygen desaturation frequency (5-15/hr). Monitor sleep posture and nasal airflow."
    elif odi_score < 30.0:
        classification = "Moderate Apnea Risk"
        status_color = "#f97316"  # orange-500
        description = "Moderate desaturation burden (15-30/hr). Clinical consultation recommended."
    else:
        classification = "Severe Apnea Risk"
        status_color = "#ef4444"  # red-500
        description = "High desaturation frequency (>=30/hr). Urgent polysomnography evaluation indicated."

    return {
        "odi_score": odi_score,
        "event_count": event_count,
        "sleep_hours": round(sleep_hours, 1),
        "classification": classification,
        "status_color": status_color,
        "description": description
    }


def calculate_hypoxic_burden(epochs_data: list[dict] | pd.DataFrame) -> dict:
    """
    Calculates nocturnal Hypoxic Burden:
    - T90: Total duration (seconds and minutes) where SpO2 < 90%
    - T85: Total duration where SpO2 < 85%
    - Min SpO2 nadir
    - Mean nocturnal SpO2
    """
    if isinstance(epochs_data, pd.DataFrame):
        if epochs_data.empty:
            return {"t90_minutes": 0.0, "t85_minutes": 0.0, "min_spo2": None, "mean_spo2": None}
        df = epochs_data
    elif epochs_data:
        df = pd.DataFrame(epochs_data)
    else:
        return {"t90_minutes": 0.0, "t85_minutes": 0.0, "min_spo2": None, "mean_spo2": None}

    if "spo2_value" not in df.columns or df["spo2_value"].dropna().empty:
        return {"t90_minutes": 0.0, "t85_minutes": 0.0, "min_spo2": None, "mean_spo2": None}

    vals = pd.to_numeric(df["spo2_value"], errors="coerce").dropna()
    if vals.empty:
        return {"t90_minutes": 0.0, "t85_minutes": 0.0, "min_spo2": None, "mean_spo2": None}

    # If epochs are 1-minute samples:
    total_samples = len(vals)
    t90_samples = (vals < 90).sum()
    t85_samples = (vals < 85).sum()

    # Each sample represents approx 1 minute
    t90_mins = round(float(t90_samples), 1)
    t85_mins = round(float(t85_samples), 1)

    min_val = int(vals.min())
    mean_val = round(float(vals.mean()), 1)

    return {
        "t90_minutes": t90_mins,
        "t85_minutes": t85_mins,
        "min_spo2": min_val,
        "mean_spo2": mean_val,
        "hypoxic_fraction_pct": round((t90_samples / total_samples) * 100.0, 1) if total_samples > 0 else 0.0
    }


def analyze_chrono_distribution(events: list[dict]) -> dict:
    """
    Bins exact-moment drop events into hourly buckets (00:00 to 23:00)
    to identify the Peak Vulnerability Window (e.g. 03:00 - 05:00 AM).
    """
    hourly_counts = {h: 0 for h in range(24)}
    hourly_severities = {h: {"CRITICAL": 0, "WARNING": 0, "MILD": 0} for h in range(24)}

    for ev in events:
        nadir_time = ev.get("nadir_time") or ev.get("start_time") or ""
        try:
            hour = int(nadir_time.split(":")[0])
            if 0 <= hour <= 23:
                hourly_counts[hour] += 1
                sev = ev.get("severity", "MILD")
                if sev in hourly_severities[hour]:
                    hourly_severities[hour][sev] += 1
        except Exception:
            continue

    # Find peak window (e.g. 2-hour sliding window with highest count)
    peak_count = 0
    peak_window = "None"
    for h in range(23):
        w_count = hourly_counts[h] + hourly_counts[h+1]
        if w_count > peak_count and w_count > 0:
            peak_count = w_count
            peak_window = f"{h:02d}:00 - {(h+2)%24:02d}:00"

    return {
        "hourly_counts": hourly_counts,
        "hourly_severities": hourly_severities,
        "peak_window": peak_window,
        "peak_event_count": peak_count
    }


if __name__ == "__main__":
    print("Testing Analytics Module...")
    df = db.get_df(limit=30)
    df_bands = calculate_hrv_baseline(df)
    print(f"Calculated baseline for {len(df_bands)} days.")
    if not df_bands.empty:
        latest = df_bands.iloc[-1]
        print(f"Latest HRV: {latest.get('hrv_last_night')} ms | Baseline: {latest.get('hrv_baseline_mean')} +/- {latest.get('hrv_baseline_sd')} ms")
        print(f"Bands: [{latest.get('hrv_band_lower')} - {latest.get('hrv_band_upper')}] Status: {latest.get('hrv_band_status')}")
    corr = calculate_correlation_matrix(df)
    print("Correlation matrix shape:", corr.shape)

