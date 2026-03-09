# data/events_fusion.py
# Unified event fusion layer (fully async)

from __future__ import annotations
from typing import Optional, Dict, Any

from data.events_schema import Event


async def build_unified_event(
    event_id: str,
    legacy_seed: Optional[Dict[str, Any]] = None,
) -> Event:
    """
    Unified event fusion layer.
    Merges ESPN, Tapology, UFCStats, and odds data into a single Event.
    Falls back to legacy_seed if no providers return data.
    """
    from data.providers.espn_events import fetch_event_from_espn
    from data.providers.tapology_events import fetch_event_from_tapology
    from data.providers.ufc_events import fetch_event_from_ufc
    from data.providers.odds_provider import fetch_odds_for_event

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

    # Start from legacy seed or build from scratch
    if legacy_seed:
        event = Event.from_legacy_dict(legacy_seed)
    else:
        event = Event(
            id=event_id,
            code=event_id.replace("_", " ").upper(),
            name=event_id.replace("_", " ").upper(),
        )

    # Store raw source data in provenance
    event.provenance.raw_sources = {
        "espn": espn,
        "tapology": tapology,
        "ufc": ufc,
        "odds": odds,
    }

    return event
