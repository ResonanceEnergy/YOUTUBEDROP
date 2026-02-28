from __future__ import annotations

from pathlib import Path
from typing import Dict
import subprocess, json, os, tempfile

from utils.io import artifacts_dir, ensure_dir


def _write_srt_for_segment(seg: Dict, out_srt: Path):
    """Create minimal SRT for the segment using its sentences."""
    # Simple single block SRT to keep it readable
    text = seg.get("text", "")
    s = "1\n00:00:00,000 --> 00:{:02d}:{:02d},000\n{}\n".format(
        int((seg["end"] - seg["start"]) // 60),
        int((seg["end"] - seg["start"]) % 60),
        text,
    )
    out_srt.write_text(s, encoding="utf-8")


def clip_segment(
    video_id: str, seg: Dict, max_seconds: int, portrait: bool = False
) -> Path:
    """Clip with ffmpeg, burn simple subtitle."""
    video_path = artifacts_dir(video_id) / f"{video_id}.mp4"
    out_dir = artifacts_dir(video_id) / "clips"
    ensure_dir(out_dir)

    start = max(seg["start"], 0.0)
    duration = min(seg["end"] - seg["start"], max_seconds)
    base = f"{video_id}_{int(start)}_{int(duration)}"
    out_mp4 = out_dir / f"{base}{'_9x16' if portrait else ''}.mp4"

    # build temp SRT
    with tempfile.TemporaryDirectory() as td:
        srt_path = Path(td) / f"{base}.srt"
        _write_srt_for_segment(seg, srt_path)

        vf = []
        if portrait:
            vf.append("scale=1080:1920:force_original_aspect_ratio=decrease")
            vf.append("pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black")
        vf.append(f"subtitles='{srt_path.as_posix()}'")
        vf_arg = ",".join(vf)

        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            str(start),
            "-t",
            str(duration),
            "-i",
            str(video_path),
            "-vf",
            vf_arg,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            str(out_mp4),
        ]
        subprocess.run(cmd, check=True)

    return out_mp4
