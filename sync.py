#!/usr/bin/env python3
"""
Garmin Health Sync — fetches HRV, sleep, heart rate, body battery, stress, training readiness, SpO2, and respiration.
Uses garminconnect library.
Stores as JSON per day and saves to SQLite database.
"""

import json
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv
from garminconnect import Garmin

# Load environment variables
load_dotenv(Path(__file__).parent / ".env")

import db
import anomaly_detector

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

TOKEN_STORE = Path(__file__).parent / ".garmin_tokens"
TOKEN_STORE.mkdir(parents=True, exist_ok=True)

def get_api():
    email = os.environ.get("GARMIN_EMAIL")
    password = os.environ.get("GARMIN_PASSWORD")
    if not email or not password:
        raise ValueError("GARMIN_EMAIL or GARMIN_PASSWORD environment variables not set in .env")
    
    # Enable session token storage to prevent 429 rate limit errors
    api = Garmin(email, password)
    api.login(str(TOKEN_STORE))
    return api

def sync_date(api, target_date: str) -> dict:
    """Fetch all available health data for a given date (YYYY-MM-DD)."""
    result = {"date": target_date}
    
    try:
        hrv = api.get_hrv_data(target_date)
        if hrv:
            result["hrv"] = hrv
    except Exception as e:
        result["hrv_error"] = str(e)
    
    try:
        sleep = api.get_sleep_data(target_date)
        if sleep:
            result["sleep"] = sleep
    except Exception as e:
        result["sleep_error"] = str(e)
    
    try:
        hr = api.get_heart_rates(target_date)
        if hr:
            result["heart_rate"] = hr
    except Exception as e:
        result["hr_error"] = str(e)
    
    try:
        bb = api.get_body_battery(target_date)
        if bb:
            result["body_battery"] = bb
    except Exception as e:
        result["body_battery_error"] = str(e)
    
    try:
        stress = api.get_all_day_stress(target_date)
        if stress:
            result["stress"] = stress
    except Exception as e:
        result["stress_error"] = str(e)
    
    try:
        steps = api.get_steps_data(target_date)
        if steps:
            result["steps"] = steps
    except Exception as e:
        result["steps_error"] = str(e)
    
    try:
        readiness = api.get_morning_training_readiness(target_date)
        if readiness:
            result["training_readiness"] = readiness
    except Exception as e:
        result["readiness_error"] = str(e)
    
    try:
        summary = api.get_stats(target_date)
        if summary:
            result["summary"] = summary
    except Exception as e:
        result["summary_error"] = str(e)

    try:
        pulse_ox = api.get_spo2_data(target_date)
        if pulse_ox:
            result["pulse_ox"] = pulse_ox
    except Exception as e:
        result["pulse_ox_error"] = str(e)

    try:
        respiration = api.get_respiration_data(target_date)
        if respiration:
            result["respiration"] = respiration
    except Exception as e:
        result["respiration_error"] = str(e)
    
    return result

def save_result(target_date: str, data: dict) -> Path:
    # Save raw JSON backup
    out_path = DATA_DIR / f"{target_date}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

    # Save to SQLite DB. Let failures propagate so callers never report a false success.
    db.save_day(target_date, data)
    print(f"[OK] {target_date} - saved to DB")
    return out_path


def smart_sync(days: int = 3) -> dict:
    """
    Smart Rolling Sync: Syncs the last N days (default 3: today, yesterday, 2 days ago).
    Ensures late-arriving sleep, nocturnal SpO2, and HRV data from Bluetooth watch syncs
    are reliably captured, and heals any brief multi-day gap.
    """
    api = get_api()
    today = date.today()
    synced_dates = []
    failed_dates = []
    warnings_accum = {}

    print(f"[SMART SYNC] Starting {days}-day rolling sync (from {today.isoformat()})...")

    for i in range(days):
        d = today - timedelta(days=i)
        ds = d.isoformat()
        print(f"[SYNC] Processing {ds} (day -{i})...")
        try:
            data = sync_date(api, ds)
            synced_sources = sorted(
                key for key, value in data.items()
                if key != "date" and not key.endswith("_error") and value
            )
            day_warnings = {
                key.removesuffix("_error"): value
                for key, value in data.items()
                if key.endswith("_error")
            }
            if day_warnings:
                warnings_accum[ds] = day_warnings

            if synced_sources:
                save_result(ds, data)
                synced_dates.append(ds)
                
                # Check for anomalies on recent days
                try:
                    anomaly_detector.dispatch_alerts_if_needed(ds)
                except Exception as alert_err:
                    print(f"[WARN] Anomaly check for {ds}: {alert_err}")
            else:
                print(f"[WARN] {ds} - No metric endpoints returned data from Garmin.")
                failed_dates.append(ds)
        except Exception as e:
            print(f"[ERROR] Failed syncing {ds}: {e}")
            failed_dates.append(ds)

        if i < days - 1:
            time.sleep(1) # API rate limit buffer

    # Ensure SpO2 high-resolution epochs and event tables are synced
    try:
        db.backfill_spo2_epochs_if_needed()
    except Exception as ep_err:
        print(f"[WARN] SpO2 backfill check: {ep_err}")

    summary = {
        "status": "success" if synced_dates else "partial",
        "synced_dates": synced_dates,
        "failed_dates": failed_dates,
        "days_synced": len(synced_dates),
        "total_requested": days,
        "warnings": warnings_accum
    }
    print(f"[DONE] Smart sync completed. {len(synced_dates)}/{days} days synced.")
    return summary


def sync_latest(target_date: str | None = None) -> dict:
    """
    Fetch and persist Garmin data.
    If target_date is specified, syncs that single date.
    Otherwise, executes a smart rolling 3-day sync to guarantee no missing sleep/SpO2 records.
    """
    if target_date:
        api = get_api()
        print(f"[SYNC] Syncing single date: {target_date}...")
        data = sync_date(api, target_date)
        synced_sources = sorted(
            key for key, value in data.items()
            if key != "date" and not key.endswith("_error") and value
        )
        warnings = {
            key.removesuffix("_error"): value
            for key, value in data.items()
            if key.endswith("_error")
        }

        if not synced_sources:
            detail = next(iter(warnings.values()), "Garmin returned no data.")
            raise RuntimeError(f"No Garmin metrics were available for {target_date}. {detail}")

        backup_path = save_result(target_date, data)
        try:
            anomaly_detector.dispatch_alerts_if_needed(target_date)
        except Exception as e:
            print(f"[WARN] Anomaly check for {target_date}: {e}")

        return {
            "date": target_date,
            "sources": synced_sources,
            "warning_count": len(warnings),
            "warnings": warnings,
            "backup_path": str(backup_path),
        }
    else:
        # Default: smart rolling 3-day sync
        res = smart_sync(days=3)
        return {
            "date": date.today().isoformat(),
            "sources": ["rolling_3_days"],
            "warning_count": len(res.get("warnings", {})),
            "warnings": res.get("warnings", {}),
            "synced_dates": res.get("synced_dates", []),
            "backup_path": str(DATA_DIR)
        }


def backfill(days: int = 30, force: bool = False) -> dict:
    """
    Comprehensive historical backfill across the last N days.
    - Checks SQLite database and skips already completed days (unless force=True).
    - Always re-syncs the most recent 3 days for finalized sleep/SpO2 data.
    - Implements 1-second rate-limiting delays to prevent Garmin 429 errors.
    - Ingests exact-moment SpO2 desaturation epochs into health.db.
    """
    api = get_api()
    today = date.today()
    synced_dates = []
    skipped_dates = []
    failed_dates = []

    print(f"[BACKFILL] Initiating {days}-day historical backfill (force={force})...")

    for i in range(days):
        d = today - timedelta(days=i)
        ds = d.isoformat()
        out_path = DATA_DIR / f"{ds}.json"

        # Check if already synced in DB
        if not force and out_path.exists() and i > 3:
            try:
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT date FROM daily_metrics WHERE date = ?", (ds,))
                row = cursor.fetchone()
                conn.close()
                if row:
                    print(f"[SKIP] {ds} - already archived in database")
                    skipped_dates.append(ds)
                    continue
            except Exception:
                pass

        print(f"[SYNC] {ds} ({i+1}/{days}) - fetching from Garmin...")
        try:
            data = sync_date(api, ds)
            save_result(ds, data)
            synced_dates.append(ds)
            print(f"[OK] {ds} - synced and parsed")
        except Exception as e:
            print(f"[ERROR] Failed {ds}: {e}")
            failed_dates.append(ds)

        time.sleep(1) # API rate limit safety

    # Run SpO2 epoch backfill pass across all historical raw JSONs
    try:
        db.backfill_spo2_epochs_if_needed()
    except Exception as ep_err:
        print(f"[WARN] SpO2 backfill error: {ep_err}")

    summary = {
        "days_synced": len(synced_dates),
        "days_skipped": len(skipped_dates),
        "days_failed": len(failed_dates),
        "synced_dates": synced_dates,
        "skipped_dates": skipped_dates
    }
    print(f"\n[DONE] Backfill complete: {len(synced_dates)} synced, {len(skipped_dates)} skipped, {len(failed_dates)} failed.")
    return summary


def sync_today() -> dict:
    """Sync today + rolling 3 days for cron/systemd service use."""
    return smart_sync(days=3)


if __name__ == "__main__":
    force_flag = "--force" in sys.argv
    if len(sys.argv) > 1 and sys.argv[1] == "backfill":
        days = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 30
        backfill(days=days, force=force_flag)
    elif len(sys.argv) > 1 and sys.argv[1] == "smart":
        days = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 3
        smart_sync(days=days)
    elif len(sys.argv) > 1 and sys.argv[1] == "today":
        sync_today()
    else:
        smart_sync(days=3)
