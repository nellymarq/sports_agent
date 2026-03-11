# data/prop_analysis.py
# Prop bet analysis: compares model method/round probabilities against
# sportsbook prop lines to identify value in method-of-victory and
# round betting markets.

from __future__ import annotations
from typing import Dict, Any, List, Optional
import math

from data.value_bets import american_to_implied, implied_to_american


# Standard method prop categories
METHOD_CATEGORIES = {
    "ko_tko": ["ko", "tko", "ko/tko"],
    "submission": ["sub", "submission"],
    "decision": ["dec", "decision", "unanimous", "split", "majority"],
}

# UFC base rates for method of victory (historical averages)
UFC_METHOD_BASE_RATES = {
    "ko_tko": 0.28,
    "submission": 0.10,
    "decision": 0.57,
    "other": 0.05,
}

# UFC base rates for round finish (3-round fight)
UFC_ROUND_BASE_RATES_3RD = {
    "r1": 0.15,
    "r2": 0.12,
    "r3": 0.10,
    "decision": 0.63,
}

# UFC base rates for round finish (5-round fight)
UFC_ROUND_BASE_RATES_5RD = {
    "r1": 0.14,
    "r2": 0.10,
    "r3": 0.08,
    "r4": 0.06,
    "r5": 0.05,
    "decision": 0.57,
}


def analyze_method_props(
    model_probs: Dict[str, int],
    market_props: Optional[Dict[str, str]] = None,
    fighter_a: str = "Fighter A",
    fighter_b: str = "Fighter B",
    predicted_winner: str = "",
) -> Dict[str, Any]:
    """
    Analyze method-of-victory prop bet value.

    Args:
        model_probs: Model's method probabilities (ko_tko, submission, decision as %)
        market_props: Optional market odds for each method (American odds strings)
        fighter_a: Name of fighter A
        fighter_b: Name of fighter B
        predicted_winner: Name of predicted winner

    Returns:
        Analysis with value props identified
    """
    if not model_probs:
        return {"props": [], "has_value": False}

    # Normalize model probabilities to sum to 100
    total = sum(model_probs.values())
    if total <= 0:
        return {"props": [], "has_value": False}

    normalized = {k: v / total for k, v in model_probs.items()}

    props = []
    for method, model_pct in normalized.items():
        base_rate = UFC_METHOD_BASE_RATES.get(method, 0.05)

        prop = {
            "method": method,
            "model_probability": round(model_pct * 100, 1),
            "base_rate": round(base_rate * 100, 1),
            "model_vs_base": round((model_pct - base_rate) * 100, 1),
            "fair_odds": implied_to_american(model_pct) if model_pct > 0 else None,
        }

        # Compare against market if available
        if market_props and method in market_props:
            market_odds = market_props[method]
            market_implied = american_to_implied(market_odds)
            if market_implied is not None:
                edge = model_pct - market_implied
                prop["market_odds"] = market_odds
                prop["market_implied"] = round(market_implied * 100, 1)
                prop["edge"] = round(edge * 100, 1)
                prop["has_value"] = edge > 0.03  # 3% min edge

        props.append(prop)

    # Identify best value prop
    value_props = [p for p in props if p.get("has_value", False)]

    return {
        "props": props,
        "has_value": len(value_props) > 0,
        "best_value": max(value_props, key=lambda p: p.get("edge", 0)) if value_props else None,
        "predicted_winner": predicted_winner,
        "fighter_a": fighter_a,
        "fighter_b": fighter_b,
    }


def analyze_round_props(
    model_probs: Dict[str, int],
    is_five_round: bool = False,
    market_props: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Analyze round betting props.

    Args:
        model_probs: Model's round probabilities (r1, r2, r3, r4, r5, decision as %)
        is_five_round: Whether this is a 5-round fight
        market_props: Optional market odds for each round (American odds)

    Returns:
        Analysis with over/under rounds and round-specific value
    """
    if not model_probs:
        return {"props": [], "over_under": None}

    total = sum(model_probs.values())
    if total <= 0:
        return {"props": [], "over_under": None}

    normalized = {k: v / total for k, v in model_probs.items()}
    base_rates = UFC_ROUND_BASE_RATES_5RD if is_five_round else UFC_ROUND_BASE_RATES_3RD

    props = []
    for rnd, model_pct in normalized.items():
        base_rate = base_rates.get(rnd, 0.05)

        prop = {
            "round": rnd,
            "model_probability": round(model_pct * 100, 1),
            "base_rate": round(base_rate * 100, 1),
            "model_vs_base": round((model_pct - base_rate) * 100, 1),
            "fair_odds": implied_to_american(model_pct) if model_pct > 0 else None,
        }

        if market_props and rnd in market_props:
            market_odds = market_props[rnd]
            market_implied = american_to_implied(market_odds)
            if market_implied is not None:
                edge = model_pct - market_implied
                prop["market_odds"] = market_odds
                prop["market_implied"] = round(market_implied * 100, 1)
                prop["edge"] = round(edge * 100, 1)
                prop["has_value"] = edge > 0.03

        props.append(prop)

    # Compute over/under analysis
    decision_prob = normalized.get("decision", 0)
    finish_prob = 1.0 - decision_prob

    # Determine the "standard" O/U line (2.5 rounds for 3-rounders, 4.5 for 5-rounders)
    if is_five_round:
        ou_line = 4.5
        # Under 4.5 = finish in R1-R4
        under_prob = sum(
            normalized.get(f"r{i}", 0) for i in range(1, 5)
        )
    else:
        ou_line = 2.5
        # Under 2.5 = finish in R1-R2
        under_prob = sum(
            normalized.get(f"r{i}", 0) for i in range(1, 3)
        )

    over_prob = 1.0 - under_prob

    over_under = {
        "line": ou_line,
        "over_probability": round(over_prob * 100, 1),
        "under_probability": round(under_prob * 100, 1),
        "lean": "OVER" if over_prob > under_prob else "UNDER",
        "finish_probability": round(finish_prob * 100, 1),
        "decision_probability": round(decision_prob * 100, 1),
        "fair_over_odds": implied_to_american(over_prob) if over_prob > 0 else None,
        "fair_under_odds": implied_to_american(under_prob) if under_prob > 0 else None,
    }

    return {
        "props": props,
        "over_under": over_under,
        "is_five_round": is_five_round,
    }


def generate_prop_card(
    prediction_data: Dict[str, Any],
    market_method_props: Optional[Dict[str, str]] = None,
    market_round_props: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Generate a full prop bet analysis card from a prediction's metadata.

    Args:
        prediction_data: Prediction dict with method_probabilities, round_probabilities, etc.
        market_method_props: Market odds for method props
        market_round_props: Market odds for round props

    Returns:
        Complete prop analysis card
    """
    method_probs = prediction_data.get("method_probabilities", {})
    round_probs = prediction_data.get("round_probabilities", {})
    fighters = [
        prediction_data.get("fighter_a", "Fighter A"),
        prediction_data.get("fighter_b", "Fighter B"),
    ]
    predicted_winner = prediction_data.get("predicted_winner", "")

    # Determine if it's a 5-round fight
    is_five_round = any(k in round_probs for k in ("r4", "r5"))

    method_analysis = analyze_method_props(
        model_probs=method_probs,
        market_props=market_method_props,
        fighter_a=fighters[0],
        fighter_b=fighters[1],
        predicted_winner=predicted_winner,
    )

    round_analysis = analyze_round_props(
        model_probs=round_probs,
        is_five_round=is_five_round,
        market_props=market_round_props,
    )

    # Combine into a summary
    value_angles = []
    if method_analysis.get("best_value"):
        bv = method_analysis["best_value"]
        value_angles.append(
            f"{bv['method'].replace('_', '/')} at {bv.get('market_odds', 'N/A')} "
            f"(+{bv.get('edge', 0):.1f}% edge)"
        )

    ou = round_analysis.get("over_under", {})
    if ou:
        value_angles.append(
            f"{ou.get('lean', 'N/A')} {ou.get('line', 'N/A')} rounds "
            f"({ou.get('over_probability' if ou.get('lean') == 'OVER' else 'under_probability', 0)}%)"
        )

    return {
        "method_analysis": method_analysis,
        "round_analysis": round_analysis,
        "value_angles": value_angles,
        "summary": " | ".join(value_angles) if value_angles else "No strong prop angles identified",
    }
