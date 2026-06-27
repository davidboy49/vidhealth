#!/usr/bin/env python3
"""
Garmin Health Sync — fetches HRV, sleep, heart rate, body battery, stress, training readiness.
Uses garminconnect library (actively maintained).
Stores as JSONL per day in /root/garmin-health/data/.
"""

import json, os, sys, time
from datetime import date, timedelta
from pathlib import Path

import yaml
from garminconnect import Garmin

CONFIG_PATH = Path(__file__).parent / "config.yaml"
DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

with open(CONFIG_PATH) as f:
    config = yaml.safe_load(f)

def get_api():
    api = Garmin(config["email"], config["password"])
    api.login()
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
        sleep = api.get_daily_sleep(target_date)
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
        steps = api.get_daily_steps(target_date)
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
        summary = api.get_daily_summary(target_date)
        if summary:
            result["summary"] = summary
    except Exception as e:
        result["summary_error"] = str(e)
    
    return result

def backfill(days: int = 14):
    """Backfill the last N days of data."""
    api = get_api()
    today = date.today()
    for i in range(days):
        d = today - timedelta(days=i)
        ds = d.isoformat()
        out_path = DATA_DIR / f"{ds}.json"
        if out_path.exists():
            print(f"[~] {ds} — already synced")
            continue
        print(f"[→] {ds} — fetching...")
        data = sync_date(api, ds)
        with open(out_path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        print(f"[✓] {ds} — saved")
        time.sleep(1)  # rate limit safety
    print(f"\n[Done] Synced {days} days to {DATA_DIR}")

def sync_today():
    """Sync just today (for cron use)."""
    api = get_api()
    d = date.today().isoformat()
    out_path = DATA_DIR / f"{d}.json"
    data = sync_date(api, d)
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"[✓] {d} — synced")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "backfill":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 14
        backfill(days)
    elif len(sys.argv) > 1 and sys.argv[1] == "today":
        sync_today()
    else:
        backfill(14)
