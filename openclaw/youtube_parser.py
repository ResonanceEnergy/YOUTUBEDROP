"""
YouTube Link Parser & Validator
Extracts video IDs from various YouTube URL formats.
"""

import re
from typing import Optional


# Regex patterns for YouTube URLs
YOUTUBE_PATTERNS = [
    # Standard watch URLs
    r"(?:https?://)?(?:www\.)?youtube\.com/watch\?.*?v=([a-zA-Z0-9_-]{11})",
    # Short URLs
    r"(?:https?://)?youtu\.be/([a-zA-Z0-9_-]{11})",
    # Embed URLs
    r"(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})",
    # Shorts URLs
    r"(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
    # Live URLs
    r"(?:https?://)?(?:www\.)?youtube\.com/live/([a-zA-Z0-9_-]{11})",
    # Mobile app share URLs
    r"(?:https?://)?m\.youtube\.com/watch\?.*?v=([a-zA-Z0-9_-]{11})",
    # YouTube Music
    r"(?:https?://)?music\.youtube\.com/watch\?.*?v=([a-zA-Z0-9_-]{11})",
]

COMPILED_PATTERNS = [re.compile(p) for p in YOUTUBE_PATTERNS]


def extract_video_id(text: str) -> Optional[str]:
    """
    Extract a YouTube video ID from text.
    Handles standard URLs, short links, embeds, shorts, live streams, mobile, and music links.
    
    Returns the 11-character video ID or None if no valid YouTube link is found.
    """
    for pattern in COMPILED_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1)
    return None


def extract_all_video_ids(text: str) -> list[str]:
    """
    Extract all YouTube video IDs from a block of text.
    Returns a deduplicated list of video IDs in order of appearance.
    """
    seen = set()
    ids = []
    for pattern in COMPILED_PATTERNS:
        for match in pattern.finditer(text):
            vid = match.group(1)
            if vid not in seen:
                seen.add(vid)
                ids.append(vid)
    return ids


def make_url(video_id: str) -> str:
    """Create a canonical YouTube URL from a video ID."""
    return f"https://www.youtube.com/watch?v={video_id}"


def is_youtube_link(text: str) -> bool:
    """Check if text contains a YouTube link."""
    return extract_video_id(text) is not None
