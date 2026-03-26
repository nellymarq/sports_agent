# data/fight_simulation.py
# Monte Carlo fight outcome simulation using fighter statistical profiles.
# Generates probability distributions by simulating thousands of fight outcomes
# based on striking differentials, takedown success rates, and historical patterns.

from __future__ import annotations
import random
import math
from typing import Dict, Any, List, Optional, Tuple


# Weight factors for different skill dimensions
DIMENSION_WEIGHTS = {
    "striking_volume": 0.15,
    "striking_accuracy": 0.12,
    "striking_defense": 0.18,
    "takedown_offense": 0.12,
    "takedown_defense": 0.15,
    "submission_threat": 0.08,
    "cardio_pace": 0.10,
    "experience": 0.10,
}

# Method probability modifiers based on style matchup
METHOD_MODIFIERS = {
    "striker_vs_striker": {"ko_tko": 1.4, "submission": 0.5, "decision": 0.9},
    "striker_vs_grappler": {"ko_tko": 1.1, "submission": 1.2, "decision": 0.9},
    "grappler_vs_striker": {"ko_tko": 0.8, "submission": 1.4, "decision": 0.95},
    "grappler_vs_grappler": {"ko_tko": 0.6, "submission": 1.5, "decision": 1.0},
    "mixed": {"ko_tko": 1.0, "submission": 1.0, "decision": 1.0},
}


def _parse_float(val: Any) -> Optional[float]:
    """Parse a numeric value from string or number."""
    if val is None:
        return None
    try:
        return float(str(val).replace("%", "").strip())
    except (ValueError, TypeError):
        return None


def _parse_record(record: str) -> Tuple[int, int, int]:
    """Parse 'W-L-D' record string."""
    try:
        parts = record.replace(" ", "").split("-")
        return (
            int(parts[0]) if len(parts) > 0 else 0,
            int(parts[1]) if len(parts) > 1 else 0,
            int(parts[2]) if len(parts) > 2 else 0,
        )
    except (ValueError, IndexError):
        return (0, 0, 0)


def extract_fighter_vector(stats: Dict[str, Any]) -> Dict[str, float]:
    """
    Extract a normalized stat vector from fighter data.
    Each dimension is scaled 0-1 relative to UFC averages.
    """
    vector = {}

    # Striking volume (SLpM) - UFC avg ~3.5
    slpm = _parse_float(stats.get("slpm"))
    vector["striking_volume"] = min(slpm / 7.0, 1.0) if slpm is not None else 0.5

    # Striking accuracy - UFC avg ~43%
    str_acc = _parse_float(stats.get("str_acc"))
    vector["striking_accuracy"] = min(str_acc / 70.0, 1.0) if str_acc is not None else 0.5

    # Striking defense - UFC avg ~55%
    str_def = _parse_float(stats.get("str_def"))
    vector["striking_defense"] = min(str_def / 80.0, 1.0) if str_def is not None else 0.5

    # Takedown offense (TD avg per 15 min) - UFC avg ~1.5
    td_avg = _parse_float(stats.get("td_avg"))
    vector["takedown_offense"] = min(td_avg / 5.0, 1.0) if td_avg is not None else 0.5

    # Takedown defense - UFC avg ~62%
    td_def = _parse_float(stats.get("td_def"))
    vector["takedown_defense"] = min(td_def / 90.0, 1.0) if td_def is not None else 0.5

    # Submission threat (sub avg per 15 min) - UFC avg ~0.5
    sub_avg = _parse_float(stats.get("sub_avg"))
    vector["submission_threat"] = min(sub_avg / 3.0, 1.0) if sub_avg is not None else 0.5

    # Absorbed per minute (lower is better) - inverted scale
    sapm = _parse_float(stats.get("sapm"))
    vector["cardio_pace"] = max(0, 1.0 - (sapm / 8.0)) if sapm is not None else 0.5

    # Experience from record
    record = stats.get("record", "")
    if record:
        w, l, d = _parse_record(record)
        total = w + l + d
        win_rate = w / max(total, 1)
        experience_score = min(total / 30, 0.5) + win_rate * 0.5
        vector["experience"] = min(experience_score, 1.0)
    else:
        vector["experience"] = 0.5

    return vector


def compute_win_probability(
    vector_a: Dict[str, float],
    vector_b: Dict[str, float],
) -> float:
    """
    Compute win probability for fighter A based on statistical vectors.
    Returns probability 0-1.
    """
    edge_score = 0.0

    for dim, weight in DIMENSION_WEIGHTS.items():
        val_a = vector_a.get(dim, 0.5)
        val_b = vector_b.get(dim, 0.5)
        # Difference scaled by weight
        edge_score += (val_a - val_b) * weight

    # Convert edge score to probability using logistic function
    # Scale factor controls spread (higher = more extreme probabilities)
    scale = 4.0
    # Clamp edge_score to prevent math.exp overflow for extreme values
    edge_score = max(-5, min(5, edge_score))
    prob_a = 1.0 / (1.0 + math.exp(-edge_score * scale))

    # Compress toward 50% (UFC fighters always have upset potential)
    # Floor at 15%, ceiling at 85%
    prob_a = 0.15 + prob_a * 0.70

    return round(prob_a, 4)


def simulate_fight(
    stats_a: Dict[str, Any],
    stats_b: Dict[str, Any],
    n_simulations: int = 10000,
    matchup_type: str = "mixed",
    is_five_round: bool = False,
) -> Dict[str, Any]:
    """
    Run Monte Carlo simulation of a fight.

    Args:
        stats_a: Fighter A stats from UFCStats
        stats_b: Fighter B stats from UFCStats
        n_simulations: Number of simulations to run
        matchup_type: Style matchup classification
        is_five_round: Whether this is a 5-round fight

    Returns:
        Simulation results with win probabilities, method distribution, round distribution
    """
    vector_a = extract_fighter_vector(stats_a)
    vector_b = extract_fighter_vector(stats_b)

    base_prob_a = compute_win_probability(vector_a, vector_b)

    # Method modifiers based on matchup type
    method_mod = METHOD_MODIFIERS.get(matchup_type, METHOD_MODIFIERS["mixed"])

    # Base method rates (adjusted by matchup)
    base_ko = 0.28 * method_mod.get("ko_tko", 1.0)
    base_sub = 0.10 * method_mod.get("submission", 1.0)
    base_dec = 1.0 - base_ko - base_sub

    # Adjust method rates based on fighter profiles
    # KO likelihood increases with high SLpM and low opponent defense
    ko_boost = 0.0
    slpm_a = _parse_float(stats_a.get("slpm"))
    str_def_b = _parse_float(stats_b.get("str_def"))
    if slpm_a and slpm_a > 5.0:
        ko_boost += 0.05
    if str_def_b and str_def_b < 50:
        ko_boost += 0.05

    slpm_b = _parse_float(stats_b.get("slpm"))
    str_def_a = _parse_float(stats_a.get("str_def"))
    if slpm_b and slpm_b > 5.0:
        ko_boost += 0.03
    if str_def_a and str_def_a < 50:
        ko_boost += 0.03

    # Sub likelihood increases with high sub avg
    sub_boost = 0.0
    sub_a = _parse_float(stats_a.get("sub_avg"))
    sub_b = _parse_float(stats_b.get("sub_avg"))
    if sub_a and sub_a > 1.0:
        sub_boost += 0.05
    if sub_b and sub_b > 1.0:
        sub_boost += 0.03

    adj_ko = min(base_ko + ko_boost, 0.60)
    adj_sub = min(base_sub + sub_boost, 0.30)
    adj_dec = max(1.0 - adj_ko - adj_sub, 0.15)

    # Normalize
    total = adj_ko + adj_sub + adj_dec
    adj_ko /= total
    adj_sub /= total
    adj_dec /= total

    # Round distribution base
    max_rounds = 5 if is_five_round else 3
    # Earlier rounds more likely for finishes
    round_weights = [1.0 / (1 + 0.3 * i) for i in range(max_rounds)]
    round_total = sum(round_weights)
    round_probs = [w / round_total for w in round_weights]

    # Run simulations
    results = {
        "a_wins": 0,
        "b_wins": 0,
        "methods": {"ko_tko": 0, "submission": 0, "decision": 0},
        "rounds": {f"r{i+1}": 0 for i in range(max_rounds)},
        "a_methods": {"ko_tko": 0, "submission": 0, "decision": 0},
        "b_methods": {"ko_tko": 0, "submission": 0, "decision": 0},
    }
    results["rounds"]["decision"] = 0

    rng = random.Random(42)  # deterministic for reproducibility

    for _ in range(n_simulations):
        # Determine winner
        winner_is_a = rng.random() < base_prob_a

        # Determine method
        method_roll = rng.random()
        if method_roll < adj_ko:
            method = "ko_tko"
        elif method_roll < adj_ko + adj_sub:
            method = "submission"
        else:
            method = "decision"

        # Determine round
        if method == "decision":
            finish_round = "decision"
        else:
            round_roll = rng.random()
            cumulative = 0.0
            finish_round = f"r{max_rounds}"
            for i, rp in enumerate(round_probs):
                cumulative += rp
                if round_roll < cumulative:
                    finish_round = f"r{i+1}"
                    break

        # Record results
        if winner_is_a:
            results["a_wins"] += 1
            results["a_methods"][method] += 1
        else:
            results["b_wins"] += 1
            results["b_methods"][method] += 1

        results["methods"][method] += 1
        results["rounds"][finish_round] += 1

    # Compile output
    name_a = stats_a.get("name", "Fighter A")
    name_b = stats_b.get("name", "Fighter B")

    return {
        "fighter_a": name_a,
        "fighter_b": name_b,
        "simulations": n_simulations,
        "win_probability": {
            name_a: round(results["a_wins"] / n_simulations * 100, 1),
            name_b: round(results["b_wins"] / n_simulations * 100, 1),
        },
        "method_distribution": {
            k: round(v / n_simulations * 100, 1)
            for k, v in results["methods"].items()
        },
        "round_distribution": {
            k: round(v / n_simulations * 100, 1)
            for k, v in results["rounds"].items()
        },
        "winner_method_breakdown": {
            name_a: {
                k: round(v / max(results["a_wins"], 1) * 100, 1)
                for k, v in results["a_methods"].items()
            },
            name_b: {
                k: round(v / max(results["b_wins"], 1) * 100, 1)
                for k, v in results["b_methods"].items()
            },
        },
        "statistical_edge": {
            dim: round(vector_a.get(dim, 0.5) - vector_b.get(dim, 0.5), 3)
            for dim in DIMENSION_WEIGHTS
        },
        "matchup_type": matchup_type,
        "is_five_round": is_five_round,
    }


# ============================================================
# ADVANCED ROUND-BY-ROUND SIMULATION
# ============================================================

# Cardio decay per round (cumulative fatigue)
CARDIO_DECAY_RATES = {
    "fast_starter": [1.0, 0.88, 0.76, 0.65, 0.55],
    "steady":       [0.95, 0.93, 0.88, 0.82, 0.76],
    "grinder":      [0.90, 0.90, 0.88, 0.86, 0.84],
}

# Championship rounds bonus for experienced fighters
CHAMP_ROUNDS_BONUS = 0.08  # 8% boost in R4/R5 if experienced


def _classify_cardio_type(stats: Dict[str, Any]) -> str:
    """Classify fighter's energy output pattern."""
    slpm = _parse_float(stats.get("slpm"))
    sapm = _parse_float(stats.get("sapm"))
    if slpm and sapm:
        output_ratio = slpm / max(sapm, 0.1)
        if slpm > 5.5 and output_ratio > 1.2:
            return "fast_starter"
        elif slpm < 3.0:
            return "grinder"
    return "steady"


def compute_physical_edge(
    stats_a: Dict[str, Any],
    stats_b: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Quantify physical attribute advantages.
    Reach, height, and size differentials.
    """
    reach_a = _parse_float(stats_a.get("reach"))
    reach_b = _parse_float(stats_b.get("reach"))
    height_a = _parse_float(stats_a.get("height"))
    height_b = _parse_float(stats_b.get("height"))

    edges = {}

    # Reach differential: every inch adds striking accuracy and defensive bonus
    if reach_a is not None and reach_b is not None:
        reach_diff = reach_a - reach_b
        edges["reach_diff_inches"] = round(reach_diff, 1)
        # +0.5% striking accuracy per inch of reach advantage
        edges["reach_accuracy_modifier"] = round(reach_diff * 0.005, 4)
        # +0.3% defensive bonus per inch (harder to hit from outside)
        edges["reach_defense_modifier"] = round(reach_diff * 0.003, 4)
        edges["reach_significant"] = abs(reach_diff) >= 3
    else:
        edges["reach_diff_inches"] = 0
        edges["reach_accuracy_modifier"] = 0
        edges["reach_defense_modifier"] = 0
        edges["reach_significant"] = False

    # Height differential: advantage in striking, disadvantage in clinch/grappling
    if height_a is not None and height_b is not None:
        height_diff = height_a - height_b
        edges["height_diff_inches"] = round(height_diff, 1)
        edges["height_striking_modifier"] = round(height_diff * 0.003, 4)
        edges["height_clinch_modifier"] = round(-height_diff * 0.002, 4)  # taller = worse in clinch
    else:
        edges["height_diff_inches"] = 0
        edges["height_striking_modifier"] = 0
        edges["height_clinch_modifier"] = 0

    return edges


def _round_finish_probability(
    base_ko_prob: float,
    base_sub_prob: float,
    round_num: int,
    cardio_a: List[float],
    cardio_b: List[float],
    damage_accumulated_a: float,
    damage_accumulated_b: float,
    physical_edge: Dict[str, Any],
) -> Dict[str, float]:
    """
    Compute per-round finish probabilities accounting for fatigue and damage.
    """
    rd = min(round_num, len(cardio_a)) - 1

    fatigue_a = cardio_a[rd] if rd < len(cardio_a) else 0.6
    fatigue_b = cardio_b[rd] if rd < len(cardio_b) else 0.6

    # Damage accumulation makes fighters more vulnerable to KO
    ko_vulnerability_a = 1.0 + damage_accumulated_a * 0.15
    ko_vulnerability_b = 1.0 + damage_accumulated_b * 0.15

    # Fatigue makes fighters more vulnerable to submissions
    sub_vulnerability_a = 1.0 + (1 - fatigue_a) * 0.3
    sub_vulnerability_b = 1.0 + (1 - fatigue_b) * 0.3

    # Round-specific base rates (R1 has more finishes)
    round_modifier = 1.0 / (1 + 0.15 * rd)

    # Physical edge modifiers
    reach_mod = physical_edge.get("reach_accuracy_modifier", 0)

    # A's probability of finishing B this round
    ko_prob_a = base_ko_prob * fatigue_a * ko_vulnerability_b * round_modifier * (1 + reach_mod)
    sub_prob_a = base_sub_prob * fatigue_a * sub_vulnerability_b * round_modifier

    # B's probability of finishing A this round
    ko_prob_b = base_ko_prob * fatigue_b * ko_vulnerability_a * round_modifier * (1 - reach_mod)
    sub_prob_b = base_sub_prob * fatigue_b * sub_vulnerability_a * round_modifier

    return {
        "ko_prob_a": min(0.3, ko_prob_a),
        "sub_prob_a": min(0.15, sub_prob_a),
        "ko_prob_b": min(0.3, ko_prob_b),
        "sub_prob_b": min(0.15, sub_prob_b),
    }


def simulate_fight_advanced(
    stats_a: Dict[str, Any],
    stats_b: Dict[str, Any],
    n_simulations: int = 10000,
    matchup_type: str = "mixed",
    is_five_round: bool = False,
) -> Dict[str, Any]:
    """
    Advanced round-by-round Monte Carlo fight simulation.

    Features:
    - Per-round finish probability with fatigue decay
    - Damage accumulation across rounds
    - Championship rounds modeling
    - Physical advantage integration
    - Confidence intervals on win probability
    """
    vector_a = extract_fighter_vector(stats_a)
    vector_b = extract_fighter_vector(stats_b)
    base_prob_a = compute_win_probability(vector_a, vector_b)

    method_mod = METHOD_MODIFIERS.get(matchup_type, METHOD_MODIFIERS["mixed"])
    max_rounds = 5 if is_five_round else 3

    # Cardio profiles
    cardio_type_a = _classify_cardio_type(stats_a)
    cardio_type_b = _classify_cardio_type(stats_b)
    cardio_a = CARDIO_DECAY_RATES[cardio_type_a][:max_rounds] or [0.85]
    cardio_b = CARDIO_DECAY_RATES[cardio_type_b][:max_rounds] or [0.85]

    # Physical edge
    physical_edge = compute_physical_edge(stats_a, stats_b)

    # Base method rates
    base_ko = 0.06 * method_mod.get("ko_tko", 1.0)
    base_sub = 0.025 * method_mod.get("submission", 1.0)

    # Adjust for fighter-specific power/grappling
    slpm_a = _parse_float(stats_a.get("slpm")) or 3.5
    str_def_b = _parse_float(stats_b.get("str_def")) or 55
    sub_a = _parse_float(stats_a.get("sub_avg")) or 0.5

    if slpm_a > 5.0:
        base_ko *= 1.2
    if str_def_b < 50:
        base_ko *= 1.15
    if sub_a > 1.0:
        base_sub *= 1.3

    # Run simulations
    rng = random.Random(42)
    results = {
        "a_wins": 0, "b_wins": 0,
        "methods": {"ko_tko": 0, "submission": 0, "decision": 0},
        "rounds": {f"r{i+1}": 0 for i in range(max_rounds)},
        "a_methods": {"ko_tko": 0, "submission": 0, "decision": 0},
        "b_methods": {"ko_tko": 0, "submission": 0, "decision": 0},
    }
    results["rounds"]["decision"] = 0

    # Track individual outcomes for confidence interval
    win_outcomes = []

    for _ in range(n_simulations):
        fight_over = False
        damage_a = 0.0
        damage_b = 0.0

        for rd in range(1, max_rounds + 1):
            probs = _round_finish_probability(
                base_ko, base_sub, rd, cardio_a, cardio_b,
                damage_a, damage_b, physical_edge,
            )

            # Check if A finishes B
            roll = rng.random()
            if roll < probs["ko_prob_a"] * base_prob_a * 2:
                results["a_wins"] += 1
                results["a_methods"]["ko_tko"] += 1
                results["methods"]["ko_tko"] += 1
                results["rounds"][f"r{rd}"] += 1
                win_outcomes.append(1)
                fight_over = True
                break
            elif roll < (probs["ko_prob_a"] + probs["sub_prob_a"]) * base_prob_a * 2:
                results["a_wins"] += 1
                results["a_methods"]["submission"] += 1
                results["methods"]["submission"] += 1
                results["rounds"][f"r{rd}"] += 1
                win_outcomes.append(1)
                fight_over = True
                break

            # Check if B finishes A
            roll2 = rng.random()
            if roll2 < probs["ko_prob_b"] * (1 - base_prob_a) * 2:
                results["b_wins"] += 1
                results["b_methods"]["ko_tko"] += 1
                results["methods"]["ko_tko"] += 1
                results["rounds"][f"r{rd}"] += 1
                win_outcomes.append(0)
                fight_over = True
                break
            elif roll2 < (probs["ko_prob_b"] + probs["sub_prob_b"]) * (1 - base_prob_a) * 2:
                results["b_wins"] += 1
                results["b_methods"]["submission"] += 1
                results["methods"]["submission"] += 1
                results["rounds"][f"r{rd}"] += 1
                win_outcomes.append(0)
                fight_over = True
                break

            # Accumulate damage this round (more damage taken as fatigue increases)
            fatigue_a = 1 - cardio_a[min(rd-1, len(cardio_a)-1)]
            fatigue_b = 1 - cardio_b[min(rd-1, len(cardio_b)-1)]
            damage_a += rng.uniform(0.05, 0.15) * (0.5 + fatigue_a)
            damage_b += rng.uniform(0.05, 0.15) * (0.5 + fatigue_b)

        if not fight_over:
            # Decision: use base probability with fatigue adjustment
            late_fatigue_a = cardio_a[-1] if cardio_a else 0.7
            late_fatigue_b = cardio_b[-1] if cardio_b else 0.7
            fatigue_edge = (late_fatigue_a - late_fatigue_b) * 0.1
            dec_prob_a = base_prob_a + fatigue_edge

            if rng.random() < dec_prob_a:
                results["a_wins"] += 1
                results["a_methods"]["decision"] += 1
                win_outcomes.append(1)
            else:
                results["b_wins"] += 1
                results["b_methods"]["decision"] += 1
                win_outcomes.append(0)
            results["methods"]["decision"] += 1
            results["rounds"]["decision"] += 1

    # Confidence interval
    ci = compute_confidence_interval(win_outcomes)

    name_a = stats_a.get("name", "Fighter A")
    name_b = stats_b.get("name", "Fighter B")

    return {
        "fighter_a": name_a,
        "fighter_b": name_b,
        "simulations": n_simulations,
        "win_probability": {
            name_a: round(results["a_wins"] / n_simulations * 100, 1),
            name_b: round(results["b_wins"] / n_simulations * 100, 1),
        },
        "method_distribution": {
            k: round(v / n_simulations * 100, 1)
            for k, v in results["methods"].items()
        },
        "round_distribution": {
            k: round(v / n_simulations * 100, 1)
            for k, v in results["rounds"].items()
        },
        "winner_method_breakdown": {
            name_a: {
                k: round(v / max(results["a_wins"], 1) * 100, 1)
                for k, v in results["a_methods"].items()
            },
            name_b: {
                k: round(v / max(results["b_wins"], 1) * 100, 1)
                for k, v in results["b_methods"].items()
            },
        },
        "statistical_edge": {
            dim: round(vector_a.get(dim, 0.5) - vector_b.get(dim, 0.5), 3)
            for dim in DIMENSION_WEIGHTS
        },
        "matchup_type": matchup_type,
        "is_five_round": is_five_round,
        "confidence_interval_90": ci,
        "cardio_profiles": {
            name_a: cardio_type_a,
            name_b: cardio_type_b,
        },
        "physical_edge": physical_edge,
        "simulation_type": "advanced_round_by_round",
    }


def compute_confidence_interval(
    outcomes: List[int],
    confidence: float = 0.90,
) -> Dict[str, float]:
    """
    Compute confidence interval for win probability from simulation outcomes.
    Uses normal approximation (valid for large N).
    """
    if not outcomes:
        return {"lower": 0.0, "upper": 100.0, "mean": 50.0}

    n = len(outcomes)
    mean = sum(outcomes) / n
    variance = sum((x - mean) ** 2 for x in outcomes) / max(n - 1, 1)
    std_err = math.sqrt(variance / n) if n > 1 else 0

    # Z-score for 90% CI = 1.645
    z = 1.645 if confidence == 0.90 else 1.96

    lower = max(0, mean - z * std_err) * 100
    upper = min(1, mean + z * std_err) * 100

    return {
        "lower": round(lower, 1),
        "upper": round(upper, 1),
        "mean": round(mean * 100, 1),
        "std_error": round(std_err * 100, 2),
    }
