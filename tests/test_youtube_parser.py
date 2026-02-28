"""Tests for openclaw.youtube_parser — YouTube URL parsing."""
import pytest
from openclaw.youtube_parser import (
    extract_video_id,
    extract_all_video_ids,
    is_youtube_link,
    make_url,
)


# ── extract_video_id ──────────────────────────────────────────────
class TestExtractVideoId:
    @pytest.mark.parametrize(
        "url, expected",
        [
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://www.youtube.com/live/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://m.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://music.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            # With extra params
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=120", "dQw4w9WgXcQ"),
            ("https://youtu.be/dQw4w9WgXcQ?si=abc123", "dQw4w9WgXcQ"),
            # Embedded in text
            ("check this out https://youtu.be/dQw4w9WgXcQ wow", "dQw4w9WgXcQ"),
        ],
    )
    def test_valid_urls(self, url, expected):
        assert extract_video_id(url) == expected

    @pytest.mark.parametrize(
        "text",
        [
            "hello world",
            "https://www.google.com",
            "https://www.youtube.com/channel/UC123",
            "",
        ],
    )
    def test_no_match(self, text):
        assert extract_video_id(text) is None


# ── extract_all_video_ids ─────────────────────────────────────────
class TestExtractAll:
    def test_multiple_ids(self):
        text = "https://youtu.be/abc12345678 and https://youtu.be/xyz98765432"
        ids = extract_all_video_ids(text)
        assert ids == ["abc12345678", "xyz98765432"]

    def test_deduplication(self):
        text = "https://youtu.be/dQw4w9WgXcQ https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        ids = extract_all_video_ids(text)
        assert ids == ["dQw4w9WgXcQ"]

    def test_empty(self):
        assert extract_all_video_ids("no links here") == []


# ── make_url / is_youtube_link ────────────────────────────────────
class TestHelpers:
    def test_make_url(self):
        assert make_url("dQw4w9WgXcQ") == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_is_youtube_link(self):
        assert is_youtube_link("https://youtu.be/dQw4w9WgXcQ")
        assert not is_youtube_link("not a link")
