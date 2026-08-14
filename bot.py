import os
import sys
import logging
import html
from pathlib import Path
from datetime import datetime, date, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv(Path(__file__).parent / ".env")

import db
import analytics
import anomaly_detector
from recovery_predictor import RecoveryPredictor

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8944060108:AAGFTzKVMtDMP87BP1CYGEM5ZjXh9UCWl5o")
AUTHORIZED_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def is_authorized(chat_id: int) -> bool:
    if not AUTHORIZED_CHAT_ID:
        return False
    return str(chat_id) == str(AUTHORIZED_CHAT_ID)

async def check_auth(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat_id = update.effective_chat.id if update.effective_chat else None
    if not chat_id:
        return False
    if not AUTHORIZED_CHAT_ID:
        if update.message:
            await update.message.reply_text(
                f"⚠️ Bot is unconfigured.\n"
                f"To authorize this chat, please add this line to your `.env` file:\n"
                f"`TELEGRAM_CHAT_ID={chat_id}`\n"
                f"Then restart the bot."
            )
        return False
    if not is_authorized(chat_id):
        if update.message:
            await update.message.reply_text("❌ Access Denied: Unauthorized User.")
        elif update.callback_query:
            await update.callback_query.answer("❌ Access Denied", show_alert=True)
        return False
    return True

# ---------- COMMAND HANDLERS ----------

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    welcome_text = (
        "🏋️ **Welcome to Hermes Health Coach Bot!**\n\n"
        "Here are the available commands:\n"
        "✍️ /log - Interactive daily activity & unholy habit logger\n"
        "📊 /health - Today's health metrics snapshot\n"
        "🧠 /insights - Biometric intelligence & HRV baseline bands\n"
        "🚨 /alerts - Check active health anomaly warnings\n"
        "📋 /notes - View your recent logged habits & notes\n"
        "💪 /gym - Today's dynamic gym plan recommendation\n"
        "🔮 /recover - Predictive recovery projection\n"
        "📝 /week - Latest AI coaching weekly summary\n"
        "❓ /status - Quick biometric readiness update\n\n"
        "💡 *Tip: You can also send me any plain text message to log a quick Free Note!*"
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
    deficit = weekly_hrv - hrv
    
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

# ---------- ACTIVITY & HABIT LOGGING HANDLERS ----------

def get_main_log_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("😈 Log Unholy Habit", callback_data="menu_unholy"),
            InlineKeyboardButton("📝 Write Free Note", callback_data="menu_note")
        ],
        [
            InlineKeyboardButton("📋 View Today's Logs", callback_data="menu_view_today")
        ]
    ])

def get_unholy_habits_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🍷 Alcohol", callback_data="unholy_alcohol_menu"),
            InlineKeyboardButton("🍕 Late Meal", callback_data="log_habit:late_meal:1:Late Heavy Meal")
        ],
        [
            InlineKeyboardButton("☕ Late Caffeine (>2PM)", callback_data="log_habit:late_caffeine:1:Late Caffeine"),
            InlineKeyboardButton("📱 Late Screen Time", callback_data="log_habit:late_screen:1:Late Screen Time")
        ],
        [
            InlineKeyboardButton("🚬 Nicotine / Vape", callback_data="log_habit:nicotine:1:Nicotine"),
            InlineKeyboardButton("⚡ High Mental Stress", callback_data="log_habit:mental_stress:1:High Mental Stress")
        ],
        [
            InlineKeyboardButton("🔙 Back to Main Menu", callback_data="menu_main")
        ]
    ])

def get_alcohol_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🍺 1 Drink", callback_data="log_habit:alcohol:1:1 standard drink"),
            InlineKeyboardButton("🍷 2 Drinks", callback_data="log_habit:alcohol:2:2 standard drinks"),
            InlineKeyboardButton("🍾 3+ Drinks", callback_data="log_habit:alcohol:3:3+ drinks")
        ],
        [
            InlineKeyboardButton("🔙 Back to Habits", callback_data="menu_unholy")
        ]
    ])

async def log_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update, context):
        return
    today_str = date.today().isoformat()
    text = (
        f"✍️ <b>Daily Activity & Habit Logger</b>\n"
        f"📅 Date: <code>{today_str}</code>\n\n"
        "Choose an action below to log unholy habits, sleep disruptors, or custom free notes:"
    )
    await update.message.reply_text(text, reply_markup=get_main_log_keyboard(), parse_mode="HTML")

async def notes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update, context):
        return
    logs = db.get_activity_logs(limit=15)
    if not logs:
        await update.message.reply_text("📋 No activity logs or habits recorded yet. Use /log to add one!", parse_mode="HTML")
        return
    
    msg_lines = ["📋 <b>Recent Activity & Habit Logs</b>\n"]
    for l in logs:
        icon = "😈" if l.get("category") == "unholy_habit" else "📝"
        tag_title = l.get("tag", "").replace("_", " ").title()
        val = f" ({l['value']})" if l.get("value") is not None else ""
        note = f"\n   <i>{html.escape(str(l['note']))}</i>" if l.get("note") else ""
        msg_lines.append(f"• <code>{l['date']}</code> {icon} <b>{tag_title}</b>{val}{note}")
    
    await update.message.reply_text("\n".join(msg_lines), parse_mode="HTML")

async def insights_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update, context):
        return
    
    df = db.get_df(limit=30)
    if df.empty:
        await update.message.reply_text("No biometric data available yet.", parse_mode="HTML")
        return
    
    df_bands = analytics.calculate_hrv_baseline(df)
    latest = df_bands.iloc[-1]
    
    hrv_val = latest.get("hrv_last_night")
    band_status = latest.get("hrv_band_status", "Calibrating")
    lower = latest.get("hrv_band_lower")
    upper = latest.get("hrv_band_upper")
    base_mean = latest.get("hrv_baseline_mean")
    
    status_icon = "🟢" if band_status == "Balanced" else ("🔵" if "Elevated" in band_status else "🔴")
    
    # Sleep disruption
    sleep_disp = analytics.calculate_sleep_disruption_index(latest)
    
    # Habit impact
    df_logs = db.get_activity_logs_df(limit=100)
    impact = analytics.analyze_habit_impact(df, df_logs)
    
    msg = (
        f"🧠 <b>Biometric Intelligence & HRV Baselines</b>\n\n"
        f"💙 <b>HRV Status:</b> {status_icon} <i>{band_status}</i>\n"
        f"• Last Night: <b>{hrv_val or '—'} ms</b>\n"
        f"• Personalized Normal Band: <b>{lower or '—'} – {upper or '—'} ms</b> (Mean: {base_mean or '—'} ms)\n\n"
        f"😴 <b>Sleep Disruption Index:</b> <b>{sleep_disp.get('score', '—')}/100</b> ({sleep_disp.get('category')})\n"
        f"• Deep Sleep: {sleep_disp.get('deep_pct')}% | REM Sleep: {sleep_disp.get('rem_pct')}%\n"
    )
    if sleep_disp.get("drivers"):
        msg += f"• Drivers: {', '.join(sleep_disp['drivers'])}\n"
        
    if impact.get("alcohol_impact"):
        alc = impact["alcohol_impact"]
        msg += (
            f"\n📊 <b>Alcohol Impact Quantification:</b>\n"
            f"• HRV Delta: <b>{alc['delta_hrv']:+.1f} ms</b> (Clean: {alc['clean_hrv']} vs Alc: {alc['alcohol_hrv']})\n"
            f"• Resting HR Delta: <b>{alc['delta_rhr']:+.1f} bpm</b> (Clean: {alc['clean_rhr']} vs Alc: {alc['alcohol_rhr']})\n"
            f"• Sleep Score Delta: <b>{alc['delta_sleep']:+.1f} pts</b>\n"
        )
        
    await update.message.reply_text(msg, parse_mode="HTML")

async def alerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update, context):
        return
    
    anomalies = anomaly_detector.scan_daily_anomalies()
    recent_db_alerts = db.get_recent_alerts(limit=5)
    
    if not anomalies and not recent_db_alerts:
        await update.message.reply_text("✅ <b>All Clear!</b> No biometric anomalies detected in recent data.", parse_mode="HTML")
        return
    
    msg_lines = ["🚨 <b>Health Anomaly & Safety Monitor</b>\n"]
    if anomalies:
        msg_lines.append("<b>Current Active Flags:</b>")
        for a in anomalies:
            icon = "🛑" if a["severity"] == "CRITICAL" else "⚠️"
            msg_lines.append(f"{icon} <b>{html.escape(a['title'])}</b>\n{html.escape(a['message'])}\n")
            
    if recent_db_alerts:
        msg_lines.append("\n<b>Recent Historical Alerts:</b>")
        for alert in recent_db_alerts[:3]:
            msg_lines.append(f"• <code>{alert['timestamp']}</code> [{alert['severity']}] {html.escape(alert['alert_type'])}")
            
    await update.message.reply_text("\n".join(msg_lines), parse_mode="HTML")

# ---------- DIRECT NOTE & HABIT COMMANDS ----------

async def note_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update, context):
        return
    note_text = " ".join(context.args).strip() if context.args else ""
    if not note_text:
        await update.message.reply_text("✍️ Please provide note content. Example:\n<code>/note Sore quads from heavy squats</code>", parse_mode="HTML")
        return
    today_str = date.today().isoformat()
    db.log_activity(date_str=today_str, category="free_note", tag="note", note=note_text)
    await update.message.reply_text(
        f"📝 <b>Free Note Logged!</b>\n"
        f"📅 Date: <code>{today_str}</code>\n"
        f"✍️ Note: <i>{html.escape(note_text)}</i>",
        parse_mode="HTML"
    )

async def habit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update, context):
        return
    if not context.args:
        await update.message.reply_text(
            "😈 <b>Log an Unholy Habit via Command:</b>\n\n"
            "Usage: <code>/habit &lt;name&gt; [units] [details]</code>\n\n"
            "Examples:\n"
            "• <code>/habit alcohol 2 two pints IPA</code>\n"
            "• <code>/habit late_meal 1 pizza at 11pm</code>\n"
            "• <code>/habit late_caffeine 1 espresso at 4pm</code>\n"
            "• <code>/habit stress 1 high mental fatigue</code>",
            parse_mode="HTML"
        )
        return
    tag = context.args[0].lower().replace(" ", "_")
    val = 1.0
    note_start = 1
    if len(context.args) > 1:
        try:
            val = float(context.args[1])
            note_start = 2
        except ValueError:
            val = 1.0
            note_start = 1
    note_text = " ".join(context.args[note_start:]).strip()
    today_str = date.today().isoformat()
    db.log_activity(date_str=today_str, category="unholy_habit", tag=tag, note=note_text, value=val)
    tag_title = tag.replace("_", " ").title()
    await update.message.reply_text(
        f"✅ <b>Unholy Habit Logged!</b>\n\n"
        f"😈 <b>Habit:</b> {tag_title} ({val})\n"
        f"📅 <b>Date:</b> <code>{today_str}</code>\n"
        f"📝 <b>Details:</b> {html.escape(note_text) if note_text else 'Logged'}",
        parse_mode="HTML"
    )

# Handle text messages (free note logger)
async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_auth(update, context):
        return
    
    if not update.message or not update.message.text:
        return
        
    text = update.message.text.strip()
    if text.startswith("/"):
        return
        
    today_str = date.today().isoformat()
    db.log_activity(
        date_str=today_str,
        category="free_note",
        tag="note",
        note=text
    )
    
    await update.message.reply_text(
        f"📝 <b>Free Note Logged!</b>\n"
        f"📅 Date: <code>{today_str}</code>\n"
        f"✍️ Note: <i>{html.escape(text)}</i>\n\n"
        f"Factored into your daily AI coaching recovery analysis.",
        parse_mode="HTML"
    )

# Callback Query Handler for inline buttons
async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    try:
        await query.answer()
    except Exception as e:
        logger.warning(f"Callback answer warning: {e}")
        
    if not await check_auth(update, context):
        return
        
    data = query.data
    today_str = date.today().isoformat()
    
    try:
        if data == "menu_main":
            text = (
                f"✍️ <b>Daily Activity & Habit Logger</b>\n"
                f"📅 Date: <code>{today_str}</code>\n\n"
                "Choose an action below to log unholy habits, sleep disruptors, or custom free notes:"
            )
            await query.edit_message_text(text, reply_markup=get_main_log_keyboard(), parse_mode="HTML")
            
        elif data == "menu_unholy":
            text = (
                f"😈 <b>Log an Unholy Habit / Disruptor</b>\n"
                f"📅 Date: <code>{today_str}</code>\n\n"
                "Select what you indulged in or experienced today:"
            )
            await query.edit_message_text(text, reply_markup=get_unholy_habits_keyboard(), parse_mode="HTML")
            
        elif data == "unholy_alcohol_menu":
            text = (
                f"🍷 <b>Alcohol Intake</b>\n"
                f"📅 Date: <code>{today_str}</code>\n\n"
                "How many standard drinks did you have?"
            )
            await query.edit_message_text(text, reply_markup=get_alcohol_keyboard(), parse_mode="HTML")
            
        elif data == "menu_note":
            text = (
                f"📝 <b>Write a Free Note</b>\n"
                f"📅 Date: <code>{today_str}</code>\n\n"
                "👇 <b>Type your note directly in the message box below and send it!</b>\n\n"
                "Examples:\n"
                "• <i>Sore quads from heavy squats</i>\n"
                "• <i>Red eye flight, feeling exhausted</i>\n"
                "• <i>Drank 3L water today, energetic</i>\n\n"
                "💡 <i>Or use <code>/note &lt;text&gt;</code> anytime.</i>"
            )
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="menu_main")]
            ])
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
            
        elif data == "menu_view_today":
            logs = db.get_activity_logs(date_str=today_str, limit=20)
            if not logs:
                text = f"📋 <b>Today's Logs ({today_str}):</b>\n\nNo habits or notes logged for today yet."
            else:
                text = f"📋 <b>Today's Logs ({today_str}):</b>\n\n"
                for l in logs:
                    icon = "😈" if l.get("category") == "unholy_habit" else "📝"
                    tag_title = l.get("tag", "").replace("_", " ").title()
                    val = f" ({l['value']})" if l.get("value") is not None else ""
                    note = f"\n   <i>{html.escape(str(l['note']))}</i>" if l.get("note") else ""
                    text += f"• {icon} <b>{tag_title}</b>{val}{note}\n"
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="menu_main")]
            ])
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
            
        elif data.startswith("log_habit:"):
            parts = data.split(":")
            tag = parts[1]
            val = float(parts[2]) if len(parts) > 2 and parts[2] else 1.0
            note = parts[3] if len(parts) > 3 else ""
            
            db.log_activity(
                date_str=today_str,
                category="unholy_habit",
                tag=tag,
                note=note,
                value=val
            )
            
            tag_title = tag.replace("_", " ").title()
            text = (
                f"✅ <b>Unholy Habit Logged!</b>\n\n"
                f"😈 <b>Habit:</b> {tag_title} ({val})\n"
                f"📅 <b>Date:</b> <code>{today_str}</code>\n"
                f"📝 <b>Details:</b> {html.escape(note) if note else 'Logged'}\n\n"
                f"Hermes Coach will correlate this with tomorrow's sleep and HRV recovery."
            )
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("➕ Log Another Habit", callback_data="menu_unholy"),
                    InlineKeyboardButton("📋 View Today's Logs", callback_data="menu_view_today")
                ]
            ])
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error handling callback query '{data}': {e}", exc_info=True)
        try:
            # Fallback plain text edit if anything failed
            await query.edit_message_text(f"Action processed: {data}")
        except Exception:
            pass

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
    app.add_handler(CommandHandler("log", log_command))
    app.add_handler(CommandHandler("note", note_command))
    app.add_handler(CommandHandler("habit", habit_command))
    app.add_handler(CommandHandler("notes", notes_command))
    app.add_handler(CommandHandler("insights", insights_command))
    app.add_handler(CommandHandler("alerts", alerts_command))
    app.add_handler(CommandHandler("health", health_command))
    app.add_handler(CommandHandler("gym", gym_command))
    app.add_handler(CommandHandler("week", week_command))
    app.add_handler(CommandHandler("recover", recover_command))
    app.add_handler(CommandHandler("status", status_command))
    
    # Inline buttons callback handler
    app.add_handler(CallbackQueryHandler(callback_query_handler))
    
    # Free text message handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))
    
    # Start polling
    app.run_polling()

if __name__ == "__main__":
    main()

