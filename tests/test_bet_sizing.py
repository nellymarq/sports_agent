# tests/test_bet_sizing.py
# Tests for bet sizing and recommendation system.

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.bet_sizing import (
    kelly_criterion,
    fractional_kelly,
    compute_edge,
    recommend_bet_size,
    format_bet_recommendation,
)


class TestKellyCriterion:
    def test_even_money_60_percent(self):
        """60% win probability at even money should give positive Kelly."""
        k = kelly_criterion(0.6, 2.0)
        assert k > 0
        assert k == pytest.approx(0.2)

    def test_50_percent_even_money(self):
        """50% at even money = zero edge = no bet."""
        k = kelly_criterion(0.5, 2.0)
        assert k == pytest.approx(0.0)

    def test_negative_edge(self):
        """Below break-even probability should return 0."""
        k = kelly_criterion(0.3, 2.0)
        assert k == 0.0

    def test_high_odds_underdog(self):
        k = kelly_criterion(0.15, 8.0)
        assert k > 0  # 15% chance at 8.0 odds is profitable

    def test_edge_cases(self):
        assert kelly_criterion(0.0, 2.0) == 0.0
        assert kelly_criterion(1.0, 2.0) == 0.0
        assert kelly_criterion(0.5, 1.0) == 0.0
        assert kelly_criterion(0.5, 0.5) == 0.0


class TestFractionalKelly:
    def test_quarter_kelly(self):
        full = kelly_criterion(0.6, 2.0)
        quarter = fractional_kelly(0.6, 2.0, 0.25)
        assert quarter == pytest.approx(full * 0.25)

    def test_fraction_reduces_bet(self):
        full = kelly_criterion(0.65, 2.5)
        frac = fractional_kelly(0.65, 2.5, 0.5)
        assert frac < full


class TestComputeEdge:
    def test_positive_edge(self):
        result = compute_edge(0.65, 0.55)
        assert result["edge_pct"] == pytest.approx(10.0)
        assert result["has_value"] is True

    def test_no_edge(self):
        result = compute_edge(0.50, 0.55)
        assert result["edge_pct"] < 0
        assert result["has_value"] is False

    def test_small_edge_below_threshold(self):
        result = compute_edge(0.52, 0.50)
        assert result["edge_pct"] == pytest.approx(2.0)
        assert result["has_value"] is False  # Below 3% threshold

    def test_relative_edge(self):
        result = compute_edge(0.70, 0.50)
        assert result["relative_edge_pct"] > 0


class TestRecommendBetSize:
    def test_strong_bet(self):
        rec = recommend_bet_size(
            model_prob=0.70,
            decimal_odds=2.0,
            confidence_tier="high",
            bankroll=1000,
        )
        assert rec["action"] == "STRONG BET"
        assert rec["sizing"]["suggested_stake"] > 0
        assert rec["potential_payout"] > 0
        assert rec["expected_value"] > 0

    def test_pass_no_edge(self):
        rec = recommend_bet_size(
            model_prob=0.45,
            decimal_odds=2.0,
            confidence_tier="moderate",
            bankroll=1000,
        )
        assert rec["action"] == "PASS"
        assert rec["sizing"]["suggested_stake"] == 0

    def test_pass_toss_up(self):
        rec = recommend_bet_size(
            model_prob=0.60,
            decimal_odds=2.0,
            confidence_tier="toss_up",
            bankroll=1000,
        )
        assert rec["action"] == "PASS"

    def test_bet_moderate_edge(self):
        rec = recommend_bet_size(
            model_prob=0.60,
            decimal_odds=2.0,
            confidence_tier="moderate",
            bankroll=1000,
        )
        assert rec["action"] in ("BET", "STRONG BET")

    def test_stake_capped_at_max(self):
        rec = recommend_bet_size(
            model_prob=0.90,
            decimal_odds=3.0,
            confidence_tier="high",
            bankroll=10000,
        )
        max_stake = rec["sizing"]["max_stake"]
        assert rec["sizing"]["suggested_stake"] <= max_stake

    def test_contains_kelly_info(self):
        rec = recommend_bet_size(
            model_prob=0.65,
            decimal_odds=2.5,
            confidence_tier="high",
        )
        assert "kelly" in rec
        assert "full_kelly_fraction" in rec["kelly"]
        assert "fractional_kelly" in rec["kelly"]

    def test_unknown_tier_defaults(self):
        rec = recommend_bet_size(
            model_prob=0.65,
            decimal_odds=2.0,
            confidence_tier="unknown_tier",
        )
        assert rec["confidence_tier"] == "moderate"


class TestFormatBetRecommendation:
    def test_pass_format(self):
        rec = recommend_bet_size(0.45, 2.0, "moderate")
        text = format_bet_recommendation(rec, "Fighter A")
        assert "PASS" in text

    def test_bet_format(self):
        rec = recommend_bet_size(0.70, 2.0, "high", bankroll=1000)
        text = format_bet_recommendation(rec, "Jon Jones")
        assert "Jon Jones" in text
        assert "Edge" in text
        assert "units" in text

    def test_format_without_fighter(self):
        rec = recommend_bet_size(0.70, 2.0, "high")
        text = format_bet_recommendation(rec)
        assert "RECOMMENDATION" in text
