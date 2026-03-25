"""Tests for data/aging_curve.py — fighter aging curve model."""
import pytest
from data.aging_curve import (
    compute_skill_multipliers,
    compute_composite_age_score,
    detect_regression,
    classify_career_phase,
    age_adjustment,
    estimate_chin_health,
    full_age_analysis,
    _parse_record,
)


# ============================================================
# Skill Multipliers
# ============================================================

class TestSkillMultipliers:
    def test_peak_age_returns_neutral(self):
        mults = compute_skill_multipliers(30, "lightweight")
        assert mults["speed"] == 1.0
        assert mults["power"] == 1.0
        assert mults["cardio"] == 1.0

    def test_young_fighter_slight_penalty(self):
        mults = compute_skill_multipliers(22, "lightweight")
        assert mults["speed"] < 1.0  # not yet developed
        assert mults["fight_iq"] == 1.0  # just starting improvement

    def test_old_fighter_decline(self):
        mults = compute_skill_multipliers(40, "lightweight")
        assert mults["speed"] < 1.0
        assert mults["cardio"] < 1.0
        assert mults["chin"] < 1.0

    def test_fight_iq_improves_with_age(self):
        m25 = compute_skill_multipliers(25)
        m34 = compute_skill_multipliers(34)
        assert m34["fight_iq"] > m25["fight_iq"]

    def test_fight_iq_plateaus_at_36(self):
        m36 = compute_skill_multipliers(36)
        m40 = compute_skill_multipliers(40)
        assert m36["fight_iq"] == m40["fight_iq"]

    def test_heavyweight_later_peak(self):
        hw = compute_skill_multipliers(35, "heavyweight")
        lw = compute_skill_multipliers(35, "lightweight")
        assert hw["speed"] >= lw["speed"]  # HW still in peak, LW past

    def test_multipliers_clamped(self):
        mults = compute_skill_multipliers(55)  # very old
        for v in mults.values():
            assert 0.5 <= v <= 1.2

    def test_chin_decline_starts_at_33(self):
        m32 = compute_skill_multipliers(32)
        m34 = compute_skill_multipliers(34)
        assert m32["chin"] == 1.0
        assert m34["chin"] < 1.0

    def test_unknown_weight_class_uses_default(self):
        mults = compute_skill_multipliers(30, "super_heavyweight")
        assert mults["speed"] == 1.0

    def test_all_skill_keys_present(self):
        mults = compute_skill_multipliers(30)
        expected = {"speed", "reflexes", "power", "cardio", "fight_iq", "technique", "chin"}
        assert set(mults.keys()) == expected


# ============================================================
# Composite Age Score
# ============================================================

class TestCompositeScore:
    def test_peak_age_high_score(self):
        score = compute_composite_age_score(30, "lightweight")
        assert score >= 95

    def test_old_fighter_lower_score(self):
        peak = compute_composite_age_score(30, "lightweight")
        old = compute_composite_age_score(42, "lightweight")
        assert old < peak

    def test_score_in_valid_range(self):
        for age in range(18, 50):
            score = compute_composite_age_score(age)
            assert 0 <= score <= 100  # clamped by function


# ============================================================
# Regression Detection
# ============================================================

class TestRegressionDetection:
    def test_no_regression_young_fighter(self):
        result = detect_regression(
            fighter_stats={"slpm": "5.0", "str_acc": "50%", "str_def": "55%"},
            age=25,
            weight_class="lightweight",
        )
        assert result["regression_score"] == 0.0
        assert result["is_regressing"] is False

    def test_past_peak_adds_score(self):
        result = detect_regression(
            fighter_stats={},
            age=38,
            weight_class="lightweight",
        )
        assert result["regression_score"] > 0
        assert "past_peak" in result["flags"] or "significantly_past_peak" in result["flags"]

    def test_recent_losses_detected(self):
        history = [
            {"result": "L", "method": "Decision"},
            {"result": "L", "method": "Decision"},
            {"result": "L", "method": "KO"},
            {"result": "W", "method": "Decision"},
            {"result": "W", "method": "Decision"},
        ]
        result = detect_regression(
            fighter_stats={},
            age=35,
            fight_history=history,
            weight_class="welterweight",
        )
        assert result["is_regressing"] is True
        assert "recent_losses" in result["flags"]

    def test_chin_deterioration_flagged(self):
        history = [
            {"result": "L", "method": "KO"},
            {"result": "W", "method": "Decision"},
            {"result": "L", "method": "TKO"},
            {"result": "W", "method": "Decision"},
            {"result": "W", "method": "Decision"},
        ]
        result = detect_regression(
            fighter_stats={},
            age=36,
            fight_history=history,
            weight_class="middleweight",
        )
        assert "chin_deterioration" in result["flags"]
        assert result["regression_type"] == "physical"

    def test_no_history_still_works(self):
        result = detect_regression(fighter_stats={}, age=30)
        assert isinstance(result["regression_score"], float)

    def test_short_history(self):
        history = [{"result": "W"}, {"result": "L"}]  # < 5 fights
        result = detect_regression(fighter_stats={}, age=30, fight_history=history)
        assert isinstance(result["regression_score"], float)


# ============================================================
# Career Phase
# ============================================================

class TestCareerPhase:
    def test_prospect(self):
        result = classify_career_phase(age=23, ufc_fight_count=3, weight_class="bantamweight")
        assert result["phase"] == "prospect"

    def test_rising(self):
        result = classify_career_phase(
            age=26, streak_type="W", streak_count=4, weight_class="lightweight"
        )
        assert result["phase"] == "rising"

    def test_prime(self):
        result = classify_career_phase(age=30, weight_class="lightweight")
        assert result["phase"] == "prime"

    def test_declining(self):
        result = classify_career_phase(
            age=38, weight_class="lightweight", regression_score=0.5
        )
        assert result["phase"] == "declining"

    def test_veteran(self):
        result = classify_career_phase(
            age=37, weight_class="lightweight", regression_score=0.1
        )
        assert result["phase"] == "veteran"

    def test_gatekeeper(self):
        result = classify_career_phase(
            age=34, record="16-15-0", weight_class="welterweight",
            regression_score=0.1,
        )
        assert result["phase"] == "gatekeeper"

    def test_confidence_modifier_returned(self):
        result = classify_career_phase(age=30, weight_class="lightweight")
        assert "confidence_modifier" in result


# ============================================================
# Age Adjustment
# ============================================================

class TestAgeAdjustment:
    def test_same_age_no_adjustment(self):
        result = age_adjustment(30, 30, "lightweight")
        assert result["modifier"] == 0.0

    def test_prime_vs_declining(self):
        result = age_adjustment(
            30, 39, "lightweight", phase_a="prime", phase_b="declining"
        )
        assert result["modifier"] > 0  # A should be boosted

    def test_declining_vs_prime(self):
        result = age_adjustment(
            39, 30, "lightweight", phase_a="declining", phase_b="prime"
        )
        assert result["modifier"] < 0  # A should be penalized

    def test_large_age_gap(self):
        result = age_adjustment(40, 25, "lightweight")
        assert result["modifier"] < 0
        assert result["age_gap"] == 15

    def test_modifier_clamped(self):
        result = age_adjustment(50, 20, "lightweight", phase_a="declining", phase_b="rising")
        assert -0.15 <= result["modifier"] <= 0.15


# ============================================================
# Chin Health
# ============================================================

class TestChinHealth:
    def test_young_no_ko_losses(self):
        result = estimate_chin_health(age=25, ko_losses=0, total_fights=10)
        assert result["chin_health"] == 1.0
        assert result["vulnerability"] == "minimal"

    def test_ko_losses_reduce_chin(self):
        result = estimate_chin_health(age=30, ko_losses=3, total_fights=20)
        assert result["chin_health"] < 1.0

    def test_age_reduces_chin(self):
        young = estimate_chin_health(age=25, ko_losses=0, total_fights=10)
        old = estimate_chin_health(age=40, ko_losses=0, total_fights=10)
        assert old["chin_health"] < young["chin_health"]

    def test_recovery_factor(self):
        no_recovery = estimate_chin_health(age=30, ko_losses=2, total_fights=15, years_since_last_ko_loss=0.5)
        with_recovery = estimate_chin_health(age=30, ko_losses=2, total_fights=15, years_since_last_ko_loss=3.0)
        assert with_recovery["chin_health"] > no_recovery["chin_health"]

    def test_high_fight_count_penalty(self):
        low = estimate_chin_health(age=30, ko_losses=0, total_fights=15)
        high = estimate_chin_health(age=30, ko_losses=0, total_fights=40)
        assert high["chin_health"] < low["chin_health"]

    def test_chin_floor_at_zero(self):
        result = estimate_chin_health(age=45, ko_losses=10, total_fights=50)
        assert result["chin_health"] >= 0.0

    def test_vulnerability_flag(self):
        result = estimate_chin_health(age=42, ko_losses=5, total_fights=40)
        assert result["vulnerability_flag"] is True


# ============================================================
# Full Analysis
# ============================================================

class TestFullAnalysis:
    def test_returns_all_sections(self):
        result = full_age_analysis(
            age=30, weight_class="lightweight", record="15-3-0",
            ko_losses=1, total_fights=18, ufc_fight_count=10,
        )
        assert "composite_age_score" in result
        assert "skill_multipliers" in result
        assert "regression" in result
        assert "career_phase" in result
        assert "chin_health" in result

    def test_works_with_minimal_args(self):
        result = full_age_analysis(age=30)
        assert result["age"] == 30


# ============================================================
# Utility
# ============================================================

class TestParseRecord:
    def test_standard_record(self):
        assert _parse_record("20-5-1") == (20, 5, 1)

    def test_no_draws(self):
        assert _parse_record("15-3") == (15, 3, 0)

    def test_invalid_record(self):
        assert _parse_record("unknown") == (0, 0, 0)

    def test_empty_string(self):
        assert _parse_record("") == (0, 0, 0)
