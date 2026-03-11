# tests/test_elo_rating.py
# Tests for the ELO rating system.

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.elo_rating import (
    expected_score,
    get_method_multiplier,
    compute_k_factor,
    update_elo,
    apply_inactivity_decay,
    ELORatingSystem,
    _rating_diff_to_confidence,
    elo_probability_to_american_odds,
    DEFAULT_ELO,
    K_BASE,
)
from datetime import date


class TestExpectedScore:
    def test_equal_ratings(self):
        assert expected_score(1500, 1500) == pytest.approx(0.5)

    def test_higher_rating_favored(self):
        assert expected_score(1600, 1400) > 0.5

    def test_lower_rating_underdog(self):
        assert expected_score(1400, 1600) < 0.5

    def test_symmetric(self):
        p = expected_score(1600, 1400)
        assert p + expected_score(1400, 1600) == pytest.approx(1.0)

    def test_large_gap(self):
        p = expected_score(1800, 1200)
        assert p > 0.95


class TestMethodMultiplier:
    def test_ko(self):
        assert get_method_multiplier("KO") == 1.3

    def test_tko(self):
        assert get_method_multiplier("TKO (Punches)") == 1.25

    def test_submission(self):
        assert get_method_multiplier("Submission (Rear Naked Choke)") == 1.2

    def test_decision(self):
        assert get_method_multiplier("Decision - Unanimous") == 1.0

    def test_split_decision(self):
        assert get_method_multiplier("Split Decision") == 0.9

    def test_unknown(self):
        assert get_method_multiplier("") == 1.0


class TestKFactor:
    def test_base_k(self):
        k = compute_k_factor(fighter_fight_count=10)
        assert k == K_BASE

    def test_early_career_bonus(self):
        k = compute_k_factor(fighter_fight_count=2)
        assert k > K_BASE

    def test_finish_bonus(self):
        k = compute_k_factor(fighter_fight_count=10, method="KO")
        assert k > K_BASE

    def test_title_bonus(self):
        k = compute_k_factor(fighter_fight_count=10, is_title_fight=True)
        assert k > K_BASE

    def test_combined_bonuses(self):
        k = compute_k_factor(fighter_fight_count=2, method="KO", is_title_fight=True)
        assert k > compute_k_factor(fighter_fight_count=10)


class TestUpdateElo:
    def test_winner_gains_loser_loses(self):
        new_w, new_l = update_elo(1500, 1500)
        assert new_w > 1500
        assert new_l < 1500

    def test_upset_bigger_swing(self):
        """Underdog winning produces a bigger swing than favorite winning."""
        # Upset: lower rated beats higher rated
        new_w_upset, new_l_upset = update_elo(1400, 1600)
        # Expected: higher rated beats lower rated
        new_w_expected, new_l_expected = update_elo(1600, 1400)

        upset_swing = new_w_upset - 1400
        expected_swing = new_w_expected - 1600
        assert upset_swing > expected_swing

    def test_finish_bigger_update(self):
        new_w_dec, _ = update_elo(1500, 1500, method="Decision")
        new_w_ko, _ = update_elo(1500, 1500, method="KO")
        assert new_w_ko > new_w_dec

    def test_split_decision_smaller(self):
        new_w_unanimous, _ = update_elo(1500, 1500, method="Decision - Unanimous")
        new_w_split, _ = update_elo(1500, 1500, method="Split Decision")
        assert new_w_unanimous > new_w_split


class TestInactivityDecay:
    def test_no_decay_within_year(self):
        result = apply_inactivity_decay(1600, "2026-01-01", date(2026, 3, 10))
        assert result == 1600

    def test_decay_after_two_years(self):
        result = apply_inactivity_decay(1600, "2024-01-01", date(2026, 3, 10))
        assert result < 1600

    def test_no_decay_without_date(self):
        result = apply_inactivity_decay(1600, None)
        assert result == 1600

    def test_floor_applied(self):
        result = apply_inactivity_decay(1350, "2020-01-01", date(2026, 3, 10))
        assert result >= DEFAULT_ELO - 200


class TestELORatingSystem:
    def test_default_rating(self):
        system = ELORatingSystem()
        assert system.get_rating("unknown") == DEFAULT_ELO

    def test_process_fight(self):
        system = ELORatingSystem()
        new_w, new_l = system.process_fight("fighter_a", "fighter_b", method="KO", fight_date="2026-01-01")
        assert new_w > DEFAULT_ELO
        assert new_l < DEFAULT_ELO
        assert system.get_fight_count("fighter_a") == 1
        assert system.get_fight_count("fighter_b") == 1

    def test_process_fights_batch(self):
        system = ELORatingSystem()
        fights = [
            {"winner_id": "a", "loser_id": "b", "date": "2025-01-01", "method": "KO"},
            {"winner_id": "a", "loser_id": "c", "date": "2025-06-01", "method": "Decision"},
            {"winner_id": "b", "loser_id": "c", "date": "2025-09-01", "method": "Submission"},
        ]
        system.process_fights_batch(fights)
        assert system.get_rating("a") > DEFAULT_ELO
        assert system.get_fight_count("a") == 2
        assert system.get_fight_count("b") == 2
        assert system.get_fight_count("c") == 2

    def test_rankings(self):
        system = ELORatingSystem()
        system.process_fight("a", "b", fight_date="2025-01-01")
        system.process_fight("a", "c", fight_date="2025-06-01")
        rankings = system.get_rankings(top_n=3, fighter_names={"a": "Alex", "b": "Bob", "c": "Carl"})
        assert rankings[0]["name"] == "Alex"
        assert rankings[0]["rank"] == 1

    def test_matchup_prediction(self):
        system = ELORatingSystem()
        system.process_fight("a", "b", fight_date="2025-01-01")
        system.process_fight("a", "c", fight_date="2025-06-01")

        pred = system.get_matchup_prediction("a", "b")
        assert pred["fighter_a_win_prob"] > 0.5
        assert pred["fighter_b_win_prob"] < 0.5
        assert pred["fighter_a_win_prob"] + pred["fighter_b_win_prob"] == pytest.approx(1.0)

    def test_serialize_deserialize(self):
        system = ELORatingSystem()
        system.process_fight("a", "b", fight_date="2025-01-01")

        data = system.to_dict()
        restored = ELORatingSystem.from_dict(data)
        assert restored.get_rating("a") == system.get_rating("a")
        assert restored.get_rating("b") == system.get_rating("b")

    def test_rating_history_recorded(self):
        system = ELORatingSystem()
        system.process_fight("a", "b", fight_date="2025-01-01", event_name="UFC 300")
        history = system.rating_history.get("a", [])
        assert len(history) == 1
        assert history[0]["result"] == "W"
        assert history[0]["event"] == "UFC 300"

    def test_trend_arrows(self):
        system = ELORatingSystem()
        system.process_fight("a", "b", fight_date="2025-01-01")
        system.process_fight("a", "c", fight_date="2025-06-01")
        trend = system._get_trend("a")
        assert trend in ("↑", "↑↑")

    def test_inactivity_decay_all(self):
        system = ELORatingSystem()
        system.process_fight("a", "b", fight_date="2023-01-01")
        decayed = system.apply_inactivity_decay_all(current_date=date(2026, 3, 10))
        assert decayed >= 1  # At least one fighter should have decayed


class TestRatingDiffToConfidence:
    def test_toss_up(self):
        assert _rating_diff_to_confidence(10) == "toss_up"

    def test_slight(self):
        assert _rating_diff_to_confidence(30) == "slight"

    def test_moderate(self):
        assert _rating_diff_to_confidence(60) == "moderate"

    def test_high(self):
        assert _rating_diff_to_confidence(150) == "high"

    def test_very_high(self):
        assert _rating_diff_to_confidence(250) == "very_high"


class TestEloToAmericanOdds:
    def test_favorite(self):
        odds = elo_probability_to_american_odds(0.7)
        assert odds.startswith("-")

    def test_underdog(self):
        odds = elo_probability_to_american_odds(0.3)
        assert odds.startswith("+")

    def test_even(self):
        odds = elo_probability_to_american_odds(0.5)
        assert odds.startswith("-")

    def test_edge_cases(self):
        assert elo_probability_to_american_odds(0.0) == "N/A"
        assert elo_probability_to_american_odds(1.0) == "N/A"
