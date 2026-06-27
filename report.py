#!/usr/bin/env python3
"""
Generate a human-readable health report from the latest data.
"""

import json
from datetime import date, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

def load_latest(days=7):
    records = []
    today = date.today()
    for i in range(days):
        d = today - timedelta(days=i)
        p = DATA_DIR / f"{d.isoformat()}.json"
        if p.exists():
            with open(p) as f:
                records.append(json.load(f))
    records.sort(key=lambda r: r["date"], reverse=True)
    return records

def safe_get(d, *keys, default=None):
    for k in keys:
        if isinstance(d, dict):
            d = d.get(k)
        else:
            return default
        if d is None:
            return default
    return d if d is not None else default

def generate_report(days=7):
    records = load_latest(days)
    if not records:
        return "No health data synced yet. Put on your Fenix 7X and wear it — data starts flowing after a few days."
    
    lines = []
    lines.append(f"📊 **Garmin Health — Last {len(records)} Days**\n")
    
    # HRV
    hrv_vals = []
    for r in records:
        h = r.get("hrv", {})
        if isinstance(h, dict):
            v = h.get("weeklyAvg") or h.get("lastNightAvg")
            if v and v != 0:
                hrv_vals.append(v)
    
    if hrv_vals:
        avg = sum(hrv_vals) / len(hrv_vals)
        lines.append(f"**HRV** 7-day avg: {avg:.0f}ms | Last: {hrv_vals[0]:.0f}ms")
    else:
        lines.append("**HRV** — calibrating (need ~7 days)")
    
    # Sleep
    sleep_scores = []
    for r in records:
        s = r.get("sleep", {})
        daily = s.get("dailySleepDTO", {})
        ss = daily.get("sleepScores", {}).get("overall", {}).get("value") if isinstance(daily, dict) else None
        if ss:
            sleep_scores.append(ss)
    
    if sleep_scores:
        avg = sum(sleep_scores) / len(sleep_scores)
        lines.append(f"**Sleep** Avg score: {avg:.0f}/100 | Last: {sleep_scores[0]}/100")
    else:
        lines.append("**Sleep** — calibrating")
    
    # Resting HR
    resting_hrs = []
    for r in records:
        hr = r.get("heart_rate", {})
        if isinstance(hr, dict):
            v = hr.get("restingHeartRate")
            if v:
                resting_hrs.append(v)
    
    if resting_hrs:
        avg = sum(resting_hrs) / len(resting_hrs)
        lines.append(f"**Resting HR** Avg: {avg:.0f} bpm | Today: {resting_hrs[0]} bpm")
    
    # Body Battery
    bb_maxes = []
    bb_mins = []
    for r in records:
        bb = r.get("body_battery", {})
        if isinstance(bb, dict):
            mx = bb.get("bodyBatteryMax")
            mn = bb.get("bodyBatteryMin")
            if mx: bb_maxes.append(mx)
            if mn: bb_mins.append(mn)
    
    if bb_maxes and bb_mins:
        lines.append(f"**Body Battery** Avg: {sum(bb_maxes)/len(bb_maxes):.0f}→{sum(bb_mins)/len(bb_mins):.0f} | Today: {bb_maxes[0]}→{bb_mins[0]}")
    
    # Stress
    stress_vals = []
    for r in records:
        st = r.get("stress", {})
        avg = safe_get(st, "bodyBatteryStressValues", "restStressDurationInMilliseconds") if isinstance(st, dict) else None
        if avg:
            stress_vals.append(avg)
    
    if stress_vals:
        lines.append(f"**Stress** tracked daily")
    
    # Steps
    steps_vals = []
    for r in records:
        st = r.get("steps", {})
        if isinstance(st, dict) and "totalSteps" in st:
            steps_vals.append(st["totalSteps"])
    
    if steps_vals:
        avg = sum(steps_vals) / len(steps_vals)
        lines.append(f"**Steps** Avg: {avg:.0f}/day | Today: {steps_vals[0]:,}")
    
    # Training readiness
    readiness_vals = []
    for r in records:
        tr = r.get("training_readiness", {})
        if isinstance(tr, dict):
            req = tr.get("readinessQualifier", {})
            rv = safe_get(req, "readinessScore") if isinstance(req, dict) else None
            if rv:
                readiness_vals.append(rv)
    
    if readiness_vals:
        lines.append(f"**Training Readiness** Today: {readiness_vals[0]}/100")
    
    lines.append("")
    
    # Quick verdict
    warnings = []
    if hrv_vals and hrv_vals[0] < 50:
        warnings.append("⚠️ HRV low — high stress or poor recovery")
    if sleep_scores and sleep_scores[0] < 70:
        warnings.append("⚠️ Sleep quality low — prioritize rest tonight")
    if readiness_vals and readiness_vals[0] and readiness_vals[0] < 60:
        warnings.append("⚠️ Training readiness low — rest day recommended")
    if resting_hrs and len(resting_hrs) > 3 and resting_hrs[0] > resting_hrs[-1] * 1.05:
        warnings.append("⚠️ Resting HR rising — possible overtraining or illness")
    
    if warnings:
        lines.append("**Verdict:**")
        lines.extend(warnings)
    else:
        lines.append("**Verdict:** ✅ Recovery looks solid. Full send.")
    
    return "\n".join(lines)

if __name__ == "__main__":
    print(generate_report())
