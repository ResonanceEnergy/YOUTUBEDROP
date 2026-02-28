# Scheduler Notes

## Local cron (midnight local)

```bash
0 0 * * * cd /path/to/YOUTUBEDROP && /usr/bin/env bash -lc 'source .venv/bin/activate && python run_daily.py --mode all > logs/cron.log 2>&1'
```

## Windows Task Scheduler

1. Open **Task Scheduler** → Create Basic Task
2. Name: `YOUTUBEDROP Daily`
3. Trigger: Daily at midnight
4. Action: Start a program
   - Program: `C:\path\to\.venv\Scripts\python.exe`
   - Arguments: `run_daily.py --mode all`
   - Start in: `C:\path\to\YOUTUBEDROP`

## OpenClaw Bot (always-on)

Run the Telegram/Discord bots as a background service:

```bash
# Linux systemd
sudo cp ops/youtubedrop-openclaw.service /etc/systemd/system/
sudo systemctl enable youtubedrop-openclaw
sudo systemctl start youtubedrop-openclaw

# Docker
docker compose up -d
```

## Manual runs

```bash
# Ingest new videos from monitored channels
python run_daily.py --mode ingest

# Process all ingested videos (transcript, segment, rank, clip, publish)
python run_daily.py --mode process_new

# Full pipeline
python run_daily.py --mode all

# Start Telegram + Discord bots (for phone/iPad drops)
python -m openclaw
```
