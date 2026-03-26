# data/line_tracker.py
# Line movement tracker: records odds snapshots over time for trend analysis.
# Enables opening vs closing line comparison, steam move detection, and
# reverse line movement (RLM) identification.

from __future__ import annotations
import json
import os
import time
import threading
from typing import Dict, Any, List, Optional

try:
    from config import STEAM_MOVE_THRESHOLD
except ImportError:
    STEAM_MOVE_THRESHOLD = 0.05


TRACKER_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "state")
LINE_HISTORY_PATH = os.path.join(TRACKER_DIR, "line_history.json")

os.makedirs(TRACKER_DIR, exist_ok=True)

_lock = threading.Lock()


def _load_history() -> Dict[str, List[Dict[str, Any]]]:
    """Load line history from disk. Key = bout_key, Value = list of snapshots."""
    if not os.path.exists(LINE_HISTORY_PATH):
        return {}
    try:
        with open(LINE_HISTORY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_history(history: Dict[str, List[Dict[str, Any]]]) -> None:
    tmp = LINE_HISTORY_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    os.replace(tmp, LINE_HISTORY_PATH)


def record_odds_snapshot(
    bout_key: str,
    fighter_a: str,
    fighter_b: str,
    odds_a: Optional[float] = None,
    odds_b: Optional[float] = None,
    implied_a: Optional[float] = None,
    implied_b: Optional[float] = None,
    source: str = "unknown",
) -> Dict[str, Any]:
    """
    Record an odds snapshot for a bout.

    Args:
        bout_key: Unique bout identifier
        fighter_a/b: Fighter names
        odds_a/b: Decimal odds for each fighter
        implied_a/b: Implied probabilities
        source: Odds source (e.g., "draftkings", "polymarket")
    """
    snapshot = {
        "timestamp": time.time(),
        "fighter_a": fighter_a,
        "fighter_b": fighter_b,
        "odds_a": odds_a,
        "odds_b": odds_b,
        "implied_a": implied_a,
        "implied_b": implied_b,
        "source": source,
    }

    with _lock:
        history = _load_history()
        if bout_key not in history:
            history[bout_key] = []
        history[bout_key].append(snapshot)
        _save_history(history)

    return snapshot


def get_line_movement(bout_key: str) -> Optional[Dict[str, Any]]:
    """
    Analyze line movement for a specific bout.

    Returns:
        Dict with opening/current/movement analysis, or None if no data.
    """
    with _lock:
        history = _load_history()

    snapshots = history.get(bout_key, [])
    if not snapshots:
        return None

    # Sort by timestamp
    sorted_snaps = sorted(snapshots, key=lambda s: s.get("timestamp", 0))
    opening = sorted_snaps[0]
    current = sorted_snaps[-1]

    result: Dict[str, Any] = {
        "bout_key": bout_key,
        "fighter_a": opening.get("fighter_a", ""),
        "fighter_b": opening.get("fighter_b", ""),
        "snapshot_count": len(sorted_snaps),
        "opening": {
            "odds_a": opening.get("odds_a"),
            "odds_b": opening.get("odds_b"),
            "implied_a": opening.get("implied_a"),
            "implied_b": opening.get("implied_b"),
            "timestamp": opening.get("timestamp"),
        },
        "current": {
            "odds_a": current.get("odds_a"),
            "odds_b": current.get("odds_b"),
            "implied_a": current.get("implied_a"),
            "implied_b": current.get("implied_b"),
            "timestamp": current.get("timestamp"),
        },
    }

    # Calculate movement
    if opening.get("implied_a") is not None and current.get("implied_a") is not None:
        move_a = current["implied_a"] - opening["implied_a"]
        move_b = current["implied_b"] - opening["implied_b"] if current.get("implied_b") and opening.get("implied_b") else None

        result["movement"] = {
            "fighter_a_shift": round(move_a, 4),
            "fighter_b_shift": round(move_b, 4) if move_b is not None else None,
            "direction": _classify_movement(move_a),
            "magnitude": _classify_magnitude(abs(move_a)),
        }

        # Steam move detection (large, fast movement)
        if len(sorted_snaps) >= 2:
            result["steam_move"] = _detect_steam_move(sorted_snaps)
    else:
        result["movement"] = None

    return result


def get_all_movements() -> List[Dict[str, Any]]:
    """Get line movement analysis for all tracked bouts."""
    with _lock:
        history = _load_history()

    movements = []
    for bout_key in history:
        movement = get_line_movement(bout_key)
        if movement:
            movements.append(movement)

    return movements


def _classify_movement(shift: float) -> str:
    """Classify the direction and significance of a line movement."""
    if abs(shift) < 0.02:
        return "stable"
    elif shift > 0:
        return "fighter_a_steaming"  # A's implied prob increasing = money on A
    else:
        return "fighter_b_steaming"


def _classify_magnitude(abs_shift: float) -> str:
    """Classify the magnitude of a line movement."""
    if abs_shift < 0.02:
        return "negligible"
    elif abs_shift < 0.05:
        return "minor"
    elif abs_shift < 0.10:
        return "moderate"
    elif abs_shift < 0.15:
        return "significant"
    else:
        return "major"


def _detect_steam_move(snapshots: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Detect steam moves — rapid, significant line shifts.
    A steam move is a 5%+ shift within a 2-hour window.
    """
    for i in range(len(snapshots) - 1):
        for j in range(i + 1, len(snapshots)):
            t_diff = snapshots[j].get("timestamp", 0) - snapshots[i].get("timestamp", 0)
            if t_diff <= 0 or t_diff > 7200:  # 2 hours
                continue

            imp_i = snapshots[i].get("implied_a", 0)
            imp_j = snapshots[j].get("implied_a", 0)
            if imp_i is None or imp_j is None:
                continue

            shift = abs(imp_j - imp_i)
            if shift >= STEAM_MOVE_THRESHOLD:
                return {
                    "detected": True,
                    "shift": round(imp_j - imp_i, 4),
                    "time_window_seconds": round(t_diff),
                    "from_snapshot": i,
                    "to_snapshot": j,
                }

    return {"detected": False}


def format_line_movement(movement: Dict[str, Any]) -> str:
    """Format line movement data as readable text."""
    if not movement:
        return "No line data available."

    lines = [
        f"LINE MOVEMENT: {movement['fighter_a']} vs {movement['fighter_b']}",
        f"  Snapshots: {movement['snapshot_count']}",
    ]

    opening = movement.get("opening", {})
    current = movement.get("current", {})

    if opening.get("implied_a") is not None:
        lines.append(f"  Opening: {opening['implied_a']*100:.1f}% / {opening.get('implied_b', 0)*100:.1f}%")
    if current.get("implied_a") is not None:
        lines.append(f"  Current: {current['implied_a']*100:.1f}% / {current.get('implied_b', 0)*100:.1f}%")

    mv = movement.get("movement")
    if mv:
        lines.append(f"  Direction: {mv['direction']} ({mv['magnitude']})")
        lines.append(f"  Shift: {mv['fighter_a_shift']:+.1%}")

    steam = movement.get("steam_move", {})
    if steam.get("detected"):
        lines.append(f"  STEAM MOVE DETECTED: {steam['shift']:+.1%} in {steam['time_window_seconds']}s")

    return "\n".join(lines)
