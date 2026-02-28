from __future__ import annotations

from typing import Dict, List
from pathlib import Path
from utils.io import artifacts_dir, load_json, load_yaml, data_root, save_json
from utils.text import keyword_hits


def score_segment(seg: Dict, profile: Dict) -> float:
    text = seg.get("text", "")
    score = 0.0
    score += 2.0 * keyword_hits(text, profile.get("keywords", []))
    score += 3.0 * keyword_hits(text, profile.get("entities", []))
    # claims add weight
    score += 1.0 * len(seg.get("claims", []))
    # penalties
    score -= 2.0 * keyword_hits(text, profile.get("penalties", []))
    if profile.get("require_claim_or_metric") and len(seg.get("claims", [])) == 0:
        score -= 3.0
    return score


def rank_video_segments(video_id: str, relevance_path: Path) -> Dict:
    segfile = artifacts_dir(video_id) / "segments.json"
    if not segfile.exists():
        return {}
    segs = load_json(segfile)["segments"]

    profiles = load_yaml(relevance_path).get("profiles", {})
    results = {}
    for org, prof in profiles.items():
        ranked = []
        for s in segs:
            seg_copy = s.copy()
            seg_copy["score"] = score_segment(seg_copy, prof)
            ranked.append(seg_copy)
        ranked.sort(key=lambda x: x["score"], reverse=True)
        results[org] = ranked

    out = {"video_id": video_id, "ranked": results}
    save_json(artifacts_dir(video_id) / "ranked.json", out)
    return out
