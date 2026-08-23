#!/usr/bin/env python3
"""
One-time data migration: copies every row from the legacy SQLite database
(health.db) into the PostgreSQL database configured via DATABASE_URL in .env.

Run this ON THE VPS, where health.db actually has data, after pulling the
updated code but before (or right after) restarting the systemd services.
It's safe to re-run: writes use ON CONFLICT DO NOTHING, so already-migrated
rows are skipped rather than duplicated or overwritten.

Usage:
    python migrate_sqlite_to_postgres.py            # migrate everything
    python migrate_sqlite_to_postgres.py --verify    # only compare row counts
    python migrate_sqlite_to_postgres.py --sqlite-path /path/to/health.db
"""
import argparse
import sqlite3
import sys
from pathlib import Path

import db  # local module — provides init_db(), _conn(), DATABASE_URL

BATCH_SIZE = 2000

# (table, columns-in-insert-order, conflict-target)
TABLES = [
    ("daily_metrics", [
        "date", "hrv_last_night", "hrv_weekly_avg", "hrv_status", "sleep_score",
        "sleep_duration", "sleep_deep", "sleep_light", "sleep_rem", "sleep_awake",
        "resting_hr", "min_hr", "max_hr", "bb_max", "bb_min", "bb_charged",
        "bb_drained", "stress_avg", "stress_max", "steps", "floors",
        "training_readiness", "spo2_avg", "spo2_min", "respiration_avg",
        "respiration_min", "workout_type", "alcohol_logged", "sleep_apnea_flag",
        "ai_summary", "raw_json",
    ], "date"),
    ("body_comp", ["date", "weight", "body_fat", "waist"], "date"),
    ("activity_logs", ["id", "date", "timestamp", "category", "tag", "note", "value"], "id"),
    ("anomaly_alerts", [
        "id", "date", "timestamp", "severity", "alert_type", "message",
        "metrics_json", "acknowledged",
    ], "id"),
    ("spo2_epochs", [
        "id", "date", "timestamp", "time_str", "spo2_value", "respiration_rate",
        "sleep_stage", "epoch_type",
    ], "id"),
    ("spo2_drop_events", [
        "id", "date", "start_time", "nadir_time", "end_time", "duration_seconds",
        "baseline_spo2", "nadir_spo2", "drop_magnitude", "sleep_stage",
        "respiration_rate", "severity", "event_type",
    ], "id"),
    ("hourly_spo2", [
        "id", "date", "hour", "spo2_avg", "spo2_min", "spo2_max", "sample_count",
        "drops_below_90", "drops_below_85", "hypoxic_minutes", "respiration_avg",
        "dominant_sleep_stage", "lowest_timestamp",
    ], "id"),
    ("garmin_activities", [
        "activity_id", "date", "start_time", "activity_name", "activity_type",
        "duration_seconds", "elapsed_duration_seconds", "distance_meters",
        "calories", "avg_hr", "max_hr", "aerobic_training_effect",
        "anaerobic_training_effect", "avg_speed", "max_speed", "elevation_gain",
        "steps", "raw_json",
    ], "activity_id"),
]

# Tables with an explicit integer PRIMARY KEY (id / activity_id) whose IDENTITY
# sequence must be advanced after a direct id-preserving insert, or the next
# INSERT INTO ... (no explicit id) from the app will collide with a migrated row.
_SEQUENCE_COLUMNS = {
    "activity_logs": "id",
    "anomaly_alerts": "id",
    "spo2_epochs": "id",
    "spo2_drop_events": "id",
    "hourly_spo2": "id",
}


def _sqlite_rows(sqlite_conn, table, columns):
    cur = sqlite_conn.cursor()
    cur.execute(f"SELECT {', '.join(columns)} FROM {table}")
    while True:
        batch = cur.fetchmany(BATCH_SIZE)
        if not batch:
            return
        yield batch


def migrate(sqlite_path: Path):
    if not sqlite_path.exists():
        print(f"[ERROR] SQLite file not found: {sqlite_path}", file=sys.stderr)
        sys.exit(1)

    db.init_db()
    sqlite_conn = sqlite3.connect(str(sqlite_path))

    for table, columns, conflict_col in TABLES:
        try:
            total = sqlite_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        except sqlite3.OperationalError:
            print(f"[SKIP] {table}: not present in SQLite DB")
            continue

        if total == 0:
            print(f"[SKIP] {table}: 0 rows in SQLite")
            continue

        placeholders = ", ".join(["%s"] * len(columns))
        col_list = ", ".join(columns)
        insert_sql = (
            f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) "
            f"ON CONFLICT ({conflict_col}) DO NOTHING"
        )

        migrated = 0
        with db._conn() as pg_conn:
            with pg_conn.cursor() as pg_cur:
                for batch in _sqlite_rows(sqlite_conn, table, columns):
                    pg_cur.executemany(insert_sql, batch)
                    migrated += len(batch)
                    print(f"[{table}] {migrated}/{total} rows sent...", end="\r")

                seq_col = _SEQUENCE_COLUMNS.get(table)
                if seq_col:
                    pg_cur.execute(
                        f"SELECT setval(pg_get_serial_sequence(%s, %s), "
                        f"GREATEST(COALESCE((SELECT MAX({seq_col}) FROM {table}), 1), 1))",
                        (table, seq_col),
                    )
        print(f"[{table}] {migrated}/{total} rows sent.       ")

    sqlite_conn.close()
    print("\nMigration complete. Run with --verify to double-check row counts.")


def verify(sqlite_path: Path):
    if not sqlite_path.exists():
        print(f"[ERROR] SQLite file not found: {sqlite_path}", file=sys.stderr)
        sys.exit(1)

    sqlite_conn = sqlite3.connect(str(sqlite_path))
    db.init_db()
    print(f"{'table':<20}{'sqlite':>10}{'postgres':>10}")
    print("-" * 40)
    mismatches = []
    with db._conn() as pg_conn:
        with pg_conn.cursor() as pg_cur:
            for table, _columns, _conflict_col in TABLES:
                try:
                    sq_count = sqlite_conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                except sqlite3.OperationalError:
                    sq_count = "n/a"
                pg_cur.execute(f"SELECT COUNT(*) FROM {table}")
                pg_count = pg_cur.fetchone()[0]
                flag = "" if sq_count in (pg_count, "n/a") else "  <-- MISMATCH"
                if flag:
                    mismatches.append(table)
                print(f"{table:<20}{str(sq_count):>10}{pg_count:>10}{flag}")
    sqlite_conn.close()
    if mismatches:
        print(f"\n{len(mismatches)} table(s) mismatched: {', '.join(mismatches)}")
        sys.exit(1)
    print("\nAll table counts match (or table absent from SQLite).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sqlite-path", type=Path, default=db.SQLITE_PATH,
        help="Path to the legacy health.db (default: next to db.py)",
    )
    parser.add_argument(
        "--verify", action="store_true",
        help="Only compare row counts between SQLite and Postgres; migrate nothing.",
    )
    args = parser.parse_args()

    if args.verify:
        verify(args.sqlite_path)
    else:
        migrate(args.sqlite_path)
