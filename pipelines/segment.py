from __future__ import annotations

from typing import Dict, List, Tuple
from utils.io import artifacts_dir, load_json, save_json, log_info
from utils.text import split_sentences, extract_simple_claims


def build_segments(video_id: str, max_gap: float = 8.0, max_len: float = 120.0) -> List[Dict]:
    """Greedy segmentation: join transcript entries until punctuation/pauses/limits."""
    tpath = artifacts_dir(video_id) / "transcript.json"
    if not tpath.exists():
        return []
    trans = load_json(tpath).get("entries", [])

    segs, cur = [], {"start": None, "end": None, "text": []}
    last_end = 0.0

    def flush():
        nonlocal cur, segs
        if cur["start"] is None:
            return
        text = " ".join(cur["text"]).strip()
        if text:
            segs.append({"start": cur["start"], "end": cur["end"], "text": text})
        cur = {"start": None, "end": None, "text": []}

    for e in trans:
        start = float(e.get("start", 0.0))
        dur = float(e.get("duration", 0.0))
        end = start + dur
        chunk = e.get("text", "").replace("\n", " ").strip()

        if cur["start"] is None:
            cur["start"] = start

        # boundaries: long pauses or segment too long
        if start - last_end > max_gap or (end - cur["start"]) > max_len:
            flush()
            cur["start"] = start

        cur["end"] = end
        cur["text"].append(chunk)
        last_end = end

    flush()

    # annotate sentences & claims
    for s in segs:
        sents = split_sentences(s["text"])
        s["sentences"] = sents
        s["claims"] = extract_simple_claims(sents)

    save_json(artifacts_dir(video_id) / "segments.json", {"video_id": video_id, "segments": segs})
    log_info(f"Built {len(segs)} segments for {video_id}")
    return segs


if __name__ == "__main__":
    # for manual test, call from run_daily orchestrator
    pass
