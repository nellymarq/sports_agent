# data/parlay_engine.py
# Correlation-aware parlay engine with SGP builder, hedge calculator,
# bankroll-aware sizing, and performance tracking.

from __future__ import annotations
import json
import os
import time
import math
from itertools import combinations
from typing import Dict, Any, List, Optional, Tuple

from data.value_bets import (
    american_to_implied,
    implied_to_american,
    implied_to_decimal,
    kelly_fraction,
    expected_value,
)


# ============================================================
# FIGHT CORRELATION MODEL
# ============================================================

def compute_fight_correlation(
    bout_a: Dict[str, Any],
    bout_b: Dict[str, Any],
) -> float:
    """
    Compute correlation between two fights on the same card.
    Returns correlation coefficient (-1 to 1).

    Factors: same weight class, same camp, venue effects, card position.
    """
    corr = 0.0

    # Same weight class: slight positive correlation (similar judging standards)
    wc_a = (bout_a.get("weight_class") or "").lower()
    wc_b = (bout_b.get("weight_class") or "").lower()
    if wc_a and wc_b and wc_a == wc_b:
        corr += 0.05

    # Same camp: negative correlation (if camp has a bad night)
    camp_a = set()
    camp_b = set()
    for f in bout_a.get("fighters", []):
        camp = (f.get("camp") or f.get("team") or "").lower()
        if camp:
            camp_a.add(camp)
    for f in bout_b.get("fighters", []):
        camp = (f.get("camp") or f.get("team") or "").lower()
        if camp:
            camp_b.add(camp)
    shared_camps = camp_a & camp_b
    if shared_camps:
        corr -= 0.10

    # Card position: main card fighters correlate slightly
    # (selection bias - promoted fights tend to be higher quality)
    pos_a = bout_a.get("card_position", "").lower()
    pos_b = bout_b.get("card_position", "").lower()
    if "main" in pos_a and "main" in pos_b:
        corr += 0.03

    return round(max(-1.0, min(1.0, corr)), 3)


def adjust_parlay_probability(
    legs: List[Dict[str, Any]],
    correlations: Optional[Dict[str, float]] = None,
) -> float:
    """
    Compute adjusted combined probability accounting for correlations.

    When legs are positively correlated, true prob > independent multiplication.
    When negatively correlated, true prob < independent multiplication.
    """
    if not legs:
        return 0.0

    # Independent probability (naive multiplication)
    independent_prob = 1.0
    for leg in legs:
        prob = leg.get("model_probability", leg.get("implied_probability", 0.5))
        independent_prob *= prob

    if not correlations or len(legs) < 2:
        return round(independent_prob, 6)

    # Apply correlation adjustment using pairwise correlations
    # Adjustment factor: 1 + average_correlation * scaling
    total_corr = 0.0
    pair_count = 0
    for i in range(len(legs)):
        for j in range(i + 1, len(legs)):
            key = f"{i}_{j}"
            alt_key = f"{j}_{i}"
            c = correlations.get(key, correlations.get(alt_key, 0.0))
            total_corr += c
            pair_count += 1

    if pair_count > 0:
        avg_corr = total_corr / pair_count
        # Positive correlation increases combined prob
        # Negative correlation decreases it
        adjustment = 1.0 + avg_corr * 0.15 * len(legs)
        adjusted = independent_prob * adjustment
    else:
        adjusted = independent_prob

    return round(max(0.0, min(1.0, adjusted)), 6)


# ============================================================
# OPTIMAL PARLAY CONSTRUCTION
# ============================================================

def build_optimal_parlays(
    value_bets: List[Dict[str, Any]],
    max_legs: int = 4,
    min_ev: float = 0.0,
    bankroll: float = 1000,
) -> List[Dict[str, Any]]:
    """
    Build optimal parlays from value bets.
    Tries 2, 3, and 4-leg combinations, ranks by risk-adjusted EV.
    Returns top 5 parlays.
    """
    eligible = [vb for vb in value_bets if vb.get("edge", 0) > 0]
    if len(eligible) < 2:
        return []

    all_parlays: List[Dict[str, Any]] = []

    for size in range(2, min(max_legs + 1, len(eligible) + 1)):
        for combo in combinations(eligible, size):
            legs = []
            combined_dec = 1.0
            combined_prob = 1.0

            for vb in combo:
                dec = vb.get("odds_decimal", 2.0)
                prob = vb.get("model_probability", 0.5)
                combined_dec *= dec
                combined_prob *= prob
                legs.append({
                    "fighter": vb.get("fighter", "Unknown"),
                    "decimal_odds": dec,
                    "model_probability": prob,
                    "edge": vb.get("edge", 0),
                })

            # Compute correlations between legs
            correlations = {}
            for i in range(len(combo)):
                for j in range(i + 1, len(combo)):
                    corr = compute_fight_correlation(
                        {"weight_class": combo[i].get("weight_class", "")},
                        {"weight_class": combo[j].get("weight_class", "")},
                    )
                    correlations[f"{i}_{j}"] = corr

            adjusted_prob = adjust_parlay_probability(legs, correlations)

            # EV calculation
            ev = adjusted_prob * combined_dec - 1.0

            if ev < min_ev:
                continue

            # Sharpe-like ratio (EV / variance proxy)
            variance_proxy = combined_dec * (1 - adjusted_prob)
            sharpe = ev / max(variance_proxy, 0.01)

            # Bet sizing
            sizing = size_parlay_bet(ev, combined_dec, bankroll)

            all_parlays.append({
                "legs": legs,
                "num_legs": len(legs),
                "combined_decimal_odds": round(combined_dec, 2),
                "combined_american_odds": implied_to_american(1.0 / combined_dec) if combined_dec > 1 else "N/A",
                "independent_probability": round(combined_prob * 100, 2),
                "adjusted_probability": round(adjusted_prob * 100, 2),
                "expected_value": round(ev, 4),
                "sharpe_ratio": round(sharpe, 4),
                "recommended_stake": sizing["recommended_stake"],
                "potential_payout": round(sizing["recommended_stake"] * combined_dec, 2),
                "correlation_adjusted": any(v != 0 for v in correlations.values()),
                "confidence": _parlay_confidence(legs),
            })

    # Sort by Sharpe ratio (risk-adjusted return)
    all_parlays.sort(key=lambda x: x["sharpe_ratio"], reverse=True)
    return all_parlays[:5]


def _parlay_confidence(legs: List[Dict[str, Any]]) -> str:
    avg_edge = sum(l.get("edge", 0) for l in legs) / max(len(legs), 1)
    if avg_edge > 0.10:
        return "high"
    elif avg_edge > 0.05:
        return "moderate"
    else:
        return "low"


# ============================================================
# SAME-GAME PARLAY (SGP) BUILDER
# ============================================================

def build_sgp(
    fighter_prediction: Dict[str, Any],
    method_probs: Dict[str, float],
    round_probs: Dict[str, float],
    market_odds: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Build same-game parlays combining winner + method + round.
    These legs are HEAVILY correlated — models the correlation correctly.
    """
    winner = fighter_prediction.get("predicted_winner", "")
    win_prob = fighter_prediction.get("win_probability", 0.5)

    if not winner or win_prob <= 0:
        return []

    sgps: List[Dict[str, Any]] = []

    # Winner + Method SGPs
    for method, method_pct in method_probs.items():
        method_prob = method_pct / 100.0 if method_pct > 1 else method_pct

        # Correlated probability: P(win AND method) = P(win) * P(method | win)
        # Since method_probs are already conditional on this fighter winning,
        # the combined prob is win_prob * method_prob
        combined_prob = win_prob * method_prob

        if combined_prob < 0.02:
            continue

        fair_decimal = round(1.0 / combined_prob, 2) if combined_prob > 0 else 100

        sgps.append({
            "type": "winner_method",
            "description": f"{winner} wins by {method}",
            "legs": [
                {"type": "winner", "selection": winner, "probability": win_prob},
                {"type": "method", "selection": method, "probability": method_prob},
            ],
            "true_probability": round(combined_prob, 4),
            "fair_decimal_odds": fair_decimal,
            "correlation_note": "Winner and method are correlated — true prob is NOT simple multiplication",
        })

    # Winner + Method + Round SGPs (only for finishes)
    for method in ["ko_tko", "submission"]:
        method_prob = method_probs.get(method, 0)
        if isinstance(method_prob, (int, float)) and method_prob > 1:
            method_prob /= 100.0

        if method_prob < 0.05:
            continue

        for rnd, rnd_pct in round_probs.items():
            if rnd == "decision":
                continue

            rnd_prob = rnd_pct / 100.0 if rnd_pct > 1 else rnd_pct

            # P(win AND method AND round) = P(win) * P(method|win) * P(round|win,method)
            combined_prob = win_prob * method_prob * rnd_prob

            if combined_prob < 0.01:
                continue

            fair_decimal = round(1.0 / combined_prob, 2) if combined_prob > 0 else 100

            sgps.append({
                "type": "winner_method_round",
                "description": f"{winner} wins by {method} in {rnd}",
                "legs": [
                    {"type": "winner", "selection": winner, "probability": win_prob},
                    {"type": "method", "selection": method, "probability": method_prob},
                    {"type": "round", "selection": rnd, "probability": rnd_prob},
                ],
                "true_probability": round(combined_prob, 4),
                "fair_decimal_odds": fair_decimal,
                "correlation_note": "Heavily correlated legs — fair odds computed from joint probability",
            })

    # Sort by probability (most likely first)
    sgps.sort(key=lambda x: x["true_probability"], reverse=True)
    return sgps[:10]


# ============================================================
# PARLAY HEDGING CALCULATOR
# ============================================================

def calculate_hedge(
    parlay_stake: float,
    parlay_odds: float,
    remaining_legs_count: int,
    hedge_odds: float,
) -> Dict[str, Any]:
    """
    Calculate optimal hedge when a parlay is partially complete.

    Args:
        parlay_stake: Original parlay bet amount
        parlay_odds: Combined decimal odds of the parlay
        remaining_legs_count: How many legs remain
        hedge_odds: Decimal odds available for the hedge bet (opposite side)
    """
    if remaining_legs_count <= 0 or hedge_odds <= 1 or parlay_odds <= 1:
        return {"error": "Invalid inputs"}

    potential_payout = parlay_stake * parlay_odds

    # Full hedge: lock in guaranteed profit
    # If parlay wins: profit = potential_payout - parlay_stake - hedge_stake
    # If parlay loses: profit = hedge_stake * (hedge_odds - 1) - parlay_stake
    # For EQUAL profit: set them equal:
    #   potential_payout - parlay_stake - hedge_stake = hedge_stake * (hedge_odds - 1) - parlay_stake
    #   potential_payout = hedge_stake * hedge_odds
    #   hedge_stake = potential_payout / hedge_odds
    hedge_stake = round(potential_payout / hedge_odds, 2)

    # With equal-profit hedge, both outcomes yield the same profit
    guaranteed_profit = round(potential_payout - parlay_stake - hedge_stake, 2)

    if_parlay_wins = guaranteed_profit
    if_parlay_loses = round(hedge_stake * (hedge_odds - 1) - parlay_stake, 2)

    # EV of letting it ride vs hedging
    # Need to estimate remaining leg probability
    # Rough estimate: if remaining odds ~ 2.0 each, prob per leg ~ 0.5
    remaining_prob = 1.0 / (parlay_odds ** (1.0 / max(remaining_legs_count, 1))) if remaining_legs_count > 0 else 0.5
    ev_ride = round(remaining_prob * potential_payout - parlay_stake, 2)
    ev_hedge = round(guaranteed_profit, 2)

    return {
        "parlay_potential_payout": round(potential_payout, 2),
        "full_hedge_stake": hedge_stake,
        "guaranteed_profit": guaranteed_profit,
        "ev_of_letting_ride": ev_ride,
        "ev_of_hedging": ev_hedge,
        "recommendation": "hedge" if ev_hedge >= ev_ride * 0.8 else "let_it_ride",
        "remaining_implied_probability": round(remaining_prob, 3),
    }


# ============================================================
# BANKROLL-AWARE PARLAY SIZING
# ============================================================

def size_parlay_bet(
    parlay_ev: float,
    parlay_odds: float,
    bankroll: float,
    risk_tolerance: str = "moderate",
) -> Dict[str, Any]:
    """
    Size a parlay bet using fractional Kelly adjusted for variance.

    Risk tolerance:
      conservative: 1/8 Kelly, max 1% of bankroll
      moderate: 1/4 Kelly, max 2.5% of bankroll
      aggressive: 1/2 Kelly, max 5% of bankroll
    """
    settings = {
        "conservative": {"fraction": 0.125, "max_pct": 0.01},
        "moderate": {"fraction": 0.25, "max_pct": 0.025},
        "aggressive": {"fraction": 0.5, "max_pct": 0.05},
    }
    s = settings.get(risk_tolerance, settings["moderate"])

    if parlay_ev <= 0 or parlay_odds <= 1 or bankroll <= 0:
        return {
            "recommended_stake": 0,
            "risk_tolerance": risk_tolerance,
            "reason": "Negative or zero EV — no bet recommended",
        }

    # Implied probability from EV
    implied_prob = (parlay_ev + 1) / parlay_odds if parlay_odds > 0 else 0

    if implied_prob <= 0 or implied_prob >= 1:
        return {
            "recommended_stake": 0,
            "risk_tolerance": risk_tolerance,
            "reason": "Invalid probability",
        }

    # Kelly
    b = parlay_odds - 1
    q = 1 - implied_prob
    full_kelly = (b * implied_prob - q) / b if b > 0 else 0

    if full_kelly <= 0:
        return {
            "recommended_stake": 0,
            "risk_tolerance": risk_tolerance,
            "reason": "Kelly criterion suggests no bet",
        }

    fractional = full_kelly * s["fraction"]
    max_stake = bankroll * s["max_pct"]
    stake = round(min(bankroll * fractional, max_stake), 2)

    # Risk of ruin approximation
    # For parlays, RoR is higher due to lower hit rate
    ror = round((1 - implied_prob) ** (bankroll / max(stake, 1)) * 100, 2) if stake > 0 else 0

    return {
        "recommended_stake": max(0, stake),
        "kelly_fraction": round(fractional, 4),
        "max_allowed_stake": round(max_stake, 2),
        "risk_tolerance": risk_tolerance,
        "risk_of_ruin_pct": min(100, ror),
        "potential_payout": round(stake * parlay_odds, 2),
    }


# ============================================================
# PARLAY PERFORMANCE TRACKER
# ============================================================

PARLAY_TRACKER_PATH = os.path.join(
    os.path.dirname(__file__), "..", "state", "parlay_history.json"
)


def _load_parlay_history() -> List[Dict[str, Any]]:
    try:
        if os.path.exists(PARLAY_TRACKER_PATH):
            with open(PARLAY_TRACKER_PATH, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return []


def _save_parlay_history(history: List[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(PARLAY_TRACKER_PATH), exist_ok=True)
    with open(PARLAY_TRACKER_PATH, "w") as f:
        json.dump(history, f, indent=2)


def track_parlay_result(
    parlay_id: str,
    legs: List[Dict[str, Any]],
    stake: float,
    result: str = "pending",
    payout: float = 0,
) -> Dict[str, Any]:
    """Track a parlay suggestion and its outcome."""
    entry = {
        "id": parlay_id,
        "legs": legs,
        "stake": stake,
        "result": result,
        "payout": payout,
        "timestamp": time.time(),
    }
    history = _load_parlay_history()
    history.append(entry)
    _save_parlay_history(history)
    return entry


def get_parlay_stats() -> Dict[str, Any]:
    """Compute performance stats for tracked parlays."""
    history = _load_parlay_history()
    resolved = [p for p in history if p.get("result") in ("won", "lost")]

    if not resolved:
        return {
            "total_tracked": len(history),
            "resolved": 0,
            "message": "No resolved parlays yet.",
        }

    wins = [p for p in resolved if p["result"] == "won"]
    total_staked = sum(p.get("stake", 0) for p in resolved)
    total_returned = sum(p.get("payout", 0) for p in wins)
    profit = total_returned - total_staked

    # Streaks
    current_streak = 0
    streak_type = None
    best_streak = 0
    worst_streak = 0
    temp_win = 0
    temp_loss = 0

    for p in sorted(resolved, key=lambda x: x.get("timestamp", 0)):
        if p["result"] == "won":
            temp_win += 1
            temp_loss = 0
            best_streak = max(best_streak, temp_win)
        else:
            temp_loss += 1
            temp_win = 0
            worst_streak = max(worst_streak, temp_loss)

    if resolved:
        last = sorted(resolved, key=lambda x: x.get("timestamp", 0))[-1]
        streak_type = last["result"]

    # Average odds
    avg_odds = sum(
        p.get("payout", 0) / max(p.get("stake", 1), 1)
        for p in wins
    ) / max(len(wins), 1) if wins else 0

    return {
        "total_tracked": len(history),
        "resolved": len(resolved),
        "wins": len(wins),
        "losses": len(resolved) - len(wins),
        "hit_rate": round(len(wins) / len(resolved) * 100, 1),
        "total_staked": round(total_staked, 2),
        "total_returned": round(total_returned, 2),
        "profit": round(profit, 2),
        "roi_pct": round(profit / max(total_staked, 1) * 100, 1),
        "avg_winning_odds": round(avg_odds, 2),
        "best_win_streak": best_streak,
        "worst_loss_streak": worst_streak,
        "last_result": streak_type,
    }
