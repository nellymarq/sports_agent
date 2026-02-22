# fighter_utils.py

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Iterable

DIVISIONS: List[str] = [
    "mens_flyweight",
    "mens_bantamweight",
    "mens_featherweight",
    "mens_lightweight",
    "mens_welterweight",
    "mens_middleweight",
    "mens_light_heavyweight",
    "mens_heavyweight",
    "womens_strawweight",
    "womens_flyweight",
    "womens_bantamweight",
    "womens_featherweight",
]

DIVISION_LABELS: Dict[str, str] = {
    "mens_flyweight": "Men's Flyweight",
    "mens_bantamweight": "Men's Bantamweight",
    "mens_featherweight": "Men's Featherweight",
    "mens_lightweight": "Men's Lightweight",
    "mens_welterweight": "Men's Welterweight",
    "mens_middleweight": "Men's Middleweight",
    "mens_light_heavyweight": "Men's Light Heavyweight",
    "mens_heavyweight": "Men's Heavyweight",
    "womens_strawweight": "Women's Strawweight",
    "womens_flyweight": "Women's Flyweight",
    "womens_bantamweight": "Women's Bantamweight",
    "womens_featherweight": "Women's Featherweight",
}


@dataclass(frozen=True)
class FighterRecord:
    canonical_name: str
    division: str
    aliases: List[str]
    nicknames: List[str]
    is_champion: bool = False
    ufc_id: Optional[str] = None
    rank: Optional[int] = None
    reach_in: Optional[int] = None
    height_in: Optional[int] = None
    stance: Optional[str] = None
    dob: Optional[str] = None
    record: Optional[str] = None
    metadata: Optional[dict] = None


try:
    from data.compiled.fighter_roster_data import (
        DIVISION_ROSTER,
        NICKNAME_MAP,
        ALIAS_MAP,
        LAST_NAME_INDEX,
    )
except Exception:
    DIVISION_ROSTER = {d: [] for d in DIVISIONS}
    NICKNAME_MAP = {}
    ALIAS_MAP = {}
    LAST_NAME_INDEX = {}


def _strip_accents(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


def _normalize(text: str) -> str:
    return _strip_accents(text).strip().lower()


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z']+", _strip_accents(text).lower())


def _simple_ratio(a: str, b: str) -> float:
    a = _normalize(a)
    b = _normalize(b)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    set_a = set(a)
    set_b = set(b)
    inter = len(set_a & set_b)
    union = len(set_a | set_b) or 1
    return inter / union


def _best_match(
    query: str,
    candidates: Iterable[FighterRecord],
    min_score: float = 0.55,
) -> Optional[FighterRecord]:
    query_norm = _normalize(query)
    best = None
    best_score = 0.0
    for fighter in candidates:
        fields = [fighter.canonical_name] + fighter.aliases + fighter.nicknames
        for field in fields:
            score = _simple_ratio(query_norm, field)
            if score > best_score:
                best_score = score
                best = fighter
    if best and best_score >= min_score:
        return best
    return None


def _extract_name_tokens_from_text(text: str) -> List[str]:
    cleaned = (
        text.replace("?", " ")
        .replace(",", " ")
        .replace(";", " ")
        .replace("vs.", " vs ")
        .replace("versus", " vs ")
    )
    cleaned = re.sub(r"\s+", " ", cleaned)
    parts = re.split(r"\bvs\b|\bor\b|\band\b", cleaned, flags=re.IGNORECASE)
    tokens = []
    for part in parts:
        words = _tokenize(part)
        if words:
            tokens.append(words[-1])
    seen = set()
    unique = []
    for t in tokens:
        nt = _normalize(t)
        if nt not in seen:
            seen.add(nt)
            unique.append(t)
    return unique


def _all_fighters() -> List[FighterRecord]:
    fighters = []
    for div in DIVISION_ROSTER.values():
        fighters.extend(div)
    return fighters


def _lookup_by_last_name(last_name: str) -> List[FighterRecord]:
    return LAST_NAME_INDEX.get(_normalize(last_name), [])


def _match_token_to_fighter(token: str) -> Optional[FighterRecord]:
    norm = _normalize(token)
    if not norm:
        return None
    if norm in NICKNAME_MAP:
        return NICKNAME_MAP[norm]
    if norm in ALIAS_MAP:
        return ALIAS_MAP[norm]
    last_name_matches = _lookup_by_last_name(norm)
    if len(last_name_matches) == 1:
        return last_name_matches[0]
    elif len(last_name_matches) > 1:
        best = _best_match(token, last_name_matches)
        if best:
            return best
    return _best_match(token, _all_fighters())


def _dedupe_fighters(fighters: List[FighterRecord]) -> List[FighterRecord]:
    seen = set()
    unique = []
    for f in fighters:
        key = _normalize(f.canonical_name)
        if key not in seen:
            seen.add(key)
            unique.append(f)
    return unique


def extract_fighters(text: str) -> Tuple[List[str], str]:
    if not text or not text.strip():
        return [], "unknown"
    tokens = _extract_name_tokens_from_text(text)
    matched = []
    for token in tokens:
        fighter = _match_token_to_fighter(token)
        if fighter:
            matched.append(fighter)
    matched = _dedupe_fighters(matched)
    if not matched:
        return [], "unknown"
    fighters = [f.canonical_name for f in matched]
    primary = fighters[0]
    return fighters, primary


def extract_fighter_name(text: str) -> str:
    _, primary = extract_fighters(text)
    return primary
