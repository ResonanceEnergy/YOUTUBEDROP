"""
Database layer for YOUTUBEDROP.
Tracks all ingested YouTube links, metadata, and processing status.
"""

import aiosqlite
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from enum import Enum


class DropStatus(str, Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"


class Database:
    """Async SQLite database for tracking YouTube drops."""

    def __init__(self, db_path: str = "youtubedrop.db"):
        # Parse sqlite:/// prefix
        if db_path.startswith("sqlite:///"):
            db_path = db_path[len("sqlite:///"):]
        self.db_path = db_path
        self._db: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """Initialize database connection and create tables."""
        self._db = await aiosqlite.connect(self.db_path)
        self._db.row_factory = aiosqlite.Row
        await self._create_tables()

    async def close(self):
        """Close database connection."""
        if self._db:
            await self._db.close()

    async def _create_tables(self):
        """Create tables if they don't exist."""
        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS drops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT NOT NULL,
                url TEXT NOT NULL,
                title TEXT DEFAULT '',
                channel TEXT DEFAULT '',
                duration INTEGER DEFAULT 0,
                description TEXT DEFAULT '',
                thumbnail_url TEXT DEFAULT '',
                transcript TEXT DEFAULT '',
                tags TEXT DEFAULT '[]',
                status TEXT DEFAULT 'pending',
                source TEXT DEFAULT '',
                source_user TEXT DEFAULT '',
                source_platform TEXT DEFAULT '',
                file_path TEXT DEFAULT '',
                error_message TEXT DEFAULT '',
                metadata_json TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(video_id)
            );

            CREATE INDEX IF NOT EXISTS idx_drops_status ON drops(status);
            CREATE INDEX IF NOT EXISTS idx_drops_video_id ON drops(video_id);
            CREATE INDEX IF NOT EXISTS idx_drops_created_at ON drops(created_at);
        """)
        await self._db.commit()

    async def add_drop(
        self,
        video_id: str,
        url: str,
        source: str = "",
        source_user: str = "",
        source_platform: str = "",
    ) -> Optional[int]:
        """Add a new YouTube drop. Returns the drop ID, or None if already exists."""
        now = datetime.now(timezone.utc).isoformat()
        try:
            cursor = await self._db.execute(
                """
                INSERT INTO drops (video_id, url, source, source_user, source_platform, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (video_id, url, source, source_user, source_platform, now, now),
            )
            await self._db.commit()
            return cursor.lastrowid
        except aiosqlite.IntegrityError:
            # Already exists
            return None

    async def update_drop(self, video_id: str, **kwargs):
        """Update a drop's fields."""
        kwargs["updated_at"] = datetime.now(timezone.utc).isoformat()
        set_clauses = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [video_id]
        await self._db.execute(
            f"UPDATE drops SET {set_clauses} WHERE video_id = ?",
            values,
        )
        await self._db.commit()

    async def get_drop(self, video_id: str) -> Optional[dict]:
        """Get a drop by video ID."""
        cursor = await self._db.execute(
            "SELECT * FROM drops WHERE video_id = ?", (video_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_recent_drops(self, limit: int = 20) -> list[dict]:
        """Get the most recent drops."""
        cursor = await self._db.execute(
            "SELECT * FROM drops ORDER BY created_at DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_drops_by_status(self, status: DropStatus) -> list[dict]:
        """Get drops by processing status."""
        cursor = await self._db.execute(
            "SELECT * FROM drops WHERE status = ? ORDER BY created_at DESC",
            (status.value,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_stats(self) -> dict:
        """Get drop statistics."""
        cursor = await self._db.execute(
            "SELECT status, COUNT(*) as count FROM drops GROUP BY status"
        )
        rows = await cursor.fetchall()
        stats = {row["status"]: row["count"] for row in rows}
        cursor2 = await self._db.execute("SELECT COUNT(*) as total FROM drops")
        row2 = await cursor2.fetchone()
        stats["total"] = row2["total"]
        return stats
