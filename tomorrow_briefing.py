#!/usr/bin/env python3
"""Tomorrow briefing for HealthBot — deterministic, no LLM. Runs nightly 21:00 via cron."""
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── Postgres (migrated Aug 2026) — load .env so db.py gets DATABASE_URL ──
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
import db  # noqa: E402  (replaces direct sqlite3 for health queries)

import requests

BASE = Path('/root/garmin-health')

# ── Load bot config ──
env = {}
for line in (BASE / '.env').read_text().splitlines():
    if '=' in line and not line.strip().startswith('#'):
        k, _, v = line.partition('=')
        env[k.strip()] = v.strip().strip('"').strip("'")

TOKEN = env.get('TELEGRAM_BOT_TOKEN', '')
CHAT_ID = env.get('TELEGRAM_CHAT_ID', '')

ICT = timezone(timedelta(hours=7))
now = datetime.now(ICT)
tomorrow = now + timedelta(days=1)
wd = tomorrow.weekday()  # 0=Mon ... 6=Sun
day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

# ── Workout / commitments by tomorrow's day ──
if wd in (0, 2, 4):
    workout = '🏋️ GYM (06:30, before work)'
elif wd in (1, 3):
    workout = '🏃 RUN at Norea (06:30, before work)'
elif wd == 5:
    workout = '🏃 Long run (08:00) — 10K training'
else:
    workout = '🧘 Rest day + 07:00 weekly plan'

pitch = ''
if wd == 4:  # Friday = pitch night
    pitch = '🎯 PITCH NIGHT — one conversation, one venue owner. Cap $15, leave 22:30.\n'

# ── Today's data from health.db (last sync; the 10pm job re-syncs) ──
steps = sleep_h = spo2 = None
try:
    with db._conn() as con:
        row = con.execute(
            "SELECT steps, sleep_duration, spo2_min FROM daily_metrics WHERE date = %s ORDER BY date DESC LIMIT 1",
            (now.strftime('%Y-%m-%d'),)).fetchone()
        if row:
            steps, sleep_dur, spo2 = row
            if sleep_dur:
                sleep_h = round(sleep_dur / 3600, 1)
except Exception:
    pass

steps_txt = f'{steps:,}' if steps else '—'
sleep_txt = f'{sleep_h}h' if sleep_h else '—'
spo2_txt = spo2 if spo2 else '—'

# ── Build-block task: /root/next-task.txt (first line) or default ──
task_file = Path('/root/next-task.txt')
task = 'Pitch prep: one-page managed-hosting offer'
if task_file.exists():
    t = task_file.read_text().strip().splitlines()
    if t and t[0].strip():
        task = t[0].strip()

# ── One flag line only when something's off (silence when on track) ──
flags = []
if steps is not None and steps < 5000:
    flags.append('⚠️ steps low')
if sleep_h is not None and sleep_h < 6:
    flags.append('⚠️ short night')
if spo2 is not None and spo2 < 85:
    flags.append('⚠️ SpO2 dipped — saline, no beer tonight')
flag_line = ('\n' + ' · '.join(flags)) if flags else ''

msg = (
    f'📅 <b>{day_names[wd]}, {tomorrow.strftime("%b %d")}</b>\n'
    f'{workout} · 💪 {task}\n'
    f'😴 22:00 (wake 05:00)\n'
    f'{pitch}'
    f'<i>steps {steps_txt} · sleep {sleep_txt} · SpO2 {spo2_txt}</i>{flag_line}'
)

# ── Send via HealthBot (HTML parse mode — safe against stray chars) ──
if TOKEN and CHAT_ID:
    try:
        requests.post(f'https://api.telegram.org/bot{TOKEN}/sendMessage',
                      json={'chat_id': CHAT_ID, 'text': msg, 'parse_mode': 'HTML'},
                      timeout=15)
    except Exception:
        pass
