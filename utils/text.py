from __future__ import annotations

import re
from typing import List, Dict

SENT_END = re.compile(r"([.!?])")


def normalize_text(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    return s


def split_sentences(text: str) -> List[str]:
    text = normalize_text(text)
    parts = SENT_END.split(text)
    # rebuild with punctuation
    out, buf = [], ""
    for p in parts:
        if SENT_END.match(p):
            buf += p
            out.append(buf.strip())
            buf = ""
        else:
            buf += (" " if buf else "") + p.strip()
    if buf.strip():
        out.append(buf.strip())
    return [s for s in out if s]


def has_numbers(s: str) -> bool:
    return bool(re.search(r"\d", s))


def keyword_hits(s: str, kw: List[str]) -> int:
    s_low = s.lower()
    return sum(1 for k in kw if k.lower() in s_low)


def extract_simple_claims(sentences: List[str]) -> List[str]:
    """Heuristic claim pick: sentences with numbers, verbs like 'will/expect/launch', or strong nouns."""
    claims = []
    for s in sentences:
        if has_numbers(s) or re.search(r"\b(will|expect|launch|announce|report|profit|guidance)\b", s, re.I):
            claims.append(s)
    return claims[:8]
