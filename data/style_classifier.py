# data/style_classifier.py
# Classifies fighter style archetype from UFCStats data.
# Used by the router to select more relevant specialists.

from __future__ import annotations
from typing import Dict, Any, Optional, List


# Style archetypes with stat thresholds
ARCHETYPES = {
    "pressure_striker": {
        "description": "High-output pressure fighter who pushes forward",
        "relevant_specialists": ["style", "pace", "damage", "fight_iq"],
    },
    "counter_striker": {
        "description": "Patient counter-striker who picks shots",
        "relevant_specialists": ["style", "fight_iq", "damage", "gameplan"],
    },
    "wrestler": {
        "description": "Primarily uses takedowns and ground control",
        "relevant_specialists": ["grappling", "scramble", "pace", "gameplan"],
    },
    "grappler": {
        "description": "Submission-oriented fighter, dangerous on the ground",
        "relevant_specialists": ["grappling", "scramble", "style", "damage"],
    },
    "well_rounded": {
        "description": "Balanced fighter comfortable everywhere",
        "relevant_specialists": ["style", "fight_iq", "gameplan", "pace"],
    },
    "knockout_artist": {
        "description": "Heavy-handed finisher with KO power",
        "relevant_specialists": ["damage", "style", "pace", "fight_iq"],
    },
    "point_fighter": {
        "description": "Technical fighter who wins decisions through volume",
        "relevant_specialists": ["judging", "pace", "fight_iq", "style"],
    },
}


def _parse_float(val: str) -> Optional[float]:
    try:
        return float(str(val).replace("%", "").strip())
    except (ValueError, TypeError, AttributeError):
        return None


def classify_style(stats: Dict[str, Any]) -> Dict[str, Any]:
    """
    Classify a fighter's style archetype from their UFCStats data.

    Args:
        stats: Fighter stats dict (from UFCStatsTool or fighter profile)

    Returns:
        Dict with primary_style, secondary_style, style_scores, and relevant_specialists
    """
    slpm = _parse_float(stats.get("slpm", ""))
    str_acc = _parse_float(stats.get("str_acc", ""))
    sapm = _parse_float(stats.get("sapm", ""))
    str_def = _parse_float(stats.get("str_def", ""))
    td_avg = _parse_float(stats.get("td_avg", ""))
    td_acc = _parse_float(stats.get("td_acc", ""))
    td_def = _parse_float(stats.get("td_def", ""))
    sub_avg = _parse_float(stats.get("sub_avg", ""))

    # Compute style scores (0-100 scale)
    scores: Dict[str, float] = {}

    # Pressure striker: high SLpM, high SApM (trades), lower accuracy
    if slpm is not None and sapm is not None:
        pressure_score = min(100, (slpm / 6.0) * 50 + (sapm / 5.0) * 30)
        if str_acc and str_acc < 50:
            pressure_score += 20
        scores["pressure_striker"] = round(pressure_score, 1)

    # Counter striker: high accuracy, low SLpM, high defense
    if str_acc is not None and str_def is not None:
        counter_score = (str_acc / 60) * 40 + (str_def / 65) * 40
        if slpm and slpm < 3.5:
            counter_score += 20
        scores["counter_striker"] = round(min(100, counter_score), 1)

    # Wrestler: high TD avg, high TD accuracy
    if td_avg is not None and td_acc is not None:
        wrestler_score = min(100, (td_avg / 4.0) * 50 + (td_acc / 50) * 50)
        scores["wrestler"] = round(wrestler_score, 1)

    # Grappler: high sub avg
    if sub_avg is not None:
        grappler_score = min(100, (sub_avg / 2.0) * 70)
        if td_avg and td_avg > 1.5:
            grappler_score += 30
        scores["grappler"] = round(min(100, grappler_score), 1)

    # Knockout artist: high SLpM, moderate accuracy, check win methods
    if slpm is not None:
        ko_score = min(100, (slpm / 5.0) * 60)
        win_methods = stats.get("win_methods_raw", {}) or stats.get("detail_stats", {}).get("win_methods", {})
        ko_wins = win_methods.get("ko_tko", 0) if win_methods else 0
        total_wins = sum(win_methods.values()) if win_methods else 0
        if total_wins > 0 and ko_wins / total_wins > 0.5:
            ko_score += 40
        scores["knockout_artist"] = round(min(100, ko_score), 1)

    # Point fighter: high accuracy, moderate output, high defense
    if str_acc is not None and str_def is not None and slpm is not None:
        point_score = (str_acc / 55) * 30 + (str_def / 60) * 30 + (slpm / 4.0) * 20
        win_methods = stats.get("win_methods_raw", {}) or stats.get("detail_stats", {}).get("win_methods", {})
        dec_wins = win_methods.get("decision", 0) if win_methods else 0
        total_wins = sum(win_methods.values()) if win_methods else 0
        if total_wins > 0 and dec_wins / total_wins > 0.5:
            point_score += 20
        scores["point_fighter"] = round(min(100, point_score), 1)

    # Well-rounded: balanced stats across all areas
    if all(v is not None for v in [slpm, str_acc, td_avg, sub_avg]):
        balance = 100 - (
            abs((slpm or 0) - 3.5) * 10 +
            abs((str_acc or 0) - 48) * 0.5 +
            abs((td_avg or 0) - 1.5) * 15 +
            abs((sub_avg or 0) - 0.5) * 20
        )
        scores["well_rounded"] = round(max(0, min(100, balance)), 1)

    if not scores:
        return {
            "primary_style": "unknown",
            "secondary_style": None,
            "style_scores": {},
            "relevant_specialists": ["style", "form", "metadata"],
        }

    # Sort by score descending
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    primary = ranked[0]
    secondary = ranked[1] if len(ranked) > 1 else None

    # Collect relevant specialists (deduplicated, ordered)
    seen = set()
    relevant: List[str] = []
    for spec in ARCHETYPES[primary[0]]["relevant_specialists"]:
        if spec not in seen:
            relevant.append(spec)
            seen.add(spec)
    if secondary:
        for spec in ARCHETYPES[secondary[0]]["relevant_specialists"]:
            if spec not in seen:
                relevant.append(spec)
                seen.add(spec)

    return {
        "primary_style": primary[0],
        "primary_score": primary[1],
        "primary_description": ARCHETYPES[primary[0]]["description"],
        "secondary_style": secondary[0] if secondary else None,
        "secondary_score": secondary[1] if secondary else None,
        "style_scores": dict(ranked),
        "relevant_specialists": relevant,
    }


def classify_matchup(
    stats_a: Dict[str, Any],
    stats_b: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Classify the matchup type between two fighters.
    Returns matchup description and recommended specialists.
    """
    style_a = classify_style(stats_a)
    style_b = classify_style(stats_b)

    primary_a = style_a.get("primary_style", "unknown")
    primary_b = style_b.get("primary_style", "unknown")

    # Determine matchup type
    striker_types = {"pressure_striker", "counter_striker", "knockout_artist", "point_fighter"}
    grappler_types = {"wrestler", "grappler"}

    if primary_a in striker_types and primary_b in grappler_types:
        matchup_type = "striker_vs_grappler"
        description = "Classic striker vs grappler matchup — where the fight takes place is key"
        extra_specialists = ["scramble", "gameplan"]
    elif primary_a in grappler_types and primary_b in striker_types:
        matchup_type = "grappler_vs_striker"
        description = "Grappler must close distance against striker"
        extra_specialists = ["scramble", "gameplan"]
    elif primary_a in striker_types and primary_b in striker_types:
        matchup_type = "striker_vs_striker"
        description = "Striking battle — accuracy, defense, and power differential matter most"
        extra_specialists = ["damage", "pace"]
    elif primary_a in grappler_types and primary_b in grappler_types:
        matchup_type = "grappler_vs_grappler"
        description = "Ground battle — scramble ability and mat wrestling decisive"
        extra_specialists = ["scramble", "fight_iq"]
    else:
        matchup_type = "mixed"
        description = "Diverse skillsets — multiple paths to victory"
        extra_specialists = ["fight_iq", "gameplan"]

    # Merge specialist recommendations
    all_specs = list(dict.fromkeys(
        style_a.get("relevant_specialists", []) +
        style_b.get("relevant_specialists", []) +
        extra_specialists
    ))

    return {
        "fighter_a_style": style_a,
        "fighter_b_style": style_b,
        "matchup_type": matchup_type,
        "matchup_description": description,
        "recommended_specialists": all_specs[:8],  # cap at 8
    }
