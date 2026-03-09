# data/events_fusion.py
# Unified event fusion layer (fully async) with graceful provider degradation.

from __future__ import annotations
from typing import Optional, Dict, Any
import asyncio
import logging

from data.events_schema import Event

_logger = logging.getLogger("events_fusion")


async def _safe_fetch(coro, provider_name: str) -> Dict[str, Any]:
    """Run a provider coroutine with error isolation."""
    try:
        result = await asyncio.wait_for(coro, timeout=15.0)
        return result or {}
    except asyncio.TimeoutError:
        _logger.warning(f"Provider '{provider_name}' timed out after 15s")
        return {}
    except Exception as e:
        _logger.warning(f"Provider '{provider_name}' failed: {e}")
        return {}


async def build_unified_event(
    event_id: str,
    legacy_seed: Optional[Dict[str, Any]] = None,
) -> Event:
    """
    Unified event fusion layer.
    Merges ESPN, Tapology, UFCStats, and odds data into a single Event.
    Each provider is isolated — failures don't break the pipeline.
    """
    from data.providers.espn_events import fetch_event_from_espn
    from data.providers.tapology_events import fetch_event_from_tapology
    from data.providers.ufc_events import fetch_event_from_ufc
    from data.providers.odds_provider import fetch_odds_for_event

    # Run all providers concurrently with individual error isolation
    ufc, espn, tapology, odds = await asyncio.gather(
        _safe_fetch(fetch_event_from_ufc(event_id), "UFCStats"),
        _safe_fetch(fetch_event_from_espn(event_id), "ESPN"),
        _safe_fetch(fetch_event_from_tapology(event_id), "Tapology"),
        _safe_fetch(fetch_odds_for_event(event_id), "Odds"),
    )

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
    sources_available = []
    if ufc:
        sources_available.append("ufc")
    if espn:
        sources_available.append("espn")
    if tapology:
        sources_available.append("tapology")
    if odds:
        sources_available.append("odds")

    event.provenance.raw_sources = {
        "espn": espn,
        "tapology": tapology,
        "ufc": ufc,
        "odds": odds,
    }
    event.provenance.merge_notes = [
        f"Sources available: {', '.join(sources_available) or 'none (legacy seed only)'}"
    ]

    return event
