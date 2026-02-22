# tools.py
# Clean, multi-agent compatible tool definitions with safer HTTP usage.

import requests
from typing import Dict, Any, List


DEFAULT_TIMEOUT = 10
DEFAULT_HEADERS = {
    "User-Agent": "UFC-Analytics-Agent/1.0 (+https://example.com)",
}


def _safe_get(url: str, timeout: int = DEFAULT_TIMEOUT) -> requests.Response:
    return requests.get(url, timeout=timeout, headers=DEFAULT_HEADERS)


class UFCStatsTool:
    name = "ufc_stats"

    def invoke(self, args: Dict[str, Any]) -> Dict[str, Any]:
        fighter = (args.get("fighter_name") or "").strip()
        if not fighter:
            return {"error": "fighter_name is required"}

        url = f"https://ufcstats.com/statistics/fighters?query={fighter.replace(' ', '+')}"
        try:
            resp = _safe_get(url)
            resp.raise_for_status()
            return {
                "source": "UFCStats",
                "query": fighter,
                "raw_html": resp.text,
                "note": "HTML returned. Specialists must parse this.",
            }
        except Exception as e:
            return {"error": f"UFCStats request failed: {str(e)}"}


class ESPNUFCTool:
    name = "espn_ufc"

    def invoke(self, args: Dict[str, Any]) -> Dict[str, Any]:
        fighter = (args.get("fighter_name") or "").strip()
        if not fighter:
            return {"error": "fighter_name is required"}

        url = "https://www.espn.com/mma/fighter/_/search/" + fighter.replace(" ", "%20")

        try:
            resp = _safe_get(url)
            resp.raise_for_status()
            return {
                "source": "ESPN UFC",
                "query": fighter,
                "raw_html": resp.text,
                "note": "HTML returned. Specialists must parse this.",
            }
        except Exception as e:
            return {"error": f"ESPN UFC request failed: {str(e)}"}


class DraftKingsTool:
    name = "draftkings_marketplace"

    def invoke(self, args: Dict[str, Any]) -> Dict[str, Any]:
        fighter = (args.get("fighter_name") or "Unknown Fighter").strip()

        return {
            "source": "DraftKings Marketplace (stub)",
            "fighter": fighter,
            "sentiment_score": 0.62,
            "collectible_volume": 128,
            "note": "This is stubbed data. Replace with real API later.",
        }


class PolymarketTool:
    name = "polymarket"

    def invoke(self, args: Dict[str, Any]) -> Dict[str, Any]:
        fighter = (args.get("fighter_name") or "Unknown Fighter").strip()

        return {
            "source": "Polymarket (stub)",
            "fighter": fighter,
            "sentiment_confidence": 0.55,
            "market_interest": "moderate",
            "note": "This is stubbed data. Replace with real API later.",
        }


ALL_TOOLS: List[Any] = [
    UFCStatsTool(),
    ESPNUFCTool(),
    DraftKingsTool(),
    PolymarketTool(),
]

TOOL_REGISTRY = {tool.name: tool for tool in ALL_TOOLS}
