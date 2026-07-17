## Webhook Pipeline

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
