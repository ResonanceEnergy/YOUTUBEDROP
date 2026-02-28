"""
YouTube Downloader & Metadata Extractor
Uses yt-dlp for downloading and youtube-transcript-api for transcripts.
Integrates with the full YOUTUBEDROP pipeline (ingest → transcript → segment → rank → publish).
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

import yt_dlp

from .config import settings
from .database import Database, DropStatus
from .youtube_parser import make_url

# Add project root to path so pipelines/utils imports work
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

logger = logging.getLogger("openclaw.processor")


class YouTubeProcessor:
    """Processes YouTube videos: downloads metadata, audio/video, transcripts, thumbnails.
    Also runs the full pipeline (segment, rank, publish) when available."""

    def __init__(self, db: Database):
        self.db = db
        self.download_dir = settings.download_dir
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self._semaphore = asyncio.Semaphore(settings.max_concurrent_downloads)

    async def process(self, video_id: str) -> dict:
        """
        Full processing pipeline for a YouTube video.
        1. Fetch metadata
        2. Download audio/video
        3. Fetch transcript
        4. Download thumbnail
        Returns the final drop record.
        """
        async with self._semaphore:
            url = make_url(video_id)
            await self.db.update_drop(video_id, status=DropStatus.DOWNLOADING.value)

            try:
                # Step 1: Extract metadata + download
                info = await self._download(video_id, url)

                # Step 2: Get transcript
                transcript = ""
                if settings.download_transcript:
                    transcript = await self._get_transcript(video_id)

                # Step 3: Update database with all info
                video_dir = self.download_dir / video_id
                await self.db.update_drop(
                    video_id,
                    title=info.get("title", ""),
                    channel=info.get("channel", info.get("uploader", "")),
                    duration=info.get("duration", 0),
                    description=info.get("description", ""),
                    thumbnail_url=info.get("thumbnail", ""),
                    transcript=transcript,
                    tags=json.dumps(info.get("tags", [])),
                    status=DropStatus.COMPLETE.value,
                    file_path=str(video_dir),
                    metadata_json=json.dumps(self._clean_metadata(info)),
                )

                drop = await self.db.get_drop(video_id)
                logger.info(f"Successfully processed: {info.get('title', video_id)}")

                # Step 4: Run the full pipeline (segment → rank → publish)
                await self._run_pipeline(video_id, info)

                return drop

            except Exception as e:
                logger.error(f"Failed to process {video_id}: {e}")
                await self.db.update_drop(
                    video_id,
                    status=DropStatus.FAILED.value,
                    error_message=str(e),
                )
                raise

    async def _download(self, video_id: str, url: str) -> dict:
        """Download video/audio using yt-dlp and return info dict."""
        video_dir = self.download_dir / video_id
        video_dir.mkdir(parents=True, exist_ok=True)

        ydl_opts = {
            "outtmpl": str(video_dir / "%(title)s.%(ext)s"),
            "writeinfojson": True,
            "writethumbnail": settings.download_thumbnail,
            "no_warnings": True,
            "quiet": True,
            "no_color": True,
        }

        if settings.audio_only:
            ydl_opts.update({
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            })
        else:
            ydl_opts["format"] = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"

        if settings.max_duration > 0:
            ydl_opts["match_filter"] = yt_dlp.utils.match_filter_func(
                f"duration <= {settings.max_duration}"
            )

        # Run yt-dlp in a thread to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, self._run_ytdlp, url, ydl_opts)
        return info

    def _run_ytdlp(self, url: str, opts: dict) -> dict:
        """Synchronous yt-dlp download (runs in executor)."""
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return info

    async def _get_transcript(self, video_id: str) -> str:
        """Fetch YouTube transcript/subtitles."""
        try:
            from youtube_transcript_api import YouTubeTranscriptApi

            loop = asyncio.get_event_loop()

            def _fetch():
                # youtube-transcript-api >=1.0 uses instance API
                try:
                    api = YouTubeTranscriptApi()
                    return api.fetch(video_id)
                except TypeError:
                    # Fallback for 0.6.x static API
                    return YouTubeTranscriptApi.get_transcript(video_id)

            transcript_list = await loop.run_in_executor(None, _fetch)
            # Combine transcript segments into full text
            full_text = "\n".join(
                f"[{self._format_time(entry['start'])}] {entry['text']}"
                for entry in transcript_list
            )

            # Save transcript to file
            transcript_file = self.download_dir / video_id / "transcript.txt"
            transcript_file.write_text(full_text, encoding="utf-8")

            return full_text

        except Exception as e:
            logger.warning(f"Could not fetch transcript for {video_id}: {e}")
            return ""

    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format seconds into MM:SS."""
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"

    @staticmethod
    def _clean_metadata(info: dict) -> dict:
        """Extract useful metadata fields, drop the huge raw dict."""
        keys = [
            "id", "title", "channel", "uploader", "upload_date", "duration",
            "view_count", "like_count", "comment_count", "tags", "categories",
            "description", "thumbnail", "webpage_url", "channel_url",
            "channel_id", "availability", "live_status", "language",
        ]
        return {k: info.get(k) for k in keys if info.get(k) is not None}

    async def _run_pipeline(self, video_id: str, info: dict):
        """Run the full YOUTUBEDROP pipeline: ingest → segment → rank → publish.
        This integrates dropped links into the same pipeline as the daily cron job."""
        try:
            from pipelines.ingest import ingest_single_video
            from pipelines.transcripts import fetch_transcript
            from pipelines.segment import build_segments
            from pipelines.rank import rank_video_segments
            from pipelines.publish import publish_packets, write_daily_brief

            loop = asyncio.get_event_loop()

            # Ingest into pipeline data store
            await loop.run_in_executor(
                None, ingest_single_video, video_id, "openclaw-bot"
            )

            # Fetch transcript into pipeline format
            await loop.run_in_executor(None, fetch_transcript, video_id)

            # Segment
            await loop.run_in_executor(None, build_segments, video_id)

            # Rank against relevance profiles
            relevance_path = _project_root / "doctrine" / "relevance_profiles.yaml"
            if relevance_path.exists():
                ranked = await loop.run_in_executor(
                    None, rank_video_segments, video_id, relevance_path
                )
                if ranked:
                    from utils.io import load_json, data_root
                    meta_path = data_root() / "videos" / video_id / "metadata.json"
                    if meta_path.exists():
                        meta = load_json(meta_path)
                        pkts = publish_packets(meta, ranked, top_k=2)
                        write_daily_brief(pkts)

            logger.info(f"Pipeline complete for {video_id}")

        except ImportError as e:
            logger.debug(f"Pipeline modules not available, skipping: {e}")
        except Exception as e:
            logger.warning(f"Pipeline post-processing failed for {video_id}: {e}")
