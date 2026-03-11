# data/bet_sizing.py
# Bet sizing recommendations based on confidence tiers and edge analysis.
# Combines Kelly criterion, confidence tier, and ELO-derived edge.

from __future__ import annotations
from typing import Dict, Any, Optional
import math


# Confidence tier to fractional Kelly multiplier
TIER_KELLY_FRACTION = {
    "very_high": 0.25,   # Quarter Kelly
    "high": 0.20,
    "moderate": 0.15,
    "slight": 0.10,
    "toss_up": 0.0,      # No bet recommended
}

# Maximum bet as fraction of bankroll by tier
TIER_MAX_FRACTION = {
    "very_high": 0.05,   # Max 5% of bankroll
    "high": 0.04,
    "moderate": 0.03,
    "slight": 0.02,
    "toss_up": 0.0,
}

# Unit size recommendations
UNIT_SIZES = {
    "very_high": 3.0,    # 3-unit play
    "high": 2.0,         # 2-unit play
    "moderate": 1.0,     # 1-unit play
    "slight": 0.5,       # Half-unit play
    "toss_up": 0.0,      # Pass
}


def kelly_criterion(
    win_prob: float,
    decimal_odds: float,
) -> float:
    """
    Calculate Kelly criterion optimal bet fraction.

    Args:
        win_prob: Estimated probability of winning (0-1)
        decimal_odds: Decimal odds offered (e.g., 2.0 for even money)

    Returns:
        Optimal fraction of bankroll to bet (can be negative = don't bet)
    """
    if decimal_odds <= 1.0 or win_prob <= 0 or win_prob >= 1:
        return 0.0

    b = decimal_odds - 1  # Net odds received on a 1-unit bet
    q = 1 - win_prob

    kelly = (b * win_prob - q) / b
    return max(kelly, 0.0)


def fractional_kelly(
    win_prob: float,
    decimal_odds: float,
    fraction: float = 0.25,
) -> float:
    """Calculate fractional Kelly (safer, reduced variance)."""
    full_kelly = kelly_criterion(win_prob, decimal_odds)
    return full_kelly * fraction


def compute_edge(
    model_prob: float,
    implied_prob: float,
) -> Dict[str, Any]:
    """
    Compute the edge between model probability and market implied probability.

    Returns dict with edge metrics.
    """
    edge = model_prob - implied_prob
    edge_pct = round(edge * 100, 1)

    if implied_prob > 0:
        relative_edge = round(edge / implied_prob * 100, 1)
    else:
        relative_edge = 0.0

    return {
        "edge": round(edge, 4),
        "edge_pct": edge_pct,
        "relative_edge_pct": relative_edge,
        "has_value": edge > 0.03,  # Minimum 3% edge threshold
    }


def recommend_bet_size(
    model_prob: float,
    decimal_odds: float,
    confidence_tier: str,
    bankroll: float = 1000.0,
    unit_size: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Generate a comprehensive bet sizing recommendation.

    Args:
        model_prob: Model's estimated win probability (0-1)
        decimal_odds: Decimal odds offered by sportsbook
        confidence_tier: Confidence tier from prediction
        bankroll: Current bankroll
        unit_size: Custom unit size (defaults to 1% of bankroll)

    Returns:
        Dict with sizing recommendations
    """
    tier = confidence_tier.lower().replace(" ", "_")
    if tier not in TIER_KELLY_FRACTION:
        tier = "moderate"

    implied_prob = 1.0 / decimal_odds if decimal_odds > 0 else 0.5
    edge_data = compute_edge(model_prob, implied_prob)

    # Kelly-based sizing
    kelly_fraction = TIER_KELLY_FRACTION.get(tier, 0.15)
    frac_kelly = fractional_kelly(model_prob, decimal_odds, kelly_fraction)

    # Cap at tier maximum
    max_frac = TIER_MAX_FRACTION.get(tier, 0.03)
    capped_fraction = min(frac_kelly, max_frac)

    # Unit-based sizing
    if unit_size is None:
        unit_size = bankroll * 0.01  # 1% of bankroll per unit

    units = UNIT_SIZES.get(tier, 1.0)

    # Determine action
    if not edge_data["has_value"] or tier == "toss_up":
        action = "PASS"
        suggested_stake = 0.0
        units = 0.0
    elif edge_data["edge_pct"] >= 10:
        action = "STRONG BET"
        suggested_stake = round(capped_fraction * bankroll, 2)
    elif edge_data["edge_pct"] >= 5:
        action = "BET"
        suggested_stake = round(capped_fraction * bankroll, 2)
    else:
        action = "LEAN"
        suggested_stake = round(capped_fraction * bankroll * 0.5, 2)
        units *= 0.5

    return {
        "action": action,
        "confidence_tier": tier,
        "model_probability": round(model_prob, 4),
        "implied_probability": round(implied_prob, 4),
        "edge": edge_data,
        "kelly": {
            "full_kelly_fraction": round(kelly_criterion(model_prob, decimal_odds), 4),
            "fractional_kelly": round(frac_kelly, 4),
            "kelly_multiplier": kelly_fraction,
        },
        "sizing": {
            "suggested_stake": suggested_stake,
            "units": round(units, 1),
            "unit_size": round(unit_size, 2),
            "max_stake": round(max_frac * bankroll, 2),
            "bankroll_fraction": round(capped_fraction, 4),
        },
        "potential_payout": round(suggested_stake * decimal_odds, 2) if suggested_stake > 0 else 0,
        "expected_value": round(
            suggested_stake * (model_prob * (decimal_odds - 1) - (1 - model_prob)), 2
        ) if suggested_stake > 0 else 0,
    }


def format_bet_recommendation(rec: Dict[str, Any], fighter_name: str = "") -> str:
    """Format a bet recommendation as readable text."""
    lines = []

    action = rec["action"]
    if action == "PASS":
        lines.append(f"RECOMMENDATION: PASS — No edge identified")
        lines.append(f"  Model: {rec['model_probability']*100:.1f}% | Market: {rec['implied_probability']*100:.1f}%")
        return "\n".join(lines)

    fighter_str = f" on {fighter_name}" if fighter_name else ""
    lines.append(f"RECOMMENDATION: {action}{fighter_str}")
    lines.append(f"  Edge: {rec['edge']['edge_pct']:+.1f}% (Model {rec['model_probability']*100:.1f}% vs Market {rec['implied_probability']*100:.1f}%)")
    lines.append(f"  Confidence: {rec['confidence_tier'].replace('_', ' ').title()}")
    lines.append(f"  Suggested: {rec['sizing']['units']} units (${rec['sizing']['suggested_stake']:.2f})")
    lines.append(f"  Potential Payout: ${rec['potential_payout']:.2f}")
    lines.append(f"  Expected Value: ${rec['expected_value']:.2f}")

    return "\n".join(lines)
