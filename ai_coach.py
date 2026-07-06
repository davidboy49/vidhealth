import os
from pathlib import Path
from datetime import date
from openai import OpenAI

from dotenv import load_dotenv

# Load env variables
load_dotenv(Path(__file__).parent / ".env")

import db

# Configure DeepSeek
api_key = os.environ.get("DEEPSEEK_API_KEY")
client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com/v1",
) if api_key else None


def _safe_round(value, digits=1):
    """Round a numeric value defensively, passing through None/non-numeric as-is."""
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return value


def _rolling_avg(df, col, window):
    """
    Compute a simple trailing rolling average for a column, using at most
    `window` most recent rows available in df (df is assumed sorted oldest->newest).
    Returns None if there's no usable numeric data.
    """
    series = df[col].dropna()
    if series.empty:
        return None
    tail = series.tail(window)
    return _safe_round(tail.mean(), 1)


def _build_metrics_block(df, include_extended: bool = True) -> str:
    """
    Builds the per-day text block AND a precomputed trend summary line, so the
    LLM doesn't have to eyeball day-to-day noise to infer direction itself.
    """
    day_lines = []
    for _, row in df.iterrows():
        if include_extended:
            day_info = (
                f"Date: {row['date']}\n"
                f"  HRV (Last Night): {row['hrv_last_night']} ms (Weekly Avg: {row['hrv_weekly_avg']} ms)\n"
                f"  Sleep Score: {row['sleep_score']}/100 (Duration: {row['sleep_duration'] or 0} s, "
                f"Deep: {row['sleep_deep'] or 0} s, REM: {row['sleep_rem'] or 0} s)\n"
                f"  Heart Rate: Resting: {row['resting_hr']} bpm, Min: {row['min_hr']} bpm, Max: {row['max_hr']} bpm\n"
                f"  Body Battery: Max: {row['bb_max']}, Min: {row['bb_min']}, Charged: {row['bb_charged']}, "
                f"Drained: {row['bb_drained']}\n"
                f"  Stress Level: Avg: {row['stress_avg']}/100, Max: {row['stress_max']}/100\n"
                f"  Steps: {row['steps']}\n"
                f"  Training Readiness: {row['training_readiness']}/100\n"
                f"  SpO2: Avg: {row['spo2_avg']}%, Min: {row['spo2_min']}%\n"
                f"  Respiration Rate: Avg: {row['respiration_avg']} breaths/min\n"
                f"--------------------------------------------------"
            )
        else:
            day_info = (
                f"Date: {row['date']}\n"
                f"  HRV: {row['hrv_last_night']} ms (Weekly Avg: {row['hrv_weekly_avg']} ms)\n"
                f"  Sleep Score: {row['sleep_score']}/100\n"
                f"  Resting HR: {row['resting_hr']} bpm\n"
                f"  Stress Level: Avg: {row['stress_avg']}/100\n"
                f"  Training Readiness: {row['training_readiness']}/100\n"
                f"--------------------------------------------------"
            )
        day_lines.append(day_info)

    metrics_block = "\n".join(day_lines)

    # Precompute trend numbers so the model reports facts instead of inferring them
    # from noisy day-over-day deltas.
    window = min(3, len(df))
    hrv_roll = _rolling_avg(df, "hrv_last_night", window)
    rhr_roll = _rolling_avg(df, "resting_hr", window)
    sleep_roll = _rolling_avg(df, "sleep_score", window)

    trend_lines = [f"PRECOMPUTED {window}-DAY ROLLING AVERAGES (use these for trend claims, not raw day-to-day deltas):"]
    trend_lines.append(f"  HRV rolling avg: {hrv_roll} ms" if hrv_roll is not None else "  HRV rolling avg: unavailable")
    trend_lines.append(f"  Resting HR rolling avg: {rhr_roll} bpm" if rhr_roll is not None else "  Resting HR rolling avg: unavailable")
    trend_lines.append(f"  Sleep Score rolling avg: {sleep_roll}/100" if sleep_roll is not None else "  Sleep Score rolling avg: unavailable")

    return metrics_block, "\n".join(trend_lines)


def generate_weekly_report(days: int = 7) -> str:
    """
    Fetches the last N days of data from the database, sends it to DeepSeek,
    generates a health report, saves it in the database for the latest day, and returns it.
    """
    if not client:
        raise ValueError("DEEPSEEK_API_KEY environment variable not found in .env")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY environment variable not found in .env")

    df = db.get_df(limit=days)
    if df.empty:
        return "No data in database to generate a report."

    # Get latest date in the database
    latest_row = df.iloc[-1]
    latest_date_str = latest_row["date"]

    metrics_block, trend_block = _build_metrics_block(df, include_extended=True)

    prompt = f"""\
You are analyzing {days} days of Garmin biometric data for one user. Your job is to identify
real, data-supported patterns and give proportionate guidance — not to write an
alarming or padded wellness report.

DATA:
{metrics_block}

{trend_block}

STRICT RULES:

1. Every claim must trace back to a specific number above. If you use a word like
   "concerning" or "critical," show the numbers that justify it. If you can't point
   to a number, don't say it.

2. Calibrate confidence to sample size. This is {days} days of data. Call something a
   "trend" only if it holds across 3+ consecutive days, and prefer the precomputed
   rolling averages above over eyeballing single-day deltas. A single day's number is
   an observation, not a trend — say so explicitly if relevant.

3. Sensor and metric limitations — apply these before interpreting:
   - Minimum SpO2 from a wrist device is frequently a motion/sensor artifact, especially
     as a single-night low. Only raise SpO2 as noteworthy if the minimum drops below 90%
     on multiple nights. Never use diagnostic language ("sleep apnea," "breathing disorder").
     At most: "worth mentioning to a doctor if this repeats."
   - "Training Readiness: None" or 0/100 with no other signal is almost always a
     data-availability issue (insufficient baseline history), not a physiological finding.
     State this plainly rather than speculating about a cause.
   - A high "Max Stress" value in isolation (spikes to 90+) is common and usually not
     meaningful. Only flag stress if the AVERAGE is elevated for 2+ consecutive days.

4. No generic filler advice (hydration, "eat whole foods," "spend time in nature", etc.)
   unless a specific number in this week's data justifies mentioning it. If there's
   nothing data-driven to say on a topic, omit that topic entirely.

5. No medical claims or diagnoses. Frame any health flag as "worth mentioning to a
   doctor," never stronger. Do not recommend supplements unless the data clearly
   points to a specific deficiency-adjacent pattern, and always attach "consult a
   doctor before starting" if you do.

6. Tone: direct, calm, and precise. Avoid dramatic language ("juxtaposed," "profound,"
   "critical," "urgent") unless a number genuinely warrants it — and even then, stay
   factual rather than alarmed.

Structure your response in clean markdown with these sections:
1. **Executive Summary** — 2-3 sentences, only what the data actually supports.
2. **Key Patterns** — HRV, RHR, sleep, stress, SpO2, steps. Skip any metric with
   nothing meaningful to report. Lead each point with the number, then one sentence
   of interpretation.
3. **For Next Week** — 3-5 recommendations MAX, each tied explicitly to a specific
   metric from this week's data. No recommendation without a number behind it.

Do not output HTML, only clean Markdown.
"""

    # Call DeepSeek API
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user", "content": prompt.strip()}
        ],
        temperature=0.3,
        max_tokens=2048,
    )

    report_text = response.choices[0].message.content.strip()

    # Save the report text in the database for the latest date
    db.update_custom_field(latest_date_str, "ai_summary", report_text)

    return report_text


def generate_morning_briefing(days: int = 3) -> str:
    """
    Generates a concise, 3-sentence daily coach briefing for the Telegram push.
    """
    if not client:
        raise ValueError("DEEPSEEK_API_KEY environment variable not found in .env")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY environment variable not found in .env")

    df = db.get_df(limit=days)
    if df.empty:
        return "No data in database to generate briefing."

    metrics_block, trend_block = _build_metrics_block(df, include_extended=False)

    prompt = f"""\
You are a sports science coach reviewing a user's last {days} days of biometrics to
write one text-message-length morning brief.

DATA:
{metrics_block}

{trend_block}

RULES:
- Only reference numbers that appear in the data above. Don't infer causes not shown.
- Use the precomputed rolling averages to judge trend direction rather than comparing
  single days. If HRV or RHR moved by only a small, normal night-to-night amount
  (roughly ±2-3ms HRV or ±2bpm RHR) and the rolling average is flat, describe today as
  stable rather than "improving" or "declining."
- If Training Readiness is None/0 with no other explanation, don't interpret it — just
  base today's call on HRV, RHR, sleep score, and stress instead.
- Don't invent urgency. If the data is unremarkable, say so plainly rather than
  manufacturing a concern or a "push hard" call that isn't backed by the numbers.

Write exactly 3 sentences, like a text from a smart coach:
1. Today's readiness, using the actual numbers (HRV and/or sleep score).
2. The trend over the last {days} days — recovering, stable, or accumulating fatigue —
   based on the rolling averages above, not a single day's number.
3. One concrete instruction for today's training, directly justified by sentences 1-2
   (e.g. "push squats today," "stick to Zone 2," "take a full rest day").

No headers, no markdown bold symbols (*), just 3 clean sentences.
"""

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user", "content": prompt.strip()}
        ],
        temperature=0.3,
        max_tokens=512,
    )
    return response.choices[0].message.content.strip()


if __name__ == "__main__":
    print("Generating report using DeepSeek...")
    try:
        report = generate_weekly_report(days=7)
        print("\n=== GENERATED REPORT ===\n")
        print(report)
    except Exception as e:
        print(f"Error: {e}")
