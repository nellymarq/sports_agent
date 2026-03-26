# data/providers/wikipedia_fighter.py
# Wikipedia-based fighter data provider. Used as fallback when UFCStats is unreachable.
# Extracts fighter stats from Wikipedia infoboxes via the MediaWiki API.

from __future__ import annotations
import re
import requests
from typing import Dict, Any, Optional, List


WIKI_API = "https://en.wikipedia.org/w/api.php"
TIMEOUT = 10
HEADERS = {"User-Agent": "UFCAnalyticsEngine/1.0 (sports_agent)"}


def search_fighter_wikipedia(name: str) -> Optional[Dict[str, Any]]:
    """
    Search Wikipedia for a UFC fighter and extract stats from infobox.
    Returns a dict compatible with the UFCStats tool format.
    """
    if not name or len(name.strip()) < 2:
        return None

    # Step 1: Search for the fighter
    page_title = _find_fighter_page(name)
    if not page_title:
        return None

    # Step 2: Parse the infobox
    fields = _parse_infobox(page_title)
    if not fields:
        return None

    # Step 3: Convert to UFCStats-compatible format
    return _to_stats_format(fields, name)


def _find_fighter_page(name: str) -> Optional[str]:
    """Search Wikipedia for a fighter page."""
    try:
        resp = requests.get(WIKI_API, headers=HEADERS, params={
            "action": "query",
            "list": "search",
            "srsearch": f"{name} MMA fighter",
            "format": "json",
            "srlimit": 5,
        }, timeout=TIMEOUT)
        resp.raise_for_status()
        results = resp.json().get("query", {}).get("search", [])

        name_lower = name.lower()
        for r in results:
            title = r.get("title", "")
            title_lower = title.lower()
            # Match if fighter name is in title
            name_parts = name_lower.split()
            if all(part in title_lower for part in name_parts):
                return title
            # Match on last name
            if name_parts and name_parts[-1] in title_lower:
                return title

        # Fallback to first result if it looks like a fighter page
        if results:
            snippet = results[0].get("snippet", "").lower()
            if any(kw in snippet for kw in ["mixed martial", "ufc", "mma", "fighter"]):
                return results[0]["title"]

    except Exception:
        pass
    return None


def _parse_infobox(page_title: str) -> Dict[str, str]:
    """Parse Wikipedia infobox fields from wikitext."""
    try:
        resp = requests.get(WIKI_API, headers=HEADERS, params={
            "action": "parse",
            "page": page_title,
            "prop": "wikitext",
            "format": "json",
        }, timeout=TIMEOUT)
        resp.raise_for_status()
        wikitext = resp.json().get("parse", {}).get("wikitext", {}).get("*", "")
    except Exception:
        return {}

    fields = {}
    for m in re.finditer(r'\|\s*([\w\s]+?)\s*=\s*(.+?)(?=\n\||\n\}\})', wikitext, re.DOTALL):
        key = m.group(1).strip().lower().replace(" ", "_")
        val = m.group(2).strip()
        # Strip wiki markup
        val = re.sub(r'\[\[([^\]|]*\|)?([^\]]*)\]\]', r'\2', val)
        val = re.sub(r'\{\{[^}]*\}\}', '', val).strip()
        val = re.sub(r'<[^>]+>', '', val).strip()
        if val and len(val) < 200:
            fields[key] = val

    return fields


def _parse_height(fields: Dict[str, str]) -> str:
    """Extract height from infobox."""
    for key in ["height", "height_ft", "height_cm"]:
        val = fields.get(key, "")
        if val:
            return val
    return ""


def _parse_reach(fields: Dict[str, str]) -> str:
    """Extract reach from infobox."""
    for key in ["reach", "reach_in"]:
        val = fields.get(key, "")
        if val:
            # Clean up: "74 in (188 cm)" -> "74"
            m = re.search(r'(\d+)', val)
            return m.group(1) if m else val
    return ""


def _to_stats_format(fields: Dict[str, str], search_name: str) -> Dict[str, Any]:
    """Convert Wikipedia infobox fields to UFCStats-compatible format."""
    # Build record from win/loss/draw counts
    ko_wins = _safe_int(fields.get("mma_kowin", "0"))
    sub_wins = _safe_int(fields.get("mma_subwin", "0"))
    dec_wins = _safe_int(fields.get("mma_decwin", "0"))
    total_wins = ko_wins + sub_wins + dec_wins

    ko_losses = _safe_int(fields.get("mma_koloss", "0"))
    sub_losses = _safe_int(fields.get("mma_subloss", "0"))
    dec_losses = _safe_int(fields.get("mma_decloss", "0"))
    total_losses = ko_losses + sub_losses + dec_losses

    draws = _safe_int(fields.get("draws", "0"))

    # Try direct wins/losses fields if component fields are missing
    if total_wins == 0:
        total_wins = _safe_int(fields.get("wins", "0"))
    if total_losses == 0:
        total_losses = _safe_int(fields.get("losses", "0"))

    record = f"{total_wins}-{total_losses}-{draws}"

    name = fields.get("name", search_name)
    nickname = fields.get("nickname", "")

    height = _parse_height(fields)
    reach = _parse_reach(fields)
    stance = fields.get("stance", "")
    weight = fields.get("weight", fields.get("weightclass", ""))

    # Build detail_stats
    win_methods = {}
    if ko_wins > 0:
        win_methods["ko_tko"] = ko_wins
    if sub_wins > 0:
        win_methods["submission"] = sub_wins
    if dec_wins > 0:
        win_methods["decision"] = dec_wins

    return {
        "best_match": {
            "name": name,
            "nickname": nickname,
            "record": record,
            "height": height,
            "weight": weight,
            "reach": reach,
            "stance": stance,
            "slpm": "",  # Not available from Wikipedia
            "str_acc": "",
            "sapm": "",
            "str_def": "",
            "td_avg": "",
            "td_acc": "",
            "td_def": "",
            "sub_avg": "",
            "detail_stats": {
                "win_methods": win_methods,
                "recent_fights": [],
            },
            "source": "wikipedia",
        }
    }


def _safe_int(val: str) -> int:
    """Parse int from string, defaulting to 0."""
    try:
        return int(re.sub(r'[^\d]', '', str(val).strip()) or "0")
    except (ValueError, TypeError):
        return 0
