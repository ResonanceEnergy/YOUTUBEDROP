from __future__ import annotations

import os, json
from pathlib import Path
from typing import List, Dict

from dotenv import load_dotenv
from utils.io import data_root, ensure_dir, save_json, video_dir, log_info
from utils.youtube_api import list_channel_uploads, get_video_snippet

load_dotenv()


def parse_channel_ids() -> List[str]:
    raw = os.getenv("YOUTUBE_CHANNEL_IDS", "")
    if Path(raw).exists():
        return [line.strip() for line in Path(raw).read_text().splitlines() if line.strip()]
    return [p.strip() for p in raw.split(",") if p.strip()]


def ingest_new() -> List[Dict]:
    ensure_dir(data_root() / "videos")
    seen_path = data_root() / "index" / "seen.json"
    ensure_dir(seen_path.parent)
    seen = {}
    if seen_path.exists():
        seen = json.loads(seen_path.read_text())

    new_items = []
    for ch in parse_channel_ids():
        vids = list_channel_uploads(ch)
        for v in vids:
            vid_id = v["video_id"]
            if vid_id in seen:
                continue

            # Fetch snippet/details once
            snippet = get_video_snippet(vid_id)
            out = {
                "video_id": vid_id,
                "channel_id": ch,
                "title": v["title"],
                "publishedAt": v["publishedAt"],
                "snippet": snippet.get("snippet", {}),
                "contentDetails": snippet.get("contentDetails", {}),
                "statistics": snippet.get("statistics", {}),
            }
            save_json(video_dir(vid_id) / "metadata.json", out)
            new_items.append(out)
            seen[vid_id] = True

    save_json(seen_path, seen)
    log_info(f"Ingested {len(new_items)} new videos")
    return new_items


def ingest_single_video(video_id: str, source: str = "manual") -> Dict:
    """Ingest a single video by ID (used by Telegram/Discord bots)."""
    seen_path = data_root() / "index" / "seen.json"
    ensure_dir(seen_path.parent)
    seen = {}
    if seen_path.exists():
        seen = json.loads(seen_path.read_text())

    if video_id in seen:
        # Already ingested — return existing metadata
        meta_path = video_dir(video_id) / "metadata.json"
        if meta_path.exists():
            return json.loads(meta_path.read_text())
        return {"video_id": video_id, "already_seen": True}

    snippet = get_video_snippet(video_id)
    out = {
        "video_id": video_id,
        "channel_id": snippet.get("snippet", {}).get("channelId", ""),
        "title": snippet.get("snippet", {}).get("title", video_id),
        "publishedAt": snippet.get("snippet", {}).get("publishedAt", ""),
        "snippet": snippet.get("snippet", {}),
        "contentDetails": snippet.get("contentDetails", {}),
        "statistics": snippet.get("statistics", {}),
        "source": source,
    }
    save_json(video_dir(video_id) / "metadata.json", out)
    seen[video_id] = True
    save_json(seen_path, seen)
    log_info(f"Ingested single video: {video_id} ({out['title']})")
    return out


if __name__ == "__main__":
    ingest_new()
