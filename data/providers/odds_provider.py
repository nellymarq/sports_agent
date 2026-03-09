# data/providers/odds_provider.py
# Async odds provider: stubs wrapped in async interface.

from __future__ import annotations
from typing import Dict, Any, Optional


def _fetch_draftkings_odds(event_id: str) -> Dict[str, Any]:
    return {"bouts": {}}


def _fetch_polymarket_odds(event_id: str) -> Dict[str, Any]:
    return {"bouts": {}}


def _fetch_oddsapi_odds(event_id: str) -> Dict[str, Any]:
    return {"bouts": {}}


def _merge_odds_sources(*sources: Dict[str, Any]) -> Dict[str, Any]:
    merged: Dict[str, Any] = {"bouts": {}}
    for src in sources:
        bouts = src.get("bouts", {}) or {}
        for k, v in bouts.items():
            if k not in merged["bouts"]:
                merged["bouts"][k] = v
    return merged


async def fetch_odds_for_event(event_id: str) -> Optional[Dict[str, Any]]:
    dk = _fetch_draftkings_odds(event_id)
    pm = _fetch_polymarket_odds(event_id)
    oa = _fetch_oddsapi_odds(event_id)

    merged = _merge_odds_sources(dk, pm, oa)
    if not merged.get("bouts"):
        return None

    merged["_fetched_at"] = merged.get("_fetched_at")
    return merged
