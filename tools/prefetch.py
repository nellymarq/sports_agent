# tools/prefetch.py
# Pre-fetch fighter stats before specialist execution to ensure
# data-driven analysis regardless of LLM tool-calling behavior.

from __future__ import annotations
from typing import Dict, Any, List, Optional
import logging

from tools import TOOL_REGISTRY, _cache_get

_logger = logging.getLogger("tools.prefetch")


def prefetch_fighter_stats(fighters: List[str]) -> Dict[str, Any]:
    """
    Eagerly fetch stats for all identified fighters.
    Returns a dict keyed by fighter name with combined data from all sources.
    Results are cached by the tool layer, so subsequent tool calls are free.
    """
    if not fighters:
        return {}

    ufc_tool = TOOL_REGISTRY.get("ufc_stats")
    dk_tool = TOOL_REGISTRY.get("draftkings_odds")

    results: Dict[str, Any] = {}

    for fighter in fighters:
        fighter = (fighter or "").strip()
        if not fighter or fighter == "unknown":
            continue

        fighter_data: Dict[str, Any] = {"name": fighter}

        # UFCStats
        if ufc_tool:
            try:
                stats = ufc_tool.invoke({"fighter_name": fighter})
                if "error" not in stats:
                    best = stats.get("best_match", {})
                    fighter_data["record"] = best.get("record", "")
                    fighter_data["height"] = best.get("height", "")
                    fighter_data["weight"] = best.get("weight", "")
                    fighter_data["reach"] = best.get("reach", "")
                    fighter_data["stance"] = best.get("stance", "")
                    fighter_data["slpm"] = best.get("slpm", "")
                    fighter_data["str_acc"] = best.get("str_acc", "")
                    fighter_data["sapm"] = best.get("sapm", "")
                    fighter_data["str_def"] = best.get("str_def", "")
                    detail = best.get("detail_stats", {})
                    if detail:
                        fighter_data["detail_stats"] = detail
                    fighter_data["stats_source"] = "UFCStats"
            except Exception as e:
                _logger.debug(f"UFCStats prefetch failed for {fighter}: {e}")

        # DraftKings odds
        if dk_tool:
            try:
                odds = dk_tool.invoke({"fighter_name": fighter})
                if "error" not in odds and odds.get("fighter_odds"):
                    fighter_data["odds"] = odds["fighter_odds"]
                    fighter_data["odds_source"] = "DraftKings"
            except Exception as e:
                _logger.debug(f"DraftKings prefetch failed for {fighter}: {e}")

        results[fighter] = fighter_data

    return results


def build_fighter_comparison(stats: Dict[str, Any]) -> str:
    """Build head-to-head comparison if exactly 2 fighters are pre-fetched."""
    if len(stats) != 2:
        return ""
    try:
        from tools.comparison import build_comparison
        fighters = list(stats.values())
        return build_comparison(fighters[0], fighters[1])
    except Exception:
        return ""


def format_prefetched_stats(stats: Dict[str, Any]) -> str:
    """Format pre-fetched stats into a readable context block."""
    if not stats:
        return ""

    lines = ["=== Pre-Fetched Fighter Stats ==="]
    for fighter, data in stats.items():
        lines.append(f"\n--- {fighter} ---")
        for key in ["record", "height", "weight", "reach", "stance",
                     "slpm", "str_acc", "sapm", "str_def"]:
            val = data.get(key, "")
            if val:
                label = key.replace("_", " ").title()
                lines.append(f"  {label}: {val}")

        # Recent fights
        detail = data.get("detail_stats", {})
        if detail.get("recent_fights"):
            lines.append("  Recent Fights:")
            for f in detail["recent_fights"][:5]:
                lines.append(
                    f"    {f.get('result', '?')} vs {f.get('opponent', '?')} "
                    f"({f.get('method', '')} R{f.get('round', '?')})"
                )

        # Odds
        if data.get("odds"):
            lines.append("  Betting Odds:")
            for o in data["odds"][:3]:
                lines.append(
                    f"    {o.get('market', '')}: {o.get('odds_american', '')} "
                    f"(implied: {o.get('implied_probability', 'N/A')})"
                )

    return "\n".join(lines)
