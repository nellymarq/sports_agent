# providers/tapology_events.py

from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re

BASE_URL = "https://www.tapology.com"


def extract_bout_id(div_id: str) -> int:
    """
    Extract numeric bout ID from IDs like:
        boutVeryCompact1105215
    """
    m = re.search(r"(\d+)$", div_id)
    return int(m.group(1)) if m else None


def parse_bout_row(row, event_key: str, index: int):
    """
    Parse a single bout row from an event detail page.
    """
    bout_id = extract_bout_id(row.get("id", ""))

    fighters = row.select("a.link-primary-red")
    fighter_a = fighters[0].get_text(strip=True) if len(fighters) > 0 else None
    fighter_b = fighters[1].get_text(strip=True) if len(fighters) > 1 else None

    status_tag = row.select_one("span.text-xs11")
    status = status_tag.get_text(strip=True) if status_tag else None

    weight_tag = row.select_one("span.bg-slate-700")
    weight_class = weight_tag.get_text(strip=True) if weight_tag else None

    sport_tag = row.select_one("div.italic")
    sport = sport_tag.get_text(strip=True) if sport_tag else None

    bout_link = row.select_one("a[href*='/fightcenter/bouts/']")
    bout_url = urljoin(BASE_URL, bout_link["href"]) if bout_link else None

    bout_key = f"{event_key}_bout_{index}"

    return {
        "bout_key": bout_key,
        "tapology_bout_id": bout_id,
        "fighter_a": fighter_a,
        "fighter_b": fighter_b,
        "weight_class": weight_class,
        "status": status,
        "sport": sport,
        "order_index": index,
        "bout_url": bout_url,
    }


def parse_event_detail(html: str, event_metadata: dict):
    """
    Parse the event detail page and attach bouts to the event dict.
    """
    soup = BeautifulSoup(html, "html.parser")

    rows = soup.select("div[id^='boutVeryCompact']")
    bouts = []

    for i, row in enumerate(rows, start=1):
        bout = parse_bout_row(row, event_metadata["event_key"], i)
        bouts.append(bout)

    event_metadata["bouts"] = bouts
    return event_metadata

from data.providers.fetch_event_from_tapology import fetch_event_from_tapology
