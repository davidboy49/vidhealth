## Webhook Pipeline

## Database (PostgreSQL)

The app persists to PostgreSQL through `db.py`; the public API (`save_day`,
`get_df`, `log_activity`, ...) is unchanged from the old SQLite version, so
`bot.py`, `dashboard/dashboard.py`, `sync.py`, `analytics.py`, etc. need no
code changes — only configuration.

Add the connection string to `/root/garmin-health/.env` (same file the
Garmin/Telegram credentials already live in):

```
DATABASE_URL=postgresql://health_user:PASSWORD@HOST:5432/health
```

`db.init_db()` creates the schema automatically on first use — no manual
`CREATE TABLE` step needed. Tables are the same set as before (`daily_metrics`,
`body_comp`, `activity_logs`, `anomaly_alerts`, `spo2_epochs`,
`spo2_drop_events`, `hourly_spo2`, `garmin_activities`), plus indexes on the
`date` columns that SQLite didn't need but Postgres benefits from.

### One-time migration from the old health.db

If `/root/garmin-health/health.db` still has data from before the switch,
copy it into Postgres once:

```bash
python migrate_sqlite_to_postgres.py            # copies every row
python migrate_sqlite_to_postgres.py --verify   # compares row counts only
```

It's safe to re-run — inserts use `ON CONFLICT DO NOTHING`, so already-migrated
rows are skipped rather than duplicated. After migrating, `health.db` is no
longer read or written by the app and can be archived or deleted once you've
confirmed the dashboard/bot look correct against Postgres.

### Datasette API (`health-api.service`)

Datasette only reads SQLite files natively. Serving Postgres instead requires
the `datasette-postgres` plugin:

```bash
/root/garmin-health/venv/bin/pip install datasette-postgres
```

`health-api.service` has been updated to pass `$DATABASE_URL` (from `.env`)
to `datasette serve` instead of a `health.db` path. This combination is
untested against the actual Datasette + `datasette-postgres` versions on the
VPS — verify it starts cleanly (`systemctl status health-api`,
`journalctl -u health-api -n 50`) after restarting, since this service is
optional and not required for the dashboard or Telegram bot to work.

## Automatic Garmin Sync

The systemd timer syncs today's Garmin data every three hours from 06:05
through 21:05 in the Asia/Bangkok timezone. `Persistent=true` runs a missed
sync after the server comes back online.

```bash
sudo cp garmin-sync.service garmin-sync.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now garmin-sync.timer
```

Check the schedule and recent sync output:

```bash
systemctl list-timers garmin-sync.timer
systemctl status garmin-sync.service
journalctl -u garmin-sync.service -n 50 --no-pager
```

The service expects Garmin credentials in `/root/garmin-health/.env` and uses
the same Python environment as the dashboard and Telegram bot.
