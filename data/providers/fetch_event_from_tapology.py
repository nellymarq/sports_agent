# data/providers/fetch_event_from_tapology.py
# Async Tapology event fetcher using browser_fetch.

from __future__ import annotations
from typing import Dict, Any, Optional
import time

from bs4 import BeautifulSoup

from tools.browser_fetch import browser_fetch
from data.providers.tapology_events import parse_event_detail
from data.providers.tapology_list import extract_ufc_events_from_html

BASE_URL = "https://www.tapology.com"


async def _fetch_events_list_html() -> Optional[str]:
    try:
        return await browser_fetch(f"{BASE_URL}/fightcenter/events")
    except Exception:
        return None


async def _find_event_metadata(event_id: str) -> Optional[Dict[str, Any]]:
    """
    Use the Tapology events list page + extract_ufc_events_from_html
    to locate the matching event and its metadata.
    """
    list_html = await _fetch_events_list_html()
    if not list_html:
        return None

    events = extract_ufc_events_from_html(list_html) or []
    target = event_id.replace("_", " ").lower()

    for ev in events:
        code = (ev.get("code") or "").lower()
        eid = (ev.get("event_id") or "").lower()
        if target == code or target == eid:
            return ev

    return None


async def fetch_event_from_tapology(event_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a single event from Tapology:
      1. Load events list and find matching event metadata
      2. Fetch event detail page
      3. Parse bouts via parse_event_detail
    """
    meta = await _find_event_metadata(event_id)
    if not meta:
        return None

    event_url = meta.get("url")
    if not event_url:
        return None

    detail_html = await browser_fetch(event_url)
    if not detail_html:
        return None

    event_metadata = {
        "event_key": meta.get("event_key") or event_id,
        "name": meta.get("name"),
        "date": meta.get("date"),
        "location": meta.get("location"),
        "_fetched_at": time.time(),
    }

    return parse_event_detail(detail_html, event_metadata)
