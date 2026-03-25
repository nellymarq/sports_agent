"""Tests for data/parlay_engine.py — correlation-aware parlay engine."""
import pytest
from data.parlay_engine import (
    compute_fight_correlation,
    adjust_parlay_probability,
    build_optimal_parlays,
    build_sgp,
    calculate_hedge,
    size_parlay_bet,
)


class TestFightCorrelation:
    def test_same_weight_class(self):
        bout_a = {"weight_class": "Lightweight"}
        bout_b = {"weight_class": "Lightweight"}
        corr = compute_fight_correlation(bout_a, bout_b)
        assert corr > 0

    def test_different_weight_class(self):
        bout_a = {"weight_class": "Lightweight"}
        bout_b = {"weight_class": "Heavyweight"}
        corr = compute_fight_correlation(bout_a, bout_b)
        assert corr == 0 or abs(corr) < 0.1

    def test_same_camp_negative(self):
        bout_a = {"fighters": [{"camp": "ATT"}]}
        bout_b = {"fighters": [{"camp": "ATT"}]}
        corr = compute_fight_correlation(bout_a, bout_b)
        assert corr < 0

    def test_correlation_bounded(self):
        bout = {"weight_class": "LW", "fighters": [{"camp": "X"}], "card_position": "main"}
        corr = compute_fight_correlation(bout, bout)
        assert -1 <= corr <= 1

    def test_empty_bouts(self):
        corr = compute_fight_correlation({}, {})
        assert corr == 0


class TestAdjustParlayProbability:
    def test_independent_legs(self):
        legs = [{"model_probability": 0.6}, {"model_probability": 0.7}]
        prob = adjust_parlay_probability(legs)
        assert abs(prob - 0.42) < 0.01  # 0.6 * 0.7

    def test_positive_correlation_increases_prob(self):
        legs = [{"model_probability": 0.6}, {"model_probability": 0.7}]
        corrs = {"0_1": 0.2}
        prob = adjust_parlay_probability(legs, corrs)
        independent = 0.6 * 0.7
        assert prob > independent

    def test_negative_correlation_decreases_prob(self):
        legs = [{"model_probability": 0.6}, {"model_probability": 0.7}]
        corrs = {"0_1": -0.2}
        prob = adjust_parlay_probability(legs, corrs)
        independent = 0.6 * 0.7
        assert prob < independent

    def test_empty_legs(self):
        assert adjust_parlay_probability([]) == 0.0


class TestBuildOptimalParlays:
    def test_basic_parlay_construction(self):
        vbets = [
            {"fighter": "A", "edge": 0.08, "odds_decimal": 2.0, "model_probability": 0.58},
            {"fighter": "B", "edge": 0.06, "odds_decimal": 1.8, "model_probability": 0.62},
            {"fighter": "C", "edge": 0.10, "odds_decimal": 2.5, "model_probability": 0.50},
        ]
        parlays = build_optimal_parlays(vbets, max_legs=3, bankroll=1000)
        assert len(parlays) > 0
        assert parlays[0]["num_legs"] >= 2

    def test_insufficient_bets(self):
        assert build_optimal_parlays([{"fighter": "A", "edge": 0.05}]) == []

    def test_max_5_returned(self):
        vbets = [
            {"fighter": f"F{i}", "edge": 0.05 + i*0.01, "odds_decimal": 1.8 + i*0.2, "model_probability": 0.55}
            for i in range(6)
        ]
        parlays = build_optimal_parlays(vbets, max_legs=3)
        assert len(parlays) <= 5


class TestBuildSGP:
    def test_basic_sgp(self):
        pred = {"predicted_winner": "Poirier", "win_probability": 0.65}
        methods = {"ko_tko": 35, "submission": 10, "decision": 55}
        rounds = {"r1": 25, "r2": 20, "r3": 15, "decision": 40}
        sgps = build_sgp(pred, methods, rounds)
        assert len(sgps) > 0
        assert sgps[0]["true_probability"] > 0

    def test_empty_prediction(self):
        sgps = build_sgp({}, {}, {})
        assert sgps == []

    def test_sgp_probabilities_correct(self):
        pred = {"predicted_winner": "A", "win_probability": 0.70}
        methods = {"ko_tko": 40, "decision": 60}
        rounds = {"r1": 30, "r2": 25, "r3": 20, "decision": 25}
        sgps = build_sgp(pred, methods, rounds)
        for sgp in sgps:
            assert sgp["true_probability"] <= pred["win_probability"]


class TestCalculateHedge:
    def test_basic_hedge(self):
        result = calculate_hedge(
            parlay_stake=50,
            parlay_odds=5.0,
            remaining_legs_count=1,
            hedge_odds=2.0,
        )
        assert result["guaranteed_profit"] >= 0
        assert "recommendation" in result

    def test_invalid_inputs(self):
        result = calculate_hedge(50, 5.0, 0, 2.0)
        assert "error" in result


class TestSizeParlayBet:
    def test_positive_ev(self):
        result = size_parlay_bet(0.2, 5.0, 1000, "moderate")
        assert result["recommended_stake"] > 0

    def test_negative_ev(self):
        result = size_parlay_bet(-0.1, 5.0, 1000)
        assert result["recommended_stake"] == 0

    def test_conservative_smaller_than_aggressive(self):
        conservative = size_parlay_bet(0.15, 4.0, 1000, "conservative")
        aggressive = size_parlay_bet(0.15, 4.0, 1000, "aggressive")
        assert conservative["recommended_stake"] <= aggressive["recommended_stake"]

    def test_zero_bankroll(self):
        result = size_parlay_bet(0.2, 5.0, 0)
        assert result["recommended_stake"] == 0
