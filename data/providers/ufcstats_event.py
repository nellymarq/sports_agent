# data/providers/ufcstats_event.py
# Fully async UFCStats event-details parser (2026-compatible)

from __future__ import annotations
import logging
from typing import Dict, Any, List, Optional
import time
from bs4 import BeautifulSoup

from tools.browser_fetch import browser_fetch

_logger = logging.getLogger("providers.ufcstats_event")


async def parse_ufcstats_event(url: str) -> Optional[Dict[str, Any]]:
    """
    Parse a UFCStats event-details page into structured event + bouts.
    Updated for 2026 HTML structure.
    """
    html = await browser_fetch(url)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    # -----------------------------
    # Event metadata
    # -----------------------------
    name_tag = soup.select_one("h2.b-content__title span.b-content__title-highlight")
    event_name = name_tag.get_text(strip=True) if name_tag else None

    info_items = soup.select("div.b-list__info-box li.b-list__box-list-item")
    event_date = None
    event_location = None

    if len(info_items) >= 1:
        event_date = info_items[0].get_text(strip=True).replace("Date:", "").strip()
    if len(info_items) >= 2:
        event_location = info_items[1].get_text(strip=True).replace("Location:", "").strip()

    # -----------------------------
    # Bout table
    # -----------------------------
    bouts: List[Dict[str, Any]] = []

    rows = soup.select("tr.b-fight-details__table-row.b-fight-details__table-row__hover")
    for idx, row in enumerate(rows, start=1):
        # Fighter names and IDs
        fighter_links = row.select("td.l-page_align_left a.b-link_style_black[href*='/fighter-details/']")
        fighters = []
        for fl in fighter_links:
            name = fl.get_text(strip=True)
            href = fl.get("href", "")
            fighter_id = href.split("/")[-1] if "/fighter-details/" in href else None
            if name and fighter_id:
                fighters.append({
                    "name": name,
                    "fighter_id": fighter_id,
                })

        # Weight class
        weight_td = row.select("td.l-page_align_left p.b-fight-details__table-text")
        weight_class = None
        for p in weight_td:
            text = p.get_text(strip=True)
            if "weight" in text.lower():
                weight_class = text.replace("<br>", "").strip()
                break

        # Bout key
        link_tag = row.select_one("a[data-link]")
        bout_key = None
        if link_tag:
            bout_key = link_tag["data-link"].split("/")[-1]

        bouts.append({
            "order": idx,
            "fighters": fighters,
            "weight_class": weight_class,
            "bout_key": bout_key,
            "is_main_event": idx == 1,
            "is_co_main_event": idx == 2,
        })

    _logger.debug(f"Parsed {len(bouts)} bouts from UFCStats")

    return {
        "name": event_name,
        "date": event_date,
        "location": event_location,
        "bouts": bouts,
        "_fetched_at": time.time(),
    }
