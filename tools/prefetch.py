# tools/prefetch.py
# Pre-fetch fighter stats before specialist execution to ensure
# data-driven analysis regardless of LLM tool-calling behavior.

from __future__ import annotations
from typing import Dict, Any, List, Optional
import logging
import time

from tools import TOOL_REGISTRY
from data.input_validator import validate_fighter_name, validate_stats_response

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

        # Validate fighter name before API lookup
        name_check = validate_fighter_name(fighter)
        if not name_check["valid"]:
            _logger.warning(f"Invalid fighter name: {name_check['error']}")
            continue
        fighter = name_check["sanitized"]

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
                    # Grappling stats and age from detail page
                    # These are parsed from the fighter detail page into
                    # detail_stats; promote them to top-level fields so
                    # analytics modules (aging_curve, style_classifier,
                    # fighter_profile) can access them directly.
                    for grappling_key in ("td_avg", "td_acc", "td_def", "sub_avg", "age"):
                        val = detail.get(grappling_key, "")
                        if val:
                            fighter_data[grappling_key] = val
                    fighter_data["stats_source"] = "UFCStats"

                    # Validate the fetched stats
                    stats_check = validate_stats_response(fighter_data, fighter)
                    if stats_check.get("warnings"):
                        fighter_data["data_warnings"] = stats_check["warnings"]
                        _logger.info(
                            f"Stats warnings for {fighter}: "
                            f"{stats_check['warnings']}"
                        )
                    if "data_quality_score" in stats_check:
                        fighter_data["validated_quality_score"] = (
                            stats_check["data_quality_score"]
                        )
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

        # Data freshness and quality tracking
        fighter_data["prefetch_timestamp"] = time.time()

        # Use validated quality score if available, otherwise compute simple one
        if "validated_quality_score" not in fighter_data:
            quality_fields = ["record", "slpm", "str_acc", "str_def", "td_avg", "td_def", "sub_avg", "reach", "age"]
            present = sum(1 for f in quality_fields if fighter_data.get(f))
            fighter_data["data_quality_score"] = round(present / len(quality_fields), 2)
        else:
            fighter_data["data_quality_score"] = fighter_data["validated_quality_score"]

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
                     "slpm", "str_acc", "sapm", "str_def",
                     "td_avg", "td_acc", "td_def", "sub_avg", "age"]:
            val = data.get(key, "")
            if val:
                label = key.replace("_", " ").title()
                lines.append(f"  {label}: {val}")

        # Recent fights
        detail = data.get("detail_stats") or {}
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


def summarize_data_quality(stats: Dict[str, Any]) -> str:
    """Summarize data quality across all prefetched fighters."""
    if not stats:
        return "No prefetched data available."

    quality_fields = ["record", "slpm", "str_acc", "str_def", "td_avg", "td_def", "sub_avg", "reach", "age"]
    lines = ["=== Data Quality Summary ==="]
    total_score = 0.0
    all_missing: Dict[str, List[str]] = {}

    for fighter, data in stats.items():
        score = data.get("data_quality_score", 0.0)
        total_score += score
        missing = [f for f in quality_fields if not data.get(f)]
        if missing:
            all_missing[fighter] = missing
        ts = data.get("prefetch_timestamp")
        age_str = ""
        if ts:
            age_seconds = time.time() - ts
            if age_seconds < 60:
                age_str = f" (fetched {int(age_seconds)}s ago)"
            else:
                age_str = f" (fetched {int(age_seconds / 60)}m ago)"
        lines.append(f"  {fighter}: quality={score:.0%}{age_str}")

    avg_score = total_score / len(stats) if stats else 0.0
    lines.append(f"\n  Average quality: {avg_score:.0%} across {len(stats)} fighter(s)")

    if all_missing:
        lines.append("  Missing fields:")
        for fighter, fields in all_missing.items():
            lines.append(f"    {fighter}: {', '.join(fields)}")

    return "\n".join(lines)
