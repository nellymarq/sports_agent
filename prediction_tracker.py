# prediction_tracker.py
# Tracks predictions and results for calibration analysis.
# Stores predictions as JSON records, allows recording actual outcomes,
# and computes calibration metrics over time.

from __future__ import annotations
import os
import json
import time
from typing import Dict, Any, List, Optional

TRACKER_DIR = os.path.join(os.path.dirname(__file__), "state")
PREDICTIONS_PATH = os.path.join(TRACKER_DIR, "predictions.json")

os.makedirs(TRACKER_DIR, exist_ok=True)


def _load_predictions() -> List[Dict[str, Any]]:
    if not os.path.exists(PREDICTIONS_PATH):
        return []
    try:
        with open(PREDICTIONS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_predictions(preds: List[Dict[str, Any]]) -> None:
    tmp = PREDICTIONS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(preds, f, indent=2, ensure_ascii=False)
    os.replace(tmp, PREDICTIONS_PATH)


def record_prediction(
    event_id: str,
    fighter_a: str,
    fighter_b: str,
    predicted_winner: str,
    win_probability: float,
    confidence_tier: str = "",
    method_lean: str = "",
    weight_class: str = "",
    method_probabilities: Optional[Dict[str, int]] = None,
    round_probabilities: Optional[Dict[str, int]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Record a new prediction for later calibration."""
    entry = {
        "id": f"{event_id}_{fighter_a}_{fighter_b}_{int(time.time())}",
        "event_id": event_id,
        "fighter_a": fighter_a,
        "fighter_b": fighter_b,
        "predicted_winner": predicted_winner,
        "win_probability": win_probability,
        "confidence_tier": confidence_tier,
        "method_lean": method_lean,
        "weight_class": weight_class,
        "method_probabilities": method_probabilities or {},
        "round_probabilities": round_probabilities or {},
        "timestamp": time.time(),
        "actual_winner": None,
        "actual_method": None,
        "actual_round": None,
        "correct": None,
        "method_correct": None,
        "metadata": metadata or {},
    }

    preds = _load_predictions()
    preds.append(entry)
    _save_predictions(preds)
    return entry


def record_result(
    event_id: str,
    fighter_a: str,
    fighter_b: str,
    actual_winner: str,
    actual_method: str = "",
    actual_round: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """Record the actual result for a previously tracked prediction."""
    preds = _load_predictions()
    updated = None

    for p in preds:
        if (
            p["event_id"] == event_id
            and p["fighter_a"] == fighter_a
            and p["fighter_b"] == fighter_b
            and p.get("actual_winner") is None
        ):
            p["actual_winner"] = actual_winner
            p["actual_method"] = actual_method
            p["actual_round"] = actual_round
            p["correct"] = (p["predicted_winner"].lower() == actual_winner.lower())

            # Check method accuracy
            method_lean = (p.get("method_lean") or "").lower()
            actual_lower = actual_method.lower()
            if method_lean and method_lean != "no strong lean":
                lean_key = method_lean.split("/")[0].strip()
                p["method_correct"] = (lean_key in actual_lower or actual_lower in lean_key)
            else:
                p["method_correct"] = None

            updated = p
            break

    if updated:
        _save_predictions(preds)
    return updated


def _compute_method_dist_score(resolved: List[Dict[str, Any]]) -> Optional[float]:
    """
    Compute log-loss for method probability distributions.
    Only evaluates predictions that have method_probabilities and actual_method.
    Lower is better (0 = perfect).
    """
    import math
    eligible = []
    for p in resolved:
        mp = p.get("method_probabilities")
        actual = (p.get("actual_method") or "").lower()
        if not mp or not actual:
            continue
        # Map actual method to our categories
        if "ko" in actual or "tko" in actual:
            actual_key = "ko_tko"
        elif "sub" in actual:
            actual_key = "submission"
        elif "dec" in actual or "unanimous" in actual or "split" in actual or "majority" in actual:
            actual_key = "decision"
        else:
            continue
        prob = mp.get(actual_key, 0) / 100.0
        prob = max(prob, 0.01)  # avoid log(0)
        eligible.append(-math.log(prob))

    if not eligible:
        return None
    return round(sum(eligible) / len(eligible), 4)


def get_calibration_stats() -> Dict[str, Any]:
    """
    Compute calibration metrics:
    - Overall accuracy
    - Accuracy by confidence tier
    - Accuracy by probability bucket (50-60%, 60-70%, 70-80%, 80%+)
    - Brier score (lower is better)
    - Method prediction accuracy
    - Event-level breakdown
    """
    preds = _load_predictions()
    resolved = [p for p in preds if p.get("correct") is not None]

    if not resolved:
        return {
            "total_predictions": len(preds),
            "resolved": 0,
            "accuracy": None,
            "message": "No resolved predictions yet.",
        }

    total = len(resolved)
    correct = sum(1 for p in resolved if p["correct"])
    accuracy = correct / total

    # Brier score
    brier = sum(
        (p["win_probability"] - (1.0 if p["correct"] else 0.0)) ** 2
        for p in resolved
    ) / total

    # By tier
    tier_stats: Dict[str, Dict[str, int]] = {}
    for p in resolved:
        tier = p.get("confidence_tier", "Unknown")
        if tier not in tier_stats:
            tier_stats[tier] = {"total": 0, "correct": 0}
        tier_stats[tier]["total"] += 1
        if p["correct"]:
            tier_stats[tier]["correct"] += 1

    tier_accuracy = {
        tier: round(s["correct"] / s["total"], 3) if s["total"] > 0 else None
        for tier, s in tier_stats.items()
    }

    # By probability bucket
    buckets = {"50-60%": [], "60-70%": [], "70-80%": [], "80%+": []}
    for p in resolved:
        prob = p["win_probability"]
        if prob < 0.6:
            buckets["50-60%"].append(p["correct"])
        elif prob < 0.7:
            buckets["60-70%"].append(p["correct"])
        elif prob < 0.8:
            buckets["70-80%"].append(p["correct"])
        else:
            buckets["80%+"].append(p["correct"])

    bucket_accuracy = {}
    for bucket, results in buckets.items():
        if results:
            bucket_accuracy[bucket] = {
                "total": len(results),
                "correct": sum(results),
                "accuracy": round(sum(results) / len(results), 3),
            }

    # Method prediction accuracy
    method_stats: Dict[str, Dict[str, int]] = {}
    for p in resolved:
        method_lean = p.get("method_lean", "").strip()
        actual_method = (p.get("actual_method") or "").strip().lower()
        if not method_lean or method_lean.lower() == "no strong lean":
            continue
        lean_key = method_lean.split("/")[0].strip().lower() if "/" in method_lean else method_lean.lower()
        if lean_key not in method_stats:
            method_stats[lean_key] = {"total": 0, "correct": 0}
        method_stats[lean_key]["total"] += 1
        if lean_key in actual_method or actual_method in lean_key:
            method_stats[lean_key]["correct"] += 1

    method_accuracy = {
        method: {
            "total": s["total"],
            "correct": s["correct"],
            "accuracy": round(s["correct"] / s["total"], 3) if s["total"] > 0 else None,
        }
        for method, s in method_stats.items()
    }

    # By event
    event_stats: Dict[str, Dict[str, int]] = {}
    for p in resolved:
        eid = p.get("event_id", "unknown")
        if eid not in event_stats:
            event_stats[eid] = {"total": 0, "correct": 0}
        event_stats[eid]["total"] += 1
        if p["correct"]:
            event_stats[eid]["correct"] += 1

    event_accuracy = {
        eid: {
            "total": s["total"],
            "correct": s["correct"],
            "accuracy": round(s["correct"] / s["total"], 3) if s["total"] > 0 else None,
        }
        for eid, s in event_stats.items()
    }

    # By weight class
    wc_stats: Dict[str, Dict[str, int]] = {}
    for p in resolved:
        wc = p.get("weight_class", "").strip() or "Unknown"
        if wc not in wc_stats:
            wc_stats[wc] = {"total": 0, "correct": 0}
        wc_stats[wc]["total"] += 1
        if p["correct"]:
            wc_stats[wc]["correct"] += 1

    wc_accuracy = {
        wc: {
            "total": s["total"],
            "correct": s["correct"],
            "accuracy": round(s["correct"] / s["total"], 3) if s["total"] > 0 else None,
        }
        for wc, s in wc_stats.items()
    }

    # Method distribution accuracy (for predictions with method_probabilities)
    method_dist_log_loss = _compute_method_dist_score(resolved)

    # Favorite/underdog split
    fav_stats = {"total": 0, "correct": 0}
    dog_stats = {"total": 0, "correct": 0}
    for p in resolved:
        prob = p.get("win_probability", 0.5)
        if prob >= 0.6:
            fav_stats["total"] += 1
            if p["correct"]:
                fav_stats["correct"] += 1
        elif prob <= 0.4:
            dog_stats["total"] += 1
            if p["correct"]:
                dog_stats["correct"] += 1

    # Rolling accuracy trend (last N resolved predictions)
    accuracy_trend = _compute_rolling_accuracy(resolved)

    return {
        "total_predictions": len(preds),
        "resolved": total,
        "correct": correct,
        "accuracy": round(accuracy, 3),
        "brier_score": round(brier, 4),
        "by_tier": tier_accuracy,
        "by_probability": bucket_accuracy,
        "by_method": method_accuracy,
        "by_event": event_accuracy,
        "by_weight_class": wc_accuracy,
        "favorite_accuracy": {
            "total": fav_stats["total"],
            "correct": fav_stats["correct"],
            "accuracy": round(fav_stats["correct"] / fav_stats["total"], 3) if fav_stats["total"] > 0 else None,
        },
        "underdog_accuracy": {
            "total": dog_stats["total"],
            "correct": dog_stats["correct"],
            "accuracy": round(dog_stats["correct"] / dog_stats["total"], 3) if dog_stats["total"] > 0 else None,
        },
        "method_distribution_score": method_dist_log_loss,
        "accuracy_trend": accuracy_trend,
    }


def _compute_rolling_accuracy(
    resolved: List[Dict[str, Any]], window: int = 10
) -> List[Dict[str, Any]]:
    """
    Compute rolling accuracy over resolved predictions.
    Returns a list of data points for trending charts.
    Each point: {index, rolling_accuracy, rolling_brier, cumulative_accuracy}
    """
    if len(resolved) < 2:
        return []

    # Sort by timestamp for chronological ordering
    sorted_preds = sorted(resolved, key=lambda p: p.get("timestamp", 0))

    trend = []
    for i, p in enumerate(sorted_preds):
        idx = i + 1

        # Cumulative accuracy
        cum_correct = sum(1 for pp in sorted_preds[:idx] if pp["correct"])
        cum_acc = round(cum_correct / idx, 3)

        # Rolling window accuracy
        window_start = max(0, idx - window)
        window_preds = sorted_preds[window_start:idx]
        roll_correct = sum(1 for pp in window_preds if pp["correct"])
        roll_acc = round(roll_correct / len(window_preds), 3)

        # Rolling Brier score
        roll_brier = sum(
            (pp["win_probability"] - (1.0 if pp["correct"] else 0.0)) ** 2
            for pp in window_preds
        ) / len(window_preds)

        point = {
            "index": idx,
            "rolling_accuracy": roll_acc,
            "rolling_brier": round(roll_brier, 4),
            "cumulative_accuracy": cum_acc,
        }

        # Add timestamp if available
        ts = p.get("timestamp")
        if ts:
            point["timestamp"] = ts

        trend.append(point)

    return trend
