# YOUTUBEDROP — OpenClaw Agent 🐾

**Send YouTube links from your phone or iPad via Telegram or Discord — and they get automatically ingested, segmented, ranked, clipped, and published as intel briefs.**

Two modes of operation:
1. **OpenClaw Bots** — Telegram + Discord bots. Paste a link from your phone → instant ingest + full pipeline.
2. **Daily Pipeline** — Cron/scheduled run that monitors YouTube channels, downloads new videos, and produces daily intel briefs.

---

## What It Does

| You send... | OpenClaw does... |
|---|---|
| A YouTube link via **Telegram** | Downloads audio, transcript, segments, ranks, publishes |
| A YouTube link via **Discord** | Downloads audio, transcript, segments, ranks, publishes |
| Multiple links in one message | Processes all of them concurrently |
| A duplicate link | Tells you it already has it |
| `python run_daily.py` | Monitors channels, ingests new videos, runs full pipeline |

### Supported Link Formats
- `youtube.com/watch?v=...`
- `youtu.be/...`
- `youtube.com/shorts/...`
- `youtube.com/live/...`
- `m.youtube.com/watch?v=...`
- `music.youtube.com/watch?v=...`
- Embed URLs

---

## Quick Start

### 1. Prerequisites
- Python 3.11+
- [ffmpeg](https://ffmpeg.org/download.html) (for audio/clip extraction)

### 2. Clone & Install

```bash
git clone https://github.com/ResonanceEnergy/YOUTUBEDROP.git
cd YOUTUBEDROP
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows
pip install -r requirements.txt
```

### 3. Create Your Bots

#### Telegram Bot
1. Open Telegram, message [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts
3. Copy the bot token

#### Discord Bot
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **New Application** → name it "YOUTUBEDROP"
3. Go to **Bot** → click **Add Bot**
4. Copy the bot token
5. Enable **MESSAGE CONTENT INTENT** under Privileged Gateway Intents
6. Go to **OAuth2 → URL Generator**:
   - Scopes: `bot`
   - Bot Permissions: `Send Messages`, `Read Message History`, `Embed Links`
7. Use the generated URL to invite the bot to your server

### 4. Configure

```bash
cp .env.example .env
```

Edit `.env` and fill in your values:

```env
# Bot tokens
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ
DISCORD_BOT_TOKEN=MTIzNDU2Nzg5MDEyMzQ1Njc4.XXXXXX.XXXXXXXX

# YouTube Data API (for channel monitoring pipeline)
YOUTUBE_API_KEY=YOUR_KEY
YOUTUBE_CHANNEL_IDS=UCX6OQ3DkcsbYNE6H8uQQuVA,UC-9-kyTW8ZkZNDHQJ6FgpwQ
```

### 5. Run

#### Start the Telegram + Discord bots (for phone/iPad drops):
```bash
python -m openclaw
```

#### Run the daily pipeline (ingest channels → process → brief):
```bash
python run_daily.py --mode all
```

---

## Docker

```bash
docker compose up -d
docker compose logs -f openclaw
```

---

## Commands

### Telegram
| Command | Description |
|---|---|
| Just paste a link | Auto-ingests + full pipeline |
| `/start` | Welcome message |
| `/help` | Show help |
| `/status <video_id>` | Check processing status |
| `/recent` | Show last 10 drops |
| `/stats` | Show statistics |

### Discord
| Command | Description |
|---|---|
| Just paste a link | Auto-ingests + full pipeline |
| `!yt help` | Show help |
| `!yt status <video_id>` | Check processing status |
| `!yt recent` | Show last 10 drops |
| `!yt stats` | Show statistics |

### VS Code Tasks
Open Command Palette → **Tasks: Run Task**:
- **Snipper: Ingest** — pull new videos from monitored channels
- **Snipper: Process New** — run transcript/segment/rank/clip/publish
- **Snipper: All** — full pipeline
- **OpenClaw: Start Bots** — launch Telegram + Discord bots

---

## Pipeline Architecture

```
Phone/iPad                          Cron / VS Code Task
    │                                       │
    ├── Telegram ──→ TelegramBot ──┐        │
    │                              │        │
    └── Discord  ──→ DiscordBot  ──┤        │
                                   │        │
                            OpenClaw Agent  │
                                   │        │
                                   ▼        ▼
                            ┌─────────────────────┐
                            │   pipelines/ingest   │  YouTube Data API
                            └─────────┬───────────┘
                                      ▼
                            ┌─────────────────────┐
                            │ pipelines/transcripts│  youtube-transcript-api + yt-dlp
                            └─────────┬───────────┘
                                      ▼
                            ┌─────────────────────┐
                            │  pipelines/segment   │  Greedy segmentation
                            └─────────┬───────────┘
                                      ▼
                            ┌─────────────────────┐
                            │   pipelines/rank     │  Relevance profiles (AAC, NCL, FP)
                            └─────────┬───────────┘
                                      ▼
                            ┌─────────────────────┐
                            │   pipelines/clip     │  ffmpeg subtitled clips
                            └─────────┬───────────┘
                                      ▼
                            ┌─────────────────────┐
                            │  pipelines/publish   │  Daily briefs + GitHub issues
                            └─────────────────────┘
                                      │
                            ┌─────────┴──────────┐
                            │                    │
                        data/                ncl_out/
                      (artifacts)         (briefs/packets)
```

---

## Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | — | Telegram bot token (from BotFather) |
| `DISCORD_BOT_TOKEN` | — | Discord bot token |
| `YOUTUBE_API_KEY` | — | YouTube Data API v3 key |
| `YOUTUBE_CHANNEL_IDS` | — | Comma-separated channel IDs to monitor |
| `DATA_ROOT` | `./data` | Raw video metadata + artifacts |
| `NCL_ROOT` | `./ncl_out` | Intel briefs output |
| `DOWNLOAD_DIR` | `./downloads` | Bot download directory |
| `DATABASE_URL` | `sqlite:///./youtubedrop.db` | Bot tracking database |
| `AUDIO_ONLY` | `true` | Download audio only (MP3) vs full video |
| `DOWNLOAD_TRANSCRIPT` | `true` | Fetch & save transcript |
| `DOWNLOAD_THUMBNAIL` | `true` | Save video thumbnail |
| `MAX_CONCURRENT_DOWNLOADS` | `3` | Parallel download limit |
| `MAX_DURATION` | `0` | Max video length in seconds (0 = no limit) |
| `DAILY_TOP_K` | `10` | Top segments per org |
| `GITHUB_TOKEN` | — | For auto-creating GitHub issues |
| `NCC_REPO_MAP_JSON` | `{}` | Org→repo mapping for issue routing |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

---

## Project Structure

```
YOUTUBEDROP/
├── openclaw/                    # Telegram + Discord bot agent
│   ├── __init__.py
│   ├── __main__.py              # python -m openclaw
│   ├── agent.py                 # Main orchestrator
│   ├── config.py                # Settings from .env
│   ├── database.py              # SQLite tracking
│   ├── discord_bot.py           # Discord bot
│   ├── processor.py             # yt-dlp download + pipeline integration
│   ├── telegram_bot.py          # Telegram bot
│   └── youtube_parser.py        # URL parser & validator
├── pipelines/                   # Full processing pipeline
│   ├── ingest.py                # YouTube Data API channel monitor
│   ├── transcripts.py           # Transcript fetch + video download
│   ├── segment.py               # Greedy transcript segmentation
│   ├── rank.py                  # Relevance scoring against profiles
│   ├── clip.py                  # ffmpeg clip generation
│   └── publish.py               # Daily briefs + GitHub issues
├── utils/                       # Shared utilities
│   ├── io.py                    # File I/O, paths, logging
│   ├── text.py                  # NLP text processing
│   └── youtube_api.py           # YouTube Data API wrapper
├── doctrine/                    # Relevance & routing config
│   ├── relevance_profiles.yaml  # AAC / NCL / FuturePredictor profiles
│   └── org_routes.yaml          # Org → repo routing
├── schemas/
│   └── intel_packet.json        # IntelPacket JSON schema
├── ops/
│   └── scheduler.md             # Cron & systemd notes
├── .vscode/
│   └── tasks.json               # VS Code task runners
├── run_daily.py                 # Daily pipeline orchestrator
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## Compliance & Safety

- This pipeline uses YouTube Data API and captions. Ensure your use complies with YouTube Terms of Service and any applicable copyright/fair use frameworks.
- Treat produced clips as internal analysis artifacts for NCL/NCC; for any redistribution, obtain permissions where required.

---

## License

MIT
