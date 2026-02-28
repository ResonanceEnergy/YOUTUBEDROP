"""Tests for pipelines.segment — transcript segmentation (uses tmp files)."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch
from pipelines.segment import build_segments


@pytest.fixture
def mock_artifacts(tmp_path):
    """Create a fake artifacts directory with a transcript."""
    transcript = {
        "video_id": "testvid123",
        "entries": [
            {"start": 0.0, "duration": 5.0, "text": "Hello world."},
            {"start": 5.0, "duration": 4.0, "text": "This is a test."},
            {"start": 9.0, "duration": 3.0, "text": "Revenue was $10 billion."},
            # Gap > 8s triggers new segment
            {"start": 25.0, "duration": 5.0, "text": "New topic here."},
            {"start": 30.0, "duration": 4.0, "text": "They will launch soon."},
        ],
    }
    vid_dir = tmp_path / "testvid123"
    vid_dir.mkdir()
    (vid_dir / "transcript.json").write_text(json.dumps(transcript))
    return tmp_path


def test_build_segments(mock_artifacts):
    with patch("pipelines.segment.artifacts_dir", return_value=mock_artifacts / "testvid123"):
        segs = build_segments("testvid123")

    # Should produce 2 segments due to the >8s gap
    assert len(segs) == 2
    assert segs[0]["start"] == 0.0
    assert "Hello world" in segs[0]["text"]
    assert segs[1]["start"] == 25.0


def test_build_segments_no_transcript(tmp_path):
    with patch("pipelines.segment.artifacts_dir", return_value=tmp_path / "noexist"):
        segs = build_segments("noexist")
    assert segs == []


def test_segments_have_claims(mock_artifacts):
    with patch("pipelines.segment.artifacts_dir", return_value=mock_artifacts / "testvid123"):
        segs = build_segments("testvid123")

    # First segment has "$10 billion" → should extract a claim
    assert "claims" in segs[0]
    assert any("$10 billion" in c for c in segs[0]["claims"])
