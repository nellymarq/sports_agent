"""Tests for data/judge_model.py — judge tendencies and decision prediction."""
import pytest
from data.judge_model import (
    score_fight_round,
    predict_decision,
    predict_decision_type,
    compute_location_bias,
    get_judge_adjustment,
    JUDGE_DATABASE,
    AVERAGE_JUDGE,
)


class TestScoreFightRound:
    def test_basic_scoring(self):
        stats_a = {"slpm": "5.0", "str_acc": "50", "str_def": "55", "td_avg": "2.0", "td_def": "65", "sapm": "3.5"}
        stats_b = {"slpm": "3.0", "str_acc": "45", "str_def": "50", "td_avg": "1.0", "td_def": "60", "sapm": "3.0"}
        result = score_fight_round(stats_a, stats_b)
        assert result["round_win_probability_a"] > 0.5  # A has better stats
        assert abs(result["round_win_probability_a"] + result["round_win_probability_b"] - 1.0) < 0.001

    def test_equal_stats(self):
        stats = {"slpm": "3.5", "str_acc": "45", "str_def": "55", "td_avg": "1.5", "td_def": "60", "sapm": "3.5"}
        result = score_fight_round(stats, stats)
        assert abs(result["round_win_probability_a"] - 0.5) < 0.05

    def test_judge_profile_affects_scoring(self):
        stats_a = {"slpm": "5.0", "str_acc": "50", "str_def": "55", "td_avg": "0.5", "td_def": "65", "sapm": "3.5"}
        stats_b = {"slpm": "2.0", "str_acc": "40", "str_def": "50", "td_avg": "4.0", "td_def": "70", "sapm": "2.5"}

        # Striker-friendly judge
        striker_judge = {"name": "Test", "aggression_weight": 0.4, "control_weight": 0.2, "damage_weight": 0.4}
        result_striker = score_fight_round(stats_a, stats_b, striker_judge)

        # Control-friendly judge
        control_judge = {"name": "Test", "aggression_weight": 0.2, "control_weight": 0.5, "damage_weight": 0.3}
        result_control = score_fight_round(stats_a, stats_b, control_judge)

        # Striker-friendly judge should favor A more
        assert result_striker["round_win_probability_a"] > result_control["round_win_probability_a"]

    def test_breakdown_included(self):
        result = score_fight_round({}, {})
        assert "breakdown" in result
        assert "damage" in result["breakdown"]
        assert "control" in result["breakdown"]
        assert "aggression" in result["breakdown"]


class TestPredictDecision:
    def test_basic_prediction(self):
        stats_a = {"slpm": "5.0", "str_acc": "50", "str_def": "55", "td_avg": "2.0", "td_def": "65", "sapm": "3.5"}
        stats_b = {"slpm": "3.0", "str_acc": "45", "str_def": "50", "td_avg": "1.0", "td_def": "60", "sapm": "3.0"}
        result = predict_decision(stats_a, stats_b)
        assert "decision_probability_a" in result
        assert "decision_probability_b" in result
        assert abs(result["decision_probability_a"] + result["decision_probability_b"] - 1.0) < 0.001

    def test_five_round_fight(self):
        result = predict_decision({}, {}, is_five_round=True)
        assert result["num_rounds"] == 5

    def test_with_specific_judges(self):
        result = predict_decision({}, {}, judges=["sal_damato", "chris_lee", "derek_cleary"])
        assert len(result["judge_cards"]) == 3

    def test_decision_type_included(self):
        result = predict_decision({}, {})
        assert "decision_type" in result
        dt = result["decision_type"]
        assert "unanimous" in dt
        assert "split" in dt


class TestDecisionType:
    def test_close_fight(self):
        result = predict_decision_type(0.03)
        assert result["split"] > result["unanimous"]

    def test_clear_winner(self):
        result = predict_decision_type(0.25)
        assert result["unanimous"] > result["split"]

    def test_probabilities_sum_to_100(self):
        result = predict_decision_type(0.10)
        total = sum(result.values())
        assert abs(total - 100) < 0.1


class TestLocationBias:
    def test_hometown_advantage(self):
        result = compute_location_bias("Brazilian", "American", "Brazil")
        assert result["bias_a"] > 0
        assert result["bias_b"] == 0

    def test_neutral_venue(self):
        result = compute_location_bias("American", "Brazilian", "UAE")
        assert result["bias_a"] == 0
        assert result["bias_b"] == 0

    def test_same_nationality_cancels(self):
        result = compute_location_bias("American", "American", "USA")
        assert result["bias_a"] == 0
        assert result["bias_b"] == 0


class TestJudgeDatabase:
    def test_all_judges_have_required_fields(self):
        required = ["name", "aggression_weight", "control_weight", "damage_weight", "split_decision_rate"]
        for key, judge in JUDGE_DATABASE.items():
            for field in required:
                assert field in judge, f"Judge {key} missing {field}"

    def test_weights_sum_to_one(self):
        for key, judge in JUDGE_DATABASE.items():
            total = judge["aggression_weight"] + judge["control_weight"] + judge["damage_weight"]
            assert abs(total - 1.0) < 0.01, f"Judge {key} weights sum to {total}"

    def test_average_judge_weights(self):
        total = AVERAGE_JUDGE["aggression_weight"] + AVERAGE_JUDGE["control_weight"] + AVERAGE_JUDGE["damage_weight"]
        assert abs(total - 1.0) < 0.01
