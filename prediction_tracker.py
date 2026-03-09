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
        "timestamp": time.time(),
        "actual_winner": None,
        "actual_method": None,
        "correct": None,
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
) -> Optional[Dict[str, Any]]:
    """Record the actual result for a previously tracked prediction."""
    preds = _load_predictions()
    updated = None

    for p in preds:
        if (
            p["event_id"] == event_id
            and p["fighter_a"] == fighter_a
            and p["fighter_b"] == fighter_b
            and p["actual_winner"] is None
        ):
            p["actual_winner"] = actual_winner
            p["actual_method"] = actual_method
            p["correct"] = (p["predicted_winner"].lower() == actual_winner.lower())
            updated = p
            break

    if updated:
        _save_predictions(preds)
    return updated


def get_calibration_stats() -> Dict[str, Any]:
    """
    Compute calibration metrics:
    - Overall accuracy
    - Accuracy by confidence tier
    - Accuracy by probability bucket (50-60%, 60-70%, 70-80%, 80%+)
    - Brier score (lower is better)
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

    return {
        "total_predictions": len(preds),
        "resolved": total,
        "correct": correct,
        "accuracy": round(accuracy, 3),
        "brier_score": round(brier, 4),
        "by_tier": tier_accuracy,
        "by_probability": bucket_accuracy,
    }
