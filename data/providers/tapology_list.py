# providers/tapology_list.py

from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re

BASE_URL = "https://www.tapology.com"


def normalize_event_key(event_name: str) -> str:
    """
    Convert Tapology event names into your canonical UFC key format.
    Examples:
        "UFC 325" -> "ufc_325"
        "UFC Fight Night: Smith vs Spann" -> "ufc_fight_night_smith_vs_spann"
    """
    name = event_name.lower().strip()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name


def extract_event_id_from_url(url: str) -> int:
    """
    Extract numeric Tapology event ID from URLs like:
        /fightcenter/events/139129-budo-sento-championship-33
    """
    m = re.search(r"/events/(\d+)-", url)
    return int(m.group(1)) if m else None


def parse_event_block(block):
    """
    Parse a single event block from the event list page.
    Only returns UFC events.
    """
    link_tag = block.select_one("div.promotion a[href*='/fightcenter/events/']")
    if not link_tag:
        return None

    event_name = link_tag.get_text(strip=True)
    if "ufc" not in event_name.lower():
        return None  # UFC-only filter

    event_url = urljoin(BASE_URL, link_tag["href"])
    tapology_event_id = extract_event_id_from_url(link_tag["href"])
    event_key = normalize_event_key(event_name)

    # Date
    date_tag = block.select_one("div.promotion span.hidden.md:inline")
    event_date = date_tag.get_text(strip=True) if date_tag else None

    # Location
    loc_tag = block.select_one("div.geography span.hidden.md:inline")
    location = loc_tag.get_text(strip=True) if loc_tag else None

    # Sport (always MMA for UFC)
    sport_tag = block.select_one("div.geography span.sport")
    sport = sport_tag.get_text(strip=True) if sport_tag else "MMA"

    return {
        "event_key": event_key,
        "tapology_event_id": tapology_event_id,
        "event_name": event_name,
        "event_url": event_url,
        "event_date": event_date,
        "location": location,
        "promotion": "UFC",
        "sport": sport,
    }


def extract_ufc_events_from_html(html: str):
    """
    Parse the full Tapology event list HTML and return UFC events only.
    """
    soup = BeautifulSoup(html, "html.parser")
    blocks = soup.select("div.fightcenterEvents div[data-controller='bout-toggler']")

    events = []
    for block in blocks:
        parsed = parse_event_block(block)
        if parsed:
            events.append(parsed)

    return events
