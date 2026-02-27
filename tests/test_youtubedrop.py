"""
YOUTUBEDROP Tests
==================
"""
import json
import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# ─── Ingestor ────────────────────────────────────────────────────────────────

class TestYouTubeIngestor:
    def setup_method(self):
        from ingestor import YouTubeIngestor
        self.ingestor = YouTubeIngestor()

    def test_extract_video_id_watch_url(self):
        from ingestor import YouTubeIngestor
        vid = YouTubeIngestor.extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert vid == "dQw4w9WgXcQ"

    def test_extract_video_id_short_url(self):
        from ingestor import YouTubeIngestor
        vid = YouTubeIngestor.extract_video_id("https://youtu.be/dQw4w9WgXcQ")
        assert vid == "dQw4w9WgXcQ"

    def test_extract_video_id_bare(self):
        from ingestor import YouTubeIngestor
        vid = YouTubeIngestor.extract_video_id("dQw4w9WgXcQ")
        assert vid == "dQw4w9WgXcQ"

    def test_extract_video_id_invalid(self):
        from ingestor import YouTubeIngestor
        vid = YouTubeIngestor.extract_video_id("https://notayoutube.com/video")
        assert vid is None

    def test_ingest_no_api_key(self):
        """Ingest without API key should still return stub metadata."""
        result = self.ingestor.ingest_video("https://youtu.be/dQw4w9WgXcQ")
        assert result["video_id"] == "dQw4w9WgXcQ"
        assert "metadata" in result
        assert "ncl_payload" in result
        assert result["ncl_payload"]["type"] == "youtube_content"

    def test_search_no_api_key(self):
        """Search without API key returns empty list gracefully."""
        self.ingestor.api_key = None
        results = self.ingestor.search_videos("test query")
        assert isinstance(results, list)
        assert len(results) == 0


# ─── Script Generator ────────────────────────────────────────────────────────

class TestScriptGenerator:
    def test_init(self):
        from script_generator import ScriptGenerator
        gen = ScriptGenerator()
        assert gen is not None

    def test_generate_no_keys(self):
        """Without API keys, generation returns None gracefully."""
        from script_generator import ScriptGenerator
        gen = ScriptGenerator()
        gen._anthropic_key = None
        gen._openai_key = None
        result = gen.generate("test topic")
        assert result is None

    @patch("script_generator.ScriptGenerator._generate_anthropic")
    def test_generate_calls_anthropic(self, mock_gen):
        from script_generator import ScriptGenerator
        mock_gen.return_value = "[HOOK]\nTest script content"
        gen = ScriptGenerator(provider="anthropic")
        gen._anthropic_key = "fake_key"
        result = gen.generate("Tesla stock analysis")
        mock_gen.assert_called_once()
        assert result == "[HOOK]\nTest script content"


# ─── Upload Manager ──────────────────────────────────────────────────────────

class TestUploadManager:
    def test_init(self):
        from upload_manager import UploadManager
        mgr = UploadManager()
        assert mgr is not None

    def test_upload_missing_file(self):
        from upload_manager import UploadManager
        mgr = UploadManager()
        result = mgr.upload("/nonexistent/video.mp4", title="Test", description="Test")
        assert result is None
