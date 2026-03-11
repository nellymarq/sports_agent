# tests/test_style_classifier.py
"""Tests for the fighter style classifier module."""

import pytest
from data.style_classifier import classify_style, classify_matchup, ARCHETYPES


class TestClassifyStyle:
    def test_pressure_striker(self):
        stats = {"slpm": "6.5", "str_acc": "45%", "sapm": "5.0", "str_def": "50%",
                 "td_avg": "0.5", "td_acc": "30%", "td_def": "60%", "sub_avg": "0.0"}
        result = classify_style(stats)
        assert result["primary_style"] in ("pressure_striker", "knockout_artist")
        assert "style" in result["relevant_specialists"]

    def test_wrestler(self):
        stats = {"slpm": "2.0", "str_acc": "40%", "sapm": "2.0", "str_def": "55%",
                 "td_avg": "4.5", "td_acc": "55%", "td_def": "80%", "sub_avg": "0.3"}
        result = classify_style(stats)
        assert result["primary_style"] == "wrestler"
        assert "grappling" in result["relevant_specialists"]

    def test_grappler(self):
        stats = {"slpm": "2.5", "str_acc": "42%", "sapm": "2.0", "str_def": "55%",
                 "td_avg": "3.0", "td_acc": "45%", "td_def": "70%", "sub_avg": "3.0"}
        result = classify_style(stats)
        assert result["primary_style"] == "grappler"
        assert "scramble" in result["relevant_specialists"]

    def test_counter_striker(self):
        stats = {"slpm": "2.8", "str_acc": "58%", "sapm": "2.0", "str_def": "68%",
                 "td_avg": "0.3", "td_acc": "20%", "td_def": "85%", "sub_avg": "0.0"}
        result = classify_style(stats)
        assert result["primary_style"] == "counter_striker"
        assert "fight_iq" in result["relevant_specialists"]

    def test_unknown_with_no_stats(self):
        result = classify_style({})
        assert result["primary_style"] == "unknown"
        assert "style" in result["relevant_specialists"]

    def test_scores_are_ranked(self):
        stats = {"slpm": "4.0", "str_acc": "50%", "sapm": "3.0", "str_def": "55%",
                 "td_avg": "1.5", "td_acc": "40%", "td_def": "65%", "sub_avg": "0.5"}
        result = classify_style(stats)
        scores = result["style_scores"]
        values = list(scores.values())
        assert values == sorted(values, reverse=True)

    def test_secondary_style(self):
        stats = {"slpm": "5.0", "str_acc": "48%", "sapm": "4.0", "str_def": "52%",
                 "td_avg": "2.0", "td_acc": "45%", "td_def": "60%", "sub_avg": "0.5"}
        result = classify_style(stats)
        assert result["secondary_style"] is not None

    def test_primary_description(self):
        stats = {"slpm": "6.0", "str_acc": "45%", "sapm": "5.0", "str_def": "48%",
                 "td_avg": "0.3", "td_acc": "20%", "td_def": "60%", "sub_avg": "0.0"}
        result = classify_style(stats)
        assert result.get("primary_description", "")

    def test_ko_artist_with_win_methods(self):
        stats = {
            "slpm": "5.5", "str_acc": "52%", "sapm": "3.0", "str_def": "55%",
            "td_avg": "0.5", "td_acc": "30%", "td_def": "70%", "sub_avg": "0.0",
            "detail_stats": {"win_methods": {"ko_tko": 8, "submission": 1, "decision": 2}},
        }
        result = classify_style(stats)
        assert result["style_scores"].get("knockout_artist", 0) > 50


class TestClassifyMatchup:
    def test_striker_vs_grappler(self):
        striker = {"slpm": "6.0", "str_acc": "50%", "sapm": "4.0", "str_def": "52%",
                   "td_avg": "0.3", "td_acc": "20%", "td_def": "60%", "sub_avg": "0.0"}
        grappler = {"slpm": "2.0", "str_acc": "40%", "sapm": "2.0", "str_def": "55%",
                    "td_avg": "4.5", "td_acc": "55%", "td_def": "80%", "sub_avg": "0.3"}
        result = classify_matchup(striker, grappler)
        assert result["matchup_type"] == "striker_vs_grappler"
        assert "scramble" in result["recommended_specialists"]

    def test_grappler_vs_striker(self):
        grappler = {"slpm": "2.0", "str_acc": "40%", "sapm": "2.0", "str_def": "55%",
                    "td_avg": "4.5", "td_acc": "55%", "td_def": "80%", "sub_avg": "0.3"}
        striker = {"slpm": "6.0", "str_acc": "50%", "sapm": "4.0", "str_def": "52%",
                   "td_avg": "0.3", "td_acc": "20%", "td_def": "60%", "sub_avg": "0.0"}
        result = classify_matchup(grappler, striker)
        assert result["matchup_type"] == "grappler_vs_striker"

    def test_striker_vs_striker(self):
        striker_a = {"slpm": "5.0", "str_acc": "48%", "sapm": "4.0", "str_def": "52%",
                     "td_avg": "0.5", "td_acc": "25%", "td_def": "65%", "sub_avg": "0.0"}
        striker_b = {"slpm": "4.5", "str_acc": "55%", "sapm": "3.0", "str_def": "60%",
                     "td_avg": "0.3", "td_acc": "20%", "td_def": "70%", "sub_avg": "0.0"}
        result = classify_matchup(striker_a, striker_b)
        assert result["matchup_type"] == "striker_vs_striker"

    def test_has_both_fighter_styles(self):
        stats = {"slpm": "4.0", "str_acc": "50%", "sapm": "3.0", "str_def": "55%",
                 "td_avg": "1.5", "td_acc": "40%", "td_def": "65%", "sub_avg": "0.5"}
        result = classify_matchup(stats, stats)
        assert "fighter_a_style" in result
        assert "fighter_b_style" in result
        assert "matchup_description" in result

    def test_recommended_specialists_capped(self):
        stats = {"slpm": "4.0", "str_acc": "50%", "sapm": "3.0", "str_def": "55%",
                 "td_avg": "1.5", "td_acc": "40%", "td_def": "65%", "sub_avg": "0.5"}
        result = classify_matchup(stats, stats)
        assert len(result["recommended_specialists"]) <= 8


class TestArchetypes:
    def test_all_archetypes_have_specialists(self):
        for name, archetype in ARCHETYPES.items():
            assert len(archetype["relevant_specialists"]) >= 2
            assert "description" in archetype
