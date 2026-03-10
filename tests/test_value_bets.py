# tests/test_value_bets.py
"""Tests for the value bet identification module."""

import pytest
from data.value_bets import (
    american_to_implied,
    decimal_to_implied,
    implied_to_decimal,
    implied_to_american,
    remove_vig,
    calculate_edge,
    kelly_fraction,
    expected_value,
    star_rating,
    confidence_label,
    identify_value_bets,
    format_value_bet_report,
)


# ── Odds conversion ──────────────────────────────────────

class TestAmericanToImplied:
    def test_favorite(self):
        # -200 => 200/300 = 0.6667
        result = american_to_implied("-200")
        assert abs(result - 0.6667) < 0.001

    def test_underdog(self):
        # +200 => 100/300 = 0.3333
        result = american_to_implied("+200")
        assert abs(result - 0.3333) < 0.001

    def test_even(self):
        # -100 => 100/200 = 0.5
        result = american_to_implied("-100")
        assert abs(result - 0.5) < 0.001

    def test_plus_100(self):
        result = american_to_implied("+100")
        assert abs(result - 0.5) < 0.001

    def test_invalid(self):
        assert american_to_implied("abc") is None
        assert american_to_implied("") is None

    def test_heavy_favorite(self):
        # -500 => 500/600 = 0.8333
        result = american_to_implied("-500")
        assert abs(result - 0.8333) < 0.001


class TestDecimalToImplied:
    def test_even(self):
        result = decimal_to_implied(2.0)
        assert abs(result - 0.5) < 0.001

    def test_favorite(self):
        result = decimal_to_implied(1.5)
        assert abs(result - 0.6667) < 0.001

    def test_underdog(self):
        result = decimal_to_implied(3.0)
        assert abs(result - 0.3333) < 0.001

    def test_invalid(self):
        assert decimal_to_implied(1.0) is None
        assert decimal_to_implied(0.5) is None


class TestImpliedToDecimal:
    def test_fifty_fifty(self):
        result = implied_to_decimal(0.5)
        assert abs(result - 2.0) < 0.001

    def test_favorite(self):
        result = implied_to_decimal(0.75)
        assert abs(result - 1.3333) < 0.001

    def test_invalid(self):
        assert implied_to_decimal(0) is None
        assert implied_to_decimal(1) is None


class TestImpliedToAmerican:
    def test_favorite(self):
        result = implied_to_american(0.6667)
        assert result.startswith("-")

    def test_underdog(self):
        result = implied_to_american(0.3333)
        assert result.startswith("+")

    def test_invalid(self):
        assert implied_to_american(0) is None
        assert implied_to_american(1) is None


# ── Vig removal ──────────────────────────────────────────

class TestRemoveVig:
    def test_standard_vig(self):
        # Typical 10% vig: 0.55 + 0.55 = 1.10
        fair_a, fair_b = remove_vig(0.55, 0.55)
        assert abs(fair_a - 0.5) < 0.001
        assert abs(fair_b - 0.5) < 0.001

    def test_asymmetric(self):
        fair_a, fair_b = remove_vig(0.70, 0.40)
        assert abs(fair_a + fair_b - 1.0) < 0.001

    def test_zero_total(self):
        a, b = remove_vig(0, 0)
        assert a == 0.5
        assert b == 0.5


# ── Edge calculation ─────────────────────────────────────

class TestCalculateEdge:
    def test_positive_edge(self):
        edge = calculate_edge(0.65, 0.55)
        assert abs(edge - 0.10) < 0.001

    def test_negative_edge(self):
        edge = calculate_edge(0.50, 0.60)
        assert edge < 0

    def test_zero_edge(self):
        edge = calculate_edge(0.55, 0.55)
        assert edge == 0.0


# ── Kelly criterion ──────────────────────────────────────

class TestKellyFraction:
    def test_positive_ev(self):
        # Model says 60%, odds are 2.0 (implied 50%)
        kelly = kelly_fraction(0.60, 2.0, fraction=1.0)
        # Full Kelly: (1 * 0.60 - 0.40) / 1 = 0.20
        assert abs(kelly - 0.20) < 0.001

    def test_quarter_kelly(self):
        kelly = kelly_fraction(0.60, 2.0, fraction=0.25)
        assert abs(kelly - 0.05) < 0.001

    def test_negative_ev(self):
        # Model says 40%, odds are 2.0 (implied 50%)
        kelly = kelly_fraction(0.40, 2.0)
        assert kelly == 0.0

    def test_edge_cases(self):
        assert kelly_fraction(0, 2.0) == 0.0
        assert kelly_fraction(1, 2.0) == 0.0
        assert kelly_fraction(0.5, 1.0) == 0.0


# ── Expected value ───────────────────────────────────────

class TestExpectedValue:
    def test_positive_ev(self):
        ev = expected_value(0.60, 2.0, stake=100)
        # 0.60 * 200 - 100 = 20
        assert abs(ev - 20.0) < 0.01

    def test_negative_ev(self):
        ev = expected_value(0.40, 2.0, stake=100)
        # 0.40 * 200 - 100 = -20
        assert abs(ev - (-20.0)) < 0.01


# ── Star rating ──────────────────────────────────────────

class TestStarRating:
    def test_no_value(self):
        assert star_rating(-0.05) == 0
        assert star_rating(0) == 0

    def test_slim(self):
        assert star_rating(0.02) == 1

    def test_moderate(self):
        assert star_rating(0.04) == 2

    def test_good(self):
        assert star_rating(0.08) == 3

    def test_strong(self):
        assert star_rating(0.12) == 4

    def test_exceptional(self):
        assert star_rating(0.20) == 5


class TestConfidenceLabel:
    def test_labels(self):
        assert confidence_label(0) == "No Value"
        assert confidence_label(0.02) == "Slim Edge"
        assert confidence_label(0.08) == "Good Value"
        assert confidence_label(0.20) == "Exceptional Value"


# ── Value bet identification ─────────────────────────────

class TestIdentifyValueBets:
    def test_finds_value_bet(self):
        predictions = [
            {
                "fighter_a": "Jon Jones",
                "fighter_b": "Tom Aspinall",
                "predicted_winner": "Jon Jones",
                "win_probability": 0.70,
            }
        ]
        odds_data = {
            "bouts": {
                "jon jones vs tom aspinall": {
                    "event": "UFC 320",
                    "source": "draftkings",
                    "fighters": [
                        {"name": "Jon Jones", "odds_american": "-150", "odds_decimal": 1.667, "implied_probability": 0.60},
                        {"name": "Tom Aspinall", "odds_american": "+130", "odds_decimal": 2.30, "implied_probability": 0.4348},
                    ],
                }
            }
        }
        bets = identify_value_bets(predictions, odds_data, min_edge=0.03)
        assert len(bets) == 1
        assert bets[0]["fighter"] == "Jon Jones"
        assert bets[0]["edge"] > 0.03
        assert bets[0]["star_rating"] >= 1

    def test_no_value_below_threshold(self):
        predictions = [
            {
                "fighter_a": "Jon Jones",
                "fighter_b": "Tom Aspinall",
                "predicted_winner": "Jon Jones",
                "win_probability": 0.61,  # barely above market
            }
        ]
        odds_data = {
            "bouts": {
                "jon jones vs tom aspinall": {
                    "event": "UFC 320",
                    "source": "draftkings",
                    "fighters": [
                        {"name": "Jon Jones", "odds_american": "-150", "odds_decimal": 1.667, "implied_probability": 0.60},
                        {"name": "Tom Aspinall", "odds_american": "+130", "odds_decimal": 2.30, "implied_probability": 0.4348},
                    ],
                }
            }
        }
        bets = identify_value_bets(predictions, odds_data, min_edge=0.03)
        assert len(bets) == 0

    def test_empty_odds(self):
        predictions = [
            {"fighter_a": "A", "fighter_b": "B", "predicted_winner": "A", "win_probability": 0.7}
        ]
        bets = identify_value_bets(predictions, {"bouts": {}})
        assert len(bets) == 0

    def test_empty_predictions(self):
        bets = identify_value_bets([], {"bouts": {"x": {}}})
        assert len(bets) == 0

    def test_sorting_by_edge(self):
        predictions = [
            {"fighter_a": "A", "fighter_b": "B", "predicted_winner": "A", "win_probability": 0.80},
            {"fighter_a": "C", "fighter_b": "D", "predicted_winner": "C", "win_probability": 0.70},
        ]
        odds_data = {
            "bouts": {
                "a vs b": {
                    "source": "dk",
                    "fighters": [
                        {"name": "A", "odds_decimal": 2.0, "implied_probability": 0.50},
                        {"name": "B", "odds_decimal": 2.0, "implied_probability": 0.50},
                    ],
                },
                "c vs d": {
                    "source": "dk",
                    "fighters": [
                        {"name": "C", "odds_decimal": 1.667, "implied_probability": 0.60},
                        {"name": "D", "odds_decimal": 2.30, "implied_probability": 0.4348},
                    ],
                },
            }
        }
        bets = identify_value_bets(predictions, odds_data, min_edge=0.03)
        assert len(bets) == 2
        # A has 30% edge, C has 10% edge — A should be first
        assert bets[0]["fighter"] == "A"


# ── Report formatting ────────────────────────────────────

class TestFormatReport:
    def test_empty_report(self):
        report = format_value_bet_report([])
        assert "No value bets" in report

    def test_report_has_content(self):
        bets = [
            {
                "fighter": "Jon Jones",
                "opponent": "Tom Aspinall",
                "model_probability": 0.70,
                "market_implied": 0.60,
                "edge": 0.10,
                "edge_pct": "10.0%",
                "odds_american": "-150",
                "odds_decimal": 1.667,
                "expected_value_per_100": 16.69,
                "kelly_fraction": 0.06,
                "suggested_stake": 60.0,
                "star_rating": 3,
                "confidence": "Good Value",
                "event": "UFC 320",
                "source": "draftkings",
            }
        ]
        report = format_value_bet_report(bets)
        assert "Jon Jones" in report
        assert "10.0%" in report
        assert "Good Value" in report
