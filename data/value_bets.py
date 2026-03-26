# data/value_bets.py
# Value bet identification: compares model predictions against market odds
# to find +EV opportunities using Kelly criterion and edge detection.

from __future__ import annotations
from typing import Dict, Any, List, Optional
import math


def american_to_implied(american: str) -> Optional[float]:
    """Convert American odds to implied probability (0-1)."""
    try:
        val = int(str(american).replace("+", "").replace("−", "-").replace("–", "-"))
        if val > 0:
            return round(100 / (val + 100), 4)
        else:
            return round(abs(val) / (abs(val) + 100), 4)
    except (ValueError, ZeroDivisionError):
        return None


def decimal_to_implied(decimal_odds: float) -> Optional[float]:
    """Convert decimal odds to implied probability (0-1)."""
    if decimal_odds <= 1.0:
        return None
    return round(1.0 / decimal_odds, 4)


def implied_to_decimal(implied: float) -> Optional[float]:
    """Convert implied probability to decimal odds."""
    if implied <= 0 or implied >= 1:
        return None
    return round(1.0 / implied, 4)


def implied_to_american(implied: float) -> Optional[str]:
    """Convert implied probability to American odds string."""
    if implied <= 0 or implied >= 1:
        return None
    if implied >= 0.5:
        return str(round(-100 * implied / (1 - implied)))
    else:
        return f"+{round(100 * (1 - implied) / implied)}"


def remove_vig(prob_a: float, prob_b: float) -> tuple[float, float]:
    """Remove the vig/juice from a two-way market to get fair probabilities."""
    total = prob_a + prob_b
    if total <= 0:
        return (0.5, 0.5)
    return (round(prob_a / total, 4), round(prob_b / total, 4))


def calculate_edge(model_prob: float, market_implied: float) -> float:
    """
    Calculate the edge: model probability minus market implied probability.
    Positive edge = value bet (model thinks fighter is more likely to win
    than the market does).
    """
    return round(model_prob - market_implied, 4)


def kelly_fraction(model_prob: float, decimal_odds: float, fraction: float = 0.25) -> float:
    """
    Calculate the Kelly criterion bet size as a fraction of bankroll.

    Uses fractional Kelly (default 1/4 Kelly) for safety.
    Returns 0 if the bet has negative expected value.

    Args:
        model_prob: Our estimated probability of winning (0-1)
        decimal_odds: Decimal odds offered by the book
        fraction: Kelly fraction (0.25 = quarter Kelly, safer)

    Returns:
        Recommended bet size as fraction of bankroll (0-1)
    """
    if model_prob <= 0 or model_prob >= 1 or decimal_odds <= 1:
        return 0.0

    b = decimal_odds - 1  # net profit per unit staked
    q = 1 - model_prob

    kelly = (b * model_prob - q) / b
    if kelly <= 0:
        return 0.0

    return round(kelly * fraction, 4)


def expected_value(model_prob: float, decimal_odds: float, stake: float = 100) -> float:
    """
    Calculate expected value of a bet.

    Args:
        model_prob: Our estimated win probability
        decimal_odds: Decimal odds
        stake: Bet amount

    Returns:
        Expected value (positive = profitable long-term)
    """
    win_payout = stake * decimal_odds
    ev = (model_prob * win_payout) - stake
    return round(ev, 2)


def star_rating(edge: float) -> int:
    """
    Rate a value bet from 1-5 stars based on edge size.
    0 stars = no value (negative edge).
    """
    if edge <= 0:
        return 0
    if edge < 0.03:
        return 1  # Slim edge
    if edge < 0.06:
        return 2  # Moderate edge
    if edge < 0.10:
        return 3  # Good edge
    if edge < 0.15:
        return 4  # Strong edge
    return 5  # Exceptional edge


def confidence_label(edge: float) -> str:
    """Human-readable confidence label for edge size."""
    stars = star_rating(edge)
    labels = {0: "No Value", 1: "Slim Edge", 2: "Moderate Edge", 3: "Good Value", 4: "Strong Value", 5: "Exceptional Value"}
    return labels.get(stars, "Unknown")


def identify_value_bets(
    predictions: List[Dict[str, Any]],
    odds_data: Dict[str, Any],
    min_edge: float = 0.03,
    bankroll: float = 1000,
    kelly_fraction_pct: float = 0.25,
) -> List[Dict[str, Any]]:
    """
    Compare model predictions against market odds to identify value bets.

    Args:
        predictions: List of prediction dicts with keys:
            - fighter_a, fighter_b: fighter names
            - predicted_winner: name of predicted winner
            - win_probability: model's estimated win prob (0-1)
        odds_data: Odds data from odds_provider (merged format)
        min_edge: Minimum edge threshold to flag as value bet
        bankroll: Total bankroll for Kelly sizing
        kelly_fraction_pct: Kelly fraction for safety (default 25%)

    Returns:
        List of value bet opportunities sorted by edge (descending)
    """
    value_bets: List[Dict[str, Any]] = []
    bouts = odds_data.get("bouts", {})

    if not bouts:
        return []

    # Build lookup of odds by normalized fighter name
    odds_by_fighter: Dict[str, Dict[str, Any]] = {}
    for bout_key, bout_data in bouts.items():
        fighters = bout_data.get("fighters", [])
        for f in fighters:
            name = f.get("name", "")
            if not name:
                continue
            key = name.strip().lower()
            odds_by_fighter[key] = {
                "name": name,
                "odds_american": f.get("odds_american", ""),
                "odds_decimal": f.get("odds_decimal"),
                "implied_probability": f.get("implied_probability"),
                "event": bout_data.get("event", ""),
                "source": bout_data.get("source", ""),
            }

    for pred in predictions:
        winner = pred.get("predicted_winner", "")
        model_prob = pred.get("win_probability", 0)
        fighter_a = pred.get("fighter_a", "")
        fighter_b = pred.get("fighter_b", "")

        if not winner or model_prob <= 0:
            continue

        winner_key = winner.strip().lower()

        # Find matching odds
        market_data = None
        for key, data in odds_by_fighter.items():
            if winner_key in key or key in winner_key:
                market_data = data
                break
            # Try last name match
            winner_last = winner_key.split()[-1] if winner_key.split() else ""
            key_last = key.split()[-1] if key.split() else ""
            if winner_last and key_last and winner_last == key_last:
                market_data = data
                break

        if not market_data:
            continue

        market_implied = market_data.get("implied_probability")
        decimal_odds = market_data.get("odds_decimal")

        if not market_implied or not decimal_odds:
            continue

        edge = calculate_edge(model_prob, market_implied)

        if edge < min_edge:
            continue

        kelly = kelly_fraction(model_prob, decimal_odds, kelly_fraction_pct)
        ev = expected_value(model_prob, decimal_odds)
        suggested_stake = round(bankroll * kelly, 2) if kelly > 0 else 0

        value_bets.append({
            "fighter": winner,
            "opponent": fighter_b if winner.lower() == fighter_a.lower() else fighter_a,
            "model_probability": model_prob,
            "market_implied": market_implied,
            "edge": edge,
            "edge_pct": f"{edge * 100:.1f}%",
            "odds_american": market_data.get("odds_american", ""),
            "odds_decimal": decimal_odds,
            "expected_value_per_100": ev,
            "kelly_fraction": kelly,
            "suggested_stake": suggested_stake,
            "star_rating": star_rating(edge),
            "confidence": confidence_label(edge),
            "event": market_data.get("event", ""),
            "source": market_data.get("source", ""),
        })

    # Sort by edge descending
    value_bets.sort(key=lambda x: x["edge"], reverse=True)
    return value_bets


def simulate_roi(
    predictions: List[Dict[str, Any]],
    strategy: str = "flat",
    bankroll: float = 1000,
    flat_stake: float = 50,
    kelly_fraction_pct: float = 0.25,
    min_edge: float = 0.0,
) -> Dict[str, Any]:
    """
    Simulate ROI over resolved predictions using different staking strategies.

    Args:
        predictions: List of resolved prediction dicts (must have 'correct' field)
        strategy: 'flat' (fixed stake), 'kelly' (proportional), or 'proportional' (% of bankroll)
        bankroll: Starting bankroll
        flat_stake: Stake per bet for flat strategy
        kelly_fraction_pct: Kelly fraction for kelly strategy
        min_edge: Minimum edge to place bet (filters low-edge bets)

    Returns:
        ROI simulation results
    """
    resolved = [p for p in predictions if p.get("correct") is not None]
    if not resolved:
        return {"total_bets": 0, "message": "No resolved predictions to simulate."}

    current_bankroll = bankroll
    total_staked = 0.0
    total_returned = 0.0
    results = []
    peak = bankroll
    trough = bankroll

    for p in resolved:
        model_prob = p.get("win_probability", 0.5)
        decimal_odds = p.get("metadata", {}).get("odds_decimal") or 2.0
        edge = model_prob - (1.0 / decimal_odds) if decimal_odds > 1 else 0

        if edge < min_edge:
            continue

        # Calculate stake
        if strategy == "kelly":
            frac = kelly_fraction(model_prob, decimal_odds, kelly_fraction_pct)
            stake = round(current_bankroll * frac, 2)
        elif strategy == "proportional":
            stake = round(current_bankroll * 0.05, 2)  # 5% of current bankroll
        else:  # flat
            stake = min(flat_stake, current_bankroll)

        if stake <= 0 or current_bankroll <= 0:
            continue

        total_staked += stake
        if p["correct"]:
            payout = stake * decimal_odds
            total_returned += payout
            current_bankroll += payout - stake
        else:
            current_bankroll -= stake

        peak = max(peak, current_bankroll)
        trough = min(trough, current_bankroll)

        results.append({
            "fighter": p.get("predicted_winner", ""),
            "correct": p["correct"],
            "stake": stake,
            "bankroll_after": round(current_bankroll, 2),
        })

    profit = total_returned - total_staked
    roi = (profit / total_staked * 100) if total_staked > 0 else 0
    max_drawdown = ((peak - trough) / peak * 100) if peak > 0 else 0

    return {
        "strategy": strategy,
        "starting_bankroll": bankroll,
        "ending_bankroll": round(current_bankroll, 2),
        "total_bets": len(results),
        "total_staked": round(total_staked, 2),
        "total_returned": round(total_returned, 2),
        "profit": round(profit, 2),
        "roi_pct": round(roi, 2),
        "peak_bankroll": round(peak, 2),
        "max_drawdown_pct": round(max_drawdown, 2),
        "win_rate": round(sum(1 for r in results if r["correct"]) / len(results) * 100, 1) if results else 0,
        "bet_history": results,
    }


def calculate_parlay(
    legs: List[Dict[str, Any]],
    stake: float = 100,
) -> Dict[str, Any]:
    """
    Calculate parlay (accumulator) odds and payouts.

    Args:
        legs: List of dicts with 'fighter', 'decimal_odds', and optionally 'model_probability'
        stake: Bet amount

    Returns:
        Parlay calculation with combined odds, payout, and implied probability
    """
    if not legs or len(legs) < 2:
        return {"error": "Parlay requires at least 2 legs."}

    combined_decimal = 1.0
    combined_model_prob = 1.0
    combined_implied = 1.0
    valid_legs = []

    for leg in legs:
        dec = leg.get("decimal_odds", 0)
        if dec <= 1:
            continue
        combined_decimal *= dec
        implied = 1.0 / dec
        combined_implied *= implied
        model_prob = leg.get("model_probability", implied)
        combined_model_prob *= model_prob
        valid_legs.append({
            "fighter": leg.get("fighter", "Unknown"),
            "decimal_odds": dec,
            "american_odds": implied_to_american(1.0 / dec) or "N/A",
            "implied_probability": round(implied * 100, 1),
            "model_probability": round(model_prob * 100, 1),
        })

    if len(valid_legs) < 2:
        return {"error": "Need at least 2 valid legs with odds > 1.0"}

    payout = round(stake * combined_decimal, 2)
    profit = round(payout - stake, 2)
    ev = expected_value(combined_model_prob, combined_decimal, stake)

    return {
        "legs": valid_legs,
        "num_legs": len(valid_legs),
        "combined_decimal_odds": round(combined_decimal, 4),
        "combined_american_odds": implied_to_american(1.0 / combined_decimal) if combined_decimal > 1 else "N/A",
        "combined_implied_probability": round(combined_implied * 100, 2),
        "combined_model_probability": round(combined_model_prob * 100, 2),
        "stake": stake,
        "potential_payout": payout,
        "potential_profit": profit,
        "expected_value": ev,
        "ev_positive": ev > 0,
        "edge": round((combined_model_prob - combined_implied) * 100, 2),
    }


def suggest_parlays(
    value_bets: List[Dict[str, Any]],
    max_legs: int = 3,
    stake: float = 25,
) -> List[Dict[str, Any]]:
    """
    Suggest parlays from value bets, combining high-confidence picks.
    Returns 2-leg and 3-leg combinations sorted by expected value.
    """
    from itertools import combinations

    if len(value_bets) < 2:
        return []

    # Only use bets with positive edge
    eligible = [vb for vb in value_bets if vb.get("edge", 0) > 0]
    if len(eligible) < 2:
        return []

    suggestions = []
    for size in range(2, min(max_legs + 1, len(eligible) + 1)):
        for combo in combinations(eligible, size):
            legs = [
                {
                    "fighter": vb["fighter"],
                    "decimal_odds": vb.get("odds_decimal", 2.0),
                    "model_probability": vb.get("model_probability", 0.5),
                }
                for vb in combo
            ]
            result = calculate_parlay(legs, stake)
            if "error" not in result and result.get("ev_positive"):
                suggestions.append(result)

    suggestions.sort(key=lambda x: x.get("expected_value", 0), reverse=True)
    return suggestions[:10]  # top 10 parlays


def format_value_bet_report(value_bets: List[Dict[str, Any]]) -> str:
    """Format value bets into a readable report string."""
    if not value_bets:
        return "No value bets identified at current thresholds."

    lines = ["## Value Bet Report", ""]

    for i, vb in enumerate(value_bets, 1):
        stars = "★" * vb["star_rating"] + "☆" * (5 - vb["star_rating"])
        lines.append(f"### {i}. {vb['fighter']} vs {vb['opponent']}")
        lines.append(f"**Rating**: {stars} ({vb['confidence']})")
        lines.append(f"**Model Prob**: {vb['model_probability']*100:.1f}% | **Market Implied**: {vb['market_implied']*100:.1f}%")
        lines.append(f"**Edge**: {vb['edge_pct']} | **Odds**: {vb['odds_american']} ({vb['odds_decimal']})")
        lines.append(f"**EV per $100**: ${vb['expected_value_per_100']:+.2f}")
        if vb["suggested_stake"] > 0:
            lines.append(f"**Kelly Stake**: ${vb['suggested_stake']:.2f} ({vb['kelly_fraction']*100:.1f}% of bankroll)")
        lines.append("")

    return "\n".join(lines)
