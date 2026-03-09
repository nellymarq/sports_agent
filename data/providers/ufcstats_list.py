# data/providers/ufcstats_list.py
# Fully async UFCStats event list fetcher using browser_fetch.

from __future__ import annotations
from typing import Optional
from bs4 import BeautifulSoup

from tools.browser_fetch import browser_fetch

UFCSTATS_COMPLETED = "http://ufcstats.com/statistics/events/completed"
UFCSTATS_UPCOMING = "http://ufcstats.com/statistics/events/upcoming"


async def _fetch_soup(url: str) -> Optional[BeautifulSoup]:
    html = await browser_fetch(url)
    if not html:
        return None
    return BeautifulSoup(html, "html.parser")


async def find_ufcstats_event_url(event_id: str) -> Optional[str]:
    """
    Given an event_id like 'ufc_325', find the matching UFCStats event-details URL.
    Matches by checking if the event name contains 'UFC 325'.
    """

    target = event_id.replace("_", " ").upper()  # "UFC 325"

    for url in (UFCSTATS_UPCOMING, UFCSTATS_COMPLETED):
        soup = await _fetch_soup(url)
        if not soup:
            continue

        rows = soup.select("table.b-statistics__table-events tbody tr")
        for row in rows:
            a = row.select_one("a.b-link")
            if not a:
                continue

            name = (a.get_text() or "").upper()
            if target in name:
                return a["href"]

    return None
