# data/event_ingestion.py
# Safely overwrites events.json using unified event data (async).

from __future__ import annotations
from typing import Dict, Any, List, Optional
import os
import json

from data.events_schema import Event
from data.events_fusion import build_unified_event

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

EVENTS_PATH = os.path.join(DATA_DIR, "events.json")


def _safe_load_json(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _safe_write_json(path: str, data) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def _load_events() -> List[Dict[str, Any]]:
    data = _safe_load_json(EVENTS_PATH, default=[])
    return data if isinstance(data, list) else []


def _update_events_list(events, updated_event):
    eid = updated_event.get("id")
    if not eid:
        return events

    new_list = []
    found = False

    for ev in events:
        if ev.get("id") == eid:
            new_list.append(updated_event)
            found = True
        else:
            new_list.append(ev)

    if not found:
        new_list.append(updated_event)

    return new_list


async def ingest_event(event_id: str) -> Optional[Dict[str, Any]]:
    """
    Build a unified Event (async), convert it back to legacy schema,
    overwrite the matching entry in events.json, and return it.
    """
    events = _load_events()

    legacy_seed = None
    for ev in events:
        if ev.get("id") == event_id:
            legacy_seed = ev
            break

    unified: Event = await build_unified_event(event_id, legacy_seed=legacy_seed)
    legacy_updated = unified.to_legacy_dict()

    new_events = _update_events_list(events, legacy_updated)
    _safe_write_json(EVENTS_PATH, new_events)

    return legacy_updated
