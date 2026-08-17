#!/usr/bin/env python3
"""
Automated Health Anomaly Detection & Dispatcher Module
Monitors Garmin biometric metrics for:
- SpO2 Oxygen desaturations
- Resting Heart Rate spikes
- Severe HRV Autonomic crashes
- Acute Recovery Debt & Sleep architecture disruption
Dispatches proactive Telegram alerts and saves records to SQLite DB.
"""

import os
import asyncio
import logging
from datetime import date
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

# Load env variables
load_dotenv(Path(__file__).parent / ".env")

import db
import analytics

logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
AUTHORIZED_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def scan_daily_anomalies(target_date: str | None = None) -> list[dict]:
    """
    Scans the specified date (or latest date in DB) for biometric anomalies
    against historical personalized baselines.
    Returns a list of anomaly dictionaries.
    """
    df = db.get_df(limit=30)
    if df.empty:
        return []

    # Get target day row
    if target_date:
        match = df[df["date"] == target_date]
        if match.empty:
            return []
        current_row = match.iloc[0]
        # Restrict history up to target_date
        df_history = df[df["date"] <= target_date].copy()
    else:
        current_row = df.iloc[-1]
        target_date = current_row["date"]
        df_history = df.copy()

    # Calculate personalized baseline stats
    df_bands = analytics.calculate_hrv_baseline(df_history)
    current_band_row = df_bands.iloc[-1]

    anomalies = []

    # 1. Exact-Moment SpO2 Desaturation Check
    spo2_min = current_row.get("spo2_min")
    spo2_avg = current_row.get("spo2_avg")
    drop_events = db.get_spo2_drop_events(target_date)
    sleep_duration = current_row.get("sleep_duration")
    odi_info = analytics.calculate_oxygen_desaturation_index(drop_events, sleep_duration)
    
    worst_event = min(drop_events, key=lambda e: e.get("nadir_spo2", 100)) if drop_events else None

    if spo2_min is not None and pd.notna(spo2_min):
        spo2_min_val = float(spo2_min)
        if spo2_min_val < 85.0:
            exact_detail = ""
            if worst_event:
                exact_detail = f" at exact moment **{worst_event.get('nadir_time')}** (duration: {worst_event.get('duration_seconds')}s, stage: {worst_event.get('sleep_stage')}, resp: {worst_event.get('respiration_rate') or '—'} brpm)"
            anomalies.append({
                "date": target_date,
                "severity": "CRITICAL",
                "alert_type": "SPO2_CRITICAL_DROP",
                "title": "🚨 Critical Oxygen Desaturation",
                "message": f"Overnight SpO2 dropped to **{int(spo2_min_val)}%**{exact_detail}. Estimated ODI: **{odi_info['odi_score']} events/hr** ({odi_info['classification']}). Frequent drops below 88% indicate airway obstruction / sleep apnea risk.",
                "metrics": {"spo2_min": spo2_min_val, "spo2_avg": float(spo2_avg) if spo2_avg else None, "worst_event": worst_event, "odi": odi_info}
            })
        elif spo2_min_val < 90.0 or odi_info["odi_score"] >= 5.0:
            exact_detail = ""
            if worst_event:
                exact_detail = f" at exact moment **{worst_event.get('nadir_time')}** (stage: {worst_event.get('sleep_stage')}, duration: {worst_event.get('duration_seconds')}s)"
            anomalies.append({
                "date": target_date,
                "severity": "WARNING",
                "alert_type": "SPO2_DESATURATION",
                "title": "⚠️ Sleep Oxygen Desaturation",
                "message": f"Overnight SpO2 reached a nadir of **{int(spo2_min_val)}%**{exact_detail}. Estimated ODI: **{odi_info['odi_score']}/hr** ({odi_info['classification']}). Total events: {len(drop_events)}.",
                "metrics": {"spo2_min": spo2_min_val, "spo2_avg": float(spo2_avg) if spo2_avg else None, "worst_event": worst_event, "odi": odi_info}
            })

    # 2. Resting HR Spike Check (vs 7-28 day baseline)
    rhr = current_row.get("resting_hr")
    if rhr is not None and pd.notna(rhr):
        rhr_val = float(rhr)
        past_rhrs = df_history["resting_hr"].dropna()
        if len(past_rhrs) >= 4:
            baseline_rhr = past_rhrs.iloc[:-1].mean()
            rhr_diff = rhr_val - baseline_rhr
            if rhr_diff >= 6.0:
                severity = "CRITICAL" if rhr_diff >= 9.0 else "WARNING"
                anomalies.append({
                    "date": target_date,
                    "severity": severity,
                    "alert_type": "ELEVATED_RHR",
                    "title": "📈 Resting Heart Rate Elevation",
                    "message": f"Resting HR is **{int(rhr_val)} bpm** (+{rhr_diff:.1f} bpm above baseline {baseline_rhr:.1f} bpm). Suggests acute sympathetic activation, systemic inflammation, or impending illness.",
                    "metrics": {"resting_hr": rhr_val, "baseline_rhr": round(baseline_rhr, 1), "diff": round(rhr_diff, 1)}
                })

    # 3. HRV Autonomic Crash Check
    hrv = current_row.get("hrv_last_night")
    if hrv is not None and pd.notna(hrv):
        hrv_val = float(hrv)
        band_status = current_band_row.get("hrv_band_status")
        band_lower = current_band_row.get("hrv_band_lower")
        base_mean = current_band_row.get("hrv_baseline_mean")
        
        if band_status == "Severe Suppression":
            anomalies.append({
                "date": target_date,
                "severity": "WARNING",
                "alert_type": "HRV_AUTONOMIC_CRASH",
                "title": "📉 Severe HRV Autonomic Crash",
                "message": f"Last night's HRV dropped to **{int(hrv_val)} ms** (Baseline normal: {band_lower or '—'} - {current_band_row.get('hrv_band_upper') or '—'} ms). Parasympathetic tone is severely suppressed.",
                "metrics": {"hrv": hrv_val, "baseline_mean": base_mean, "band_lower": band_lower}
            })

    # 4. Acute Recovery Debt Check (Body Battery & Sleep)
    bb_max = current_row.get("bb_max")
    sleep_score = current_row.get("sleep_score")
    stress_avg = current_row.get("stress_avg")
    if bb_max is not None and pd.notna(bb_max):
        bb_max_val = float(bb_max)
        if bb_max_val < 45.0:
            anomalies.append({
                "date": target_date,
                "severity": "WARNING",
                "alert_type": "ACUTE_RECOVERY_DEBT",
                "title": "🔋 Low Body Battery Recharge",
                "message": f"Body Battery only reached a peak of **{int(bb_max_val)}/100** overnight. Sleep Score: {sleep_score or '—'}/100, Stress: {stress_avg or '—'}/100. Deload or active recovery is strongly indicated.",
                "metrics": {"bb_max": bb_max_val, "sleep_score": sleep_score, "stress_avg": stress_avg}
            })

    # 5. Sleep Architecture Disruption
    sleep_disruption = analytics.calculate_sleep_disruption_index(current_row)
    if sleep_disruption.get("category") == "High Disruption":
        drivers_text = ", ".join(sleep_disruption.get("drivers", []))
        anomalies.append({
            "date": target_date,
            "severity": "INFO",
            "alert_type": "SLEEP_ARCHITECTURE_DISRUPTED",
            "title": "😴 Fragmented Sleep Architecture",
            "message": f"Sleep Disruption Index reached **{sleep_disruption['score']}/100** ({drivers_text}).",
            "metrics": sleep_disruption
        })

    return anomalies


async def _send_telegram_alert(anomaly: dict):
    """Sends formatted anomaly alert to whitelisted Telegram chat."""
    if not BOT_TOKEN or not AUTHORIZED_CHAT_ID:
        return

    from telegram import Bot
    bot = Bot(token=BOT_TOKEN)

    badge = "🚨 [CRITICAL ALERT]" if anomaly["severity"] == "CRITICAL" else "⚠️ [HEALTH NOTICE]"
    msg = (
        f"{badge}\n"
        f"*{anomaly['title']}*\n"
        f"📅 Date: `{anomaly['date']}`\n\n"
        f"{anomaly['message']}\n"
    )

    try:
        await bot.send_message(chat_id=AUTHORIZED_CHAT_ID, text=msg, parse_mode="Markdown")
        logger.info(f"Dispatched Telegram alert: {anomaly['alert_type']}")
    except Exception as e:
        logger.error(f"Failed to dispatch Telegram alert: {e}")


def dispatch_alerts_if_needed(target_date: str | None = None, notify_telegram: bool = True) -> list[dict]:
    """
    Scans for anomalies, saves new ones to DB, and sends Telegram alerts.
    Prevents duplicate alerts of same type for the same date.
    """
    anomalies = scan_daily_anomalies(target_date)
    if not anomalies:
        return []

    existing_alerts = db.get_recent_alerts(limit=50)
    existing_keys = {(a["date"], a["alert_type"]) for a in existing_alerts}

    dispatched = []
    for anomaly in anomalies:
        key = (anomaly["date"], anomaly["alert_type"])
        if key not in existing_keys:
            # Save to database
            db.save_anomaly_alert(
                date_str=anomaly["date"],
                severity=anomaly["severity"],
                alert_type=anomaly["alert_type"],
                message=anomaly["message"],
                metrics_dict=anomaly.get("metrics")
            )
            dispatched.append(anomaly)

            # Send Telegram push if enabled
            if notify_telegram and BOT_TOKEN and AUTHORIZED_CHAT_ID:
                try:
                    asyncio.run(_send_telegram_alert(anomaly))
                except Exception as e:
                    # In case of event loop issues
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            loop.create_task(_send_telegram_alert(anomaly))
                        else:
                            loop.run_until_complete(_send_telegram_alert(anomaly))
                    except Exception as loop_err:
                        logger.error(f"Telegram notification error: {loop_err}")

    return dispatched


if __name__ == "__main__":
    print("Scanning for Biometric Anomalies...")
    anomalies = scan_daily_anomalies()
    print(f"Found {len(anomalies)} anomalies:")
    for a in anomalies:
        print(f"- [{a['severity']}] {a['title']}: {a['message']}")
