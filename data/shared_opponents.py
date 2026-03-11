# data/shared_opponents.py
# Shared opponent analysis: compare how two fighters performed against common opponents.

from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple

from data.history_client import HistoryDB


def _normalize_method(method: str) -> str:
    """Normalize fight method to standard categories."""
    m = (method or "").lower()
    if "ko" in m or "tko" in m:
        return "KO/TKO"
    if "sub" in m:
        return "Submission"
    if "dec" in m or "unanimous" in m or "split" in m or "majority" in m:
        return "Decision"
    return "Other"


def _round_val(r: Any) -> Optional[int]:
    try:
        return int(r)
    except (TypeError, ValueError):
        return None


def get_shared_opponent_analysis(
    fighter_a_id: str,
    fighter_b_id: str,
    fighter_a_name: str = "",
    fighter_b_name: str = "",
    db: Optional[HistoryDB] = None,
) -> Dict[str, Any]:
    """
    Analyze how two fighters performed against their shared opponents.

    Returns a dict with:
    - shared_opponents: list of common opponent IDs
    - comparisons: per-opponent performance comparison
    - summary: aggregate edge analysis
    """
    db = db or HistoryDB()

    shared_ids = db.get_shared_opponents(fighter_a_id, fighter_b_id)
    if not shared_ids:
        return {
            "shared_opponents": [],
            "comparisons": [],
            "summary": {"count": 0, "edge": "insufficient_data"},
            "fighter_a": fighter_a_name or fighter_a_id,
            "fighter_b": fighter_b_name or fighter_b_id,
        }

    # Deduplicate
    shared_ids = list(set(shared_ids))

    history_a = db.get_fighter_history(fighter_a_id)
    history_b = db.get_fighter_history(fighter_b_id)

    # Index by opponent_id
    fights_a_by_opp: Dict[str, List[Dict]] = {}
    for f in history_a:
        opp = f.get("opponent_id", "")
        if opp in shared_ids:
            fights_a_by_opp.setdefault(opp, []).append(f)

    fights_b_by_opp: Dict[str, List[Dict]] = {}
    for f in history_b:
        opp = f.get("opponent_id", "")
        if opp in shared_ids:
            fights_b_by_opp.setdefault(opp, []).append(f)

    comparisons = []
    a_wins = 0
    b_wins = 0
    a_finish = 0
    b_finish = 0
    a_faster = 0
    b_faster = 0

    for opp_id in shared_ids:
        a_fights = fights_a_by_opp.get(opp_id, [])
        b_fights = fights_b_by_opp.get(opp_id, [])
        if not a_fights or not b_fights:
            continue

        # Use most recent fight for each
        a_fight = a_fights[0]
        b_fight = b_fights[0]

        a_result = (a_fight.get("result") or "").upper().strip()
        b_result = (b_fight.get("result") or "").upper().strip()
        a_won = a_result.startswith("W")
        b_won = b_result.startswith("W")
        a_method = _normalize_method(a_fight.get("method", ""))
        b_method = _normalize_method(b_fight.get("method", ""))
        a_round = _round_val(a_fight.get("round"))
        b_round = _round_val(b_fight.get("round"))

        if a_won:
            a_wins += 1
        if b_won:
            b_wins += 1

        # Track finishes
        a_finished = a_won and a_method in ("KO/TKO", "Submission")
        b_finished = b_won and b_method in ("KO/TKO", "Submission")
        if a_finished:
            a_finish += 1
        if b_finished:
            b_finish += 1

        # Track speed (lower round = faster)
        if a_finished and b_finished and a_round and b_round:
            if a_round < b_round:
                a_faster += 1
            elif b_round < a_round:
                b_faster += 1

        comp = {
            "opponent_id": opp_id,
            "fighter_a": {
                "result": a_result,
                "method": a_method,
                "round": a_round,
                "date": a_fight.get("date"),
            },
            "fighter_b": {
                "result": b_result,
                "method": b_method,
                "round": b_round,
                "date": b_fight.get("date"),
            },
        }
        comparisons.append(comp)

    count = len(comparisons)
    if count == 0:
        edge = "insufficient_data"
    elif a_wins > b_wins:
        edge = "fighter_a"
    elif b_wins > a_wins:
        edge = "fighter_b"
    else:
        edge = "even"

    name_a = fighter_a_name or fighter_a_id
    name_b = fighter_b_name or fighter_b_id

    return {
        "shared_opponents": shared_ids,
        "comparisons": comparisons,
        "summary": {
            "count": count,
            "edge": edge,
            "fighter_a_wins": a_wins,
            "fighter_b_wins": b_wins,
            "fighter_a_finishes": a_finish,
            "fighter_b_finishes": b_finish,
            "fighter_a_faster_finishes": a_faster,
            "fighter_b_faster_finishes": b_faster,
        },
        "fighter_a": name_a,
        "fighter_b": name_b,
    }


def format_shared_opponent_report(analysis: Dict[str, Any]) -> str:
    """Format shared opponent analysis into a readable report."""
    name_a = analysis.get("fighter_a", "Fighter A")
    name_b = analysis.get("fighter_b", "Fighter B")
    summary = analysis.get("summary", {})
    comparisons = analysis.get("comparisons", [])

    if summary.get("count", 0) == 0:
        return f"No shared opponents found between {name_a} and {name_b}."

    lines = [
        f"=== SHARED OPPONENT ANALYSIS: {name_a} vs {name_b} ===",
        f"Common opponents: {summary['count']}",
        "",
    ]

    for comp in comparisons:
        opp = comp["opponent_id"]
        fa = comp["fighter_a"]
        fb = comp["fighter_b"]
        lines.append(f"  vs {opp}:")
        a_str = f"    {name_a}: {fa['result']} via {fa['method']}"
        if fa["round"]:
            a_str += f" (R{fa['round']})"
        b_str = f"    {name_b}: {fb['result']} via {fb['method']}"
        if fb["round"]:
            b_str += f" (R{fb['round']})"
        lines.extend([a_str, b_str, ""])

    lines.append("--- Summary ---")
    lines.append(f"  {name_a} wins: {summary['fighter_a_wins']}/{summary['count']}")
    lines.append(f"  {name_b} wins: {summary['fighter_b_wins']}/{summary['count']}")
    lines.append(f"  {name_a} finishes: {summary['fighter_a_finishes']}")
    lines.append(f"  {name_b} finishes: {summary['fighter_b_finishes']}")

    edge = summary.get("edge", "insufficient_data")
    if edge == "fighter_a":
        lines.append(f"  Edge: {name_a}")
    elif edge == "fighter_b":
        lines.append(f"  Edge: {name_b}")
    elif edge == "even":
        lines.append("  Edge: Even")
    else:
        lines.append("  Edge: Insufficient data")

    return "\n".join(lines)
