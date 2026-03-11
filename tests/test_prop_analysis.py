# tests/test_prop_analysis.py
# Tests for prop bet analysis module.

import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from data.prop_analysis import (
    analyze_method_props,
    analyze_round_props,
    generate_prop_card,
    UFC_METHOD_BASE_RATES,
    UFC_ROUND_BASE_RATES_3RD,
    UFC_ROUND_BASE_RATES_5RD,
)


class TestMethodPropsAnalysis:
    def test_empty_probs(self):
        result = analyze_method_props({})
        assert result["has_value"] is False
        assert result["props"] == []

    def test_basic_analysis(self):
        probs = {"ko_tko": 40, "submission": 10, "decision": 50}
        result = analyze_method_props(probs)
        assert len(result["props"]) == 3
        assert not result["has_value"]  # no market props to compare

    def test_probabilities_normalized(self):
        probs = {"ko_tko": 40, "submission": 10, "decision": 50}
        result = analyze_method_props(probs)
        total = sum(p["model_probability"] for p in result["props"])
        assert abs(total - 100.0) < 0.5

    def test_fair_odds_generated(self):
        probs = {"ko_tko": 60, "submission": 10, "decision": 30}
        result = analyze_method_props(probs)
        for prop in result["props"]:
            assert prop["fair_odds"] is not None

    def test_value_detection_with_market(self):
        probs = {"ko_tko": 60, "submission": 10, "decision": 30}
        market = {"ko_tko": "+120"}  # implied 45.5% but model says 60%
        result = analyze_method_props(probs, market_props=market)
        ko_prop = next(p for p in result["props"] if p["method"] == "ko_tko")
        assert ko_prop["has_value"] is True
        assert ko_prop["edge"] > 10  # 60% - 45% = ~15%

    def test_no_value_when_market_higher(self):
        probs = {"ko_tko": 20, "submission": 10, "decision": 70}
        market = {"ko_tko": "-200"}  # implied ~67% but model says 20%
        result = analyze_method_props(probs, market_props=market)
        ko_prop = next(p for p in result["props"] if p["method"] == "ko_tko")
        assert ko_prop.get("has_value", False) is False

    def test_model_vs_base_rate(self):
        probs = {"ko_tko": 60, "submission": 10, "decision": 30}
        result = analyze_method_props(probs)
        ko_prop = next(p for p in result["props"] if p["method"] == "ko_tko")
        # 60% model vs ~28% base rate = positive difference
        assert ko_prop["model_vs_base"] > 0

    def test_fighter_names_passed_through(self):
        result = analyze_method_props(
            {"ko_tko": 50, "decision": 50},
            fighter_a="Alex Pereira",
            fighter_b="Ankalaev",
        )
        assert result["fighter_a"] == "Alex Pereira"
        assert result["fighter_b"] == "Ankalaev"


class TestRoundPropsAnalysis:
    def test_empty_probs(self):
        result = analyze_round_props({})
        assert result["props"] == []
        assert result["over_under"] is None

    def test_three_round_analysis(self):
        probs = {"r1": 15, "r2": 12, "r3": 10, "decision": 63}
        result = analyze_round_props(probs, is_five_round=False)
        assert len(result["props"]) == 4
        assert result["over_under"] is not None
        assert result["over_under"]["line"] == 2.5

    def test_five_round_analysis(self):
        probs = {"r1": 10, "r2": 8, "r3": 7, "r4": 5, "r5": 5, "decision": 65}
        result = analyze_round_props(probs, is_five_round=True)
        assert result["is_five_round"] is True
        assert result["over_under"]["line"] == 4.5

    def test_over_under_lean(self):
        # Heavy decision fight
        probs = {"r1": 5, "r2": 5, "r3": 5, "decision": 85}
        result = analyze_round_props(probs, is_five_round=False)
        assert result["over_under"]["lean"] == "OVER"
        assert result["over_under"]["over_probability"] > 80

    def test_under_lean_for_finishers(self):
        # Heavy finish fight
        probs = {"r1": 30, "r2": 25, "r3": 15, "decision": 30}
        result = analyze_round_props(probs, is_five_round=False)
        assert result["over_under"]["lean"] == "UNDER"

    def test_fair_odds_on_rounds(self):
        probs = {"r1": 20, "r2": 15, "r3": 10, "decision": 55}
        result = analyze_round_props(probs)
        for prop in result["props"]:
            assert prop["fair_odds"] is not None

    def test_finish_probability(self):
        probs = {"r1": 20, "r2": 15, "r3": 10, "decision": 55}
        result = analyze_round_props(probs)
        assert result["over_under"]["finish_probability"] == 45.0
        assert result["over_under"]["decision_probability"] == 55.0


class TestGeneratePropCard:
    def test_full_card_generation(self):
        pred = {
            "fighter_a": "Fighter A",
            "fighter_b": "Fighter B",
            "predicted_winner": "Fighter A",
            "method_probabilities": {"ko_tko": 40, "submission": 10, "decision": 50},
            "round_probabilities": {"r1": 15, "r2": 10, "r3": 8, "decision": 67},
        }
        card = generate_prop_card(pred)
        assert "method_analysis" in card
        assert "round_analysis" in card
        assert "value_angles" in card
        assert "summary" in card

    def test_card_with_market_props(self):
        pred = {
            "fighter_a": "A",
            "fighter_b": "B",
            "predicted_winner": "A",
            "method_probabilities": {"ko_tko": 60, "submission": 10, "decision": 30},
            "round_probabilities": {},
        }
        market_method = {"ko_tko": "+150"}  # implied ~40%
        card = generate_prop_card(pred, market_method_props=market_method)
        assert card["method_analysis"]["has_value"] is True

    def test_card_five_round_detection(self):
        pred = {
            "fighter_a": "A",
            "fighter_b": "B",
            "predicted_winner": "A",
            "method_probabilities": {},
            "round_probabilities": {"r1": 10, "r2": 8, "r3": 7, "r4": 5, "r5": 5, "decision": 65},
        }
        card = generate_prop_card(pred)
        assert card["round_analysis"]["is_five_round"] is True

    def test_card_no_probs(self):
        pred = {
            "fighter_a": "A",
            "fighter_b": "B",
            "predicted_winner": "A",
        }
        card = generate_prop_card(pred)
        assert card["method_analysis"]["props"] == []


class TestBaseRates:
    def test_method_base_rates_sum_to_one(self):
        total = sum(UFC_METHOD_BASE_RATES.values())
        assert abs(total - 1.0) < 0.01

    def test_round_3rd_rates_sum_to_one(self):
        total = sum(UFC_ROUND_BASE_RATES_3RD.values())
        assert abs(total - 1.0) < 0.01

    def test_round_5rd_rates_sum_to_one(self):
        total = sum(UFC_ROUND_BASE_RATES_5RD.values())
        assert abs(total - 1.0) < 0.01
