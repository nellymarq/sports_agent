"""Tests for data/cage_control.py — clinch dynamics and cage control."""
import pytest
from data.cage_control import (
    analyze_clinch_profile,
    analyze_clinch_matchup,
    compute_octagon_control_score,
    predict_fight_location,
)


class TestClinchProfile:
    def test_dirty_boxer_classification(self):
        stats = {"slpm": "4.5", "sapm": "5.0", "str_def": "45", "td_avg": "1.0", "td_acc": "40", "sub_avg": "0.3"}
        result = analyze_clinch_profile(stats)
        assert result["clinch_style"] == "dirty_boxer"
        assert result["clinch_tendency"] > 0  # Has meaningful clinch tendency

    def test_cage_wrestler_classification(self):
        stats = {"slpm": "3.0", "sapm": "3.0", "str_def": "55", "td_avg": "4.0", "td_acc": "50", "sub_avg": "0.5"}
        result = analyze_clinch_profile(stats)
        assert result["clinch_style"] == "cage_wrestler"

    def test_range_fighter_classification(self):
        stats = {"slpm": "5.0", "sapm": "2.5", "str_def": "65", "td_avg": "0.5", "td_acc": "30", "sub_avg": "0.2"}
        result = analyze_clinch_profile(stats)
        assert result["clinch_style"] == "range_fighter"
        assert result["prefers_clinch"] is False

    def test_empty_stats_returns_defaults(self):
        result = analyze_clinch_profile({})
        assert "clinch_tendency" in result
        assert 0 <= result["clinch_tendency"] <= 1

    def test_clinch_tendency_bounded(self):
        stats = {"slpm": "10", "sapm": "10", "str_def": "20", "td_avg": "5", "td_acc": "60", "sub_avg": "3"}
        result = analyze_clinch_profile(stats)
        assert result["clinch_tendency"] <= 1.0


class TestClinchMatchup:
    def test_basic_matchup(self):
        stats_a = {"name": "Fighter A", "slpm": "5", "sapm": "5", "str_def": "50", "td_avg": "1", "td_acc": "40", "td_def": "65", "sub_avg": "0.3"}
        stats_b = {"name": "Fighter B", "slpm": "3", "sapm": "2.5", "str_def": "60", "td_avg": "3", "td_acc": "55", "td_def": "70", "sub_avg": "1.0"}
        result = analyze_clinch_matchup(stats_a, stats_b)
        assert "clinch_initiator" in result
        assert "clinch_dominant" in result
        assert result["clinch_time_estimate_pct"] > 0

    def test_empty_stats(self):
        result = analyze_clinch_matchup({}, {})
        assert "clinch_finish_probability" in result


class TestOctagonControl:
    def test_pressure_fighter(self):
        stats = {"slpm": "6.0", "sapm": "5.0", "str_acc": "40", "str_def": "48", "td_avg": "2.0"}
        result = compute_octagon_control_score(stats)
        assert result["control_style"] == "pressure"
        assert result["pressure_rating"] > result["footwork_rating"]

    def test_counter_fighter(self):
        stats = {"slpm": "2.5", "sapm": "2.0", "str_acc": "55", "str_def": "65", "td_avg": "0.5"}
        result = compute_octagon_control_score(stats)
        assert result["control_style"] == "counter"

    def test_score_bounded(self):
        result = compute_octagon_control_score({})
        assert 0 <= result["control_score"] <= 100


class TestFightLocation:
    def test_striker_matchup(self):
        stats_a = {"td_avg": "0.5", "td_def": "85", "sub_avg": "0.1", "sapm": "3"}
        stats_b = {"td_avg": "0.3", "td_def": "80", "sub_avg": "0.2", "sapm": "3"}
        result = predict_fight_location(stats_a, stats_b)
        assert result["primary_location"] == "range"
        assert result["location_distribution"]["range"] > 40

    def test_grappler_matchup(self):
        stats_a = {"td_avg": "5.0", "td_def": "50", "sub_avg": "2.0", "sapm": "4"}
        stats_b = {"td_avg": "4.0", "td_def": "45", "sub_avg": "1.5", "sapm": "4"}
        result = predict_fight_location(stats_a, stats_b)
        assert result["location_distribution"]["ground"] > 20

    def test_probabilities_sum_to_100(self):
        result = predict_fight_location({}, {})
        dist = result["location_distribution"]
        total = dist["range"] + dist["clinch"] + dist["ground"]
        assert abs(total - 100) < 1
