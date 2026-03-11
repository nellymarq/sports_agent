# tests/test_fighter_profile.py
"""Tests for the fighter profile aggregator module."""

import pytest
from data.fighter_profile import (
    compute_streak,
    compute_method_distribution,
    compute_round_distribution,
    compute_activity,
    build_fighter_profile,
    format_tale_of_the_tape,
)


class TestComputeStreak:
    def test_win_streak(self):
        fights = [
            {"result": "Win"},
            {"result": "Win"},
            {"result": "Win"},
            {"result": "Loss"},
        ]
        result = compute_streak(fights)
        assert result["current_streak"] == 3
        assert result["streak_type"] == "W"
        assert result["form_last_5"] == "WWWL"

    def test_loss_streak(self):
        fights = [
            {"result": "Loss"},
            {"result": "Loss"},
            {"result": "Win"},
        ]
        result = compute_streak(fights)
        assert result["current_streak"] == 2
        assert result["streak_type"] == "L"

    def test_empty(self):
        result = compute_streak([])
        assert result["current_streak"] == 0
        assert result["streak_type"] == "none"

    def test_single_fight(self):
        result = compute_streak([{"result": "Win"}])
        assert result["current_streak"] == 1
        assert result["form_last_5"] == "W"

    def test_draw_breaks_streak(self):
        fights = [
            {"result": "Draw"},
            {"result": "Win"},
        ]
        result = compute_streak(fights)
        assert result["current_streak"] == 0

    def test_form_last_5_capped(self):
        fights = [{"result": "Win"} for _ in range(8)]
        result = compute_streak(fights)
        assert len(result["form_last_5"]) == 5


class TestComputeMethodDistribution:
    def test_mixed_methods(self):
        fights = [
            {"result": "Win", "method": "KO/TKO"},
            {"result": "Win", "method": "Submission"},
            {"result": "Win", "method": "Decision - Unanimous"},
            {"result": "Loss", "method": "KO"},
        ]
        result = compute_method_distribution(fights)
        assert result["wins"]["ko_tko"] == 1
        assert result["wins"]["submission"] == 1
        assert result["wins"]["decision"] == 1
        assert result["total_wins"] == 3
        assert result["total_losses"] == 1
        assert result["finish_rate"] > 60

    def test_ko_rate(self):
        fights = [
            {"result": "Win", "method": "KO"},
            {"result": "Win", "method": "TKO"},
            {"result": "Win", "method": "Decision"},
            {"result": "Win", "method": "Decision"},
        ]
        result = compute_method_distribution(fights)
        assert result["ko_rate"] == 50.0

    def test_empty(self):
        result = compute_method_distribution([])
        assert result["total_wins"] == 0
        assert result["finish_rate"] == 0

    def test_been_finished_rate(self):
        fights = [
            {"result": "Loss", "method": "KO"},
            {"result": "Loss", "method": "Submission"},
            {"result": "Loss", "method": "Decision"},
        ]
        result = compute_method_distribution(fights)
        assert result["been_finished_rate"] == pytest.approx(66.7, abs=0.1)


class TestComputeRoundDistribution:
    def test_round_counts(self):
        fights = [
            {"round": 1},
            {"round": 1},
            {"round": 3},
            {"round": 2},
        ]
        result = compute_round_distribution(fights)
        assert result["r1"] == 2
        assert result["r2"] == 1
        assert result["r3"] == 1

    def test_empty(self):
        result = compute_round_distribution([])
        assert result == {}

    def test_no_round_data(self):
        result = compute_round_distribution([{"method": "KO"}])
        assert result == {}


class TestComputeActivity:
    def test_with_dates(self):
        fights = [
            {"date": "2025-01-15"},
            {"date": "2024-06-20"},
            {"date": "2024-01-10"},
        ]
        result = compute_activity(fights)
        assert result["total_ufc_fights"] == 3
        assert result["fights_per_year"] > 0
        assert result["last_fight_days_ago"] is not None

    def test_empty(self):
        result = compute_activity([])
        assert result["fights_per_year"] == 0
        assert result["total_ufc_fights"] == 0


class TestBuildFighterProfile:
    def test_from_ufc_stats(self):
        stats = {
            "name": "Alex Pereira",
            "record": "12-2-0",
            "height": "6'4\"",
            "reach": "79\"",
            "slpm": "5.47",
            "str_acc": "56%",
            "detail_stats": {
                "recent_fights": [
                    {"result": "Win", "method": "KO", "round": 1, "opponent": "Prochazka"},
                    {"result": "Win", "method": "TKO", "round": 2, "opponent": "Prochazka"},
                    {"result": "Win", "method": "KO", "round": 1, "opponent": "Adesanya"},
                ],
            },
        }
        profile = build_fighter_profile("Alex Pereira", ufc_stats=stats)
        assert profile["name"] == "Alex Pereira"
        assert profile["record"] == "12-2-0"
        assert "streak" in profile
        assert profile["streak"]["streak_type"] == "W"
        assert "method_distribution" in profile
        assert profile["method_distribution"]["ko_rate"] > 50

    def test_minimal_profile(self):
        profile = build_fighter_profile("Unknown Fighter")
        assert profile["name"] == "Unknown Fighter"

    def test_with_fight_history(self):
        history = [
            {"result": "Win", "method": "KO", "round": 1, "date": "2025-01-01"},
            {"result": "Win", "method": "Decision", "round": 3, "date": "2024-06-01"},
        ]
        profile = build_fighter_profile("Test Fighter", fight_history=history)
        assert profile["streak"]["current_streak"] == 2


class TestTaleOfTheTape:
    def test_format(self):
        profile_a = {
            "name": "Alex Pereira",
            "record": "12-2-0",
            "height": "6'4\"",
            "reach": "79\"",
            "slpm": "5.47",
            "streak": {"current_streak": 3, "streak_type": "W", "form_last_5": "WWWWW"},
            "method_distribution": {"finish_rate": 83.3, "ko_rate": 66.7, "sub_rate": 0},
        }
        profile_b = {
            "name": "Magomed Ankalaev",
            "record": "20-1-1",
            "height": "6'3\"",
            "reach": "75\"",
            "slpm": "3.89",
            "streak": {"current_streak": 12, "streak_type": "W", "form_last_5": "WWWWW"},
            "method_distribution": {"finish_rate": 55.0, "ko_rate": 40.0, "sub_rate": 5.0},
        }
        tape = format_tale_of_the_tape(profile_a, profile_b)
        assert "TALE OF THE TAPE" in tape
        assert "Alex Pereira" in tape
        assert "Magomed Ankalaev" in tape
        assert "12-2-0" in tape
        assert "Finish Rate" in tape
