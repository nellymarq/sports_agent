# data/judge_model.py
# Judge tendencies database and decision prediction model.
# Models UFC judging patterns, hometown bias, and scoring criteria.

from __future__ import annotations
from typing import Dict, Any, Optional, List, Tuple


# ============================================================
# JUDGE DATABASE
# ============================================================

JUDGE_DATABASE = {
    "sal_damato": {
        "name": "Sal D'Amato",
        "aggression_weight": 0.35,
        "control_weight": 0.28,
        "damage_weight": 0.37,
        "split_decision_rate": 0.18,
        "ten_eight_rate": 0.02,
        "favors_striker": True,
        "hometown_bias": 0.02,
    },
    "chris_lee": {
        "name": "Chris Lee",
        "aggression_weight": 0.30,
        "control_weight": 0.35,
        "damage_weight": 0.35,
        "split_decision_rate": 0.22,
        "ten_eight_rate": 0.015,
        "favors_striker": False,
        "hometown_bias": 0.01,
    },
    "derek_cleary": {
        "name": "Derek Cleary",
        "aggression_weight": 0.32,
        "control_weight": 0.30,
        "damage_weight": 0.38,
        "split_decision_rate": 0.15,
        "ten_eight_rate": 0.03,
        "favors_striker": True,
        "hometown_bias": 0.015,
    },
    "mike_bell": {
        "name": "Mike Bell",
        "aggression_weight": 0.28,
        "control_weight": 0.38,
        "damage_weight": 0.34,
        "split_decision_rate": 0.20,
        "ten_eight_rate": 0.02,
        "favors_striker": False,
        "hometown_bias": 0.01,
    },
    "dave_hagen": {
        "name": "Dave Hagen",
        "aggression_weight": 0.33,
        "control_weight": 0.30,
        "damage_weight": 0.37,
        "split_decision_rate": 0.16,
        "ten_eight_rate": 0.025,
        "favors_striker": True,
        "hometown_bias": 0.02,
    },
    "junichiro_kamijo": {
        "name": "Junichiro Kamijo",
        "aggression_weight": 0.30,
        "control_weight": 0.35,
        "damage_weight": 0.35,
        "split_decision_rate": 0.14,
        "ten_eight_rate": 0.01,
        "favors_striker": False,
        "hometown_bias": 0.005,
    },
    "douglas_crosby": {
        "name": "Douglas Crosby",
        "aggression_weight": 0.35,
        "control_weight": 0.25,
        "damage_weight": 0.40,
        "split_decision_rate": 0.17,
        "ten_eight_rate": 0.035,
        "favors_striker": True,
        "hometown_bias": 0.015,
    },
    "ron_mccarthy": {
        "name": "Ron McCarthy",
        "aggression_weight": 0.30,
        "control_weight": 0.35,
        "damage_weight": 0.35,
        "split_decision_rate": 0.19,
        "ten_eight_rate": 0.02,
        "favors_striker": False,
        "hometown_bias": 0.01,
    },
    "bryan_miner": {
        "name": "Bryan Miner",
        "aggression_weight": 0.32,
        "control_weight": 0.33,
        "damage_weight": 0.35,
        "split_decision_rate": 0.18,
        "ten_eight_rate": 0.02,
        "favors_striker": False,
        "hometown_bias": 0.01,
    },
    "eric_colon": {
        "name": "Eric Colon",
        "aggression_weight": 0.34,
        "control_weight": 0.28,
        "damage_weight": 0.38,
        "split_decision_rate": 0.20,
        "ten_eight_rate": 0.025,
        "favors_striker": True,
        "hometown_bias": 0.02,
    },
    "chris_tognoni": {
        "name": "Chris Tognoni",
        "aggression_weight": 0.30,
        "control_weight": 0.32,
        "damage_weight": 0.38,
        "split_decision_rate": 0.16,
        "ten_eight_rate": 0.02,
        "favors_striker": True,
        "hometown_bias": 0.01,
    },
    "adalaide_byrd": {
        "name": "Adalaide Byrd",
        "aggression_weight": 0.28,
        "control_weight": 0.40,
        "damage_weight": 0.32,
        "split_decision_rate": 0.25,
        "ten_eight_rate": 0.01,
        "favors_striker": False,
        "hometown_bias": 0.03,
    },
    "tony_weeks": {
        "name": "Tony Weeks",
        "aggression_weight": 0.33,
        "control_weight": 0.30,
        "damage_weight": 0.37,
        "split_decision_rate": 0.17,
        "ten_eight_rate": 0.025,
        "favors_striker": True,
        "hometown_bias": 0.015,
    },
    "glenn_trowbridge": {
        "name": "Glenn Trowbridge",
        "aggression_weight": 0.30,
        "control_weight": 0.35,
        "damage_weight": 0.35,
        "split_decision_rate": 0.19,
        "ten_eight_rate": 0.02,
        "favors_striker": False,
        "hometown_bias": 0.015,
    },
    "mark_ratner": {
        "name": "Mark Ratner",
        "aggression_weight": 0.32,
        "control_weight": 0.33,
        "damage_weight": 0.35,
        "split_decision_rate": 0.18,
        "ten_eight_rate": 0.02,
        "favors_striker": False,
        "hometown_bias": 0.01,
    },
}

# Average judge profile (used when specific judges unknown)
AVERAGE_JUDGE = {
    "name": "Average UFC Judge",
    "aggression_weight": 0.31,
    "control_weight": 0.32,
    "damage_weight": 0.37,
    "split_decision_rate": 0.18,
    "ten_eight_rate": 0.02,
    "favors_striker": False,
    "hometown_bias": 0.015,
}


def _parse_float(val) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(str(val).replace("%", "").strip())
    except (ValueError, TypeError):
        return None


def _get_judge_profile(judge_name: Optional[str] = None) -> Dict[str, Any]:
    """Look up a judge profile by name, falling back to average."""
    if not judge_name:
        return AVERAGE_JUDGE
    key = judge_name.lower().replace(" ", "_").replace("'", "")
    return JUDGE_DATABASE.get(key, AVERAGE_JUDGE)


def score_fight_round(
    stats_a: Dict[str, Any],
    stats_b: Dict[str, Any],
    judge_profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Score a round based on unified MMA rules and judge tendencies.
    Returns round score estimates for each fighter.
    """
    judge = judge_profile or AVERAGE_JUDGE

    slpm_a = _parse_float(stats_a.get("slpm")) or 3.5
    slpm_b = _parse_float(stats_b.get("slpm")) or 3.5
    str_acc_a = _parse_float(stats_a.get("str_acc")) or 45
    str_acc_b = _parse_float(stats_b.get("str_acc")) or 45
    str_def_a = _parse_float(stats_a.get("str_def")) or 55
    str_def_b = _parse_float(stats_b.get("str_def")) or 55
    td_avg_a = _parse_float(stats_a.get("td_avg")) or 1.5
    td_avg_b = _parse_float(stats_b.get("td_avg")) or 1.5
    td_def_a = _parse_float(stats_a.get("td_def")) or 60
    td_def_b = _parse_float(stats_b.get("td_def")) or 60
    sapm_a = _parse_float(stats_a.get("sapm")) or 3.5
    sapm_b = _parse_float(stats_b.get("sapm")) or 3.5

    # Effective striking (damage): volume * accuracy * (1 - opponent defense)
    damage_a = slpm_a * (str_acc_a / 100) * (1 - str_def_b / 100)
    damage_b = slpm_b * (str_acc_b / 100) * (1 - str_def_a / 100)

    # Control: takedown volume weighted by defense
    control_a = td_avg_a * (1 - td_def_b / 100) * 10 + max(0, slpm_a - sapm_a)
    control_b = td_avg_b * (1 - td_def_a / 100) * 10 + max(0, slpm_b - sapm_b)

    # Aggression: forward pressure (output volume)
    aggression_a = slpm_a + td_avg_a * 3
    aggression_b = slpm_b + td_avg_b * 3

    # Weighted composite
    w_dmg = judge["damage_weight"]
    w_ctrl = judge["control_weight"]
    w_agg = judge["aggression_weight"]

    score_a = damage_a * w_dmg + control_a * w_ctrl + aggression_a * w_agg
    score_b = damage_b * w_dmg + control_b * w_ctrl + aggression_b * w_agg

    total = score_a + score_b
    if total <= 0:
        prob_a = 0.5
    else:
        prob_a = score_a / total

    return {
        "round_win_probability_a": round(prob_a, 3),
        "round_win_probability_b": round(1 - prob_a, 3),
        "breakdown": {
            "damage": {"a": round(damage_a, 3), "b": round(damage_b, 3)},
            "control": {"a": round(control_a, 3), "b": round(control_b, 3)},
            "aggression": {"a": round(aggression_a, 3), "b": round(aggression_b, 3)},
        },
        "judge": judge.get("name", "Average"),
    }


def predict_decision(
    stats_a: Dict[str, Any],
    stats_b: Dict[str, Any],
    judges: Optional[List[str]] = None,
    is_five_round: bool = False,
) -> Dict[str, Any]:
    """
    Predict decision outcome given fighter stats and optional judge panel.
    """
    num_rounds = 5 if is_five_round else 3

    if judges and len(judges) >= 3:
        judge_profiles = [_get_judge_profile(j) for j in judges[:3]]
    else:
        judge_profiles = [AVERAGE_JUDGE, AVERAGE_JUDGE, AVERAGE_JUDGE]

    # Score each round with each judge
    judge_cards: List[Dict[str, Any]] = []
    judge_probs: List[float] = []
    for judge_prof in judge_profiles:
        round_score = score_fight_round(stats_a, stats_b, judge_prof)
        prob_a = round_score["round_win_probability_a"]
        judge_probs.append(prob_a)

        # Over N rounds, win probability compounds
        rounds_won_a = prob_a * num_rounds
        rounds_won_b = (1 - prob_a) * num_rounds

        judge_cards.append({
            "judge": judge_prof.get("name", "Unknown"),
            "rounds_for_a": round(rounds_won_a, 1),
            "rounds_for_b": round(rounds_won_b, 1),
            "leans_toward": "A" if rounds_won_a > rounds_won_b else "B",
        })

    # Overall decision probability (reuse already-computed scores)
    avg_prob_a = sum(judge_probs) / len(judge_probs)

    # Decision type prediction
    margin = abs(avg_prob_a - 0.5)
    decision_type = predict_decision_type(margin)

    # 10-8 round likelihood
    avg_ten_eight = sum(j.get("ten_eight_rate", 0.02) for j in judge_profiles) / len(judge_profiles)

    return {
        "decision_probability_a": round(avg_prob_a, 3),
        "decision_probability_b": round(1 - avg_prob_a, 3),
        "judge_cards": judge_cards,
        "decision_type": decision_type,
        "ten_eight_likelihood": round(avg_ten_eight, 3),
        "num_rounds": num_rounds,
    }


def predict_decision_type(margin: float) -> Dict[str, float]:
    """
    Predict decision type based on how close the fight is.
    margin = how far from 50/50 the prediction is.
    """
    if margin < 0.05:
        return {"unanimous": 35.0, "split": 50.0, "majority": 15.0}
    elif margin < 0.10:
        return {"unanimous": 55.0, "split": 30.0, "majority": 15.0}
    elif margin < 0.20:
        return {"unanimous": 75.0, "split": 15.0, "majority": 10.0}
    else:
        return {"unanimous": 90.0, "split": 7.0, "majority": 3.0}


# ============================================================
# LOCATION BIAS MODEL
# ============================================================

LOCATION_BIAS = {
    "brazil": 0.04,
    "usa": 0.015,
    "uk": 0.025,
    "australia": 0.025,
    "canada": 0.02,
    "uae": 0.0,
    "abu_dhabi": 0.0,
    "singapore": 0.005,
    "mexico": 0.03,
    "china": 0.02,
    "japan": 0.015,
    "south_korea": 0.02,
}


def compute_location_bias(
    nationality_a: str,
    nationality_b: str,
    venue_country: str,
) -> Dict[str, Any]:
    """
    Compute hometown/location judge bias for each fighter.
    Returns probability adjustment (-0.1 to +0.1).
    """
    venue_key = venue_country.lower().replace(" ", "_")
    nat_a = nationality_a.lower().strip()
    nat_b = nationality_b.lower().strip()

    bias_factor = LOCATION_BIAS.get(venue_key, 0.01)

    # Nationality aliases for matching
    _nat_aliases = {
        "american": "usa", "brazilian": "brazil", "british": "uk",
        "australian": "australia", "canadian": "canada", "mexican": "mexico",
        "japanese": "japan", "chinese": "china", "korean": "south_korea",
        "emirati": "uae", "singaporean": "singapore",
    }

    def _matches_venue(nationality: str, venue: str) -> bool:
        alias = _nat_aliases.get(nationality, nationality)
        return alias in venue or venue in alias or nationality in venue or venue in nationality

    bias_a = 0.0
    bias_b = 0.0

    if _matches_venue(nat_a, venue_key):
        bias_a = bias_factor
    if _matches_venue(nat_b, venue_key):
        bias_b = bias_factor

    # If both fighters are from the same country as venue, cancel out
    if bias_a > 0 and bias_b > 0:
        bias_a = 0.0
        bias_b = 0.0

    return {
        "bias_a": round(bias_a, 3),
        "bias_b": round(bias_b, 3),
        "venue_country": venue_country,
        "description": _bias_description(bias_a, bias_b, nationality_a, nationality_b, venue_country),
    }


def _bias_description(bias_a, bias_b, nat_a, nat_b, venue):
    if bias_a > 0:
        return f"{nat_a} fighter has home crowd advantage in {venue} (+{bias_a*100:.1f}% decision boost)"
    elif bias_b > 0:
        return f"{nat_b} fighter has home crowd advantage in {venue} (+{bias_b*100:.1f}% decision boost)"
    return f"Neutral venue — no significant hometown bias in {venue}"


def get_judge_adjustment(
    prediction_data: Dict[str, Any],
    judges: Optional[List[str]] = None,
    venue_country: Optional[str] = None,
    nationality_a: str = "",
    nationality_b: str = "",
) -> Dict[str, Any]:
    """
    Compute combined judge + venue adjustment to apply to prediction output.
    """
    adjustments = {}

    # Judge-based adjustment
    if judges:
        profiles = [_get_judge_profile(j) for j in judges]
        # Check if panel favors strikers
        striker_bias = sum(1 for p in profiles if p.get("favors_striker")) / len(profiles)
        adjustments["striker_friendly_panel"] = striker_bias > 0.5
        adjustments["split_decision_risk"] = round(
            sum(p.get("split_decision_rate", 0.18) for p in profiles) / len(profiles), 3
        )

    # Location bias
    if venue_country and nationality_a and nationality_b:
        loc_bias = compute_location_bias(nationality_a, nationality_b, venue_country)
        adjustments["location_bias"] = loc_bias

    return adjustments
