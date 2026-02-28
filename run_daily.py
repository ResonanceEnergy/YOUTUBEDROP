from __future__ import annotations

import argparse, json
from pathlib import Path

from dotenv import load_dotenv
from utils.io import load_json, load_yaml, data_root, log_info, log_warn
from pipelines.ingest import ingest_new
from pipelines.transcripts import fetch_transcript, download_video
from pipelines.segment import build_segments
from pipelines.rank import rank_video_segments
from pipelines.clip import clip_segment
from pipelines.publish import publish_packets, write_daily_brief, maybe_open_issues
import os

load_dotenv()


def process_video(
    video_id: str, relevance_path: Path, routes_path: Path, portrait: bool = False
):
    meta_path = data_root() / "videos" / video_id / "metadata.json"
    if not meta_path.exists():
        log_warn(f"No metadata for {video_id}, skipping")
        return
    meta = load_json(meta_path)

    # transcript + download
    t = fetch_transcript(video_id)
    download_video(video_id)

    # segments
    segs = build_segments(video_id)

    # rank
    ranked = rank_video_segments(video_id, relevance_path)
    if not ranked or "ranked" not in ranked:
        log_warn(f"No ranked output for {video_id}, skipping")
        return

    # clip top segments per org (news + insight)
    profiles_data = load_yaml(relevance_path)
    daily_top_k = int(os.getenv("DAILY_TOP_K", "10"))

    for org, org_segs in ranked["ranked"].items():
        if not org_segs:
            continue
        max_news = profiles_data["profiles"][org].get("max_clip_seconds_news", 60)
        max_ins = profiles_data["profiles"][org].get("max_clip_seconds_insight", 180)

        # Take first 1 as news, next 1 as insight (if longer window)
        chosen = []
        if len(org_segs) > 0:
            chosen.append(("news", org_segs[0], max_news))
        if len(org_segs) > 1:
            chosen.append(("insight", org_segs[1], max_ins))

        for kind, s, mx in chosen:
            clip_path = clip_segment(video_id, s, max_seconds=mx, portrait=portrait)
            s.setdefault("clip_paths", []).append(str(clip_path))

    # publish packets & brief
    pkts = publish_packets(meta, ranked, top_k=daily_top_k)
    write_daily_brief(pkts)
    maybe_open_issues(pkts, routes_path)


def main():
    ap = argparse.ArgumentParser(description="YouTube Snipper Orchestrator")
    ap.add_argument("--relevance", default="doctrine/relevance_profiles.yaml")
    ap.add_argument("--routes", default="doctrine/org_routes.yaml")
    ap.add_argument("--portrait", action="store_true", help="Create 9:16 clips too")
    ap.add_argument(
        "--mode", choices=["ingest", "process_new", "all"], default="all"
    )
    args = ap.parse_args()

    if args.mode in ("ingest", "all"):
        ingest_new()

    if args.mode in ("process_new", "all"):
        seen = (
            load_json(data_root() / "index" / "seen.json")
            if (data_root() / "index" / "seen.json").exists()
            else {}
        )
        if not seen:
            log_warn("No videos to process. Run ingest mode first.")
            return
        for vid in seen.keys():
            try:
                process_video(
                    vid,
                    Path(args.relevance),
                    Path(args.routes),
                    portrait=args.portrait,
                )
            except Exception as e:
                log_warn(f"Failed to process {vid}, continuing: {e}")


if __name__ == "__main__":
    main()
