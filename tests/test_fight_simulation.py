# tests/test_fight_simulation.py
# Tests for Monte Carlo fight simulation.

import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from data.fight_simulation import (
    extract_fighter_vector,
    compute_win_probability,
    simulate_fight,
    DIMENSION_WEIGHTS,
)


STRIKER_STATS = {
    "name": "Striker",
    "record": "20-3-0",
    "slpm": "6.5",
    "str_acc": "55%",
    "sapm": "3.0",
    "str_def": "62%",
    "td_avg": "0.3",
    "td_acc": "25%",
    "td_def": "75%",
    "sub_avg": "0.1",
}

WRESTLER_STATS = {
    "name": "Wrestler",
    "record": "18-5-0",
    "slpm": "2.5",
    "str_acc": "42%",
    "sapm": "2.8",
    "str_def": "58%",
    "td_avg": "4.0",
    "td_acc": "55%",
    "td_def": "80%",
    "sub_avg": "0.8",
}

AVERAGE_STATS = {
    "name": "Average",
    "record": "10-5-0",
    "slpm": "3.5",
    "str_acc": "43%",
    "sapm": "3.5",
    "str_def": "55%",
    "td_avg": "1.5",
    "td_acc": "40%",
    "td_def": "62%",
    "sub_avg": "0.5",
}


class TestExtractFighterVector:
    def test_basic_extraction(self):
        vec = extract_fighter_vector(STRIKER_STATS)
        assert "striking_volume" in vec
        assert "striking_defense" in vec
        assert "takedown_offense" in vec
        assert "experience" in vec
        # All values should be 0-1
        for v in vec.values():
            assert 0 <= v <= 1

    def test_empty_stats(self):
        vec = extract_fighter_vector({})
        # Should default to 0.5 for all
        for v in vec.values():
            assert v == 0.5

    def test_striker_has_high_striking(self):
        vec = extract_fighter_vector(STRIKER_STATS)
        assert vec["striking_volume"] > 0.7  # 6.5 SLpM is very high

    def test_wrestler_has_high_td(self):
        vec = extract_fighter_vector(WRESTLER_STATS)
        assert vec["takedown_offense"] > 0.7  # 4.0 TD avg is very high

    def test_experience_from_record(self):
        vec = extract_fighter_vector({"record": "25-2-0"})
        assert vec["experience"] > 0.7  # lots of wins


class TestWinProbability:
    def test_equal_fighters(self):
        vec = extract_fighter_vector(AVERAGE_STATS)
        prob = compute_win_probability(vec, vec)
        assert abs(prob - 0.5) < 0.05  # should be ~50/50

    def test_better_fighter_favored(self):
        vec_a = extract_fighter_vector(STRIKER_STATS)
        vec_avg = extract_fighter_vector(AVERAGE_STATS)
        prob = compute_win_probability(vec_a, vec_avg)
        assert prob > 0.5  # striker should be favored vs average

    def test_probability_bounded(self):
        # Even extreme differences should stay in bounds
        vec_elite = extract_fighter_vector({
            "slpm": "8.0", "str_acc": "65%", "sapm": "1.0",
            "str_def": "75%", "td_avg": "3.0", "td_acc": "60%",
            "td_def": "90%", "sub_avg": "2.0", "record": "30-0-0",
        })
        vec_bad = extract_fighter_vector({
            "slpm": "1.0", "str_acc": "25%", "sapm": "7.0",
            "str_def": "30%", "td_avg": "0.1", "td_acc": "10%",
            "td_def": "20%", "sub_avg": "0.0", "record": "2-10-0",
        })
        prob = compute_win_probability(vec_elite, vec_bad)
        assert 0.15 <= prob <= 0.85

    def test_symmetric(self):
        vec_a = extract_fighter_vector(STRIKER_STATS)
        vec_b = extract_fighter_vector(WRESTLER_STATS)
        prob_ab = compute_win_probability(vec_a, vec_b)
        prob_ba = compute_win_probability(vec_b, vec_a)
        assert abs(prob_ab + prob_ba - 1.0) < 0.01


class TestSimulateFight:
    def test_basic_simulation(self):
        result = simulate_fight(STRIKER_STATS, WRESTLER_STATS, n_simulations=1000)
        assert "win_probability" in result
        assert "method_distribution" in result
        assert "round_distribution" in result
        assert result["simulations"] == 1000

    def test_probabilities_sum_to_100(self):
        result = simulate_fight(STRIKER_STATS, WRESTLER_STATS, n_simulations=5000)
        win_total = sum(result["win_probability"].values())
        assert abs(win_total - 100.0) < 0.5

        method_total = sum(result["method_distribution"].values())
        assert abs(method_total - 100.0) < 0.5

        round_total = sum(result["round_distribution"].values())
        assert abs(round_total - 100.0) < 0.5

    def test_five_round_has_more_rounds(self):
        result_3 = simulate_fight(STRIKER_STATS, WRESTLER_STATS, n_simulations=1000, is_five_round=False)
        result_5 = simulate_fight(STRIKER_STATS, WRESTLER_STATS, n_simulations=1000, is_five_round=True)
        assert "r4" not in result_3["round_distribution"] or result_3["round_distribution"].get("r4", 0) == 0
        assert "r4" in result_5["round_distribution"]
        assert "r5" in result_5["round_distribution"]

    def test_deterministic_with_seed(self):
        """Same inputs should give same results (seeded RNG)."""
        r1 = simulate_fight(STRIKER_STATS, WRESTLER_STATS, n_simulations=1000)
        r2 = simulate_fight(STRIKER_STATS, WRESTLER_STATS, n_simulations=1000)
        assert r1["win_probability"] == r2["win_probability"]

    def test_fighter_names_in_output(self):
        result = simulate_fight(STRIKER_STATS, WRESTLER_STATS, n_simulations=100)
        assert result["fighter_a"] == "Striker"
        assert result["fighter_b"] == "Wrestler"
        assert "Striker" in result["win_probability"]

    def test_statistical_edge_included(self):
        result = simulate_fight(STRIKER_STATS, WRESTLER_STATS, n_simulations=100)
        assert "statistical_edge" in result
        # Striker should have positive striking_volume edge
        assert result["statistical_edge"]["striking_volume"] > 0
        # Wrestler should have positive takedown edge (negative for A's perspective)
        assert result["statistical_edge"]["takedown_offense"] < 0

    def test_matchup_type_affects_methods(self):
        result_sv = simulate_fight(
            STRIKER_STATS, WRESTLER_STATS,
            n_simulations=5000, matchup_type="striker_vs_grappler",
        )
        result_gv = simulate_fight(
            STRIKER_STATS, WRESTLER_STATS,
            n_simulations=5000, matchup_type="grappler_vs_grappler",
        )
        # Striker vs grappler should have higher KO rate than grappler vs grappler
        assert result_sv["method_distribution"]["ko_tko"] > result_gv["method_distribution"]["ko_tko"]

    def test_simulation_cap(self):
        """Simulations should be capped at 50000 by the endpoint."""
        # Direct call doesn't cap, but should still work
        result = simulate_fight(STRIKER_STATS, WRESTLER_STATS, n_simulations=100)
        assert result["simulations"] == 100

    def test_winner_method_breakdown(self):
        result = simulate_fight(STRIKER_STATS, WRESTLER_STATS, n_simulations=1000)
        assert "winner_method_breakdown" in result
        assert "Striker" in result["winner_method_breakdown"]
        assert "Wrestler" in result["winner_method_breakdown"]
        # Each fighter's methods should roughly sum to 100
        for fighter_methods in result["winner_method_breakdown"].values():
            total = sum(fighter_methods.values())
            assert abs(total - 100.0) < 1.0


class TestDimensionWeights:
    def test_weights_sum_to_one(self):
        total = sum(DIMENSION_WEIGHTS.values())
        assert abs(total - 1.0) < 0.01

    def test_defensive_stats_weighted_higher(self):
        """Defensive stats should collectively outweigh offensive stats."""
        defensive = DIMENSION_WEIGHTS["striking_defense"] + DIMENSION_WEIGHTS["takedown_defense"]
        offensive = DIMENSION_WEIGHTS["striking_volume"] + DIMENSION_WEIGHTS["takedown_offense"]
        assert defensive >= offensive
