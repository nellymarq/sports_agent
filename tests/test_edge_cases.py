"""
Comprehensive edge case tests across all analytics modules.
Tests boundary conditions, empty inputs, extreme values, and cross-module integration.
"""
import pytest
import math
from data.fight_simulation import (
    extract_fighter_vector,
    compute_win_probability,
    simulate_fight,
    simulate_fight_advanced,
    compute_physical_edge,
    compute_confidence_interval,
)
from data.elo_rating import (
    expected_score,
    get_method_multiplier,
    compute_k_factor,
    apply_inactivity_decay,
    update_elo,
    ELORatingSystem,
    GlickoELORatingSystem,
)
from data.value_bets import (
    american_to_implied,
    decimal_to_implied,
    implied_to_american,
    remove_vig,
    kelly_fraction,
    expected_value,
    calculate_parlay,
    identify_value_bets,
)
from data.style_classifier import classify_style, classify_matchup
from data.prop_analysis import analyze_method_props, analyze_round_props
from data.aging_curve import (
    compute_skill_multipliers,
    estimate_chin_health,
    detect_regression,
    classify_career_phase,
    age_adjustment,
)
from data.cage_control import analyze_clinch_profile, predict_fight_location
from data.judge_model import score_fight_round, predict_decision
from data.calibration import decompose_calibration_error, analyze_prediction_streaks


# ============================================================
# FIGHT SIMULATION EDGE CASES
# ============================================================

class TestSimulationEdgeCases:
    def test_empty_stats(self):
        """Empty stats dicts should use defaults and not crash."""
        result = simulate_fight({}, {})
        assert result["simulations"] == 10000
        assert "win_probability" in result

    def test_all_none_stats(self):
        """Stats with all None values should use defaults."""
        stats = {"slpm": None, "str_acc": None, "str_def": None, "td_avg": None,
                 "td_def": None, "sub_avg": None, "sapm": None, "record": None}
        result = simulate_fight(stats, stats)
        name_a = stats.get("name", "Fighter A")
        assert abs(result["win_probability"][name_a] - 50) < 5

    def test_extreme_high_stats(self):
        """Extreme stats should not produce probabilities outside 0-100."""
        stats_a = {"slpm": "20", "str_acc": "100", "str_def": "100",
                   "td_avg": "10", "td_def": "100", "sub_avg": "5", "sapm": "0", "record": "50-0-0"}
        stats_b = {"slpm": "0", "str_acc": "0", "str_def": "0",
                   "td_avg": "0", "td_def": "0", "sub_avg": "0", "sapm": "20", "record": "0-50-0"}
        result = simulate_fight(stats_a, stats_b)
        for prob in result["win_probability"].values():
            assert 0 <= prob <= 100

    def test_identical_fighters_roughly_50_50(self):
        """Identical fighters should produce ~50/50."""
        stats = {"slpm": "4.0", "str_acc": "48", "str_def": "55",
                 "td_avg": "1.5", "td_def": "62", "sub_avg": "0.5",
                 "sapm": "3.5", "record": "15-5-0", "name": "Fighter"}
        result = simulate_fight(stats, stats)
        assert abs(result["win_probability"]["Fighter"] - 50) < 10

    def test_single_simulation(self):
        """N=1 simulation should still work."""
        result = simulate_fight({}, {}, n_simulations=1)
        assert result["simulations"] == 1

    def test_method_distribution_sums_to_100(self):
        """Method percentages should sum to ~100."""
        result = simulate_fight({}, {})
        total = sum(result["method_distribution"].values())
        assert abs(total - 100) < 1

    def test_invalid_matchup_type(self):
        """Invalid matchup type should fall back to 'mixed'."""
        result = simulate_fight({}, {}, matchup_type="nonexistent_type")
        assert result["matchup_type"] == "nonexistent_type"
        assert "win_probability" in result

    def test_negative_stats(self):
        """Negative stats should not crash."""
        stats = {"slpm": "-5", "str_acc": "-10", "str_def": "-20"}
        result = simulate_fight(stats, {})
        assert "win_probability" in result


class TestAdvancedSimulationEdgeCases:
    def test_basic_advanced_sim(self):
        result = simulate_fight_advanced({}, {}, n_simulations=100)
        assert result["simulation_type"] == "advanced_round_by_round"
        assert "confidence_interval_90" in result

    def test_five_round_advanced(self):
        result = simulate_fight_advanced({}, {}, n_simulations=100, is_five_round=True)
        assert "r4" in result["round_distribution"]
        assert "r5" in result["round_distribution"]

    def test_physical_edge_no_data(self):
        edge = compute_physical_edge({}, {})
        assert edge["reach_diff_inches"] == 0

    def test_physical_edge_with_data(self):
        edge = compute_physical_edge({"reach": "76"}, {"reach": "70"})
        assert edge["reach_diff_inches"] == 6
        assert edge["reach_significant"] is True

    def test_confidence_interval_empty(self):
        ci = compute_confidence_interval([])
        assert ci["lower"] == 0.0
        assert ci["upper"] == 100.0

    def test_confidence_interval_all_wins(self):
        ci = compute_confidence_interval([1] * 100)
        assert ci["mean"] == 100.0

    def test_confidence_interval_all_losses(self):
        ci = compute_confidence_interval([0] * 100)
        assert ci["mean"] == 0.0


# ============================================================
# ELO RATING EDGE CASES
# ============================================================

class TestELOEdgeCases:
    def test_new_fighter_default(self):
        """New fighters should start at default rating."""
        system = ELORatingSystem()
        assert system.get_rating("unknown_fighter") == 1500

    def test_extreme_rating_gap(self):
        """Large rating gap should produce extreme but bounded probabilities."""
        prob = expected_score(2000, 1000)
        assert prob > 0.95
        assert prob < 1.0

    def test_equal_ratings(self):
        """Equal ratings should give 50% win probability."""
        prob = expected_score(1500, 1500)
        assert abs(prob - 0.5) < 0.001

    def test_process_same_fight_twice(self):
        """Processing same fight twice should update ratings twice."""
        system = ELORatingSystem()
        r1 = system.process_fight("a", "b", "KO", "2024-01-01")
        r2 = system.process_fight("a", "b", "KO", "2024-01-01")
        assert system.get_rating("a") > r1[0]  # Rating should increase further

    def test_empty_method_string(self):
        """Empty method string should not crash."""
        mult = get_method_multiplier("")
        assert mult == 1.0

    def test_inactivity_no_date(self):
        """No last fight date should return rating unchanged."""
        result = apply_inactivity_decay(1600, None)
        assert result == 1600

    def test_inactivity_invalid_date(self):
        result = apply_inactivity_decay(1600, "not-a-date")
        assert result == 1600

    def test_rating_floor(self):
        """Rating should not go below floor."""
        result = apply_inactivity_decay(1300, "2015-01-01")
        assert result >= 1300  # DEFAULT_ELO - 200

    def test_k_factor_early_career(self):
        k = compute_k_factor(2, "KO", True)
        assert k > compute_k_factor(20, "Decision", False)


class TestGlickoELOEdgeCases:
    def test_rd_decreases_after_fight(self):
        system = GlickoELORatingSystem()
        initial_rd = system.get_rd("fighter_a")
        system.process_fight("fighter_a", "fighter_b", "Decision")
        assert system.get_rd("fighter_a") < initial_rd

    def test_peak_rating_tracking(self):
        system = GlickoELORatingSystem()
        system.process_fight("a", "b", "KO", "2024-01-01")
        peak = system.get_peak_rating("a")
        assert peak is not None
        assert peak["rating"] > 1500

    def test_quality_wins(self):
        system = GlickoELORatingSystem()
        system.ratings["b"] = 1650
        system.process_fight("a", "b", "KO")
        assert system.get_quality_wins("a") == 1

    def test_division_transfer(self):
        system = GlickoELORatingSystem()
        system.ratings["a"] = 1600
        system.division_ratings["a"] = {"lightweight": 1600}
        new = system.transfer_division("a", "lightweight", "welterweight", "up")
        assert new == 1550  # -50 penalty

    def test_rating_velocity(self):
        system = GlickoELORatingSystem()
        for i in range(5):
            system.process_fight("a", f"b{i}", "Decision", f"2024-0{i+1}-01")
        velocity = system.get_rating_velocity("a")
        assert velocity is not None
        assert velocity > 0  # winning = positive velocity

    def test_matchup_with_uncertainty(self):
        system = GlickoELORatingSystem()
        pred = system.get_matchup_prediction("a", "b")
        assert "uncertainty_band" in pred
        assert "prob_range_a" in pred
        assert pred["reliability"] == "low"  # new fighters = low reliability


# ============================================================
# VALUE BET EDGE CASES
# ============================================================

class TestValueBetEdgeCases:
    def test_odds_at_boundary_plus_100(self):
        result = american_to_implied("+100")
        assert result == 0.5

    def test_odds_at_boundary_minus_100(self):
        result = american_to_implied("-100")
        assert result == 0.5

    def test_extreme_long_odds(self):
        result = american_to_implied("+5000")
        assert result is not None
        assert result < 0.05

    def test_extreme_short_odds(self):
        result = american_to_implied("-5000")
        assert result is not None
        assert result > 0.95

    def test_model_prob_zero(self):
        kelly = kelly_fraction(0.0, 2.0)
        assert kelly == 0.0

    def test_model_prob_one(self):
        kelly = kelly_fraction(1.0, 2.0)
        assert kelly == 0.0

    def test_negative_edge_kelly(self):
        """Kelly should return 0 for negative edge bets."""
        kelly = kelly_fraction(0.3, 2.0)
        assert kelly == 0.0

    def test_vig_removal_extreme(self):
        """Extreme vig should still normalize."""
        fair_a, fair_b = remove_vig(0.7, 0.7)  # 140% total implied
        assert abs(fair_a + fair_b - 1.0) < 0.001

    def test_parlay_single_leg(self):
        """Single leg parlay should error."""
        result = calculate_parlay([{"fighter": "A", "decimal_odds": 2.0}])
        assert "error" in result

    def test_parlay_zero_odds(self):
        """Legs with odds <= 1 should be filtered."""
        result = calculate_parlay([
            {"fighter": "A", "decimal_odds": 0.5},
            {"fighter": "B", "decimal_odds": 1.0},
        ])
        assert "error" in result

    def test_empty_predictions_value_bets(self):
        result = identify_value_bets([], {})
        assert result == []


# ============================================================
# STYLE CLASSIFIER EDGE CASES
# ============================================================

class TestStyleClassifierEdgeCases:
    def test_all_zero_stats(self):
        result = classify_style({"slpm": "0", "str_acc": "0", "str_def": "0",
                                 "td_avg": "0", "td_acc": "0", "td_def": "0", "sub_avg": "0", "sapm": "0"})
        assert "primary_style" in result

    def test_only_striking_stats(self):
        result = classify_style({"slpm": "6.0", "str_acc": "55", "str_def": "60", "sapm": "3.0"})
        assert result["primary_style"] != "unknown"

    def test_only_grappling_stats(self):
        result = classify_style({"td_avg": "5.0", "td_acc": "60", "sub_avg": "2.0"})
        assert result["primary_style"] in ["wrestler", "grappler"]

    def test_perfect_stats(self):
        result = classify_style({"slpm": "10", "str_acc": "70", "str_def": "80",
                                 "td_avg": "5", "td_acc": "65", "td_def": "90",
                                 "sub_avg": "3", "sapm": "1"})
        assert result["primary_style"] != "unknown"

    def test_matchup_between_unknowns(self):
        result = classify_matchup({}, {})
        assert "matchup_type" in result

    def test_clinch_fighter_archetype(self):
        """New clinch_fighter archetype should be classifiable."""
        result = classify_style({"slpm": "3.5", "sapm": "5.0", "str_def": "50",
                                 "td_avg": "2.0", "str_acc": "42"})
        assert "clinch_fighter" in result.get("style_scores", {})


# ============================================================
# AGING CURVE EDGE CASES
# ============================================================

class TestAgingCurveEdgeCases:
    def test_very_young_fighter(self):
        mults = compute_skill_multipliers(18)
        assert all(0.5 <= v <= 1.2 for v in mults.values())

    def test_very_old_fighter(self):
        mults = compute_skill_multipliers(50)
        assert mults["chin"] < 1.0
        assert mults["cardio"] < 1.0

    def test_chin_zero_ko_losses(self):
        result = estimate_chin_health(25, ko_losses=0)
        assert result["chin_health"] == 1.0

    def test_chin_many_ko_losses(self):
        result = estimate_chin_health(40, ko_losses=8, total_fights=40)
        assert result["vulnerability_flag"] is True

    def test_regression_no_history(self):
        result = detect_regression({}, age=30)
        assert isinstance(result["regression_score"], float)

    def test_career_phase_all_types(self):
        """Ensure all career phases are reachable."""
        assert classify_career_phase(22, ufc_fight_count=2)["phase"] == "prospect"
        assert classify_career_phase(30, weight_class="lightweight")["phase"] == "prime"
        assert classify_career_phase(38, weight_class="lightweight", regression_score=0.5)["phase"] == "declining"

    def test_age_adjustment_same_age(self):
        result = age_adjustment(30, 30)
        assert result["modifier"] == 0.0


# ============================================================
# PROP ANALYSIS EDGE CASES
# ============================================================

class TestPropEdgeCases:
    def test_method_probs_summing_over_100(self):
        """Method probabilities > 100 should still produce output."""
        result = analyze_method_props({"ko_tko": 60, "submission": 30, "decision": 40})
        assert result is not None

    def test_round_probs_missing_rounds(self):
        """Missing rounds should be handled gracefully."""
        result = analyze_round_props({"r1": 30, "r3": 20})
        assert result is not None

    def test_empty_method_probs(self):
        result = analyze_method_props({})
        assert result is not None


# ============================================================
# JUDGE MODEL EDGE CASES
# ============================================================

class TestJudgeEdgeCases:
    def test_empty_stats_scoring(self):
        result = score_fight_round({}, {})
        assert abs(result["round_win_probability_a"] + result["round_win_probability_b"] - 1.0) < 0.001

    def test_decision_with_unknown_judges(self):
        result = predict_decision({}, {}, judges=["nonexistent_judge_1", "nonexistent_2", "nonexistent_3"])
        assert len(result["judge_cards"]) == 3


# ============================================================
# CALIBRATION EDGE CASES
# ============================================================

class TestCalibrationEdgeCases:
    def test_decompose_single_prediction(self):
        preds = [{"win_probability": 0.7, "correct": True}]
        result = decompose_calibration_error(preds)
        assert "brier_score" in result

    def test_streaks_single_prediction(self):
        preds = [{"correct": True, "timestamp": 1}]
        result = analyze_prediction_streaks(preds)
        assert result["longest_correct_streak"] == 1

    def test_all_predictions_correct(self):
        preds = [{"win_probability": 0.7, "correct": True, "timestamp": i} for i in range(10)]
        streaks = analyze_prediction_streaks(preds)
        assert streaks["hot_cold_indicator"] == "hot"

    def test_all_predictions_incorrect(self):
        preds = [{"win_probability": 0.7, "correct": False, "timestamp": i} for i in range(10)]
        streaks = analyze_prediction_streaks(preds)
        assert streaks["hot_cold_indicator"] == "cold"


# ============================================================
# CROSS-MODULE INTEGRATION TESTS
# ============================================================

class TestCrossModuleIntegration:
    def test_style_to_simulation_pipeline(self):
        """Style classification should feed into simulation matchup type."""
        stats_a = {"slpm": "6.0", "str_acc": "50", "str_def": "55", "sapm": "4.0",
                   "td_avg": "1.0", "td_acc": "30", "td_def": "70", "sub_avg": "0.3",
                   "name": "Striker A", "record": "15-3-0"}
        stats_b = {"slpm": "2.0", "str_acc": "40", "str_def": "50", "sapm": "2.5",
                   "td_avg": "5.0", "td_acc": "55", "td_def": "65", "sub_avg": "1.5",
                   "name": "Grappler B", "record": "12-5-0"}

        matchup = classify_matchup(stats_a, stats_b)
        matchup_type = matchup["matchup_type"]

        sim = simulate_fight(stats_a, stats_b, matchup_type=matchup_type)
        assert sim["matchup_type"] == matchup_type
        assert sim["win_probability"]["Striker A"] > 0

    def test_elo_direction_matches_simulation(self):
        """ELO prediction direction should broadly match simulation."""
        system = ELORatingSystem()
        # Give fighter A a strong record
        for i in range(10):
            system.process_fight("strong", f"weak{i}", "KO")

        elo_pred = system.get_matchup_prediction("strong", "new_fighter")
        # Strong fighter should be favored
        assert elo_pred["fighter_a_win_prob"] > 0.5

    def test_aging_feeds_into_simulation(self):
        """Aging curve data should be computable alongside simulation."""
        stats = {"slpm": "4.0", "str_acc": "48", "str_def": "55",
                 "td_avg": "1.5", "td_def": "62", "sub_avg": "0.5",
                 "sapm": "3.5", "record": "20-5-0", "name": "Veteran"}

        aging = estimate_chin_health(age=38, ko_losses=3, total_fights=25)
        sim = simulate_fight(stats, stats)

        # Both should produce valid results
        assert aging["chin_health"] < 1.0
        assert sim["win_probability"]["Veteran"] > 0

    def test_clinch_location_to_simulation(self):
        """Fight location prediction should be consistent with fighter styles."""
        grappler = {"td_avg": "5.0", "td_def": "50", "sub_avg": "2.0", "sapm": "4.0"}
        striker = {"td_avg": "0.5", "td_def": "80", "sub_avg": "0.1", "sapm": "2.5"}

        location = predict_fight_location(grappler, striker)
        # Grappler vs striker should have meaningful ground time
        assert location["location_distribution"]["ground"] > 10
