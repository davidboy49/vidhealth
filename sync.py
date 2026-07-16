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


def sync_latest(target_date: str | None = None) -> dict:
    """
    Fetch and persist the latest Garmin data.

    Garmin endpoints are independent, so partial results are saved while endpoint
    failures are returned as warnings for dashboard and command-line feedback.
    """
    api = get_api()
    date_str = target_date or date.today().isoformat()
    print(f"[SYNC] Syncing {date_str}...")

    data = sync_date(api, date_str)
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
        raise RuntimeError(f"No Garmin metrics were available for {date_str}. {detail}")

    backup_path = save_result(date_str, data)
    print(f"[OK] {date_str} - completed sync")
    return {
        "date": date_str,
        "sources": synced_sources,
        "warning_count": len(warnings),
        "warnings": warnings,
        "backup_path": str(backup_path),
    }

def backfill(days: int = 14):
    """Backfill the last N days of data."""
    api = get_api()
    today = date.today()
    for i in range(days):
        d = today - timedelta(days=i)
        ds = d.isoformat()
        out_path = DATA_DIR / f"{ds}.json"
        
        # Check if already synced in DB or file
        if out_path.exists() and i > 1:
            try:
                conn = db.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT date FROM daily_metrics WHERE date = ?", (ds,))
                row = cursor.fetchone()
                conn.close()
                if row:
                    print(f"[SKIP] {ds} - already synced")
                    continue
            except Exception:
                pass
        
        print(f"[SYNC] {ds} - fetching...")
        data = sync_date(api, ds)
        save_result(ds, data)
        print(f"[OK] {ds} - synced")
        time.sleep(1)  # rate limit safety
    print(f"\n[DONE] Synced {days} days")

def sync_today() -> dict:
    """Sync just today (for cron use)."""
    return sync_latest()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "backfill":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 14
        backfill(days)
    elif len(sys.argv) > 1 and sys.argv[1] == "today":
        sync_today()
    else:
        backfill(14)
