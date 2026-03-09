# data/events_fusion.py
# Unified event fusion layer (fully async)

from __future__ import annotations
from typing import Optional, Dict, Any

from data.providers.espn_events import fetch_event_from_espn
from data.providers.tapology_events import fetch_event_from_tapology
from data.providers.ufc_events import fetch_event_from_ufc
from data.providers.odds_provider import fetch_odds_for_event


async def build_unified_event(event_id: str) -> Optional[Dict[str, Any]]:
    """
    Unified event fusion layer.
    Merges ESPN, Tapology, UFCStats, and odds data into a single event object.
    """

    # Launch non-UFC providers concurrently
    espn_task = fetch_event_from_espn(event_id)
    tapology_task = fetch_event_from_tapology(event_id)
    odds_task = fetch_odds_for_event(event_id)

    # UFCStats must be awaited directly so the parser runs immediately
    ufc = await fetch_event_from_ufc(event_id)

    # Await the other providers
    espn = await espn_task or {}
    tapology = await tapology_task or {}
    odds = await odds_task or {}

    # Merge all sources
    return {
        "event_id": event_id,
        "espn": espn,
        "tapology": tapology,
        "ufc": ufc,
        "odds": odds,
    }
