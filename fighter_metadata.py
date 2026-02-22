# -*- coding: utf-8 -*-
# fighter_metadata.py
# Final-form metadata API for UFC fighters.

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple, List

from fighter_utils import FighterRecord, _normalize
from data.compiled.fighter_roster_data import (
    DIVISION_ROSTER,
    NICKNAME_MAP,
    ALIAS_MAP,
    LAST_NAME_INDEX,
)


# ------------------------------------------------------------
# Internal resolution helpers
# ------------------------------------------------------------

def _resolve_fighter(name: str) -> Optional[FighterRecord]:
    """
    Resolve a user-supplied name, nickname, or partial into a FighterRecord.
    Resolution order:
      1) exact nickname match
      2) exact alias match
      3) last-name index
      4) full scan of DIVISION_ROSTER (fallback)
    """
    if not name:
        return None

    norm = _normalize(name)

    # 1) Nickname map
    if norm in NICKNAME_MAP:
        return NICKNAME_MAP[norm]

    # 2) Alias map
    if norm in ALIAS_MAP:
        return ALIAS_MAP[norm]

    # 3) Last-name index
    if norm in LAST_NAME_INDEX:
        fighters = LAST_NAME_INDEX[norm]
        if len(fighters) == 1:
            return fighters[0]
        # If ambiguous, prefer champions, then most aliases
        champs = [f for f in fighters if f.is_champion]
        if len(champs) == 1:
            return champs[0]
        return sorted(fighters, key=lambda f: len(f.aliases), reverse=True)[0]

    # 4) Fallback: scan all fighters
    candidates: List[FighterRecord] = []
    for fighters in DIVISION_ROSTER.values():
        for f in fighters:
            if norm == _normalize(f.canonical_name):
                candidates.append(f)

    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    champs = [f for f in candidates if f.is_champion]
    if len(champs) == 1:
        return champs[0]

    return sorted(candidates, key=lambda f: len(f.aliases), reverse=True)[0]


# Public: keep this name for backward compatibility
def get_fighter(name: str) -> Optional[FighterRecord]:
    return _resolve_fighter(name)


# ------------------------------------------------------------
# Parsing & derived attributes
# ------------------------------------------------------------

def _parse_record(record: Optional[str]) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """
    Parse a record string like '20–5–1' or '18-6' into (wins, losses, draws).
    Returns (None, None, None) if parsing fails.
    """
    if not record:
        return None, None, None

    # Normalize dashes
    s = record.replace("–", "-").replace("—", "-").strip()
    # Strip extra text like "(1 NC)"
    s = s.split(" ")[0]
    parts = s.split("-")
    if len(parts) < 2:
        return None, None, None

    try:
        wins = int(parts[0])
        losses = int(parts[1])
        draws = int(parts[2]) if len(parts) >= 3 else 0
        return wins, losses, draws
    except ValueError:
        return None, None, None


def _age_tier(age_str: Optional[str]) -> Optional[str]:
    """
    Map age to a coarse tier: 'young', 'prime', 'veteran'.
    """
    if not age_str:
        return None
    try:
        age = int(age_str)
    except ValueError:
        return None

    if age < 28:
        return "young"
    if age <= 33:
        return "prime"
    return "veteran"


def _experience_tier(record: Optional[str]) -> Optional[str]:
    """
    Map record to experience tier based on total fights.
    """
    wins, losses, draws = _parse_record(record)
    if wins is None or losses is None or draws is None:
        return None
    total = wins + losses + draws
    if total < 10:
        return "low"
    if total < 20:
        return "medium"
    return "high"


def _frame_length(height_in: Optional[int], reach_in: Optional[int]) -> Optional[int]:
    """
    Simple derived 'frame length' metric: height + reach (in inches).
    """
    if height_in is None or reach_in is None:
        return None
    return height_in + reach_in


# ------------------------------------------------------------
# Core API: profile, physical, competitive, metadata
# ------------------------------------------------------------

def get_profile(name: str) -> Optional[Dict[str, Any]]:
    """
    High-level profile combining identity, physical, and competitive info.
    """
    fighter = _resolve_fighter(name)
    if not fighter:
        return None

    physical = get_physical(name)
    competitive = get_competitive(name)

    return {
        "canonical_name": fighter.canonical_name,
        "division": fighter.division,
        "is_champion": fighter.is_champion,
        "aliases": list(fighter.aliases),
        "nicknames": list(fighter.nicknames),
        "country": fighter.metadata.get("country"),
        "age": fighter.metadata.get("age"),
        "physical": physical,
        "competitive": competitive,
    }


def get_physical(name: str) -> Optional[Dict[str, Any]]:
    """
    Physical attributes only: height, reach, stance, age, country, frame length.
    """
    fighter = _resolve_fighter(name)
    if not fighter:
        return None

    height_in = fighter.height_in
    reach_in = fighter.reach_in
    age_str = fighter.metadata.get("age")

    return {
        "height_in": height_in,
        "reach_in": reach_in,
        "stance": fighter.stance,
        "country": fighter.metadata.get("country"),
        "age": age_str,
        "age_tier": _age_tier(age_str),
        "frame_length": _frame_length(height_in, reach_in),
    }


def get_competitive(name: str) -> Optional[Dict[str, Any]]:
    """
    Competitive attributes only: record, parsed record, experience tier, champion status.
    """
    fighter = _resolve_fighter(name)
    if not fighter:
        return None

    wins, losses, draws = _parse_record(fighter.record)

    return {
        "record": fighter.record,
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "experience_tier": _experience_tier(fighter.record),
        "is_champion": fighter.is_champion,
        "division": fighter.division,
    }


def get_metadata(name: str) -> Optional[Dict[str, Any]]:
    """
    Unified metadata view: identity + physical + competitive.
    """
    fighter = _resolve_fighter(name)
    if not fighter:
        return None

    physical = get_physical(name)
    competitive = get_competitive(name)

    return {
        "canonical_name": fighter.canonical_name,
        "division": fighter.division,
        "is_champion": fighter.is_champion,
        "aliases": list(fighter.aliases),
        "nicknames": list(fighter.nicknames),
        "country": fighter.metadata.get("country"),
        "age": fighter.metadata.get("age"),
        "record": fighter.record,
        "physical": physical,
        "competitive": competitive,
    }


# ------------------------------------------------------------
# Simple convenience accessors (backward compatible)
# ------------------------------------------------------------

def get_country(name: str) -> Optional[str]:
    fighter = _resolve_fighter(name)
    if not fighter:
        return None
    return fighter.metadata.get("country")


def get_height(name: str) -> Optional[int]:
    fighter = _resolve_fighter(name)
    if not fighter:
        return None
    return fighter.height_in


def get_age(name: str) -> Optional[str]:
    fighter = _resolve_fighter(name)
    if not fighter:
        return None
    return fighter.metadata.get("age")


def get_division(name: str) -> Optional[str]:
    fighter = _resolve_fighter(name)
    if not fighter:
        return None
    return fighter.division


def get_champion_status(name: str) -> Optional[bool]:
    fighter = _resolve_fighter(name)
    if not fighter:
        return None
    return fighter.is_champion


def get_record(name: str) -> Optional[str]:
    fighter = _resolve_fighter(name)
    if not fighter:
        return None
    return fighter.record
