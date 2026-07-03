import sqlite3
import json
from pathlib import Path
from datetime import datetime, date

DB_PATH = Path(__file__).parent / "health.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS daily_metrics (
        date TEXT PRIMARY KEY,
        hrv_last_night INTEGER,
        hrv_weekly_avg INTEGER,
        hrv_status TEXT,
        sleep_score INTEGER,
        sleep_duration INTEGER,
        sleep_deep INTEGER,
        sleep_light INTEGER,
        sleep_rem INTEGER,
        sleep_awake INTEGER,
        resting_hr INTEGER,
        min_hr INTEGER,
        max_hr INTEGER,
        bb_max INTEGER,
        bb_min INTEGER,
        bb_charged INTEGER,
        bb_drained INTEGER,
        stress_avg INTEGER,
        stress_max INTEGER,
        steps INTEGER,
        floors INTEGER,
        training_readiness INTEGER,
        spo2_avg REAL,
        spo2_min INTEGER,
        respiration_avg REAL,
        respiration_min REAL,
        workout_type TEXT,
        alcohol_logged INTEGER DEFAULT 0,
        sleep_apnea_flag INTEGER DEFAULT 0,
        ai_summary TEXT,
        raw_json TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS body_comp (
        date TEXT PRIMARY KEY,
        weight REAL,
        body_fat REAL,
        waist REAL
    )
    """)
    conn.commit()
    conn.close()

def save_day(date_str: str, raw_data: dict):
    """
    Parses Garmin raw data dictionary and updates/inserts it into the SQLite DB.
    Uses the 'summary' endpoint as the primary source for consolidated metrics
    (it has consistent field names), then falls back to individual endpoints.
    """
    init_db()
    
    summary = raw_data.get("summary", {})
    if isinstance(summary, dict):
        # Summary has the most reliable, consolidated data
        resting_hr = summary.get("restingHeartRate")
        min_hr = summary.get("minHeartRate")
        max_hr = summary.get("maxHeartRate")
        stress_avg = summary.get("averageStressLevel")
        stress_max = summary.get("maxStressLevel")
        steps = summary.get("totalSteps")
        spo2_avg = summary.get("averageSpo2")
        spo2_min = summary.get("lowestSpo2")
        respiration_avg = summary.get("avgWakingRespirationValue")
        respiration_min = summary.get("lowestRespirationValue")
        bb_max = summary.get("bodyBatteryHighestValue")
        bb_min = summary.get("bodyBatteryLowestValue")
        bb_charged = summary.get("bodyBatteryChargedValue")
        bb_drained = summary.get("bodyBatteryDrainedValue")
        training_readiness = summary.get("trainingReadiness")
        floors = summary.get("floorsAscended")
    else:
        resting_hr = min_hr = max_hr = None
        stress_avg = stress_max = None
        steps = None
        spo2_avg = spo2_min = None
        respiration_avg = respiration_min = None
        bb_max = bb_min = bb_charged = bb_drained = None
        training_readiness = None
        floors = None

    # HRV — nested under hrv.hrvSummary
    hrv = raw_data.get("hrv", {})
    hrv_last_night = None
    hrv_weekly_avg = None
    hrv_status = None
    if isinstance(hrv, dict):
        hrv_summary = hrv.get("hrvSummary", {})
        if isinstance(hrv_summary, dict):
            hrv_last_night = hrv_summary.get("lastNightAvg")
            hrv_weekly_avg = hrv_summary.get("weeklyAvg")
            hrv_status = hrv_summary.get("status")

    # Sleep — dailySleepDTO has sleepTimeSeconds, not sleepTime
    sleep = raw_data.get("sleep", {})
    daily_sleep = sleep.get("dailySleepDTO", {}) if isinstance(sleep, dict) else {}
    sleep_score = None
    sleep_duration = None
    sleep_deep = None
    sleep_light = None
    sleep_rem = None
    sleep_awake = None
    if isinstance(daily_sleep, dict):
        ss = daily_sleep.get("sleepScores", {})
        sleep_score = ss.get("overall", {}).get("value") if isinstance(ss, dict) else None
        sleep_duration = daily_sleep.get("sleepTimeSeconds")
        sleep_deep = daily_sleep.get("deepSleepSeconds")
        sleep_light = daily_sleep.get("lightSleepSeconds")
        sleep_rem = daily_sleep.get("remSleepSeconds")
        sleep_awake = daily_sleep.get("awakeSleepSeconds")

    # Steps — when it's a list of interval buckets, sum them
    steps_data = raw_data.get("steps", [])
    if steps is None:
        if isinstance(steps_data, list):
            steps = sum(item.get("steps", 0) for item in steps_data if isinstance(item, dict))
        elif isinstance(steps_data, dict):
            steps = steps_data.get("totalSteps")
        elif isinstance(steps_data, (int, float)):
            steps = int(steps_data)

    # HR fallback (if summary wasn't available)
    if resting_hr is None:
        hr = raw_data.get("heart_rate", {})
        if isinstance(hr, dict):
            resting_hr = hr.get("restingHeartRate")
            min_hr = hr.get("minHeartRate")
            max_hr = hr.get("maxHeartRate")

    # Training readiness fallback
    if training_readiness is None:
        tr = raw_data.get("training_readiness", {})
        if isinstance(tr, dict):
            rq = tr.get("readinessQualifier", {})
            if isinstance(rq, dict):
                training_readiness = rq.get("readinessScore")

    # Store raw json
    raw_json_str = json.dumps(raw_data, default=str)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO daily_metrics (
        date, hrv_last_night, hrv_weekly_avg, hrv_status, sleep_score, sleep_duration,
        sleep_deep, sleep_light, sleep_rem, sleep_awake, resting_hr, min_hr, max_hr,
        bb_max, bb_min, bb_charged, bb_drained, stress_avg, stress_max, steps, floors,
        training_readiness, spo2_avg, spo2_min, respiration_avg, respiration_min, raw_json
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(date) DO UPDATE SET
        hrv_last_night = excluded.hrv_last_night,
        hrv_weekly_avg = excluded.hrv_weekly_avg,
        hrv_status = excluded.hrv_status,
        sleep_score = excluded.sleep_score,
        sleep_duration = excluded.sleep_duration,
        sleep_deep = excluded.sleep_deep,
        sleep_light = excluded.sleep_light,
        sleep_rem = excluded.sleep_rem,
        sleep_awake = excluded.sleep_awake,
        resting_hr = excluded.resting_hr,
        min_hr = excluded.min_hr,
        max_hr = excluded.max_hr,
        bb_max = excluded.bb_max,
        bb_min = excluded.bb_min,
        bb_charged = excluded.bb_charged,
        bb_drained = excluded.bb_drained,
        stress_avg = excluded.stress_avg,
        stress_max = excluded.stress_max,
        steps = excluded.steps,
        floors = excluded.floors,
        training_readiness = excluded.training_readiness,
        spo2_avg = excluded.spo2_avg,
        spo2_min = excluded.spo2_min,
        respiration_avg = excluded.respiration_avg,
        respiration_min = excluded.respiration_min,
        raw_json = excluded.raw_json
    """, (
        date_str, hrv_last_night, hrv_weekly_avg, hrv_status, sleep_score, sleep_duration,
        sleep_deep, sleep_light, sleep_rem, sleep_awake, resting_hr, min_hr, max_hr,
        bb_max, bb_min, bb_charged, bb_drained, stress_avg, stress_max, steps, floors,
        training_readiness, spo2_avg, spo2_min, respiration_avg, respiration_min, raw_json_str
    ))
    conn.commit()
    conn.close()

def get_df(limit: int | None = 30):
    """
    Loads daily metrics as a pandas DataFrame.
    """
    import pandas as pd
    init_db()
    conn = get_connection()
    query = """
        SELECT * FROM daily_metrics
        ORDER BY date ASC
    """
    params = ()
    if limit is not None:
        query += " LIMIT ?"
        params = (int(limit),)
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def update_custom_field(date_str: str, field_name: str, value):
    """
    Updates custom fields like workout_type, alcohol_logged, sleep_apnea_flag, etc.
    """
    init_db()
    valid_fields = {"workout_type", "alcohol_logged", "sleep_apnea_flag", "ai_summary"}
    if field_name not in valid_fields:
        raise ValueError(f"Invalid field: {field_name}")
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE daily_metrics SET {field_name} = ? WHERE date = ?", (value, date_str))
    conn.commit()
    conn.close()

def save_body_comp(date_str: str, weight: float, body_fat: float, waist: float):
    """
    Saves or updates manual body composition measurements.
    """
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO body_comp (date, weight, body_fat, waist)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(date) DO UPDATE SET
        weight = excluded.weight,
        body_fat = excluded.body_fat,
        waist = excluded.waist
    """, (date_str, weight, body_fat, waist))
    conn.commit()
    conn.close()

def get_body_comp_df(limit: int = 30):
    """
    Loads body composition metrics as a pandas DataFrame.
    """
    import pandas as pd
    init_db()
    conn = get_connection()
    df = pd.read_sql_query(f"""
        SELECT * FROM body_comp 
        ORDER BY date ASC 
        LIMIT {limit}
    """, conn)
    conn.close()
    return df

if __name__ == "__main__":
    init_db()
    print("Database initialized at:", DB_PATH)
