from __future__ import annotations

import os
from typing import Dict, List

from googleapiclient.discovery import build
from utils.io import log_info


def build_client():
    key = os.getenv("YOUTUBE_API_KEY")
    if not key:
        raise RuntimeError("YOUTUBE_API_KEY missing")
    return build("youtube", "v3", developerKey=key)


def list_channel_uploads(channel_id: str, max_videos: int = 200) -> List[Dict]:
    """Return latest videos (id, title, publishedAt) for a channel.
    max_videos caps the total fetched to avoid quota exhaustion."""
    yt = build_client()

    # Step 1: get uploads playlist id
    channels = yt.channels().list(part="contentDetails", id=channel_id).execute()
    items = channels.get("items", [])
    if not items:
        return []
    uploads_pl = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

    # Step 2: iterate playlistItems (page through if needed)
    vids = []
    request = yt.playlistItems().list(
        part="contentDetails,snippet", playlistId=uploads_pl, maxResults=50
    )
    while request and len(vids) < max_videos:
        resp = request.execute()
        for it in resp.get("items", []):
            vid_id = it["contentDetails"]["videoId"]
            title = it["snippet"]["title"]
            publishedAt = it["contentDetails"].get("videoPublishedAt") or it["snippet"].get("publishedAt")
            vids.append({"video_id": vid_id, "title": title, "publishedAt": publishedAt})
            if len(vids) >= max_videos:
                break
        request = yt.playlistItems().list_next(request, resp)

    log_info(f"Found {len(vids)} videos for channel {channel_id}")
    return vids


def get_video_snippet(video_id: str) -> Dict:
    yt = build_client()
    r = yt.videos().list(part="snippet,contentDetails,statistics", id=video_id).execute()
    items = r.get("items", [])
    return items[0] if items else {}
