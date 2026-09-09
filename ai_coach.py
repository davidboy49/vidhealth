import math
import os
from pathlib import Path
from datetime import date
from openai import OpenAI

from dotenv import load_dotenv

# Load env variables
load_dotenv(Path(__file__).parent / ".env")

import db

# Configure AI Coach provider
gemini_key = os.environ.get("GEMINI_API_KEY")
deepseek_key = os.environ.get("DEEPSEEK_API_KEY")

if gemini_key:
    api_key = gemini_key
    base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
    weekly_model = "gemini-3.5-flash"
    briefing_model = "gemini-3.5-flash"
elif deepseek_key:
    api_key = deepseek_key
    base_url = "https://api.deepseek.com"
    weekly_model = "deepseek-v4-pro"
    briefing_model = "deepseek-v4-flash"
else:
    api_key = None
    base_url = None
    weekly_model = None
    briefing_model = None

# Allow manual model overrides from environment variables
weekly_model_override = os.environ.get("AI_WEEKLY_MODEL")
briefing_model_override = os.environ.get("AI_BRIEFING_MODEL")
if weekly_model_override:
    weekly_model = weekly_model_override
if briefing_model_override:
    briefing_model = briefing_model_override

client = OpenAI(
    api_key=api_key,
    base_url=base_url,
) if api_key else None


class AIReportGenerationError(RuntimeError):
    """Raised when the AI coach cannot generate or save a report."""

def _is_missing(value) -> bool:
    if value is None:
        return True
    try:
        return math.isnan(float(value))
    except (TypeError, ValueError):
        return str(value).strip().lower() in {"", "nan", "none", "nat", "<na>"}


def _format_metric(value, fallback="unavailable"):
    if _is_missing(value):
        return fallback
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return str(value)
    if numeric.is_integer():
        return str(int(numeric))
    return f"{numeric:.1f}".rstrip("0").rstrip(".")


def _safe_round(value, digits=1):
    """Round a numeric value defensively, returning None for missing/non-finite values."""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(numeric) or math.isinf(numeric):
        return None
    return round(numeric, digits)


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


def _build_metrics_block(df, include_extended: bool = True) -> tuple[str, str]:
    """
    Builds the per-day text block AND a precomputed trend summary line, so the
    LLM doesn't have to eyeball day-to-day noise to infer direction itself.
    Includes daily user-logged habits and notes.
    """
    day_lines = []
    for _, row in df.iterrows():
        date_str = str(row['date'])
        logs = db.get_activity_logs(date_str=date_str, limit=20)
        logs_summary = []
        for l in logs:
            tag_label = l.get('tag', '').replace('_', ' ').title()
            val_label = f" ({l['value']})" if l.get('value') is not None else ""
            note_label = f" - {l['note']}" if l.get('note') else ""
            cat_prefix = "[Unholy Habit] " if l.get('category') == 'unholy_habit' else "[Note] "
            logs_summary.append(f"{cat_prefix}{tag_label}{val_label}{note_label}")
        
        logs_text = " | ".join(logs_summary) if logs_summary else "None logged"

        if include_extended:
            day_info = (
                f"Date: {date_str}\n"
                f"  HRV (Last Night): {_format_metric(row.get('hrv_last_night'))} ms (Weekly Avg: {_format_metric(row.get('hrv_weekly_avg'))} ms)\n"
                f"  Sleep Score: {_format_metric(row.get('sleep_score'))}/100 (Duration: {_format_metric(row.get('sleep_duration'), '0')} s, "
                f"Deep: {_format_metric(row.get('sleep_deep'), '0')} s, REM: {_format_metric(row.get('sleep_rem'), '0')} s)\n"
                f"  Heart Rate: Resting: {_format_metric(row.get('resting_hr'))} bpm, Min: {_format_metric(row.get('min_hr'))} bpm, Max: {_format_metric(row.get('max_hr'))} bpm\n"
                f"  Body Battery: Max: {_format_metric(row.get('bb_max'))}, Min: {_format_metric(row.get('bb_min'))}, Charged: {_format_metric(row.get('bb_charged'))}, "
                f"Drained: {_format_metric(row.get('bb_drained'))}\n"
                f"  Stress Level: Avg: {_format_metric(row.get('stress_avg'))}/100, Max: {_format_metric(row.get('stress_max'))}/100\n"
                f"  Steps: {_format_metric(row.get('steps'))}\n"
                f"  Training Readiness: {_format_metric(row.get('training_readiness'))}/100\n"
                f"  SpO2: Avg: {_format_metric(row.get('spo2_avg'))}%, Min: {_format_metric(row.get('spo2_min'))}%\n"
                f"  Respiration Rate: Avg: {_format_metric(row.get('respiration_avg'))} breaths/min\n"
                f"  Daily Habits / Notes: {logs_text}\n"
                f"--------------------------------------------------"
            )
        else:
            day_info = (
                f"Date: {date_str}\n"
                f"  HRV: {_format_metric(row.get('hrv_last_night'))} ms (Weekly Avg: {_format_metric(row.get('hrv_weekly_avg'))} ms)\n"
                f"  Sleep Score: {_format_metric(row.get('sleep_score'))}/100\n"
                f"  Resting HR: {_format_metric(row.get('resting_hr'))} bpm\n"
                f"  Stress Level: Avg: {_format_metric(row.get('stress_avg'))}/100\n"
                f"  Training Readiness: {_format_metric(row.get('training_readiness'))}/100\n"
                f"  Daily Habits / Notes: {logs_text}\n"
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


def generate_weekly_report(days: int = 7, model_override: str = None) -> str:
    """
    Fetches the last N days of data from the database, sends it to the AI Coach model,
    generates a health report, saves it in the database for the latest day, and returns it.
    """
    model_to_use = model_override if model_override else weekly_model
    
    # Dynamically select provider based on model prefix
    current_api_key = api_key
    current_base_url = base_url
    if model_to_use and model_to_use.startswith("deepseek"):
        current_api_key = os.environ.get("DEEPSEEK_API_KEY") or current_api_key
        current_base_url = "https://api.deepseek.com"
    elif model_to_use and model_to_use.startswith("gemini"):
        current_api_key = os.environ.get("GEMINI_API_KEY") or current_api_key
        current_base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"

    if not current_api_key:
        raise ValueError(f"No API key found for model {model_to_use}. Please set GEMINI_API_KEY or DEEPSEEK_API_KEY in .env")

    dynamic_client = OpenAI(api_key=current_api_key, base_url=current_base_url)

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
3. **Training & Recovery Guidelines for Next Week** — guidance for training load,
   sleep, and (only if the data in rule 3 above actually warrants it) recovery
   flags, all directly justified by the numbers above. Skip any of these three
   topics if nothing in the data justifies commenting on it.

Do not output HTML, only clean Markdown.
"""

    try:
        response = dynamic_client.chat.completions.create(
            model=model_to_use,
            messages=[
                {"role": "user", "content": prompt.strip()}
            ],
            temperature=0.3,
            max_tokens=8192,
        )
    except Exception as e:
        raise AIReportGenerationError(
            f"AI Coach model request failed before a report was generated. Reason: {e}"
        ) from e

    try:
        report_text = response.choices[0].message.content.strip()
    except (AttributeError, IndexError, TypeError) as e:
        raise AIReportGenerationError(
            "AI Coach returned an unexpected response format, so no report text could be read."
        ) from e

    if not report_text:
        raise AIReportGenerationError("AI Coach returned an empty report.")

    try:
        db.update_custom_field(latest_date_str, "ai_summary", report_text)
    except Exception as e:
        raise AIReportGenerationError(
            f"AI Coach generated a report, but saving it for {latest_date_str} failed. Reason: {e}"
        ) from e

    return report_text


def _parse_action_plan(text: str) -> tuple[str, list[str]]:
    """
    Pulls the machine-readable pieces (headline, watch-list items) out of the
    model's markdown response. Falls back to empty values if the model didn't
    follow the requested structure exactly — the raw text is always saved
    regardless, so nothing is lost even if parsing comes up short.
    """
    import re

    headline = ""
    headline_match = re.search(r"^\s*HEADLINE:\s*(.+?)\s*$", text, re.MULTILINE)
    if headline_match:
        headline = headline_match.group(1).strip()

    watchlist: list[str] = []
    watchlist_match = re.search(
        r"\*\*Watch List for Next Check-In\*\*\s*\n(.*)", text, re.IGNORECASE | re.DOTALL
    )
    if watchlist_match:
        for line in watchlist_match.group(1).splitlines():
            line = line.strip().lstrip("-*").strip()
            if line:
                watchlist.append(line)

    return headline, watchlist


def generate_action_plan(days: int = 7, model_override: str = None) -> dict:
    """
    Generates a forward-looking action plan (as opposed to generate_weekly_report's
    recap) for the next period, saves it to the action_plans table, and returns
    {"headline": str, "plan_text": str, "watchlist": list[str], "id": int}.

    If a prior plan exists, its watch-list is fed back into the prompt so this
    plan can explicitly follow up on it (resolved / improved / unchanged /
    worsened, with the number) instead of starting from a blank slate each time.
    """
    model_to_use = model_override if model_override else weekly_model

    current_api_key = api_key
    current_base_url = base_url
    if model_to_use and model_to_use.startswith("deepseek"):
        current_api_key = os.environ.get("DEEPSEEK_API_KEY") or current_api_key
        current_base_url = "https://api.deepseek.com"
    elif model_to_use and model_to_use.startswith("gemini"):
        current_api_key = os.environ.get("GEMINI_API_KEY") or current_api_key
        current_base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"

    if not current_api_key:
        raise ValueError(f"No API key found for model {model_to_use}. Please set GEMINI_API_KEY or DEEPSEEK_API_KEY in .env")

    dynamic_client = OpenAI(api_key=current_api_key, base_url=current_base_url)

    df = db.get_df(limit=days)
    if df.empty:
        raise AIReportGenerationError("No data in database to generate an action plan.")

    period_start = str(df.iloc[0]["date"])
    period_end = str(df.iloc[-1]["date"])

    metrics_block, trend_block = _build_metrics_block(df, include_extended=True)

    previous_plan = db.get_latest_action_plan()
    if previous_plan and previous_plan.get("watchlist"):
        watchlist_lines = "\n".join(f"- {item}" for item in previous_plan["watchlist"])
        previous_watchlist_block = f"""\
LAST PERIOD'S WATCH LIST (from the plan generated {previous_plan['generated_at']}):
{watchlist_lines}

In the "What Changed" section, explicitly address each item above: say whether the
data now shows it resolved, improved, unchanged, or worsened, citing the number.
"""
    else:
        previous_watchlist_block = ""

    prompt = f"""\
You are a sports-science coach producing an ACTION PLAN for the next {days} days,
not a narrative recap. Every claim must trace back to a specific number below —
if you can't point to a number, don't say it.

DATA (last {days} days):
{metrics_block}

{trend_block}

{previous_watchlist_block}
STRICT RULES:

1. Every claim must trace back to a specific number above. If you use a word like
   "concerning" or "critical," show the numbers that justify it.

2. Calibrate confidence to sample size. Call something a "trend" only if it holds
   across 3+ consecutive days, and prefer the precomputed rolling averages above
   over eyeballing single-day deltas.

3. Sensor and metric limitations — apply these before interpreting:
   - Minimum SpO2 from a wrist device is frequently a motion/sensor artifact, especially
     as a single-night low. Only raise SpO2 as noteworthy if the minimum drops below 90%
     on multiple nights. Never use diagnostic language ("sleep apnea," "breathing disorder").
     At most: "worth mentioning to a doctor if this repeats."
   - "Training Readiness: None" or 0/100 with no other signal is almost always a
     data-availability issue, not a physiological finding. State this plainly.
   - A high "Max Stress" value in isolation (spikes to 90+) is common and usually not
     meaningful. Only flag stress if the AVERAGE is elevated for 2+ consecutive days.

4. No generic filler advice (hydration, "eat whole foods," "spend time in nature", etc.)
   unless a specific number in this period's data justifies mentioning it.

5. No medical claims or diagnoses. Frame any health flag as "worth mentioning to a
   doctor," never stronger.

6. Tone: direct, calm, and precise. Avoid dramatic language unless a number
   genuinely warrants it. Bias toward under-alarming — a false alarm costs more
   trust than a missed catch, especially from a non-medical-grade wrist sensor.

7. Every action in "This Period's Actions" must open with the specific number
   that justifies it (e.g. "Cap training at Zone 2 through Thursday — RHR has
   run +4bpm above your weekly baseline for 4 straight nights"), not generic
   advice that could apply to anyone.

Structure your response EXACTLY like this — use **bold** section labels, not
# headers, so it renders correctly in both a markdown viewer and Telegram:

HEADLINE: <one sentence readiness verdict, must cite a specific number>

**What Changed**
<data-grounded patterns, same discipline as above; if a prior watch-list was
given, explicitly follow up on each item first>

**This Period's Actions**
<3-5 bullets, each opening with the number that justifies it. Skip any topic
(training, sleep, stress, recovery) with nothing data-driven to say.>

**Watch List for Next Check-In**
<1-2 bullets: an exact metric + threshold to track before the next plan,
phrased so it can be checked directly against next period's data>

Do not output HTML, only clean Markdown.
"""

    try:
        response = dynamic_client.chat.completions.create(
            model=model_to_use,
            messages=[
                {"role": "user", "content": prompt.strip()}
            ],
            temperature=0.3,
            max_tokens=8192,
        )
    except Exception as e:
        raise AIReportGenerationError(
            f"AI Coach model request failed before an action plan was generated. Reason: {e}"
        ) from e

    try:
        plan_text = response.choices[0].message.content.strip()
    except (AttributeError, IndexError, TypeError) as e:
        raise AIReportGenerationError(
            "AI Coach returned an unexpected response format, so no action plan could be read."
        ) from e

    if not plan_text:
        raise AIReportGenerationError("AI Coach returned an empty action plan.")

    headline, watchlist = _parse_action_plan(plan_text)

    try:
        plan_id = db.save_action_plan(
            period_start=period_start,
            period_end=period_end,
            model=model_to_use,
            headline=headline,
            plan_text=plan_text,
            watchlist=watchlist,
        )
    except Exception as e:
        raise AIReportGenerationError(
            f"AI Coach generated an action plan, but saving it failed. Reason: {e}"
        ) from e

    return {"id": plan_id, "headline": headline, "plan_text": plan_text, "watchlist": watchlist}


def generate_morning_briefing(days: int = 3) -> str:
    """
    Generates a concise, 3-sentence daily coach briefing for the Telegram push.
    """
    if not client or not api_key:
        raise ValueError("Neither GEMINI_API_KEY nor DEEPSEEK_API_KEY environment variable was found in .env")

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
        model=briefing_model,
        messages=[
            {"role": "user", "content": prompt.strip()}
        ],
        temperature=0.3,
        max_tokens=512,
    )
    return response.choices[0].message.content.strip()


if __name__ == "__main__":
    print("Generating report using AI Coach...")
    try:
        report = generate_weekly_report(days=7)
        print("\n=== GENERATED REPORT ===\n")
        print(report)
    except Exception as e:
        print(f"Error: {e}")
