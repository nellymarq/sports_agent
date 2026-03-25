# data/aging_curve.py
# Fighter aging curve model: age-performance relationships, regression detection,
# career phase classification, chin degradation, and age-adjusted win probability.

from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple


# ============================================================
# WEIGHT-CLASS PEAK AGE WINDOWS
# ============================================================
PEAK_WINDOWS = {
    "flyweight":       (27, 31),
    "bantamweight":    (27, 31),
    "featherweight":   (28, 32),
    "lightweight":     (28, 32),
    "welterweight":    (29, 33),
    "middleweight":    (29, 33),
    "light_heavyweight": (30, 36),
    "heavyweight":     (30, 36),
    "strawweight":     (27, 31),   # women's
    "women_flyweight": (27, 31),
    "women_bantamweight": (28, 32),
}

DEFAULT_PEAK_WINDOW = (28, 33)


# ============================================================
# SKILL DIMENSION AGING RATES (per year past peak)
# ============================================================
# Negative = decline, positive = improvement
SKILL_AGING_RATES = {
    "speed":       -0.030,   # -3% per year after peak
    "reflexes":    -0.030,   # -3%
    "power":       -0.015,   # -1.5% (slower decline)
    "cardio":      -0.040,   # -4% (fastest decline)
    "fight_iq":     0.010,   # +1% per year until 36
    "technique":    0.010,   # +1% per year until 36
    "chin":        -0.050,   # -5% per year after 33 (sharp decline)
}

# Age at which fight_iq/technique stop improving
IQ_PLATEAU_AGE = 36

# Chin decline starts at this age regardless of weight class
CHIN_DECLINE_START = 33


def _get_peak_window(weight_class: Optional[str] = None) -> Tuple[int, int]:
    """Get the peak age window for a weight class."""
    if not weight_class:
        return DEFAULT_PEAK_WINDOW
    wc = weight_class.lower().replace(" ", "_").replace("'", "")
    # Handle common aliases
    aliases = {
        "women's_strawweight": "strawweight",
        "women's_flyweight": "women_flyweight",
        "women's_bantamweight": "women_bantamweight",
        "women's_featherweight": "women_bantamweight",
    }
    wc = aliases.get(wc, wc)
    return PEAK_WINDOWS.get(wc, DEFAULT_PEAK_WINDOW)


def compute_skill_multipliers(
    age: int,
    weight_class: Optional[str] = None,
) -> Dict[str, float]:
    """
    Compute age-based multipliers for each skill dimension.

    Returns a dict mapping skill -> multiplier (1.0 = no effect, <1.0 = decline, >1.0 = improvement).
    All multipliers are clamped to [0.5, 1.2].

    Args:
        age: Fighter's current age
        weight_class: UFC weight class for peak window lookup
    """
    peak_start, peak_end = _get_peak_window(weight_class)
    multipliers: Dict[str, float] = {}

    for skill, rate in SKILL_AGING_RATES.items():
        if rate > 0:
            # Improvement skills (fight_iq, technique)
            if age <= IQ_PLATEAU_AGE:
                # Improve from early career through plateau age
                years_of_improvement = max(0, age - 22)  # assume improvement starts at 22
                mult = 1.0 + rate * min(years_of_improvement, IQ_PLATEAU_AGE - 22)
            else:
                # Plateau after IQ_PLATEAU_AGE
                mult = 1.0 + rate * (IQ_PLATEAU_AGE - 22)
        elif skill == "chin":
            # Chin has its own decline start
            if age <= CHIN_DECLINE_START:
                mult = 1.0
            else:
                years_past = age - CHIN_DECLINE_START
                mult = 1.0 + rate * years_past  # rate is negative
        else:
            # Decline skills
            if age <= peak_start:
                # Before peak: slight improvement as they develop
                years_before = peak_start - age
                mult = 1.0 - 0.005 * years_before  # slight youth penalty (raw, undeveloped)
            elif age <= peak_end:
                # In peak window: no decline
                mult = 1.0
            else:
                # Past peak: declining
                years_past = age - peak_end
                mult = 1.0 + rate * years_past  # rate is negative

        # Clamp
        multipliers[skill] = round(max(0.5, min(1.2, mult)), 3)

    return multipliers


def compute_composite_age_score(
    age: int,
    weight_class: Optional[str] = None,
) -> float:
    """
    Compute a single composite age score (0-100).
    100 = peak performance, declining toward 50 as fighter ages.
    """
    multipliers = compute_skill_multipliers(age, weight_class)

    # Weighted average of skill multipliers
    weights = {
        "speed": 0.18,
        "reflexes": 0.12,
        "power": 0.15,
        "cardio": 0.18,
        "fight_iq": 0.15,
        "technique": 0.10,
        "chin": 0.12,
    }

    weighted_sum = sum(
        multipliers.get(skill, 1.0) * w for skill, w in weights.items()
    )
    total_weight = sum(weights.values())

    # Normalize to 0-100 scale
    raw = weighted_sum / total_weight
    score = round(raw * 100, 1)
    return max(0, min(100, score))


# ============================================================
# REGRESSION DETECTION
# ============================================================

def detect_regression(
    fighter_stats: Dict[str, Any],
    age: int,
    fight_history: Optional[List[Dict[str, Any]]] = None,
    weight_class: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Detect whether a fighter is showing regression signs.

    Compares recent performance (last 3 fights) vs career averages.
    Returns regression analysis with score and type.

    Args:
        fighter_stats: Current fighter stats (slpm, str_acc, etc.)
        age: Fighter's current age
        fight_history: List of fight dicts (most recent first)
        weight_class: Weight class for age curve context
    """
    flags: List[str] = []
    regression_score = 0.0

    # Age-based regression check
    peak_start, peak_end = _get_peak_window(weight_class)
    years_past_peak = max(0, age - peak_end)

    if years_past_peak > 0:
        regression_score += min(0.3, years_past_peak * 0.06)
        if years_past_peak >= 3:
            flags.append("significantly_past_peak")
        elif years_past_peak >= 1:
            flags.append("past_peak")

    # Stat-based regression (compare recent to career)
    if fight_history and len(fight_history) >= 5:
        recent = fight_history[:3]
        career = fight_history

        # Check recent results
        recent_losses = sum(
            1 for f in recent
            if (f.get("result") or "").upper().startswith("L")
        )
        if recent_losses >= 2:
            regression_score += 0.2
            flags.append("recent_losses")
        if recent_losses >= 3:
            regression_score += 0.15
            flags.append("losing_streak")

        # Check if recent losses are to lower-quality opponents
        recent_ko_losses = sum(
            1 for f in recent
            if (f.get("result") or "").upper().startswith("L")
            and any(x in (f.get("method") or "").lower() for x in ("ko", "tko"))
        )
        if recent_ko_losses >= 1 and age > CHIN_DECLINE_START:
            regression_score += 0.15
            flags.append("chin_deterioration")

        # Check finish rate regression
        career_wins = [f for f in career if (f.get("result") or "").upper().startswith("W")]
        recent_wins = [f for f in recent if (f.get("result") or "").upper().startswith("W")]

        if len(career_wins) >= 5 and len(recent_wins) >= 1:
            career_finishes = sum(
                1 for f in career_wins
                if any(x in (f.get("method") or "").lower() for x in ("ko", "tko", "sub"))
            )
            career_finish_rate = career_finishes / len(career_wins) if career_wins else 0

            recent_finishes = sum(
                1 for f in recent_wins
                if any(x in (f.get("method") or "").lower() for x in ("ko", "tko", "sub"))
            )
            recent_finish_rate = recent_finishes / len(recent_wins) if recent_wins else 0

            if career_finish_rate > 0 and recent_finish_rate < career_finish_rate * 0.7:
                regression_score += 0.1
                flags.append("finish_rate_decline")

    # Stat-level regression indicators
    slpm = _parse_float(fighter_stats.get("slpm"))
    str_acc = _parse_float(fighter_stats.get("str_acc"))
    str_def = _parse_float(fighter_stats.get("str_def"))

    # Fighters past peak with poor defense are concerning
    if str_def is not None and str_def < 48 and years_past_peak > 0:
        regression_score += 0.1
        flags.append("defensive_decline")

    # Clamp
    regression_score = round(min(1.0, regression_score), 3)

    # Classify regression type
    if "chin_deterioration" in flags:
        regression_type = "physical"
    elif "finish_rate_decline" in flags and "defensive_decline" in flags:
        regression_type = "physical"
    elif "recent_losses" in flags and regression_score < 0.4:
        regression_type = "motivational"
    elif flags:
        regression_type = "mixed"
    else:
        regression_type = "none"

    return {
        "regression_score": regression_score,
        "regression_type": regression_type,
        "flags": flags,
        "years_past_peak": years_past_peak,
        "is_regressing": regression_score >= 0.3,
        "age": age,
        "peak_window": (peak_start, peak_end),
    }


# ============================================================
# CAREER PHASE CLASSIFICATION
# ============================================================

def classify_career_phase(
    age: int,
    record: str = "",
    streak_type: str = "",
    streak_count: int = 0,
    ufc_fight_count: int = 0,
    weight_class: Optional[str] = None,
    regression_score: float = 0.0,
) -> Dict[str, Any]:
    """
    Classify a fighter's current career phase.

    Returns:
        Dict with phase name, description, and prediction implications.
    """
    peak_start, peak_end = _get_peak_window(weight_class)

    # Parse record
    wins, losses, draws = _parse_record(record)
    total = wins + losses + draws
    win_rate = wins / max(total, 1)

    # Determine phase
    if age < 26 and ufc_fight_count < 8:
        phase = "prospect"
        description = "Young, developing fighter with limited UFC experience"
        prediction_note = "High variance — could significantly outperform or underperform expectations"
        confidence_modifier = -0.10  # widen uncertainty

    elif age <= peak_start and streak_type == "W" and streak_count >= 2:
        phase = "rising"
        description = "Improving fighter trending upward, approaching peak"
        prediction_note = "Momentum factor — recent improvement may continue"
        confidence_modifier = 0.0

    elif peak_start <= age <= peak_end and regression_score < 0.3:
        phase = "prime"
        description = "In peak performance window with reliable recent form"
        prediction_note = "Most reliable prediction window — stats are representative"
        confidence_modifier = 0.05

    elif age > peak_end and regression_score >= 0.4:
        phase = "declining"
        description = "Past peak and showing regression signs"
        prediction_note = "Decline risk — historical stats may overstate current ability"
        confidence_modifier = -0.05

    elif total >= 15 and 0.45 <= win_rate <= 0.55 and age >= 28:
        phase = "gatekeeper"
        description = "Experienced but plateaued — tests prospects, loses to elite"
        prediction_note = "Reliable floor but limited ceiling — overperforms vs prospects, underperforms vs ranked"
        confidence_modifier = 0.0

    elif age > peak_end and regression_score < 0.4:
        phase = "veteran"
        description = "Past peak but still competitive through experience"
        prediction_note = "Fight IQ compensates for physical decline — watch for chin issues"
        confidence_modifier = 0.0

    elif age >= peak_start and age <= peak_end:
        phase = "prime"
        description = "In peak performance window"
        prediction_note = "Most reliable prediction window"
        confidence_modifier = 0.05

    else:
        phase = "developing"
        description = "Establishing themselves in the division"
        prediction_note = "Moderate prediction uncertainty"
        confidence_modifier = 0.0

    return {
        "phase": phase,
        "description": description,
        "prediction_note": prediction_note,
        "confidence_modifier": confidence_modifier,
        "age": age,
        "in_peak_window": peak_start <= age <= peak_end,
    }


# ============================================================
# AGE-ADJUSTED WIN PROBABILITY MODIFIER
# ============================================================

def age_adjustment(
    age_a: int,
    age_b: int,
    weight_class: Optional[str] = None,
    phase_a: Optional[str] = None,
    phase_b: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Compute age-based win probability adjustment.

    Returns modifier for fighter A's win probability.
    Positive = boost A, negative = penalize A.

    Args:
        age_a: Fighter A's age
        age_b: Fighter B's age
        weight_class: Weight class for peak window
        phase_a: Career phase of A (optional, computed if not provided)
        phase_b: Career phase of B (optional, computed if not provided)
    """
    peak_start, peak_end = _get_peak_window(weight_class)

    # Compute phases if not provided
    if not phase_a:
        phase_a = "prime" if peak_start <= age_a <= peak_end else (
            "declining" if age_a > peak_end + 2 else "other"
        )
    if not phase_b:
        phase_b = "prime" if peak_start <= age_b <= peak_end else (
            "declining" if age_b > peak_end + 2 else "other"
        )

    modifier = 0.0
    reasons: List[str] = []

    # Phase-based adjustments
    if phase_a == "prime" and phase_b == "declining":
        modifier += 0.07
        reasons.append(f"A in prime vs B declining (+7%)")
    elif phase_a == "declining" and phase_b == "prime":
        modifier -= 0.07
        reasons.append(f"A declining vs B in prime (-7%)")

    if phase_a == "prime" and phase_b == "prospect":
        modifier += 0.03
        reasons.append(f"A in prime vs prospect B (experience edge +3%)")
    elif phase_a == "prospect" and phase_b == "prime":
        modifier -= 0.03
        reasons.append(f"A prospect vs prime B (-3%)")

    # Large age gap penalty for older fighter
    age_gap = abs(age_a - age_b)
    if age_gap >= 10:
        older_is_a = age_a > age_b
        gap_penalty = min(0.08, (age_gap - 8) * 0.02)
        if older_is_a:
            modifier -= gap_penalty
            reasons.append(f"Large age gap ({age_gap} yrs), A is older (-{gap_penalty*100:.0f}%)")
        else:
            modifier += gap_penalty
            reasons.append(f"Large age gap ({age_gap} yrs), B is older (+{gap_penalty*100:.0f}%)")
    elif age_gap >= 6:
        older_is_a = age_a > age_b
        gap_penalty = 0.02
        if older_is_a and age_a > peak_end:
            modifier -= gap_penalty
            reasons.append(f"Age gap with A past peak (-2%)")
        elif not older_is_a and age_b > peak_end:
            modifier += gap_penalty
            reasons.append(f"Age gap with B past peak (+2%)")

    # Clamp modifier
    modifier = round(max(-0.15, min(0.15, modifier)), 3)

    return {
        "modifier": modifier,
        "modifier_pct": f"{modifier*100:+.1f}%",
        "reasons": reasons,
        "age_a": age_a,
        "age_b": age_b,
        "phase_a": phase_a,
        "phase_b": phase_b,
        "age_gap": abs(age_a - age_b),
    }


# ============================================================
# CHIN DEGRADATION MODEL
# ============================================================

def estimate_chin_health(
    age: int,
    ko_losses: int = 0,
    total_fights: int = 0,
    years_since_last_ko_loss: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Estimate a fighter's chin health / knockout vulnerability.

    Returns chin_health (0-1) where 1.0 = iron chin, 0.0 = glass chin.

    Args:
        age: Fighter's current age
        ko_losses: Number of career KO/TKO losses
        total_fights: Total career fights
        years_since_last_ko_loss: Years since most recent KO loss (None = never been KO'd)
    """
    chin = 1.0

    # KO loss damage (cumulative and permanent)
    chin -= ko_losses * 0.08

    # Age-related chin deterioration
    if age > CHIN_DECLINE_START:
        years_past = age - CHIN_DECLINE_START
        chin -= years_past * 0.03

    # Recovery factor: time since last KO loss
    if years_since_last_ko_loss is not None and years_since_last_ko_loss >= 2.0 and ko_losses > 0:
        recovery = min(0.06, years_since_last_ko_loss * 0.03)
        chin += recovery

    # High fight count = accumulated damage
    if total_fights > 30:
        accumulated = (total_fights - 30) * 0.005
        chin -= min(accumulated, 0.10)

    # Clamp
    chin = round(max(0.0, min(1.0, chin)), 3)

    # Vulnerability assessment
    if chin < 0.5:
        vulnerability = "high"
    elif chin < 0.7:
        vulnerability = "moderate"
    elif chin < 0.85:
        vulnerability = "low"
    else:
        vulnerability = "minimal"

    return {
        "chin_health": chin,
        "vulnerability": vulnerability,
        "vulnerability_flag": chin < 0.6,
        "ko_susceptibility_modifier": round(1.0 - chin, 3),
        "factors": {
            "ko_losses_impact": round(ko_losses * 0.08, 3),
            "age_impact": round(max(0, age - CHIN_DECLINE_START) * 0.03, 3),
            "accumulated_damage": round(max(0, (total_fights - 30) * 0.005), 3) if total_fights > 30 else 0,
            "recovery_bonus": round(
                min(0.06, years_since_last_ko_loss * 0.03), 3
            ) if years_since_last_ko_loss is not None and years_since_last_ko_loss >= 2.0 and ko_losses > 0 else 0,
        },
    }


# ============================================================
# COMBINED AGE ANALYSIS
# ============================================================

def full_age_analysis(
    age: int,
    weight_class: Optional[str] = None,
    record: str = "",
    fight_history: Optional[List[Dict[str, Any]]] = None,
    fighter_stats: Optional[Dict[str, Any]] = None,
    ko_losses: int = 0,
    total_fights: int = 0,
    years_since_last_ko_loss: Optional[float] = None,
    streak_type: str = "",
    streak_count: int = 0,
    ufc_fight_count: int = 0,
) -> Dict[str, Any]:
    """
    Run the complete age analysis pipeline for a fighter.
    Combines all aging curve modules into a single report.
    """
    skill_multipliers = compute_skill_multipliers(age, weight_class)
    composite_score = compute_composite_age_score(age, weight_class)

    regression = detect_regression(
        fighter_stats=fighter_stats or {},
        age=age,
        fight_history=fight_history,
        weight_class=weight_class,
    )

    career_phase = classify_career_phase(
        age=age,
        record=record,
        streak_type=streak_type,
        streak_count=streak_count,
        ufc_fight_count=ufc_fight_count,
        weight_class=weight_class,
        regression_score=regression["regression_score"],
    )

    chin = estimate_chin_health(
        age=age,
        ko_losses=ko_losses,
        total_fights=total_fights,
        years_since_last_ko_loss=years_since_last_ko_loss,
    )

    return {
        "age": age,
        "weight_class": weight_class,
        "composite_age_score": composite_score,
        "skill_multipliers": skill_multipliers,
        "regression": regression,
        "career_phase": career_phase,
        "chin_health": chin,
    }


# ============================================================
# UTILITY
# ============================================================

def _parse_float(val) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(str(val).replace("%", "").strip())
    except (ValueError, TypeError):
        return None


def _parse_record(record: str) -> Tuple[int, int, int]:
    try:
        parts = record.replace(" ", "").split("-")
        return (
            int(parts[0]) if len(parts) > 0 else 0,
            int(parts[1]) if len(parts) > 1 else 0,
            int(parts[2]) if len(parts) > 2 else 0,
        )
    except (ValueError, IndexError):
        return (0, 0, 0)
