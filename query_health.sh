#!/bin/bash
# Query the health Postgres DB (replaces inline sqlite3 health.db in cron prompts)
# Usage: bash /root/garmin-health/query_health.sh "SELECT ..."
PASS=$(grep '^PASS=' /root/backups/health-pg-credentials.txt | cut -d= -f2)
PGPASSWORD="$PASS" psql -h 127.0.0.1 -U health_user -d health -t -A -F '|' -c "$1"
