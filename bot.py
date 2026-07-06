import os
import sys
import logging
from pathlib import Path
from datetime import datetime, date, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

import db
from recovery_predictor import RecoveryPredictor

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8944060108:AAGFTzKVMtDMP87BP1CYGEM5ZjXh9UCWl5o")
AUTHORIZED_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def is_authorized(chat_id: int) -> bool:
    if not AUTHORIZED_CHAT_ID:
        return False
    return str(chat_id) == str(AUTHORIZED_CHAT_ID)

async def check_auth(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat_id = update.effective_chat.id
    if not AUTHORIZED_CHAT_ID:
        await update.message.reply_text(
            f"⚠️ Bot is unconfigured.\n"
            f"To authorize this chat, please add this line to your `.env` file:\n"
            f"`TELEGRAM_CHAT_ID={chat_id}`\n"
            f"Then restart the bot."
        )
        return False
    if not is_authorized(chat_id):
        await update.message.reply_text("❌ Access Denied: Unauthorized User.")
        return False
    return True

# ---------- COMMAND HANDLERS ----------

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    welcome_text = (
        "🏋️ **Welcome to Hermes Health Coach Bot!**\n\n"
        "Here are the available commands:\n"
        "📊 /health - Today's health metrics snapshot\n"
        "💪 /gym - Today's dynamic gym plan recommendation\n"
        "📝 /week - Latest AI coaching weekly summary\n"
        "🔮 /recover - Predictive recovery projection\n"
        "❓ /status - Quick biometric readiness update\n\n"
        f"Your Telegram Chat ID: `{chat_id}`\n"
    )
    if not AUTHORIZED_CHAT_ID:
        welcome_text += (
            f"\n⚠️ **Action Required**:\n"
            f"To authorize this bot, add `TELEGRAM_CHAT_ID={chat_id}` to your `.env` file."
        )
    elif not is_authorized(chat_id):
        welcome_text += "\n❌ You are not authorized to use this bot."
    else:
        welcome_text += "\n✅ You are authorized!"
        
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def health_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update, context):
        return
        
    df = db.get_df(limit=7)
    if df.empty:
        await update.message.reply_text("No health data synced yet.")
        return
        
    latest = df.iloc[-1]
    
    # Format message
    sleep_duration_hrs = (latest["sleep_duration"] / 3600.0) if latest["sleep_duration"] else 0
    
    msg = (
        f"📊 **Biometrics Snapshot: {latest['date']}**\n\n"
        f"🏃 **Readiness:** {latest['training_readiness'] or '—'}/100\n"
        f"💙 **HRV Last Night:** {latest['hrv_last_night'] or '—'} ms (Avg: {latest['hrv_weekly_avg'] or '—'} ms)\n"
        f"😴 **Sleep Score:** {latest['sleep_score'] or '—'}/100 ({sleep_duration_hrs:.1f} hrs)\n"
        f"💤 **Resting HR:** {latest['resting_hr'] or '—'} bpm (Min: {latest['min_hr'] or '—'} bpm)\n"
        f"⚡ **Body Battery:** Min: {latest['bb_min'] or '—'} / Max: {latest['bb_max'] or '—'}\n"
        f"🔥 **Stress Level:** Avg: {latest['stress_avg'] or '—'}/100 (Max: {latest['stress_max'] or '—'})\n"
        f"👣 **Steps Today:** {latest['steps'] or 0:,}\n"
        f"🩺 **Pulse Ox (SpO2):** Avg: {latest['spo2_avg'] or '—'}% (Min: {latest['spo2_min'] or '—'}%)\n"
        f"🫁 **Respiration:** Avg: {latest['respiration_avg'] or '—'} br/min\n"
    )
    
    # Anomaly detection flags
    anomalies = []
    # Alcohol
    weekly_rhr = df["resting_hr"].mean()
    weekly_hrv = df["hrv_weekly_avg"].iloc[-1] if not df["hrv_weekly_avg"].empty else df["hrv_last_night"].mean()
    if latest["stress_avg"] and latest["stress_avg"] > 45 and latest["resting_hr"] and weekly_rhr and latest["resting_hr"] > weekly_rhr + 6 and latest["hrv_last_night"] and weekly_hrv and latest["hrv_last_night"] < weekly_hrv * 0.82:
        anomalies.append("🍷 Recovery Disruption Detected (high sleep stress, low HRV, elevated RHR)")
    
    # Apnea
    if latest["spo2_min"] and latest["spo2_min"] < 90:
        anomalies.append("🫁 Sleep Apnea / Oxygen Desaturation Flagged")
        
    if anomalies:
        msg += "\n🚨 **Flags:**\n" + "\n".join(anomalies)
        
    await update.message.reply_text(msg, parse_mode="Markdown")

async def gym_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update, context):
        return
        
    df = db.get_df(limit=7)
    if df.empty:
        await update.message.reply_text("No health data synced yet.")
        return
        
    latest = df.iloc[-1]
    readiness = latest.get("training_readiness") or 50
    day_name = datetime.strptime(latest["date"], "%Y-%m-%d").strftime("%A")
    
    # Suggestsplit
    split_suggestions = {
        "Monday": ("Pull Day (Back & Biceps)", ["Deadlifts: 3x5", "Pull-ups: 3xmax", "Barbell Rows: 3x8", "Hammer Curls: 3x12"]),
        "Tuesday": ("Push Day (Chest, Shoulders, Triceps)", ["Bench Press: 3x5", "Overhead Press: 3x8", "Incline DB Flyes: 3x10", "Tricep Pushdowns: 3x12"]),
        "Wednesday": ("Active Recovery / Core", ["Planks: 3x1 min", "Hanging Leg Raises: 3x15", "Zone 2 Cardio: 30 mins"]),
        "Thursday": ("Leg Day (Quads, Hamstrings, Calves)", ["Squats: 3x5", "Romanian Deadlifts: 3x10", "Leg Press: 3x12", "Calf Raises: 4x15"]),
        "Friday": ("Arms & Core Focus", ["Bicep Curls: 3x10", "Skull Crushers: 3x10", "Cable Woodchops: 3x15", "Zone 2 Cardio: 20 mins"]),
        "Saturday": ("Full Body Conditioning", ["Kettlebell Swings: 4x15", "Thrusters: 3x10", "Farmer Walks: 4x50m", "Rowing Machine: 15 mins"]),
        "Sunday": ("Rest / Restorative Yoga", ["Deep stretching: 20 mins", "Foam rolling", "Light walk: 30 mins"])
    }
    
    workout_name, movements = split_suggestions.get(day_name, ("Cardio & Core", ["Zone 2 Cardio: 45 mins", "Core"]))
    
    if readiness >= 80:
        intensity = "⚡ **Optimal (Full Send)**: RPE 9. Complete full volume."
        adjusted_movements = movements
    elif readiness >= 55:
        intensity = "🏋️ **Good (Moderate)**: RPE 7-8. Standard volume."
        adjusted_movements = movements
    elif readiness >= 40:
        intensity = "🏃 **Fatigued (Active Recovery)**: RPE 6. Reduce sets by 1. Keep weights light."
        adjusted_movements = [m.replace("3x", "2x").replace("4x", "2x") for m in movements]
    else:
        intensity = "🛑 **Rest Alert (Critical Fatigue)**: Skip lifting today. Replace with yoga/breathwork."
        adjusted_movements = ["Restorative stretching: 20 mins", "Deep breathing: 10 mins"]
        workout_name = "Rest Protocol"
        
    msg = (
        f"💪 **Gym Plan Suggestion for {day_name}**\n\n"
        f"**Workout:** {workout_name}\n"
        f"**Readiness Score:** {int(readiness)}/100\n"
        f"**Intensity:** {intensity}\n\n"
        f"**Routine:**\n" + "\n".join(f"• {m}" for m in adjusted_movements)
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def week_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update, context):
        return
        
    df = db.get_df(limit=1)
    if df.empty:
        await update.message.reply_text("No health data synced yet.")
        return
        
    latest = df.iloc[-1]
    ai_summary = latest.get("ai_summary")
    
    if not ai_summary:
        await update.message.reply_text(
            "📝 Weekly AI coaching summary not generated yet.\n"
            "Generate it on the Web Dashboard or trigger sync/report scripts."
        )
        return
        
    # Split message if it exceeds Telegram's 4096 char limit
    if len(ai_summary) > 4000:
        for chunk in [ai_summary[i:i+4000] for i in range(0, len(ai_summary), 4000)]:
            await update.message.reply_text(chunk, parse_mode="Markdown")
    else:
        await update.message.reply_text(f"📝 **AI Coach Weekly Coaching Report**\n\n{ai_summary}", parse_mode="Markdown")

async def recover_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update, context):
        return
        
    df = db.get_df(limit=14)
    if df.empty:
        await update.message.reply_text("No health data synced yet.")
        return
        
    latest = df.iloc[-1]
    hrv = latest.get("hrv_last_night") or 50
    weekly_hrv = latest.get("hrv_weekly_avg") or df["hrv_last_night"].mean()
    
    # Call shared predictive recovery model
    prediction_8h = RecoveryPredictor.predict_tomorrow(
        current_hrv=hrv,
        target_hrv=weekly_hrv,
        sleep_hours=8.0,
        workout_intensity="Rest Day"
    )
    prediction_6h = RecoveryPredictor.predict_tomorrow(
        current_hrv=hrv,
        target_hrv=weekly_hrv,
        sleep_hours=6.0,
        workout_intensity="Hypertrophy (Moderate)"
    )
    
    pred_hrv_8h = prediction_8h["projected_hrv_tomorrow"]
    days_needed_8h = prediction_8h["days_to_recovery"]
    pred_hrv_6h = prediction_6h["projected_hrv_tomorrow"]
    
    msg = (
        f"🔮 **Predictive Recovery Forecast**\n\n"
        f"• **Current HRV:** {int(hrv)} ms\n"
        f"• **Baseline Target:** {int(weekly_hrv)} ms ({'-' if deficit > 0 else '+'}{abs(int(deficit))} ms diff)\n\n"
    )
    
    if deficit <= 0:
        msg += "✅ **Nervous System Fully Recovered!** You are in optimal athletic condition. Go hard!"
    else:
        msg += "📉 **Nervous System is Suppressed.** Forecast:\n"
        day_8h = "Tomorrow" if days_needed_8h == 0 else f"in {days_needed_8h} days"
        msg += f"• **If you sleep 8h tonight:** HRV recovers to {int(pred_hrv_8h)} ms (Full recovery {day_8h})\n"
        msg += f"• **If you sleep 6h tonight:** HRV remains suppressed at {int(pred_hrv_6h)} ms (Recovery delayed)\n"
        
    await update.message.reply_text(msg, parse_mode="Markdown")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update, context):
        return
        
    df = db.get_df(limit=1)
    if df.empty:
        await update.message.reply_text("No health data synced yet.")
        return
        
    latest = df.iloc[-1]
    readiness = latest.get("training_readiness") or 50
    
    if readiness >= 80:
        status = "⚡ Optimal readiness (Full Send)"
    elif readiness >= 50:
        status = "🏋️ Moderate readiness (Standard training)"
    else:
        status = "🛑 Low readiness (Deload or recovery day)"
        
    await update.message.reply_text(f"❓ **Status:** {status} ({int(readiness)}/100)", parse_mode="Markdown")

# ---------- DAILY AUTOMATED PUSH FUNCTION ----------

async def send_daily_push():
    """Sends today's snapshot directly to whitelisted Chat ID."""
    if not BOT_TOKEN or not AUTHORIZED_CHAT_ID:
        print("[FAIL] Bot token or whitelisted Chat ID missing in env.")
        return
        
    df = db.get_df(limit=7)
    if df.empty:
        print("[FAIL] Database is empty. No data to push.")
        return
        
    latest = df.iloc[-1]
    
    # Generate narrative morning briefing using AI Coach
    import ai_coach
    try:
        briefing = ai_coach.generate_morning_briefing(days=3)
    except Exception as e:
        briefing = f"Could not generate AI briefing: {e}"
    
    msg = (
        f"🔔 **Hermes Morning Report: {latest['date']}**\n\n"
        f"{briefing}\n"
    )
        
    # Send message using Application
    app = Application.builder().token(BOT_TOKEN).build()
    await app.initialize()
    await app.bot.send_message(chat_id=AUTHORIZED_CHAT_ID, text=msg, parse_mode="Markdown")
    await app.shutdown()
    print("[OK] Daily push completed successfully.")

# ---------- MAIN RUNNING LOOP ----------

def main():
    if not BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN environment variable not set in .env")
        sys.exit(1)
        
    # Run standalone push argument
    if len(sys.argv) > 1 and sys.argv[1] == "push":
        import asyncio
        asyncio.run(send_daily_push())
        return
        
    print("Starting Hermes Health Bot...")
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("health", health_command))
    app.add_handler(CommandHandler("gym", gym_command))
    app.add_handler(CommandHandler("week", week_command))
    app.add_handler(CommandHandler("recover", recover_command))
    app.add_handler(CommandHandler("status", status_command))
    
    # Start polling
    app.run_polling()

if __name__ == "__main__":
    main()
