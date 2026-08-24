#!/usr/bin/env python3
"""Restore raw_json/ai_summary from frozen health.db into Postgres daily_metrics,
then re-run the idempotent migration to restore wiped epoch/alert tables."""
import sqlite3
from dotenv import load_dotenv
load_dotenv('/root/garmin-health/.env')
import db

src = sqlite3.connect('/root/garmin-health/health.db')
rows = src.execute("SELECT date, raw_json, ai_summary FROM daily_metrics WHERE raw_json IS NOT NULL OR ai_summary IS NOT NULL").fetchall()
src.close()

done = 0
with db._conn() as con:
    for date, raw, ai in rows:
        con.execute("UPDATE daily_metrics SET raw_json = %s, ai_summary = %s WHERE date = %s",
                    (raw, ai, date))
        done += 1
print(f'raw_json/ai_summary backfilled: {done} rows')
