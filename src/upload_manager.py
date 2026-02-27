"""
YOUTUBEDROP - Upload Manager
==============================
Uploads videos to YouTube via Data API v3.
Handles authentication, metadata, and upload status.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class UploadManager:
    """
    Manages YouTube video uploads via Data API v3.
    Requires OAuth2 credentials (not just an API key).
    """

    def __init__(self, credentials_file: str = "config/oauth_credentials.json"):
        self.credentials_file = Path(credentials_file)
        self._service = None
        logger.info("UploadManager initialized")

    def _get_service(self):
        """Build authenticated YouTube service."""
        if self._service:
            return self._service

        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
            from google.auth.transport.requests import Request
            import pickle

            SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
            token_file = Path("config/token.pickle")
            creds = None

            if token_file.exists():
                with open(token_file, "rb") as f:
                    import pickle
                    creds = pickle.load(f)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not self.credentials_file.exists():
                        raise FileNotFoundError(
                            f"OAuth credentials not found: {self.credentials_file}\n"
                            "Download from Google Cloud Console → APIs & Services → Credentials"
                        )
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.credentials_file), SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                with open(token_file, "wb") as f:
                    pickle.dump(creds, f)

            self._service = build("youtube", "v3", credentials=creds)
            logger.info("YouTube service authenticated")
            return self._service

        except ImportError:
            logger.error(
                "Missing packages. Run: pip install google-api-python-client "
                "google-auth-oauthlib google-auth-httplib2"
            )
            return None

    def upload(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list = None,
        category_id: str = "22",  # People & Blogs
        privacy: str = "private",  # Start private, review before publishing
    ) -> Optional[str]:
        """
        Upload a video to YouTube.
        Returns the YouTube video ID on success, None on failure.
        privacy: "private" | "unlisted" | "public"
        """
        service = self._get_service()
        if not service:
            return None

        video_path = Path(video_path)
        if not video_path.exists():
            logger.error(f"Video file not found: {video_path}")
            return None

        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": tags or [],
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
            },
        }

        try:
            from googleapiclient.http import MediaFileUpload

            media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)
            request = service.videos().insert(
                part=",".join(body.keys()),
                body=body,
                media_body=media,
            )

            logger.info(f"Uploading: {title}")
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    pct = int(status.progress() * 100)
                    logger.info(f"  Upload progress: {pct}%")

            video_id = response["id"]
            url = f"https://youtube.com/watch?v={video_id}"
            logger.info(f"Upload complete: {url}")
            return video_id

        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return None

    def set_thumbnail(self, video_id: str, thumbnail_path: str) -> bool:
        """Set custom thumbnail for uploaded video."""
        service = self._get_service()
        if not service:
            return False

        try:
            from googleapiclient.http import MediaFileUpload
            media = MediaFileUpload(thumbnail_path)
            service.thumbnails().set(videoId=video_id, media_body=media).execute()
            logger.info(f"Thumbnail set for {video_id}")
            return True
        except Exception as e:
            logger.error(f"Thumbnail upload failed: {e}")
            return False

    def get_upload_status(self, video_id: str) -> dict:
        """Get processing status of an uploaded video."""
        service = self._get_service()
        if not service:
            return {}

        try:
            resp = service.videos().list(
                part="status,processingDetails",
                id=video_id,
            ).execute()
            items = resp.get("items", [])
            if items:
                return {
                    "video_id": video_id,
                    "status": items[0].get("status", {}),
                    "processing": items[0].get("processingDetails", {}),
                    "url": f"https://youtube.com/watch?v={video_id}",
                }
            return {}
        except Exception as e:
            logger.error(f"Status check failed: {e}")
            return {}
