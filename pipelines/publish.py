from __future__ import annotations

import os, json
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv
from utils.io import load_json, load_yaml, ncl_root, ensure_dir, save_json, log_info
from datetime import datetime
import requests

load_dotenv()


def summarize_segment(seg: Dict) -> List[str]:
    txt = seg.get("text", "")
    claims = seg.get("claims", [])[:3]
    bullets = []
    if claims:
        bullets.extend([f"• {c}" for c in claims])
    if not bullets and txt:
        bullets.append(f"• {txt[:200]}…")
    return bullets[:5]


def make_packet(video_meta: Dict, seg: Dict, ranked: Dict) -> Dict:
    packet = {
        "video_id": video_meta["video_id"],
        "channel_id": video_meta.get("channel_id", ""),
        "title": video_meta["title"],
        "publishedAt": video_meta.get("publishedAt", ""),
        "segment_start": seg["start"],
        "segment_end": seg["end"],
        "summary_bullets": summarize_segment(seg),
        "claims": seg.get("claims", [])[:8],
        "routing": list(ranked.keys()),
        "score_by_org": {k: seg.get("score", 0.0) for k in ranked.keys()},
        "clip_paths": seg.get("clip_paths", []),
    }
    return packet


def write_daily_brief(packets: List[Dict]):
    day = datetime.now().strftime("%Y-%m-%d")
    root = ncl_root() / "briefs" / day
    ensure_dir(root)

    # overall brief
    lines = [f"# Daily YouTube Intel Brief — {day}\n"]
    org_groups = {}
    for p in packets:
        for org in p["routing"]:
            org_groups.setdefault(org, []).append(p)

    for org, items in org_groups.items():
        items = sorted(items, key=lambda x: max(x["score_by_org"].values()), reverse=True)
        lines.append(f"\n## {org}\n")
        for it in items[:10]:
            clip_line = ""
            if it["clip_paths"]:
                clip_line = f"\n  - Clip: {it['clip_paths'][0]}"
            bullets = "\n  ".join(it["summary_bullets"])
            lines.append(
                f"- **{it['title']}** ({it['video_id']}) [{it['segment_start']}–{it['segment_end']}s]\n  {bullets}{clip_line}"
            )

    (root / "brief.md").write_text("\n".join(lines), encoding="utf-8")
    # save packets JSON for programmatic consumption
    save_json(root / "packets.json", {"packets": packets})
    log_info(f"Wrote brief to {root / 'brief.md'}")


def create_github_issue(repo_key: str, title: str, body: str):
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        return
    mapping_json = os.getenv("NCC_REPO_MAP_JSON", "{}")
    mapping = json.loads(mapping_json)
    repo = mapping.get(repo_key)
    if not repo:
        return
    url = f"https://api.github.com/repos/{repo}/issues"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
    payload = {"title": title, "body": body}
    r = requests.post(url, headers=headers, json=payload, timeout=20)
    if r.status_code >= 300:
        print("GitHub issue failed:", r.status_code, r.text)


def publish_packets(video_meta: Dict, ranked: Dict, top_k: int = 3) -> List[Dict]:
    """Take top segments across orgs, generate packets, write brief entries, and optionally create GitHub issues."""
    packets = []
    # Build a unified candidate set: top for each org
    org_top = {}
    for org, segs in ranked["ranked"].items():
        org_top[org] = segs[:top_k]

    # unify segments by (start,end)
    uniq = {}
    for org, segs in org_top.items():
        for s in segs:
            key = (int(s["start"]), int(s["end"]))
            if key not in uniq:
                uniq[key] = s.copy()
            uniq[key][f"score_{org}"] = s.get("score", 0.0)

    # finalize packets
    for seg in uniq.values():
        pkt = make_packet(video_meta, seg, ranked["ranked"])
        packets.append(pkt)

    return packets


def maybe_open_issues(packets: List[Dict], routes_path: Path):
    routes = load_yaml(routes_path).get("routes", {})
    for p in packets:
        for org in p["routing"]:
            r = routes.get(org, {})
            if not r:
                continue
            title = f"[Snipper] {p['title']} [{int(p['segment_start'])}-{int(p['segment_end'])}s]"
            body = "\n".join(
                [
                    f"Video: https://www.youtube.com/watch?v={p['video_id']}",
                    f"Window: {p['segment_start']}–{p['segment_end']}s",
                    "Summary:",
                    *(p["summary_bullets"]),
                ]
            )
            create_github_issue(r.get("github_repo", ""), title, body)
