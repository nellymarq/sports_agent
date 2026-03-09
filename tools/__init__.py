# tools/__init__.py
# Multi-agent compatible tool definitions with real data parsing.

import requests
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from bs4 import BeautifulSoup
from logger import info, error

try:
    from config import TOOL_REQUEST_TIMEOUT, TOOL_CACHE_TTL_SECONDS
except ImportError:
    TOOL_REQUEST_TIMEOUT = 15
    TOOL_CACHE_TTL_SECONDS = 300

DEFAULT_TIMEOUT = TOOL_REQUEST_TIMEOUT
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

# ============================================================
# RESPONSE CACHE — avoids redundant API calls across specialists
# ============================================================
_CACHE: Dict[str, Tuple[float, Any]] = {}  # key -> (timestamp, result)
_CACHE_TTL = TOOL_CACHE_TTL_SECONDS


def _cache_get(key: str) -> Optional[Any]:
    if key in _CACHE:
        ts, val = _CACHE[key]
        if time.time() - ts < _CACHE_TTL:
            return val
        del _CACHE[key]
    return None


def _cache_set(key: str, val: Any) -> None:
    _CACHE[key] = (time.time(), val)


# ============================================================
# ODDS UTILITIES — American odds to implied probability
# ============================================================

def american_to_implied_prob(odds: str) -> Optional[float]:
    """Convert American odds string to implied probability (0-1)."""
    try:
        o = int(odds.replace("+", "").strip())
    except (ValueError, AttributeError):
        return None
    if o > 0:
        return 100.0 / (o + 100.0)
    elif o < 0:
        return abs(o) / (abs(o) + 100.0)
    return None


def implied_prob_pair(fav_odds: str, dog_odds: str) -> Dict[str, Optional[float]]:
    """Return implied probabilities for a favorite/underdog pair."""
    fav_p = american_to_implied_prob(fav_odds)
    dog_p = american_to_implied_prob(dog_odds)
    # Remove vig (normalize to sum=1)
    if fav_p and dog_p:
        total = fav_p + dog_p
        fav_p = fav_p / total
        dog_p = dog_p / total
    return {"favorite_prob": fav_p, "underdog_prob": dog_p}


def _safe_get(url: str, timeout: int = DEFAULT_TIMEOUT, headers: Optional[Dict] = None) -> requests.Response:
    return requests.get(url, timeout=timeout, headers=headers or DEFAULT_HEADERS)


# ============================================================
# UFC STATS TOOL - Real HTML parsing
# ============================================================

class UFCStatsTool:
    name = "ufc_stats"

    def _parse_fighter_row(self, row) -> Optional[Dict[str, Any]]:
        """Parse a single fighter row from ufcstats.com search results."""
        cols = row.find_all("td")
        if len(cols) < 11:
            return None

        def _text(col):
            return col.get_text(strip=True) if col else ""

        first_link = cols[0].find("a")
        name = first_link.get_text(strip=True) if first_link else _text(cols[0])
        detail_url = first_link["href"] if first_link and first_link.has_attr("href") else None

        return {
            "name": name,
            "detail_url": detail_url,
            "nickname": _text(cols[1]),
            "height": _text(cols[2]),
            "weight": _text(cols[3]),
            "reach": _text(cols[4]),
            "stance": _text(cols[5]),
            "record": _text(cols[6]),
            "slpm": _text(cols[7]),       # Sig. Strikes Landed per Min
            "str_acc": _text(cols[8]),     # Striking Accuracy
            "sapm": _text(cols[9]),        # Sig. Strikes Absorbed per Min
            "str_def": _text(cols[10]),    # Striking Defense
        }

    def _parse_fighter_detail(self, html: str) -> Dict[str, Any]:
        """Parse a fighter detail page from ufcstats.com."""
        soup = BeautifulSoup(html, "html.parser")
        stats = {}

        # Career stats from the detail page
        stat_items = soup.select("li.b-list__box-list-item")
        for item in stat_items:
            text = item.get_text(separator="|", strip=True)
            if "|" in text:
                parts = text.split("|", 1)
                key = parts[0].strip().rstrip(":").lower().replace(" ", "_").replace(".", "")
                val = parts[1].strip()
                if val and val != "--":
                    stats[key] = val

        # Fight history
        fights = []
        fight_rows = soup.select("tr.b-fight-details__table-row")
        for row in fight_rows[1:6]:  # Last 5 fights
            cells = row.find_all("td")
            if len(cells) >= 8:
                fight = {
                    "result": cells[0].get_text(strip=True),
                    "opponent": cells[1].get_text(strip=True),
                    "method": cells[7].get_text(strip=True) if len(cells) > 7 else "",
                    "round": cells[8].get_text(strip=True) if len(cells) > 8 else "",
                }
                if fight["opponent"]:
                    fights.append(fight)

        stats["recent_fights"] = fights
        return stats

    def invoke(self, args: Dict[str, Any]) -> Dict[str, Any]:
        fighter = (args.get("fighter_name") or "").strip()
        if not fighter:
            return {"error": "fighter_name is required"}

        cache_key = f"ufcstats:{fighter.lower()}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        url = f"https://ufcstats.com/statistics/fighters?query={fighter.replace(' ', '+')}"
        try:
            resp = _safe_get(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            rows = soup.select("tr.b-statistics__table-row")
            fighters_found = []
            for row in rows[1:]:  # skip header
                parsed = self._parse_fighter_row(row)
                if parsed and parsed["name"]:
                    fighters_found.append(parsed)

            if not fighters_found:
                return {
                    "source": "UFCStats",
                    "query": fighter,
                    "fighters": [],
                    "note": "No fighters found matching query.",
                }

            # Try to get detail page for best match
            best = fighters_found[0]
            detail_stats = {}
            if best.get("detail_url"):
                try:
                    detail_resp = _safe_get(best["detail_url"])
                    detail_resp.raise_for_status()
                    detail_stats = self._parse_fighter_detail(detail_resp.text)
                except Exception:
                    pass

            best["detail_stats"] = detail_stats

            result = {
                "source": "UFCStats",
                "query": fighter,
                "best_match": best,
                "all_matches": fighters_found[:5],
                "stats_parsed": True,
            }
            _cache_set(cache_key, result)
            return result

        except Exception as e:
            error(f"UFCStats request failed: {e}")
            return {"error": f"UFCStats request failed: {str(e)}"}


# ============================================================
# ESPN UFC TOOL - Real API + fallback scrape
# ============================================================

class ESPNUFCTool:
    name = "espn_ufc"

    def invoke(self, args: Dict[str, Any]) -> Dict[str, Any]:
        fighter = (args.get("fighter_name") or "").strip()
        if not fighter:
            return {"error": "fighter_name is required"}

        cache_key = f"espn:{fighter.lower()}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        # ESPN athlete search API
        search_url = f"https://site.web.api.espn.com/apis/common/v3/search?query={fighter.replace(' ', '+')}&limit=5&type=player&sport=mma"
        try:
            resp = _safe_get(search_url, headers={
                "User-Agent": DEFAULT_HEADERS["User-Agent"],
                "Accept": "application/json",
            })
            resp.raise_for_status()
            data = resp.json()

            results = []
            for item in data.get("results", []):
                for entry in item.get("contents", []):
                    results.append({
                        "name": entry.get("displayName", ""),
                        "id": entry.get("id", ""),
                        "position": entry.get("position", ""),
                        "team": entry.get("teamName", ""),
                    })

            if not results:
                result = {
                    "source": "ESPN UFC",
                    "query": fighter,
                    "fighters": [],
                    "note": "No fighters found via ESPN search API.",
                }
                _cache_set(cache_key, result)
                return result

            result = {
                "source": "ESPN UFC",
                "query": fighter,
                "fighters": results[:5],
                "stats_parsed": True,
            }
            _cache_set(cache_key, result)
            return result

        except Exception as e:
            # Fallback: try scraping
            try:
                fallback_url = f"https://www.espn.com/mma/fighter/_/search/{fighter.replace(' ', '%20')}"
                resp = _safe_get(fallback_url)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")

                name_el = soup.select_one("h1")
                bio_items = soup.select(".PlayerHeader__Bio__Item")

                bio = {}
                for item in bio_items:
                    text = item.get_text(strip=True)
                    bio[f"info_{len(bio)}"] = text

                return {
                    "source": "ESPN UFC (fallback scrape)",
                    "query": fighter,
                    "name": name_el.get_text(strip=True) if name_el else fighter,
                    "bio": bio,
                    "stats_parsed": bool(bio),
                }
            except Exception as e2:
                error(f"ESPN UFC request failed: {e2}")
                return {"error": f"ESPN UFC request failed: {str(e)} / fallback: {str(e2)}"}


# ============================================================
# DRAFTKINGS ODDS TOOL - Real API
# ============================================================

class DraftKingsTool:
    name = "draftkings_odds"

    def invoke(self, args: Dict[str, Any]) -> Dict[str, Any]:
        fighter = (args.get("fighter_name") or "").strip().lower()

        cache_key = f"dk:{fighter or 'all'}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        try:
            url = "https://sportsbook-nash.draftkings.com/sites/US-SB/api/v5/eventgroups/9034/categories/all"
            resp = _safe_get(url, headers={
                "User-Agent": DEFAULT_HEADERS["User-Agent"],
                "Accept": "application/json",
            })
            resp.raise_for_status()
            data = resp.json()

            events = []
            fighter_odds = []

            for event_group in data.get("eventGroup", {}).get("events", []) or []:
                event_name = event_group.get("name", "")

                for market in event_group.get("displayGroups", []) or []:
                    for m in market.get("markets", []) or []:
                        for outcome in m.get("outcomes", []) or []:
                            participant = outcome.get("participant", "").lower()
                            odds_american = outcome.get("oddsAmerican", "")
                            odds_decimal = outcome.get("oddsDecimal", "")

                            impl_prob = american_to_implied_prob(odds_american)
                            entry = {
                                "event": event_name,
                                "fighter": outcome.get("participant", ""),
                                "odds_american": odds_american,
                                "odds_decimal": odds_decimal,
                                "implied_probability": round(impl_prob, 4) if impl_prob else None,
                                "market": m.get("description", ""),
                            }

                            if fighter and fighter in participant:
                                fighter_odds.append(entry)

                            events.append(entry)

            if fighter and fighter_odds:
                result = {
                    "source": "DraftKings Sportsbook",
                    "query": fighter,
                    "fighter_odds": fighter_odds,
                    "total_markets": len(events),
                    "live_data": True,
                }
                _cache_set(cache_key, result)
                return result

            result = {
                "source": "DraftKings Sportsbook",
                "query": fighter or "all",
                "all_odds": events[:20],
                "total_markets": len(events),
                "fighter_specific": [],
                "live_data": True,
            }
            _cache_set(cache_key, result)
            return result

        except Exception as e:
            error(f"DraftKings API failed: {e}")
            return {
                "source": "DraftKings Sportsbook",
                "query": fighter,
                "error": f"DraftKings API unavailable: {str(e)}",
                "live_data": False,
            }


# ============================================================
# POLYMARKET TOOL - Real API
# ============================================================

class PolymarketTool:
    name = "polymarket"

    def invoke(self, args: Dict[str, Any]) -> Dict[str, Any]:
        fighter = (args.get("fighter_name") or "").strip().lower()

        cache_key = f"poly:{fighter or 'all'}"
        cached = _cache_get(cache_key)
        if cached is not None:
            return cached

        try:
            url = "https://gamma-api.polymarket.com/events?tag=mma&closed=false&limit=20"
            resp = _safe_get(url, headers={
                "User-Agent": DEFAULT_HEADERS["User-Agent"],
                "Accept": "application/json",
            })
            resp.raise_for_status()
            events = resp.json()

            markets = []
            fighter_markets = []

            for event in events:
                title = event.get("title", "")
                for market in event.get("markets", []) or []:
                    entry = {
                        "event_title": title,
                        "question": market.get("question", ""),
                        "outcome_yes": market.get("outcomePrices", ["", ""])[0] if market.get("outcomePrices") else "",
                        "outcome_no": market.get("outcomePrices", ["", ""])[1] if len(market.get("outcomePrices", [])) > 1 else "",
                        "volume": market.get("volume", 0),
                        "liquidity": market.get("liquidity", 0),
                    }
                    markets.append(entry)

                    if fighter and fighter in title.lower():
                        fighter_markets.append(entry)

            if fighter and fighter_markets:
                result = {
                    "source": "Polymarket",
                    "query": fighter,
                    "fighter_markets": fighter_markets,
                    "total_mma_markets": len(markets),
                    "live_data": True,
                }
                _cache_set(cache_key, result)
                return result

            result = {
                "source": "Polymarket",
                "query": fighter or "all",
                "all_mma_markets": markets[:15],
                "total_mma_markets": len(markets),
                "live_data": True,
            }
            _cache_set(cache_key, result)
            return result

        except Exception as e:
            error(f"Polymarket API failed: {e}")
            return {
                "source": "Polymarket",
                "query": fighter,
                "error": f"Polymarket API unavailable: {str(e)}",
                "live_data": False,
            }


# ============================================================
# REGISTRY
# ============================================================

ALL_TOOLS: List[Any] = [
    UFCStatsTool(),
    ESPNUFCTool(),
    DraftKingsTool(),
    PolymarketTool(),
]

TOOL_REGISTRY = {tool.name: tool for tool in ALL_TOOLS}


def _get_json(url: str, timeout: int = DEFAULT_TIMEOUT):
    resp = _safe_get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _get_soup(url: str, timeout: int = DEFAULT_TIMEOUT):
    resp = _safe_get(url, timeout=timeout)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")
