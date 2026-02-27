# YOUTUBEDROP

YouTube content pipeline for the Resonance Energy empire.
**Ingest → Script → Upload** — fully automated.

## What It Does
- **Ingest**: Fetch metadata, download audio/video, transcribe with Whisper
- **Script**: Generate full video scripts from topics using Claude/GPT
- **Upload**: Push videos to YouTube via Data API v3

## Quick Start

```bash
cd src
pip install -r ../requirements.txt
cp ../.env.example ../.env  # fill in your API keys

# Search YouTube
python main.py search "Tesla earnings 2026" --limit 5

# Ingest a video (metadata + transcription)
python main.py ingest https://youtu.be/VIDEO_ID --download --transcribe

# Generate a script
python main.py script "Why Tesla will dominate 2026" --duration 10

# Full pipeline (script → metadata → ready to record)
python main.py pipeline "Tesla stock analysis Q1 2026" --output-dir output/tesla-q1
```

## API Keys Required
| Key | Purpose |
|-----|---------|
| `YOUTUBE_API_KEY` | Search + metadata |
| `ANTHROPIC_API_KEY` | Script generation (preferred) |
| `OPENAI_API_KEY` | Script generation (fallback) + Whisper transcription |

Get YouTube API key: [Google Cloud Console](https://console.cloud.google.com/) → Enable YouTube Data API v3

## Structure
```
src/
  main.py           # CLI entry point
  ingestor.py       # YouTube fetch + download + transcribe
  script_generator.py  # LLM script generation
  upload_manager.py    # YouTube upload via OAuth2
tests/
  test_youtubedrop.py
config/
  settings.json
```

## Part of ResonanceEnergy Portfolio
Built and maintained by OPTIMUS (Agent Y) + GASKET (Agent G) via Repo Depot Flywheel.
