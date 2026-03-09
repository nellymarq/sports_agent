# tools/comparison.py
# Head-to-head fighter comparison from pre-fetched stats.

from __future__ import annotations
from typing import Dict, Any, Optional, List


def _parse_record(record: str) -> Dict[str, int]:
    """Parse '27-1-0' into {'wins': 27, 'losses': 1, 'draws': 0}."""
    parts = record.replace(" ", "").split("-")
    try:
        return {
            "wins": int(parts[0]) if len(parts) > 0 else 0,
            "losses": int(parts[1]) if len(parts) > 1 else 0,
            "draws": int(parts[2]) if len(parts) > 2 else 0,
        }
    except (ValueError, IndexError):
        return {"wins": 0, "losses": 0, "draws": 0}


def _parse_pct(val: str) -> Optional[float]:
    """Parse '55%' into 0.55."""
    try:
        return float(val.replace("%", "").strip()) / 100.0
    except (ValueError, AttributeError):
        return None


def _parse_float(val: str) -> Optional[float]:
    """Parse '5.2' into 5.2."""
    try:
        return float(val.strip())
    except (ValueError, AttributeError):
        return None


def _edge_label(a: Optional[float], b: Optional[float], higher_is_better: bool = True) -> str:
    """Return which fighter has the edge, or 'Even'."""
    if a is None or b is None:
        return "N/A"
    diff = a - b
    if abs(diff) < 0.02:  # within 2% is essentially even
        return "Even"
    if higher_is_better:
        return "Fighter A" if diff > 0 else "Fighter B"
    else:
        return "Fighter A" if diff < 0 else "Fighter B"


def build_comparison(
    fighter_a: Dict[str, Any],
    fighter_b: Dict[str, Any],
) -> str:
    """
    Build a structured head-to-head comparison from pre-fetched fighter stats.
    Returns a formatted string for injection into specialist context.
    """
    name_a = fighter_a.get("name", "Fighter A")
    name_b = fighter_b.get("name", "Fighter B")

    lines = [f"=== HEAD-TO-HEAD COMPARISON: {name_a} vs {name_b} ===\n"]

    # Records
    rec_a = _parse_record(fighter_a.get("record", ""))
    rec_b = _parse_record(fighter_b.get("record", ""))
    lines.append(f"Record: {name_a} ({fighter_a.get('record', 'N/A')}) vs {name_b} ({fighter_b.get('record', 'N/A')})")

    # Physical attributes
    lines.append(f"\nPhysical:")
    for attr in ["height", "weight", "reach", "stance"]:
        val_a = fighter_a.get(attr, "N/A")
        val_b = fighter_b.get(attr, "N/A")
        if val_a != "N/A" or val_b != "N/A":
            lines.append(f"  {attr.title()}: {name_a} ({val_a}) vs {name_b} ({val_b})")

    # Statistical comparison
    lines.append(f"\nStriking Stats:")

    slpm_a = _parse_float(fighter_a.get("slpm", ""))
    slpm_b = _parse_float(fighter_b.get("slpm", ""))
    edge = _edge_label(slpm_a, slpm_b)
    lines.append(f"  SLpM (Sig. Strikes/Min): {fighter_a.get('slpm', 'N/A')} vs {fighter_b.get('slpm', 'N/A')} — Edge: {edge.replace('Fighter A', name_a).replace('Fighter B', name_b)}")

    acc_a = _parse_pct(fighter_a.get("str_acc", ""))
    acc_b = _parse_pct(fighter_b.get("str_acc", ""))
    edge = _edge_label(acc_a, acc_b)
    lines.append(f"  Str. Accuracy: {fighter_a.get('str_acc', 'N/A')} vs {fighter_b.get('str_acc', 'N/A')} — Edge: {edge.replace('Fighter A', name_a).replace('Fighter B', name_b)}")

    sapm_a = _parse_float(fighter_a.get("sapm", ""))
    sapm_b = _parse_float(fighter_b.get("sapm", ""))
    edge = _edge_label(sapm_a, sapm_b, higher_is_better=False)  # lower is better
    lines.append(f"  SApM (Absorbed/Min): {fighter_a.get('sapm', 'N/A')} vs {fighter_b.get('sapm', 'N/A')} — Edge: {edge.replace('Fighter A', name_a).replace('Fighter B', name_b)}")

    def_a = _parse_pct(fighter_a.get("str_def", ""))
    def_b = _parse_pct(fighter_b.get("str_def", ""))
    edge = _edge_label(def_a, def_b)
    lines.append(f"  Str. Defense: {fighter_a.get('str_def', 'N/A')} vs {fighter_b.get('str_def', 'N/A')} — Edge: {edge.replace('Fighter A', name_a).replace('Fighter B', name_b)}")

    # Count edges
    edges_a = 0
    edges_b = 0
    for a_val, b_val, higher_better in [
        (slpm_a, slpm_b, True), (acc_a, acc_b, True),
        (sapm_a, sapm_b, False), (def_a, def_b, True),
    ]:
        lbl = _edge_label(a_val, b_val, higher_better)
        if lbl == "Fighter A":
            edges_a += 1
        elif lbl == "Fighter B":
            edges_b += 1

    lines.append(f"\nStatistical Edge Count: {name_a} ({edges_a}) vs {name_b} ({edges_b})")

    # Recent fights summary
    for fighter, name in [(fighter_a, name_a), (fighter_b, name_b)]:
        detail = fighter.get("detail_stats", {})
        recent = detail.get("recent_fights", [])
        if recent:
            wins = sum(1 for f in recent if f.get("result", "").upper().startswith("W"))
            losses = len(recent) - wins
            lines.append(f"\n{name} Last {len(recent)}: {wins}W-{losses}L")
            for f in recent[:3]:
                lines.append(f"  {f.get('result', '?')} vs {f.get('opponent', '?')} ({f.get('method', '')} R{f.get('round', '?')})")

    return "\n".join(lines)
