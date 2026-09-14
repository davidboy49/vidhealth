#!/usr/bin/env bash
# Gym-day recovery gate (Mon/Wed/Fri 7:30am cron).
# Force-syncs Garmin FIRST (watch data reaches us via the phone BT cache and is
# routinely stale), then prints the last 3 days of gate metrics.
#
# NOTE: the live store is Postgres. /root/garmin-health/health.db is the legacy
# SQLite file and is frozen at 2026-08-23 — never quote numbers from it.
set -eo pipefail

cd /root/garmin-health

echo "=== FORCE SYNC ==="
timeout 300 python3 sync.py smart 4 --force

echo
echo "=== GATE METRICS (newest first) ==="
set -a
. ./.env
set +a
psql "$DATABASE_URL" -A -F'|' -c \
  "SELECT date, hrv_last_night, hrv_weekly_avg, sleep_score, sleep_duration, resting_hr, bb_max, spo2_min FROM daily_metrics ORDER BY date DESC LIMIT 3;"
