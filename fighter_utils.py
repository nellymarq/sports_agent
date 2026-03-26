# fighter_utils.py
# Legacy fighter extraction + new unified-schema helpers (Option A)

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import re


# ------------------------------------------------------------
# FighterRecord dataclass — canonical fighter representation
# ------------------------------------------------------------

@dataclass
class FighterRecord:
    canonical_name: str
    division: str
    aliases: List[str] = field(default_factory=list)
    nicknames: List[str] = field(default_factory=list)
    is_champion: bool = False
    ufc_id: Optional[str] = None
    rank: Optional[int] = None
    reach_in: Optional[int] = None
    height_in: Optional[int] = None
    stance: Optional[str] = None
    dob: Optional[str] = None
    record: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# All recognized UFC divisions
DIVISIONS = [
    "mens_heavyweight",
    "mens_light_heavyweight",
    "mens_middleweight",
    "mens_welterweight",
    "mens_lightweight",
    "mens_featherweight",
    "mens_bantamweight",
    "mens_flyweight",
    "womens_strawweight",
    "womens_flyweight",
    "womens_bantamweight",
    "womens_featherweight",
]

_STOPWORDS = {
    "ufc", "mma", "fight", "fights", "fighter", "fighters",
    "main", "event", "card", "title", "bout", "who", "wins",
    "win", "take", "takes", "next", "the", "a", "an", "vs",
    "versus", "vs.", "for", "of", "in", "on", "at",
}


def _normalize(text: str) -> str:
    return (text or "").strip()


def _dedupe_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _extract_from_vs_pattern(text: str) -> List[str]:
    """
    Extract fighters from patterns like:
      - "Who wins Islam Makhachev vs Dustin Poirier?"
      - "Volkanovski vs. Topuria"
    """
    t = text.lower()
    t = t.replace(" vs. ", " vs ").replace(" versus ", " vs ")
    parts = t.split(" vs ")
    if len(parts) != 2:
        return []

    left, right = parts[0], parts[1]

    def _clean_side(side: str) -> str:
        side = re.sub(r"[^\w\s'-]", " ", side)
        side = re.sub(r"\s+", " ", side).strip()
        return side

    left = _clean_side(left)
    right = _clean_side(right)

    if not left or not right:
        return []

    def _to_name(side: str) -> str:
        tokens = [w for w in side.split() if w not in _STOPWORDS]
        if not tokens:
            return ""
        return " ".join(w.capitalize() for w in tokens)

    f1 = _to_name(left)
    f2 = _to_name(right)

    fighters = [f for f in (f1, f2) if f]
    return _dedupe_preserve_order(fighters)


def _extract_capitalized_sequences(original: str) -> List[str]:
    """
    Fallback: extract capitalized name-like sequences:
      - "Islam Makhachev"
      - "Dustin Poirier"
    while skipping obvious stopwords.
    """
    pattern = r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b"
    candidates = re.findall(pattern, original)
    fighters: List[str] = []
    for cand in candidates:
        tokens = cand.split()
        if any(t.lower() in _STOPWORDS for t in tokens):
            continue
        fighters.append(cand.strip())
    return _dedupe_preserve_order(fighters)


def extract_fighters(question: str) -> Tuple[List[str], str]:
    """
    Heuristic fighter extraction, no dependency on event_utils:
      1. Try explicit "X vs Y" patterns
      2. Fallback to capitalized name sequences
    """
    question = _normalize(question)
    if not question:
        return [], "unknown"

    # 1) Strong signal: "X vs Y"
    vs_fighters = _extract_from_vs_pattern(question)
    if vs_fighters:
        return vs_fighters, vs_fighters[0]

    # 2) Fallback: capitalized sequences
    cap_fighters = _extract_capitalized_sequences(question)
    if cap_fighters:
        return cap_fighters, cap_fighters[0]

    return [], "unknown"

# ---------------------------------------------------------------------
# NEW UNIFIED-SCHEMA LAYER (lazy imports to avoid hard dependency on bs4)
# ---------------------------------------------------------------------


def extract_canonical_fighters(question: str) -> Tuple[List[str], str]:
    """
    Unified version:
    - resolves fighter names from the question
    - canonicalizes fighter IDs
    - attaches history summaries via FighterHistoryService
    """
    from data.fighter_history_service import FighterHistoryService

    fighters, primary = extract_fighters(question)
    if not fighters:
        return [], "unknown"

    service = FighterHistoryService()
    canonical_ids = [service.canon.resolve_fighter_id(f) for f in fighters]
    return canonical_ids, canonical_ids[0] if canonical_ids else "unknown"
