from __future__ import annotations

from pathlib import Path
from typing import Dict

from dotenv import load_dotenv
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
)
from utils.io import (
    data_root, artifacts_dir, save_json, log_warn,
)

import subprocess
import json

load_dotenv()


def fetch_transcript(video_id: str) -> Dict:
    path = artifacts_dir(video_id) / "transcript.json"
    if path.exists():
        return json.loads(path.read_text())

    try:
        # Try modern API (>=1.0) first, fall back to 0.6.x
        try:
            api = YouTubeTranscriptApi()
            entries = api.fetch(video_id)
        except TypeError:
            # 0.6.x static API fallback
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            transcript = None
            for lang in ["en", "en-US", "en-GB"]:
                try:
                    transcript = transcript_list.find_transcript([lang])
                    break
                except Exception:
                    continue

            if transcript is None:
                try:
                    transcript = transcript_list.find_generated_transcript(
                        transcript_list._generated_transcripts.keys()
                    )
                except Exception:
                    pass

            if transcript is None:
                log_warn(f"No usable transcript for {video_id}")
                return {"video_id": video_id, "entries": []}

            entries = transcript.fetch()

        # Ensure entries are plain dicts for JSON serialization
        entries = [
            dict(e) if not isinstance(e, dict) else e
            for e in entries
        ]
        out = {"video_id": video_id, "entries": entries}
        save_json(path, out)
        return out

    except (TranscriptsDisabled, NoTranscriptFound) as e:
        log_warn(f"No transcript for {video_id}: {e}")
        return {"video_id": video_id, "entries": []}


def download_video(video_id: str) -> Path:
    """Download best mp4 using yt-dlp."""
    out_dir = artifacts_dir(video_id)
    out_file = out_dir / f"{video_id}.mp4"
    if out_file.exists():
        return out_file
    cmd = [
        "yt-dlp",
        "-f", "mp4/best",
        f"https://www.youtube.com/watch?v={video_id}",
        "-o", str(out_dir / f"{video_id}.%(ext)s"),
        "--no-playlist",
    ]
    subprocess.run(cmd, check=True)
    return out_file


def run_for_new_videos():
    idx = data_root() / "index" / "seen.json"
    if not idx.exists():
        log_warn("No seen index. Run ingest first.")
        return
    seen = json.loads(idx.read_text())
    for vid in seen.keys():
        t = fetch_transcript(vid)
        if not t["entries"]:
            # optional: download audio & run offline speech-to-text (future)
            pass
        # Ensure we have the asset
        try:
            download_video(vid)
        except Exception as e:
            log_warn(f"Download failed for {vid}: {e}")


if __name__ == "__main__":
    run_for_new_videos()
