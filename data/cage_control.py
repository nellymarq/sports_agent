# data/cage_control.py
# Clinch dynamics, octagon control, and fight location prediction.
# Analyzes dirty boxing, cage wrestling, and positional dominance.

from __future__ import annotations
from typing import Dict, Any, Optional, List, Tuple


def _parse_float(val) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(str(val).replace("%", "").strip())
    except (ValueError, TypeError):
        return None


def analyze_clinch_profile(stats: Dict[str, Any]) -> Dict[str, Any]:
    """
    Classify a fighter's clinch tendency and style.

    High SApM + low TD avg + moderate SLpM = clinch-heavy (dirty boxer)
    High TD avg + high TD acc = cage-press wrestler
    Low SApM + high str_def = range fighter (avoids clinch)
    """
    slpm = _parse_float(stats.get("slpm")) or 3.5
    sapm = _parse_float(stats.get("sapm")) or 3.5
    str_def = _parse_float(stats.get("str_def")) or 55
    td_avg = _parse_float(stats.get("td_avg")) or 1.5
    td_acc = _parse_float(stats.get("td_acc")) or 40
    sub_avg = _parse_float(stats.get("sub_avg")) or 0.5

    # Clinch tendency (0-1): high SApM correlates with clinch exchanges
    clinch_tendency = min(1.0, (sapm / 6.0) * 0.4 + (1 - str_def / 100) * 0.3)
    if td_avg > 2.5:
        clinch_tendency = min(1.0, clinch_tendency + 0.2)

    # Classify clinch style
    if sapm >= 4.0 and td_avg < 2.0 and slpm >= 3.0:
        clinch_style = "dirty_boxer"
        description = "Prefers close-range clinch striking, knees, elbows in the pocket"
    elif td_avg > 3.0 and td_acc > 45:
        clinch_style = "cage_wrestler"
        description = "Uses cage to secure takedowns and control position"
    elif td_avg > 2.0 and sub_avg > 1.0:
        clinch_style = "trip_artist"
        description = "Uses clinch trips and body locks to get to the ground for submissions"
    elif sapm < 3.0 and str_def > 58:
        clinch_style = "range_fighter"
        description = "Avoids clinch, prefers to fight at range"
        clinch_tendency = max(0, clinch_tendency - 0.15)
    else:
        clinch_style = "neutral"
        description = "No strong clinch preference"

    return {
        "clinch_tendency": round(clinch_tendency, 3),
        "clinch_style": clinch_style,
        "description": description,
        "prefers_clinch": clinch_tendency > 0.5,
        "stats_used": {
            "slpm": slpm,
            "sapm": sapm,
            "str_def": str_def,
            "td_avg": td_avg,
            "td_acc": td_acc,
        },
    }


def analyze_clinch_matchup(
    stats_a: Dict[str, Any],
    stats_b: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Analyze how two fighters interact in clinch situations.
    Determines clinch initiator, position winner, and finish probability.
    """
    profile_a = analyze_clinch_profile(stats_a)
    profile_b = analyze_clinch_profile(stats_b)

    # Who initiates clinch? (higher SApM / clinch tendency)
    tend_a = profile_a["clinch_tendency"]
    tend_b = profile_b["clinch_tendency"]

    if tend_a > tend_b + 0.15:
        clinch_initiator = stats_a.get("name", "Fighter A")
    elif tend_b > tend_a + 0.15:
        clinch_initiator = stats_b.get("name", "Fighter B")
    else:
        clinch_initiator = "Either"

    # Who wins clinch position? (TD acc + TD def = clinch control proxy)
    td_acc_a = _parse_float(stats_a.get("td_acc")) or 40
    td_def_a = _parse_float(stats_a.get("td_def")) or 60
    td_acc_b = _parse_float(stats_b.get("td_acc")) or 40
    td_def_b = _parse_float(stats_b.get("td_def")) or 60

    control_a = td_acc_a * 0.6 + td_def_a * 0.4
    control_b = td_acc_b * 0.6 + td_def_b * 0.4

    if control_a > control_b + 5:
        clinch_dominant = stats_a.get("name", "Fighter A")
    elif control_b > control_a + 5:
        clinch_dominant = stats_b.get("name", "Fighter B")
    else:
        clinch_dominant = "Even"

    # Clinch time estimate (% of fight in clinch)
    avg_tendency = (tend_a + tend_b) / 2
    clinch_time_pct = round(min(40, avg_tendency * 35 + 5), 1)

    # Clinch finish probability
    sub_a = _parse_float(stats_a.get("sub_avg")) or 0.5
    sub_b = _parse_float(stats_b.get("sub_avg")) or 0.5
    slpm_a = _parse_float(stats_a.get("slpm")) or 3.5
    slpm_b = _parse_float(stats_b.get("slpm")) or 3.5

    clinch_finish_prob = round(
        min(0.25, avg_tendency * 0.1 + max(sub_a, sub_b) * 0.03 + max(slpm_a, slpm_b) * 0.01),
        3,
    )

    return {
        "clinch_initiator": clinch_initiator,
        "clinch_dominant": clinch_dominant,
        "clinch_time_estimate_pct": clinch_time_pct,
        "clinch_finish_probability": clinch_finish_prob,
        "profile_a": profile_a,
        "profile_b": profile_b,
        "control_scores": {
            "a": round(control_a, 1),
            "b": round(control_b, 1),
        },
    }


def compute_octagon_control_score(stats: Dict[str, Any]) -> Dict[str, Any]:
    """
    Estimate octagon control capability.
    Forward pressure vs counter fighting analysis.
    """
    slpm = _parse_float(stats.get("slpm")) or 3.5
    sapm = _parse_float(stats.get("sapm")) or 3.5
    str_acc = _parse_float(stats.get("str_acc")) or 45
    str_def = _parse_float(stats.get("str_def")) or 55
    td_avg = _parse_float(stats.get("td_avg")) or 1.5

    # Forward pressure: high output + high absorption = pushing forward
    pressure_raw = slpm * 8 + sapm * 5 + td_avg * 8
    pressure_rating = round(min(100, pressure_raw), 1)

    # Footwork/evasion: high defense + high accuracy + low absorption
    footwork_raw = str_def * 0.8 + str_acc * 0.5 + max(0, (4.0 - sapm) * 10)
    footwork_rating = round(min(100, footwork_raw), 1)

    # Overall control: pressure fighters control octagon center,
    # counter fighters control range
    if pressure_rating > footwork_rating:
        style = "pressure"
        control_score = round((pressure_rating * 0.7 + footwork_rating * 0.3), 1)
    else:
        style = "counter"
        control_score = round((footwork_rating * 0.6 + pressure_rating * 0.4), 1)

    return {
        "control_score": min(100, control_score),
        "pressure_rating": pressure_rating,
        "footwork_rating": footwork_rating,
        "control_style": style,
        "description": f"{'Pressure-based' if style == 'pressure' else 'Movement-based'} octagon control",
    }


def predict_fight_location(
    stats_a: Dict[str, Any],
    stats_b: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Predict where the fight will take place.
    Returns probability distribution: range, clinch, ground.
    """
    td_avg_a = _parse_float(stats_a.get("td_avg")) or 1.5
    td_avg_b = _parse_float(stats_b.get("td_avg")) or 1.5
    td_def_a = _parse_float(stats_a.get("td_def")) or 60
    td_def_b = _parse_float(stats_b.get("td_def")) or 60
    sub_a = _parse_float(stats_a.get("sub_avg")) or 0.5
    sub_b = _parse_float(stats_b.get("sub_avg")) or 0.5
    sapm_a = _parse_float(stats_a.get("sapm")) or 3.5
    sapm_b = _parse_float(stats_b.get("sapm")) or 3.5

    # Ground time: based on takedown volume vs defense
    ground_score = (
        (td_avg_a * (1 - td_def_b / 100) + td_avg_b * (1 - td_def_a / 100)) * 8
        + (sub_a + sub_b) * 5
    )

    # Clinch time: based on SApM and clinch tendencies
    clinch_score = (sapm_a + sapm_b) * 3 + (td_avg_a + td_avg_b) * 2

    # Range: everything else
    range_score = 50 + max(0, 30 - ground_score - clinch_score * 0.3)

    total = range_score + clinch_score + ground_score
    if total <= 0:
        total = 100

    range_pct = round(range_score / total * 100, 1)
    clinch_pct = round(clinch_score / total * 100, 1)
    ground_pct = round(ground_score / total * 100, 1)

    # Normalize to 100%
    norm_total = range_pct + clinch_pct + ground_pct
    if norm_total > 0:
        range_pct = round(range_pct / norm_total * 100, 1)
        clinch_pct = round(clinch_pct / norm_total * 100, 1)
        ground_pct = max(0, round(100 - range_pct - clinch_pct, 1))

    # Determine primary location
    probs = {"range": range_pct, "clinch": clinch_pct, "ground": ground_pct}
    primary = max(probs, key=probs.get)

    return {
        "location_distribution": probs,
        "primary_location": primary,
        "fight_location_description": _location_description(primary, probs),
    }


def _location_description(primary: str, probs: Dict[str, float]) -> str:
    if primary == "range":
        return f"Primarily a striking fight at range ({probs['range']:.0f}% estimated)"
    elif primary == "clinch":
        return f"Significant clinch work expected ({probs['clinch']:.0f}% estimated)"
    else:
        return f"Substantial ground fighting expected ({probs['ground']:.0f}% estimated)"
