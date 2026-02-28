"""
YOUTUBEDROP Configuration
Loads settings from .env and provides typed config access.
"""

import os
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseModel):
    """Application settings loaded from environment variables."""

    # Telegram
    telegram_bot_token: str = Field(default="", description="Telegram Bot API token")

    # Discord
    discord_bot_token: str = Field(default="", description="Discord Bot token")

    # YouTube
    youtube_api_key: str = Field(default="", description="YouTube Data API key (optional)")

    # Storage
    download_dir: Path = Field(default=Path("./downloads"), description="Download directory")
    database_url: str = Field(default="sqlite:///./youtubedrop.db", description="Database URL")

    # Agent settings
    max_concurrent_downloads: int = Field(default=3, ge=1, le=10)
    audio_only: bool = Field(default=True)
    download_transcript: bool = Field(default=True)
    download_thumbnail: bool = Field(default=True)
    max_duration: int = Field(default=0, ge=0, description="Max video duration in seconds, 0=no limit")

    # Logging
    log_level: str = Field(default="INFO")

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables."""
        return cls(
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            discord_bot_token=os.getenv("DISCORD_BOT_TOKEN", ""),
            youtube_api_key=os.getenv("YOUTUBE_API_KEY", ""),
            download_dir=Path(os.getenv("DOWNLOAD_DIR", "./downloads")),
            database_url=os.getenv("DATABASE_URL", "sqlite:///./youtubedrop.db"),
            max_concurrent_downloads=int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "3")),
            audio_only=os.getenv("AUDIO_ONLY", "true").lower() == "true",
            download_transcript=os.getenv("DOWNLOAD_TRANSCRIPT", "true").lower() == "true",
            download_thumbnail=os.getenv("DOWNLOAD_THUMBNAIL", "true").lower() == "true",
            max_duration=int(os.getenv("MAX_DURATION", "0")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )


# Global settings instance
settings = Settings.from_env()
