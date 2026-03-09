# data/providers/ufc_events.py
# Fully async UFCStats ingestion provider (2026-compatible)

from __future__ import annotations
from typing import Optional, Dict, Any

from data.providers.ufcstats_list import find_ufcstats_event_url
from data.providers.ufcstats_event import parse_ufcstats_event


async def fetch_event_from_ufc(event_id: str) -> Optional[Dict[str, Any]]:
    """
    Unified UFC provider (async).
    UFCStats is the authoritative source for:
      - event name
      - date
      - location
      - full bout list (fighters, IDs, weight class, bout_key)
    """
    stats_url = await find_ufcstats_event_url(event_id)
    if not stats_url:
        print("DEBUG: UFCStats URL not found for", event_id)
        return None

    data = await parse_ufcstats_event(stats_url)
    if not data:
        print("DEBUG: UFCStats event parse failed for", stats_url)
        return None

    return data
