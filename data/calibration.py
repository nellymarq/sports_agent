# data/calibration.py
# Advanced prediction calibration and backtesting framework.
# Feature importance, calibration decomposition, upset analysis,
# model vs market comparison, and recalibration suggestions.

from __future__ import annotations
import math
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict


# ============================================================
# FEATURE IMPORTANCE (PSEUDO-SHAPLEY)
# ============================================================

def compute_feature_importance(
    resolved_predictions: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Analyze which prediction features correlate with correct outcomes.
    Returns ranked features by predictive power.
    """
    if not resolved_predictions:
        return []

    features = {
        "high_confidence": {"correct": 0, "total": 0},
        "medium_confidence": {"correct": 0, "total": 0},
        "low_confidence": {"correct": 0, "total": 0},
        "strong_method_lean": {"correct": 0, "total": 0},
        "large_edge": {"correct": 0, "total": 0},
        "moderate_edge": {"correct": 0, "total": 0},
        "slim_edge": {"correct": 0, "total": 0},
        "favorite_pick": {"correct": 0, "total": 0},
        "underdog_pick": {"correct": 0, "total": 0},
        "toss_up": {"correct": 0, "total": 0},
    }

    for p in resolved_predictions:
        prob = p.get("win_probability", 0.5)
        correct = p.get("correct", False)
        tier = (p.get("confidence_tier") or "").lower()
        method_lean = (p.get("method_lean") or "").strip()

        # Confidence tier
        if "high" in tier or "very" in tier:
            features["high_confidence"]["total"] += 1
            if correct:
                features["high_confidence"]["correct"] += 1
        elif "medium" in tier or "moderate" in tier:
            features["medium_confidence"]["total"] += 1
            if correct:
                features["medium_confidence"]["correct"] += 1
        else:
            features["low_confidence"]["total"] += 1
            if correct:
                features["low_confidence"]["correct"] += 1

        # Method lean strength
        if method_lean and method_lean.lower() != "no strong lean":
            features["strong_method_lean"]["total"] += 1
            if correct:
                features["strong_method_lean"]["correct"] += 1

        # Edge size
        edge = abs(prob - 0.5)
        if edge >= 0.20:
            features["large_edge"]["total"] += 1
            if correct:
                features["large_edge"]["correct"] += 1
        elif edge >= 0.10:
            features["moderate_edge"]["total"] += 1
            if correct:
                features["moderate_edge"]["correct"] += 1
        else:
            features["slim_edge"]["total"] += 1
            if correct:
                features["slim_edge"]["correct"] += 1

        # Favorite vs underdog
        if prob >= 0.65:
            features["favorite_pick"]["total"] += 1
            if correct:
                features["favorite_pick"]["correct"] += 1
        elif prob <= 0.45:
            features["underdog_pick"]["total"] += 1
            if correct:
                features["underdog_pick"]["correct"] += 1
        else:
            features["toss_up"]["total"] += 1
            if correct:
                features["toss_up"]["correct"] += 1

    # Compute accuracy for each feature
    results = []
    for feature, stats in features.items():
        if stats["total"] > 0:
            accuracy = stats["correct"] / stats["total"]
            results.append({
                "feature": feature,
                "accuracy": round(accuracy, 3),
                "total": stats["total"],
                "correct": stats["correct"],
                "predictive_power": round(abs(accuracy - 0.5) * 2, 3),
            })

    results.sort(key=lambda x: x["predictive_power"], reverse=True)
    return results


# ============================================================
# CALIBRATION ERROR DECOMPOSITION
# ============================================================

def decompose_calibration_error(
    resolved_predictions: List[Dict[str, Any]],
    n_bins: int = 5,
) -> Dict[str, Any]:
    """
    Decompose calibration into reliability, resolution, and sharpness.
    """
    if not resolved_predictions:
        return {"error": "No resolved predictions"}

    n = len(resolved_predictions)
    overall_rate = sum(1 for p in resolved_predictions if p.get("correct")) / n

    # Bin predictions by probability
    bins: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for p in resolved_predictions:
        prob = p.get("win_probability", 0.5)
        bin_idx = min(int(prob * n_bins), n_bins - 1)
        bins[bin_idx].append(p)

    # Reliability (lower is better): avg squared diff between predicted prob and actual rate in each bin
    reliability = 0.0
    for bin_idx, preds in bins.items():
        if not preds:
            continue
        bin_size = len(preds)
        avg_predicted = sum(p.get("win_probability", 0.5) for p in preds) / bin_size
        actual_rate = sum(1 for p in preds if p.get("correct")) / bin_size
        reliability += bin_size * (avg_predicted - actual_rate) ** 2
    reliability /= n

    # Resolution (higher is better): how much the model separates outcomes
    resolution = 0.0
    for bin_idx, preds in bins.items():
        if not preds:
            continue
        bin_size = len(preds)
        actual_rate = sum(1 for p in preds if p.get("correct")) / bin_size
        resolution += bin_size * (actual_rate - overall_rate) ** 2
    resolution /= n

    # Sharpness: how far predictions are from 50% (confident vs uncertain)
    sharpness = sum(
        (p.get("win_probability", 0.5) - 0.5) ** 2 for p in resolved_predictions
    ) / n

    # Brier score = reliability - resolution + uncertainty
    uncertainty = overall_rate * (1 - overall_rate)
    brier = reliability - resolution + uncertainty

    return {
        "reliability": round(reliability, 4),
        "resolution": round(resolution, 4),
        "sharpness": round(sharpness, 4),
        "uncertainty": round(uncertainty, 4),
        "brier_score": round(brier, 4),
        "interpretation": {
            "reliability": "good" if reliability < 0.02 else "moderate" if reliability < 0.05 else "poor",
            "resolution": "good" if resolution > 0.03 else "moderate" if resolution > 0.01 else "poor",
            "sharpness": "sharp" if sharpness > 0.04 else "moderate" if sharpness > 0.02 else "diffuse",
        },
        "n_predictions": n,
        "overall_base_rate": round(overall_rate, 3),
    }


# ============================================================
# UPSET PATTERN ANALYSIS
# ============================================================

def analyze_upset_patterns(
    resolved_predictions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    For all incorrect predictions, find common patterns.
    """
    incorrect = [p for p in resolved_predictions if p.get("correct") is False]
    correct = [p for p in resolved_predictions if p.get("correct") is True]

    if not incorrect:
        return {"total_upsets": 0, "upsets": 0, "message": "No upsets to analyze"}

    # By weight class
    wc_upsets: Dict[str, int] = defaultdict(int)
    wc_totals: Dict[str, int] = defaultdict(int)
    for p in resolved_predictions:
        wc = p.get("weight_class", "Unknown")
        wc_totals[wc] += 1
        if not p.get("correct"):
            wc_upsets[wc] += 1

    wc_rates = {
        wc: {
            "upset_rate": round(wc_upsets.get(wc, 0) / total, 3),
            "upsets": wc_upsets.get(wc, 0),
            "total": total,
        }
        for wc, total in wc_totals.items()
        if total >= 2
    }

    # By confidence level
    high_conf_upsets = sum(
        1 for p in incorrect
        if p.get("win_probability", 0) >= 0.70
    )
    total_high_conf = sum(
        1 for p in resolved_predictions
        if p.get("win_probability", 0) >= 0.70
    )

    # By method lean
    method_lean_wrong = defaultdict(int)
    for p in incorrect:
        lean = (p.get("method_lean") or "unknown").lower()
        method_lean_wrong[lean] += 1

    # Probability distribution of upsets
    upset_probs = [p.get("win_probability", 0.5) for p in incorrect]
    avg_upset_confidence = sum(upset_probs) / len(upset_probs) if upset_probs else 0

    return {
        "total_upsets": len(incorrect),
        "total_predictions": len(resolved_predictions),
        "upset_rate": round(len(incorrect) / max(len(resolved_predictions), 1), 3),
        "avg_upset_confidence": round(avg_upset_confidence, 3),
        "high_confidence_upsets": {
            "count": high_conf_upsets,
            "total_high_conf": total_high_conf,
            "rate": round(high_conf_upsets / max(total_high_conf, 1), 3),
        },
        "by_weight_class": dict(sorted(
            wc_rates.items(),
            key=lambda x: x[1]["upset_rate"],
            reverse=True,
        )),
        "by_method_lean_wrong": dict(method_lean_wrong),
        "vulnerability_factors": _identify_vulnerability_factors(incorrect),
    }


def _identify_vulnerability_factors(incorrect: List[Dict[str, Any]]) -> List[str]:
    """Identify common factors in upsets."""
    factors = []
    if not incorrect:
        return factors

    avg_prob = sum(p.get("win_probability", 0.5) for p in incorrect) / len(incorrect)
    if avg_prob > 0.65:
        factors.append("Model tends to be overconfident in favorites")

    method_leans = [p.get("method_lean", "") for p in incorrect]
    if method_leans.count("Decision") > len(incorrect) * 0.5:
        factors.append("Decision-leaning predictions upset more often")

    return factors


# ============================================================
# CALIBRATION ADJUSTER
# ============================================================

def suggest_calibration_adjustment(
    resolved_predictions: List[Dict[str, Any]],
    n_bins: int = 5,
) -> Dict[str, Any]:
    """
    If model is systematically over/under-confident, suggest recalibration.
    Uses piecewise linear approximation of isotonic regression.
    """
    if len(resolved_predictions) < 10:
        return {"message": "Need at least 10 resolved predictions for recalibration"}

    # Bin predictions
    bins = defaultdict(list)
    for p in resolved_predictions:
        prob = p.get("win_probability", 0.5)
        bin_idx = min(int(prob * n_bins), n_bins - 1)
        bins[bin_idx].append(p)

    # Build mapping: predicted_avg -> actual_rate
    adjustment_points = []
    total_overconfidence = 0
    total_underconfidence = 0
    count = 0

    for bin_idx in sorted(bins.keys()):
        preds = bins[bin_idx]
        if not preds:
            continue
        avg_predicted = sum(p.get("win_probability", 0.5) for p in preds) / len(preds)
        actual_rate = sum(1 for p in preds if p.get("correct")) / len(preds)
        gap = avg_predicted - actual_rate

        if gap > 0:
            total_overconfidence += gap
        else:
            total_underconfidence += abs(gap)
        count += 1

        adjustment_points.append({
            "predicted_range": f"{bin_idx/n_bins:.0%}-{(bin_idx+1)/n_bins:.0%}",
            "avg_predicted": round(avg_predicted, 3),
            "actual_rate": round(actual_rate, 3),
            "adjustment_needed": round(-gap, 3),
            "sample_size": len(preds),
        })

    avg_over = total_overconfidence / max(count, 1)
    avg_under = total_underconfidence / max(count, 1)

    if avg_over > avg_under + 0.02:
        direction = "overconfident"
        suggestion = f"Reduce predicted probabilities by ~{avg_over*100:.1f}%"
    elif avg_under > avg_over + 0.02:
        direction = "underconfident"
        suggestion = f"Increase predicted probabilities by ~{avg_under*100:.1f}%"
    else:
        direction = "well_calibrated"
        suggestion = "Model is reasonably well-calibrated"

    return {
        "direction": direction,
        "suggestion": suggestion,
        "overconfidence_score": round(avg_over, 4),
        "underconfidence_score": round(avg_under, 4),
        "adjustment_points": adjustment_points,
    }


# ============================================================
# MODEL VS MARKET COMPARISON
# ============================================================

def compare_against_market(
    resolved_predictions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Compare model accuracy vs market (closing odds) accuracy.
    """
    # Filter predictions that have market odds in metadata
    eligible = []
    for p in resolved_predictions:
        meta = p.get("metadata", {})
        market_implied = meta.get("market_implied") or meta.get("implied_probability")
        if market_implied is not None:
            eligible.append({**p, "_market_implied": float(market_implied)})

    if not eligible:
        return {"message": "No predictions with market odds data available"}

    model_brier = sum(
        (p["win_probability"] - (1.0 if p["correct"] else 0.0)) ** 2
        for p in eligible
    ) / len(eligible)

    market_brier = sum(
        (p["_market_implied"] - (1.0 if p["correct"] else 0.0)) ** 2
        for p in eligible
    ) / len(eligible)

    # Where model beats market
    model_better = 0
    market_better = 0
    for p in eligible:
        model_error = abs(p["win_probability"] - (1.0 if p["correct"] else 0.0))
        market_error = abs(p["_market_implied"] - (1.0 if p["correct"] else 0.0))
        if model_error < market_error:
            model_better += 1
        elif market_error < model_error:
            market_better += 1

    return {
        "eligible_predictions": len(eligible),
        "model_brier_score": round(model_brier, 4),
        "market_brier_score": round(market_brier, 4),
        "model_beats_market": model_brier < market_brier,
        "edge_pct": round((market_brier - model_brier) / max(market_brier, 0.001) * 100, 1),
        "model_more_accurate_count": model_better,
        "market_more_accurate_count": market_better,
    }


# ============================================================
# STREAK & MOMENTUM ANALYSIS
# ============================================================

def analyze_prediction_streaks(
    resolved_predictions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Track correct/incorrect streaks and hot/cold detection.
    """
    if not resolved_predictions:
        return {"message": "No resolved predictions"}

    sorted_preds = sorted(resolved_predictions, key=lambda p: p.get("timestamp", 0))

    streaks = []
    current_len = 0
    current_type = None
    longest_correct = 0
    longest_incorrect = 0

    for p in sorted_preds:
        c = p.get("correct")
        if c == current_type:
            current_len += 1
        else:
            if current_type is not None:
                streaks.append({"type": "correct" if current_type else "incorrect", "length": current_len})
            current_type = c
            current_len = 1

        if c:
            longest_correct = max(longest_correct, current_len)
        else:
            longest_incorrect = max(longest_incorrect, current_len)

    if current_type is not None:
        streaks.append({"type": "correct" if current_type else "incorrect", "length": current_len})

    # Hot/cold detection: last 5 predictions
    last_5 = sorted_preds[-5:] if len(sorted_preds) >= 5 else sorted_preds
    last_5_correct = sum(1 for p in last_5 if p.get("correct"))
    last_5_rate = last_5_correct / len(last_5)

    if last_5_rate >= 0.8:
        indicator = "hot"
    elif last_5_rate <= 0.2:
        indicator = "cold"
    else:
        indicator = "neutral"

    return {
        "longest_correct_streak": longest_correct,
        "longest_incorrect_streak": longest_incorrect,
        "current_streak": streaks[-1] if streaks else None,
        "hot_cold_indicator": indicator,
        "last_5_accuracy": round(last_5_rate, 2),
        "total_streaks": len(streaks),
        "regression_alert": indicator == "cold",
    }


# ============================================================
# MULTI-DIMENSIONAL ACCURACY BREAKDOWN
# ============================================================

def accuracy_by_dimension(
    resolved_predictions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Break down accuracy by every available dimension.
    """
    dimensions: Dict[str, Dict[str, Dict[str, int]]] = {
        "weight_class": defaultdict(lambda: {"total": 0, "correct": 0}),
        "confidence_tier": defaultdict(lambda: {"total": 0, "correct": 0}),
        "method_lean": defaultdict(lambda: {"total": 0, "correct": 0}),
        "probability_bucket": defaultdict(lambda: {"total": 0, "correct": 0}),
    }

    for p in resolved_predictions:
        correct = p.get("correct", False)

        # Weight class
        wc = p.get("weight_class", "Unknown")
        dimensions["weight_class"][wc]["total"] += 1
        if correct:
            dimensions["weight_class"][wc]["correct"] += 1

        # Confidence tier
        tier = p.get("confidence_tier", "Unknown")
        dimensions["confidence_tier"][tier]["total"] += 1
        if correct:
            dimensions["confidence_tier"][tier]["correct"] += 1

        # Method lean
        lean = p.get("method_lean", "Unknown")
        dimensions["method_lean"][lean]["total"] += 1
        if correct:
            dimensions["method_lean"][lean]["correct"] += 1

        # Probability bucket
        prob = p.get("win_probability", 0.5)
        if prob < 0.55:
            bucket = "50-55%"
        elif prob < 0.60:
            bucket = "55-60%"
        elif prob < 0.65:
            bucket = "60-65%"
        elif prob < 0.70:
            bucket = "65-70%"
        elif prob < 0.75:
            bucket = "70-75%"
        else:
            bucket = "75%+"
        dimensions["probability_bucket"][bucket]["total"] += 1
        if correct:
            dimensions["probability_bucket"][bucket]["correct"] += 1

    # Convert to accuracy
    result = {}
    for dim_name, dim_data in dimensions.items():
        result[dim_name] = {}
        for key, stats in dim_data.items():
            result[dim_name][key] = {
                "total": stats["total"],
                "correct": stats["correct"],
                "accuracy": round(stats["correct"] / stats["total"], 3) if stats["total"] > 0 else None,
            }

    return result


# ============================================================
# COMPREHENSIVE CALIBRATION REPORT
# ============================================================

def generate_calibration_report(
    resolved_predictions: List[Dict[str, Any]],
) -> str:
    """
    Generate a comprehensive markdown calibration report.
    """
    if not resolved_predictions:
        return "# Calibration Report\n\nNo resolved predictions to analyze."

    total = len(resolved_predictions)
    correct = sum(1 for p in resolved_predictions if p.get("correct"))
    accuracy = correct / total

    lines = [
        "# Advanced Calibration Report",
        "",
        f"**Total Predictions**: {total}",
        f"**Accuracy**: {accuracy:.1%} ({correct}/{total})",
        "",
    ]

    # Decomposition
    decomp = decompose_calibration_error(resolved_predictions)
    lines.extend([
        "## Calibration Decomposition",
        f"- **Reliability**: {decomp.get('reliability', 'N/A')} ({decomp.get('interpretation', {}).get('reliability', '')})",
        f"- **Resolution**: {decomp.get('resolution', 'N/A')} ({decomp.get('interpretation', {}).get('resolution', '')})",
        f"- **Sharpness**: {decomp.get('sharpness', 'N/A')} ({decomp.get('interpretation', {}).get('sharpness', '')})",
        f"- **Brier Score**: {decomp.get('brier_score', 'N/A')}",
        "",
    ])

    # Feature importance
    features = compute_feature_importance(resolved_predictions)
    if features:
        lines.extend(["## Feature Importance", ""])
        for f in features[:5]:
            lines.append(
                f"- **{f['feature']}**: {f['accuracy']:.1%} accuracy "
                f"({f['total']} predictions, power={f['predictive_power']:.2f})"
            )
        lines.append("")

    # Upset patterns
    upsets = analyze_upset_patterns(resolved_predictions)
    lines.extend([
        "## Upset Analysis",
        f"- **Upset Rate**: {upsets.get('upset_rate', 0):.1%}",
        f"- **Avg Confidence on Upsets**: {upsets.get('avg_upset_confidence', 0):.1%}",
    ])
    for factor in upsets.get("vulnerability_factors", []):
        lines.append(f"- Warning: {factor}")
    lines.append("")

    # Calibration adjustment
    adj = suggest_calibration_adjustment(resolved_predictions)
    lines.extend([
        "## Calibration Adjustment",
        f"- **Direction**: {adj.get('direction', 'N/A')}",
        f"- **Suggestion**: {adj.get('suggestion', 'N/A')}",
        "",
    ])

    # Streaks
    streaks = analyze_prediction_streaks(resolved_predictions)
    lines.extend([
        "## Prediction Streaks",
        f"- **Longest Win Streak**: {streaks.get('longest_correct_streak', 0)}",
        f"- **Longest Loss Streak**: {streaks.get('longest_incorrect_streak', 0)}",
        f"- **Current Status**: {streaks.get('hot_cold_indicator', 'neutral')}",
        f"- **Last 5 Accuracy**: {streaks.get('last_5_accuracy', 0):.0%}",
        "",
    ])

    # Market comparison
    market = compare_against_market(resolved_predictions)
    if "eligible_predictions" in market:
        lines.extend([
            "## Model vs Market",
            f"- **Model Brier**: {market.get('model_brier_score', 'N/A')}",
            f"- **Market Brier**: {market.get('market_brier_score', 'N/A')}",
            f"- **Model Beats Market**: {'Yes' if market.get('model_beats_market') else 'No'}",
            f"- **Edge**: {market.get('edge_pct', 0):.1f}%",
            "",
        ])

    return "\n".join(lines)
