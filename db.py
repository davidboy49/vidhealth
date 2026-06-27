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
    """
    init_db()
    
    # Extract values safely
    hrv = raw_data.get("hrv", {})
    hrv_last_night = None
    hrv_weekly_avg = None
    if isinstance(hrv, dict):
        hrv_last_night = hrv.get("lastNightAvg") or hrv.get("last_night_avg")
        hrv_weekly_avg = hrv.get("weeklyAvg") or hrv.get("weekly_avg")

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
        sleep_duration = daily_sleep.get("sleepTime")
        sleep_deep = daily_sleep.get("deepSleepSeconds")
        sleep_light = daily_sleep.get("lightSleepSeconds")
        sleep_rem = daily_sleep.get("remSleepSeconds")
        sleep_awake = daily_sleep.get("awakeSleepSeconds")

    hr = raw_data.get("heart_rate", {})
    resting_hr = None
    min_hr = None
    max_hr = None
    if isinstance(hr, dict):
        resting_hr = hr.get("restingHeartRate")
        min_hr = hr.get("minHeartRate")
        max_hr = hr.get("maxHeartRate")

    bb_list = raw_data.get("body_battery", [])
    bb_max = None
    bb_min = None
    bb_charged = None
    bb_drained = None
    if isinstance(bb_list, list) and len(bb_list) > 0:
        bb = bb_list[0]
        bb_max = bb.get("bodyBatteryMax") or bb.get("max")
        bb_min = bb.get("bodyBatteryMin") or bb.get("min")
        bb_charged = bb.get("charged")
        bb_drained = bb.get("drained")

    stress = raw_data.get("stress", {})
    stress_avg = None
    stress_max = None
    if isinstance(stress, dict):
        stress_avg = stress.get("avgStressLevel")
        stress_max = stress.get("maxStressLevel")

    steps_dict = raw_data.get("steps", {})
    steps = None
    if isinstance(steps_dict, dict):
        steps = steps_dict.get("totalSteps")
    elif isinstance(steps_dict, (int, float)):
        steps = int(steps_dict)

    tr = raw_data.get("training_readiness", {})
    training_readiness = None
    if isinstance(tr, dict):
        rq = tr.get("readinessQualifier", {})
        if isinstance(rq, dict):
            training_readiness = rq.get("readinessScore")

    # SpO2 (Pulse Ox) & Respiration parsing
    # Typically in Garmin Connect:
    # Pulse Ox is a list/dict structure. Let's parse average/min.
    spo2_data = raw_data.get("pulse_ox", {})
    spo2_avg = None
    spo2_min = None
    if isinstance(spo2_data, dict):
        # Depending on API response, can be avgVal, minVal
        spo2_avg = spo2_data.get("avgVal") or spo2_data.get("spo2Avg")
        spo2_min = spo2_data.get("minVal") or spo2_data.get("spo2Min")
        
    resp_data = raw_data.get("respiration", {})
    respiration_avg = None
    respiration_min = None
    if isinstance(resp_data, dict):
        respiration_avg = resp_data.get("avgVal") or resp_data.get("avgRespirationRate")
        respiration_min = resp_data.get("minVal") or resp_data.get("minRespirationRate")

    # Store raw json
    raw_json_str = json.dumps(raw_data, default=str)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO daily_metrics (
        date, hrv_last_night, hrv_weekly_avg, sleep_score, sleep_duration,
        sleep_deep, sleep_light, sleep_rem, sleep_awake, resting_hr, min_hr, max_hr,
        bb_max, bb_min, bb_charged, bb_drained, stress_avg, stress_max, steps,
        training_readiness, spo2_avg, spo2_min, respiration_avg, respiration_min, raw_json
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(date) DO UPDATE SET
        hrv_last_night = excluded.hrv_last_night,
        hrv_weekly_avg = excluded.hrv_weekly_avg,
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
        training_readiness = excluded.training_readiness,
        spo2_avg = excluded.spo2_avg,
        spo2_min = excluded.spo2_min,
        respiration_avg = excluded.respiration_avg,
        respiration_min = excluded.respiration_min,
        raw_json = excluded.raw_json
    """, (
        date_str, hrv_last_night, hrv_weekly_avg, sleep_score, sleep_duration,
        sleep_deep, sleep_light, sleep_rem, sleep_awake, resting_hr, min_hr, max_hr,
        bb_max, bb_min, bb_charged, bb_drained, stress_avg, stress_max, steps,
        training_readiness, spo2_avg, spo2_min, respiration_avg, respiration_min, raw_json_str
    ))
    conn.commit()
    conn.close()

def get_df(limit: int = 30):
    """
    Loads daily metrics as a pandas DataFrame.
    """
    import pandas as pd
    init_db()
    conn = get_connection()
    df = pd.read_sql_query(f"""
        SELECT * FROM daily_metrics 
        ORDER BY date ASC 
        LIMIT {limit}
    """, conn)
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
