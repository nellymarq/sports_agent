# data/providers/espn_events.py
# ESPN ingestion (2026‑compatible): async browser-based fetch for JSON + HTML.

from __future__ import annotations
from typing import Dict, Any, Optional
import re
import time
import json
from bs4 import BeautifulSoup

from tools.browser_fetch import browser_fetch

SCOREBOARD_URL = "https://site.web.api.espn.com/apis/site/v2/sports/mma/ufc/scoreboard"
SCHEDULE_URL = "https://www.espn.com/mma/schedule"


async def _fetch_scoreboard() -> Optional[Dict[str, Any]]:
    """
    Fetch ESPN's scoreboard JSON using async browser_fetch.
    """
    try:
        raw = await browser_fetch(SCOREBOARD_URL)
        if not raw:
            return None
        return json.loads(raw)
    except Exception:
        return None


async def _extract_event_from_scoreboard(event_id: str) -> Optional[Dict[str, Any]]:
    """
    Match event by name inside scoreboard JSON.
    """
    sb = await _fetch_scoreboard()
    if not sb:
        return None

    events = sb.get("events") or []
    target = event_id.replace("_", " ").upper()

    for ev in events:
        name = (ev.get("name") or "").upper()
        if target in name:
            return ev

    return None


def _normalize_scoreboard_event(ev: Dict[str, Any]) -> Dict[str, Any]:
    competitions = ev.get("competitions") or []
    if not competitions:
        return {}

    comp = competitions[0]
    cards = comp.get("cards") or []
    bouts = []

    for idx, card in enumerate(cards, start=1):
        fighters = []
        for c in card.get("competitors", []):
            name = c.get("athlete", {}).get("displayName")
            if name:
                fighters.append({"name": name})

        weight = card.get("weightClass", {}).get("displayName", "")

        bouts.append(
            {
                "order": idx,
                "is_main_event": idx == 1,
                "fighters": fighters,
                "weight_class": weight,
            }
        )

    venue = comp.get("venue", {}) or {}
    address = venue.get("address", {}) or {}

    return {
        "bouts": bouts,
        "name": ev.get("name"),
        "date": ev.get("date"),
        "venue": venue.get("fullName"),
        "city": address.get("city"),
        "country": address.get("country"),
        "location": venue.get("fullName"),
        "_fetched_at": time.time(),
    }


async def _map_event_to_espn_numeric(event_id: str) -> Optional[str]:
    """
    Map event_id (ufc_326) → ESPN numeric ID by scanning schedule page.
    """
    try:
        html = await browser_fetch(SCHEDULE_URL)
        if not html:
            return None
    except Exception:
        return None

    soup = BeautifulSoup(html, "html.parser")
    target = event_id.replace("_", " ").upper()

    for a in soup.find_all("a", href=True):
        text = (a.get_text() or "").upper()
        if target in text:
            m = re.search(r"id/(\d+)", a["href"])
            if m:
                return m.group(1)

    return None


async def _fetch_fightcenter_html(numeric_id: str) -> Optional[BeautifulSoup]:
    """
    Fetch ESPN FightCenter HTML using async browser_fetch.
    """
    url = f"https://www.espn.com/mma/fightcenter/_/id/{numeric_id}"
    try:
        html = await browser_fetch(url)
        if not html:
            return None
        return BeautifulSoup(html, "html.parser")
    except Exception:
        return None


def _normalize_fightcenter_html(soup: BeautifulSoup) -> Dict[str, Any]:
    bouts = []
    rows = soup.select(".FightCard__Bout")

    for idx, row in enumerate(rows, start=1):
        fighters = []
        for n in row.select(".FightCard__CompetitorName"):
            name = n.get_text(strip=True)
            if name:
                fighters.append({"name": name})

        wc = row.select_one(".FightCard__WeightClass")
        weight = wc.get_text(strip=True) if wc else ""

        bouts.append(
            {
                "order": idx,
                "is_main_event": idx == 1,
                "fighters": fighters,
                "weight_class": weight,
            }
        )

    return {
        "bouts": bouts,
        "_fetched_at": time.time(),
    }


async def fetch_event_from_espn(event_id: str) -> Optional[Dict[str, Any]]:
    """
    Full ESPN ingestion:
      1. Try scoreboard JSON (async)
      2. Fallback to FightCenter HTML (async)
    """
    ev = await _extract_event_from_scoreboard(event_id)
    if ev:
        return _normalize_scoreboard_event(ev)

    numeric = await _map_event_to_espn_numeric(event_id)
    if not numeric:
        return None

    soup = await _fetch_fightcenter_html(numeric)
    if not soup:
        return None

    return _normalize_fightcenter_html(soup)
