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
