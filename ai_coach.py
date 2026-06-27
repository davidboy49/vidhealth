import os
from pathlib import Path
from datetime import date
HAS_GENAI = True
try:
    import google.generativeai as genai
except ImportError:
    HAS_GENAI = False

from dotenv import load_dotenv

# Load env variables
load_dotenv(Path(__file__).parent / ".env")

import db

# Configure Gemini
api_key = os.environ.get("GEMINI_API_KEY")
if api_key and HAS_GENAI:
    genai.configure(api_key=api_key)

def generate_weekly_report(days: int = 7) -> str:
    """
    Fetches the last N days of data from the database, sends it to Gemini,
    generates a health report, saves it in the database for the latest day, and returns it.
    """
    if not HAS_GENAI:
        raise ImportError(
            "The 'google-generativeai' package is not installed in this Python environment. "
            "Please run 'pip install -r requirements.txt' on your server."
        )
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not found in .env")
        
    df = db.get_df(limit=days)
    if df.empty:
        return "No data in database to generate a report."
        
    # Get latest date in the database
    latest_row = df.iloc[-1]
    latest_date_str = latest_row["date"]
    
    # Format metrics to text for the prompt
    data_summary = []
    for _, row in df.iterrows():
        day_info = (
            f"Date: {row['date']}\n"
            f"  HRV (Last Night): {row['hrv_last_night']} ms (Weekly Avg: {row['hrv_weekly_avg']} ms)\n"
            f"  Sleep Score: {row['sleep_score']}/100 (Duration: {row['sleep_duration'] or 0} s, Deep: {row['sleep_deep'] or 0} s, REM: {row['sleep_rem'] or 0} s)\n"
            f"  Heart Rate: Resting: {row['resting_hr']} bpm, Min: {row['min_hr']} bpm, Max: {row['max_hr']} bpm\n"
            f"  Body Battery: Max: {row['bb_max']}, Min: {row['bb_min']}, Charged: {row['bb_charged']}, Drained: {row['bb_drained']}\n"
            f"  Stress Level: Avg: {row['stress_avg']}/100, Max: {row['stress_max']}/100\n"
            f"  Steps: {row['steps']}\n"
            f"  Training Readiness: {row['training_readiness']}/100\n"
            f"  SpO2: Avg: {row['spo2_avg']}%, Min: {row['spo2_min']}%\n"
            f"  Respiration Rate: Avg: {row['respiration_avg']} breaths/min\n"
            f"--------------------------------------------------"
        )
        data_summary.append(day_info)
        
    metrics_block = "\n".join(data_summary)
    
    prompt = f"""
You are a highly qualified sports science coach and medical biohacking consultant.
Analyze the following personal health and biometrics data from a Garmin watch over the last {days} days:

{metrics_block}

Please write a comprehensive, readable health coaching report.
Structure your response in clean markdown with the following sections:
1. **Executive Summary** (A 3-sentence summary of the user's physiological state, fatigue levels, and overall recovery trend).
2. **Key Biometric Patterns & Trends** (Discuss HRV, Resting HR, Sleep architecture, Stress profiles, and highlight any anomalies like stress spikes, low SpO2, or rising RHR).
3. **Training & recovery guidelines for next week** (Actionable advice on workout intensity, Deload vs Full Send, sleep targets, and stress management).

Make the tone encouraging, technical, and precise. Mention specific numbers (like average HRV, sleep scores) in your analysis to make it personal. Do not output HTML, only clean Markdown.
"""

    # Call Gemini API
    # Use gemini-2.5-flash as default stable model in this environment
    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(prompt)
    
    report_text = response.text
    
    # Save the report text in the database for the latest date
    db.update_custom_field(latest_date_str, "ai_summary", report_text)
    
    return report_text

if __name__ == "__main__":
    print("Generating report using Gemini...")
    try:
        report = generate_weekly_report(days=7)
        print("\n=== GENERATED REPORT ===\n")
        print(report)
    except Exception as e:
        print(f"Error: {e}")
