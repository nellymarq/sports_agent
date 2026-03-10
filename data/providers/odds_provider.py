# data/providers/odds_provider.py
# Async odds provider: fetches real odds from DraftKings and Polymarket APIs.

from __future__ import annotations
from typing import Dict, Any, Optional, List
import logging
import time

import requests

_logger = logging.getLogger("odds_provider")

DEFAULT_TIMEOUT = 12
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}


def _safe_get(url: str, timeout: int = DEFAULT_TIMEOUT) -> requests.Response:
    return requests.get(url, timeout=timeout, headers=DEFAULT_HEADERS)


def _american_to_decimal(american: str) -> Optional[float]:
    """Convert American odds string to decimal odds."""
    try:
        val = int(american.replace("+", ""))
        if val > 0:
            return round(1 + val / 100, 4)
        else:
            return round(1 + 100 / abs(val), 4)
    except (ValueError, ZeroDivisionError):
        return None


def _decimal_to_implied(decimal_odds: float) -> float:
    """Convert decimal odds to implied probability."""
    if decimal_odds <= 0:
        return 0.0
    return round(1.0 / decimal_odds, 4)


def _normalize_fighter_key(name: str) -> str:
    """Normalize a fighter name into a lowercase key for matching."""
    return name.strip().lower().replace(".", "").replace("'", "")


def _fetch_draftkings_odds(event_id: str) -> Dict[str, Any]:
    """Fetch real UFC odds from DraftKings Sportsbook API."""
    try:
        url = "https://sportsbook-nash.draftkings.com/sites/US-SB/api/v5/eventgroups/9034/categories/all"
        resp = _safe_get(url)
        resp.raise_for_status()
        data = resp.json()

        bouts: Dict[str, Any] = {}

        for event in data.get("eventGroup", {}).get("events", []) or []:
            event_name = event.get("name", "")

            for dg in event.get("displayGroups", []) or []:
                for market in dg.get("markets", []) or []:
                    market_desc = market.get("description", "")
                    if "moneyline" not in market_desc.lower() and "bout" not in market_desc.lower():
                        # Focus on moneyline / fight winner markets
                        if "fight" not in market_desc.lower() and "winner" not in market_desc.lower():
                            continue

                    outcomes = market.get("outcomes", []) or []
                    if len(outcomes) < 2:
                        continue

                    fighters = []
                    for outcome in outcomes:
                        name = outcome.get("participant", "")
                        american = outcome.get("oddsAmerican", "")
                        decimal_str = outcome.get("oddsDecimal", "")

                        decimal_odds = None
                        if decimal_str:
                            try:
                                decimal_odds = float(decimal_str)
                            except ValueError:
                                pass
                        if decimal_odds is None and american:
                            decimal_odds = _american_to_decimal(american)

                        implied = _decimal_to_implied(decimal_odds) if decimal_odds else None

                        fighters.append({
                            "name": name,
                            "odds_american": american,
                            "odds_decimal": decimal_odds,
                            "implied_probability": implied,
                        })

                    if len(fighters) >= 2:
                        bout_key = _normalize_fighter_key(fighters[0]["name"]) + " vs " + _normalize_fighter_key(fighters[1]["name"])
                        bouts[bout_key] = {
                            "event": event_name,
                            "market": market_desc,
                            "source": "draftkings",
                            "fighters": fighters,
                            "fetched_at": time.time(),
                        }

        return {"bouts": bouts}

    except Exception as e:
        _logger.warning(f"DraftKings odds fetch failed: {e}")
        return {"bouts": {}}


def _fetch_polymarket_odds(event_id: str) -> Dict[str, Any]:
    """Fetch real UFC prediction market data from Polymarket."""
    try:
        url = "https://gamma-api.polymarket.com/events?tag=mma&closed=false&limit=20"
        resp = _safe_get(url)
        resp.raise_for_status()
        events = resp.json()

        bouts: Dict[str, Any] = {}

        for event in events:
            title = event.get("title", "")
            for market in event.get("markets", []) or []:
                question = market.get("question", "")
                outcome_prices = market.get("outcomePrices", [])

                if len(outcome_prices) >= 2:
                    try:
                        yes_price = float(outcome_prices[0])
                        no_price = float(outcome_prices[1])
                    except (ValueError, IndexError):
                        continue

                    bout_key = _normalize_fighter_key(title)
                    bouts[bout_key] = {
                        "event": title,
                        "question": question,
                        "source": "polymarket",
                        "yes_probability": round(yes_price, 4),
                        "no_probability": round(no_price, 4),
                        "volume": market.get("volume", 0),
                        "liquidity": market.get("liquidity", 0),
                        "fetched_at": time.time(),
                    }

        return {"bouts": bouts}

    except Exception as e:
        _logger.warning(f"Polymarket odds fetch failed: {e}")
        return {"bouts": {}}


def _merge_odds_sources(*sources: Dict[str, Any]) -> Dict[str, Any]:
    """Merge odds from multiple sources, preferring the first source with data."""
    merged: Dict[str, Any] = {"bouts": {}}
    for src in sources:
        bouts = src.get("bouts", {}) or {}
        for k, v in bouts.items():
            if k not in merged["bouts"]:
                merged["bouts"][k] = v
            else:
                # Store as alternative source
                existing = merged["bouts"][k]
                if "alt_sources" not in existing:
                    existing["alt_sources"] = []
                existing["alt_sources"].append(v)
    return merged


async def fetch_odds_for_event(event_id: str) -> Optional[Dict[str, Any]]:
    """Fetch and merge odds from all available providers."""
    dk = _fetch_draftkings_odds(event_id)
    pm = _fetch_polymarket_odds(event_id)

    merged = _merge_odds_sources(dk, pm)
    if not merged.get("bouts"):
        return None

    merged["_fetched_at"] = time.time()
    merged["_sources"] = []
    if dk.get("bouts"):
        merged["_sources"].append("draftkings")
    if pm.get("bouts"):
        merged["_sources"].append("polymarket")

    return merged


def fetch_all_ufc_odds() -> Dict[str, Any]:
    """Synchronous convenience function to fetch all current UFC odds."""
    dk = _fetch_draftkings_odds("")
    pm = _fetch_polymarket_odds("")
    merged = _merge_odds_sources(dk, pm)
    merged["_fetched_at"] = time.time()
    return merged
