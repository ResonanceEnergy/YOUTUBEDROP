"""
YOUTUBEDROP - YouTube Intelligence Ingestor
==========================================
Downloads, transcribes, and processes YouTube content for the NCL knowledge base.
Uses YouTube Data API v3 for metadata and yt-dlp for downloads.
"""

import json
import logging
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class YouTubeIngestor:
    """
    YouTube content ingestion pipeline.
    Fetch metadata, download audio/video, transcribe, package for NCL.
    """

    def __init__(self, config_path: str = "config/settings.json"):
        self.config = self._load_config(config_path)
        self.api_key = self.config.get("youtube_api_key") or os.getenv("YOUTUBE_API_KEY")
        self.download_dir = Path(self.config.get("download_dir", "downloads"))
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        logger.info("YouTubeIngestor initialized")

    def _load_config(self, config_path: str) -> Dict:
        try:
            with open(config_path, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "youtube_api_key": os.getenv("YOUTUBE_API_KEY"),
                "download_dir": "downloads",
                "max_video_duration": 3600,
                "supported_formats": ["mp4", "webm"],
                "ncl_integration": True,
            }

    # -------------------------------------------------------------------------
    # SEARCH
    # -------------------------------------------------------------------------

    def search_videos(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search YouTube using Data API v3."""
        if not self.api_key:
            logger.warning("No YOUTUBE_API_KEY — returning empty results")
            return []

        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": max_results,
            "key": self.api_key,
        }

        try:
            resp = self.session.get(url, params=params, timeout=10)
            resp.raise_for_status()
            items = resp.json().get("items", [])
            results = []
            for item in items:
                snippet = item.get("snippet", {})
                results.append({
                    "video_id": item["id"]["videoId"],
                    "title": snippet.get("title", ""),
                    "channel": snippet.get("channelTitle", ""),
                    "published": snippet.get("publishedAt", ""),
                    "description": snippet.get("description", "")[:200],
                    "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}",
                })
            logger.info(f"Found {len(results)} videos for: {query}")
            return results
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    # -------------------------------------------------------------------------
    # METADATA
    # -------------------------------------------------------------------------

    def get_metadata(self, video_id: str) -> Dict:
        """Fetch full video metadata from YouTube Data API."""
        if not self.api_key:
            return self._stub_metadata(video_id)

        url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            "part": "snippet,contentDetails,statistics",
            "id": video_id,
            "key": self.api_key,
        }

        try:
            resp = self.session.get(url, params=params, timeout=10)
            resp.raise_for_status()
            items = resp.json().get("items", [])
            if not items:
                return self._stub_metadata(video_id)

            item = items[0]
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            details = item.get("contentDetails", {})

            return {
                "video_id": video_id,
                "title": snippet.get("title", ""),
                "description": snippet.get("description", ""),
                "channel": snippet.get("channelTitle", ""),
                "channel_id": snippet.get("channelId", ""),
                "published": snippet.get("publishedAt", ""),
                "tags": snippet.get("tags", []),
                "duration": details.get("duration", ""),
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "fetched_at": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"Metadata fetch failed: {e}")
            return self._stub_metadata(video_id)

    def _stub_metadata(self, video_id: str) -> Dict:
        return {
            "video_id": video_id,
            "title": f"Video {video_id}",
            "description": "",
            "channel": "Unknown",
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "fetched_at": datetime.now().isoformat(),
        }

    # -------------------------------------------------------------------------
    # DOWNLOAD
    # -------------------------------------------------------------------------

    def download_audio(self, video_id: str) -> Optional[Path]:
        """Download audio using yt-dlp. Returns path to audio file."""
        output_template = str(self.download_dir / f"{video_id}.%(ext)s")
        cmd = [
            "yt-dlp",
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "0",
            "--output", output_template,
            "--no-playlist",
            "--quiet",
            f"https://www.youtube.com/watch?v={video_id}",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                audio_path = self.download_dir / f"{video_id}.mp3"
                if audio_path.exists():
                    logger.info(f"Downloaded audio: {audio_path}")
                    return audio_path
            logger.error(f"yt-dlp failed: {result.stderr[:200]}")
            return None
        except FileNotFoundError:
            logger.warning("yt-dlp not installed — run: pip install yt-dlp")
            return None
        except subprocess.TimeoutExpired:
            logger.error(f"Download timed out for {video_id}")
            return None

    def download_video(self, video_id: str, quality: str = "720") -> Optional[Path]:
        """Download video using yt-dlp."""
        output_template = str(self.download_dir / f"{video_id}.%(ext)s")
        cmd = [
            "yt-dlp",
            "-f", f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]",
            "--merge-output-format", "mp4",
            "--output", output_template,
            "--no-playlist",
            "--quiet",
            f"https://www.youtube.com/watch?v={video_id}",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode == 0:
                video_path = self.download_dir / f"{video_id}.mp4"
                if video_path.exists():
                    logger.info(f"Downloaded video: {video_path}")
                    return video_path
            logger.error(f"yt-dlp failed: {result.stderr[:200]}")
            return None
        except FileNotFoundError:
            logger.warning("yt-dlp not installed — run: pip install yt-dlp")
            return None

    # -------------------------------------------------------------------------
    # TRANSCRIPTION
    # -------------------------------------------------------------------------

    def transcribe(self, audio_path: Path) -> Optional[str]:
        """Transcribe audio using OpenAI Whisper API."""
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            logger.warning("No OPENAI_API_KEY — skipping transcription")
            return None

        try:
            import openai
            client = openai.OpenAI(api_key=openai_key)
            with open(audio_path, "rb") as f:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    response_format="text",
                )
            logger.info(f"Transcribed: {audio_path.name} ({len(transcript)} chars)")
            return transcript
        except ImportError:
            logger.warning("openai package not installed")
            return None
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return None

    # -------------------------------------------------------------------------
    # FULL PIPELINE
    # -------------------------------------------------------------------------

    def ingest_video(self, video_url: str, download: bool = False, transcribe: bool = False) -> Dict:
        """
        Full ingestion pipeline for a YouTube video.
        Returns structured payload ready for NCL knowledge base.
        """
        video_id = self.extract_video_id(video_url)
        if not video_id:
            raise ValueError(f"Cannot extract video ID from: {video_url}")

        logger.info(f"Ingesting: {video_id}")

        # Fetch metadata
        metadata = self.get_metadata(video_id)
        audio_path = None
        transcription = None

        # Optional download
        if download:
            audio_path = self.download_audio(video_id)

        # Optional transcription
        if transcribe and audio_path:
            transcription = self.transcribe(audio_path)

        # Build NCL payload
        result = {
            "video_id": video_id,
            "metadata": metadata,
            "audio_file": str(audio_path) if audio_path else None,
            "transcription": transcription,
            "ncl_payload": {
                "type": "youtube_content",
                "source": f"https://youtube.com/watch?v={video_id}",
                "title": metadata.get("title", ""),
                "channel": metadata.get("channel", ""),
                "content": transcription or metadata.get("description", ""),
                "tags": metadata.get("tags", []),
                "timestamp": datetime.now().isoformat(),
            },
            "ingested_at": datetime.now().isoformat(),
        }

        logger.info(f"Ingestion complete: {metadata.get('title', video_id)}")
        return result

    @staticmethod
    def extract_video_id(url: str) -> Optional[str]:
        """Extract video ID from any YouTube URL format."""
        patterns = [
            r"(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})",
            r"youtube\.com\/v\/([a-zA-Z0-9_-]{11})",
            r"^([a-zA-Z0-9_-]{11})$",  # bare ID
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
