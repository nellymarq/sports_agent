# event_utils.py
# Legacy event utilities + new unified-schema layer (async ingestion).

from __future__ import annotations
from typing import List, Dict, Any, Optional
import os
import json
from datetime import datetime

from data.event_ingestion import ingest_event

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")

EVENTS_PATH = os.path.join(DATA_DIR, "events.json")
EVENTS_PATCH_PATH = os.path.join(DATA_DIR, "events_updates.json")


def _safe_load_json(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _parse_date(value: str) -> Optional[datetime]:
    if not value:
        return None

    for fmt in (
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
    ):
        try:
            return datetime.strptime(value, fmt)
        except Exception:
            continue

    for fmt in ("%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(value, fmt)
        except Exception:
            continue

    return None


def _load_baseline_events() -> List[Dict[str, Any]]:
    data = _safe_load_json(EVENTS_PATH, default=[])
    return data if isinstance(data, list) else []


def _load_event_patches() -> List[Dict[str, Any]]:
    data = _safe_load_json(EVENTS_PATCH_PATH, default=[])
    return data if isinstance(data, list) else []


def merge_event_data(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)

    for key in ["date", "location", "name", "main_event", "co_main_event"]:
        if key in patch:
            merged[key] = patch[key]

    card = merged.get("card", []).copy()

    for bout in patch.get("removed_fights", []):
        card = [b for b in card if b != bout]

    for bout in patch.get("added_fights", []):
        if bout not in card:
            card.append(bout)

    merged["card"] = card
    return merged


def _apply_patches(events: List[Dict[str, Any]], patches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_id = {e.get("id"): e for e in events}
    for p in patches:
        eid = p.get("id")
        if not eid or eid not in by_id:
            continue
        by_id[eid] = merge_event_data(by_id[eid], p)
    return list(by_id.values())


def get_event_by_code(event_id: str) -> Optional[Dict[str, Any]]:
    events = _load_baseline_events()
    patches = _load_event_patches()
    events = _apply_patches(events, patches)

    for ev in events:
        if ev.get("id") == event_id:
            return ev
    return None


async def get_next_scheduled_event() -> Optional[Dict[str, Any]]:
    """
    Async wrapper that ensures the next event is ingested and returned.
    """
    events = _load_baseline_events()
    patches = _load_event_patches()
    events = _apply_patches(events, patches)

    upcoming = []
    now = datetime.now(tz=None)  # naive UTC-equivalent for comparison

    for ev in events:
        dt = _parse_date(ev.get("date", ""))
        if dt and dt >= now:
            upcoming.append(ev)

    if not upcoming:
        # No future events — fall back to the most recent event
        all_dated = [
            (ev, _parse_date(ev.get("date", "")))
            for ev in events
            if _parse_date(ev.get("date", ""))
        ]
        if all_dated:
            all_dated.sort(key=lambda x: x[1], reverse=True)
            return all_dated[0][0]  # Return cached data directly
        return None

    upcoming.sort(key=lambda e: _parse_date(e.get("date", "")) or datetime.max)
    next_ev = upcoming[0]
    eid = next_ev.get("id")
    if not eid:
        return None

    await ingest_event(eid)
    return get_event_by_code(eid)


async def get_unified_event(event_id: str) -> Optional[Dict[str, Any]]:
    """
    Ensure a specific event is ingested and return its legacy view.
    """
    await ingest_event(event_id)
    return get_event_by_code(event_id)


async def get_unified_next_event() -> Optional[Dict[str, Any]]:
    """
    Async helper to get the next scheduled event (ingested).
    """
    return await get_next_scheduled_event()


def get_event_fighters(event_id: str) -> List[str]:
    """
    Extract main event fighters from a given event.
    Falls back to co-main or first card bout if main event is empty.
    """
    ev = get_event_by_code(event_id)
    if not ev:
        return []

    # Try main event first
    main = ev.get("main_event", {})
    fighters = main.get("fighters", [])
    if fighters and len(fighters) >= 2:
        return [f if isinstance(f, str) else f.get("name", "") for f in fighters]

    # Try co-main
    co_main = ev.get("co_main_event", {})
    fighters = co_main.get("fighters", [])
    if fighters and len(fighters) >= 2:
        return [f if isinstance(f, str) else f.get("name", "") for f in fighters]

    # Try first card bout
    card = ev.get("card", [])
    if card:
        fighters = card[0].get("fighters", [])
        if fighters and len(fighters) >= 2:
            return [f if isinstance(f, str) else f.get("name", "") for f in fighters]

    return []
