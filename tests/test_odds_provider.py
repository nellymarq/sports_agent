# tests/test_odds_provider.py
"""Tests for the odds provider module."""

import pytest
from unittest.mock import patch, MagicMock
from data.providers.odds_provider import (
    _american_to_decimal,
    _decimal_to_implied,
    _normalize_fighter_key,
    _merge_odds_sources,
    _fetch_draftkings_odds,
    _fetch_polymarket_odds,
    fetch_all_ufc_odds,
    fetch_odds_for_event,
)
from data.exceptions import DataSourceError


class TestOddsConversions:
    def test_american_to_decimal_favorite(self):
        result = _american_to_decimal("-200")
        assert abs(result - 1.5) < 0.01

    def test_american_to_decimal_underdog(self):
        result = _american_to_decimal("+200")
        assert abs(result - 3.0) < 0.01

    def test_american_to_decimal_even(self):
        result = _american_to_decimal("+100")
        assert abs(result - 2.0) < 0.01

    def test_american_to_decimal_invalid(self):
        assert _american_to_decimal("abc") is None

    def test_decimal_to_implied(self):
        assert abs(_decimal_to_implied(2.0) - 0.5) < 0.001
        assert abs(_decimal_to_implied(1.5) - 0.6667) < 0.001

    def test_decimal_to_implied_zero(self):
        assert _decimal_to_implied(0) == 0.0


class TestNormalizeFighterKey:
    def test_basic(self):
        assert _normalize_fighter_key("Jon Jones") == "jon jones"

    def test_dots_apostrophes(self):
        assert _normalize_fighter_key("B.J. Penn") == "bj penn"
        assert _normalize_fighter_key("O'Malley") == "omalley"

    def test_whitespace(self):
        assert _normalize_fighter_key("  Jon Jones  ") == "jon jones"


class TestMergeOddsSources:
    def test_merge_empty(self):
        result = _merge_odds_sources({"bouts": {}}, {"bouts": {}})
        assert result == {"bouts": {}}

    def test_merge_disjoint(self):
        a = {"bouts": {"fight1": {"source": "dk"}}}
        b = {"bouts": {"fight2": {"source": "pm"}}}
        result = _merge_odds_sources(a, b)
        assert "fight1" in result["bouts"]
        assert "fight2" in result["bouts"]

    def test_merge_overlap_keeps_first(self):
        a = {"bouts": {"fight1": {"source": "dk", "odds": 1.5}}}
        b = {"bouts": {"fight1": {"source": "pm", "odds": 1.6}}}
        result = _merge_odds_sources(a, b)
        assert result["bouts"]["fight1"]["source"] == "dk"
        assert "alt_sources" in result["bouts"]["fight1"]


class TestFetchDraftKingsOdds:
    @patch("data.providers.odds_provider._safe_get")
    def test_successful_fetch(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "eventGroup": {
                "events": [
                    {
                        "name": "UFC 320",
                        "displayGroups": [
                            {
                                "markets": [
                                    {
                                        "description": "Moneyline",
                                        "outcomes": [
                                            {"participant": "Jon Jones", "oddsAmerican": "-200", "oddsDecimal": "1.5"},
                                            {"participant": "Tom Aspinall", "oddsAmerican": "+170", "oddsDecimal": "2.7"},
                                        ],
                                    }
                                ]
                            }
                        ],
                    }
                ]
            }
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = _fetch_draftkings_odds("")
        assert len(result["bouts"]) > 0

    @patch("data.providers.odds_provider._safe_get")
    def test_api_failure(self, mock_get):
        mock_get.side_effect = Exception("Network error")
        with pytest.raises(DataSourceError, match="DraftKings"):
            _fetch_draftkings_odds("")


class TestFetchPolymarketOdds:
    @patch("data.providers.odds_provider._safe_get")
    def test_successful_fetch(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            {
                "title": "Jones vs Aspinall",
                "markets": [
                    {
                        "question": "Will Jones win?",
                        "outcomePrices": ["0.65", "0.35"],
                        "volume": 50000,
                        "liquidity": 10000,
                    }
                ],
            }
        ]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = _fetch_polymarket_odds("")
        assert len(result["bouts"]) > 0

    @patch("data.providers.odds_provider._safe_get")
    def test_api_failure(self, mock_get):
        mock_get.side_effect = Exception("Network error")
        with pytest.raises(DataSourceError, match="Polymarket"):
            _fetch_polymarket_odds("")


class TestFetchAllUfcOdds:
    @patch("data.providers.odds_provider._fetch_polymarket_odds")
    @patch("data.providers.odds_provider._fetch_draftkings_odds")
    def test_merges_sources(self, mock_dk, mock_pm):
        mock_dk.return_value = {"bouts": {"fight1": {"source": "dk"}}}
        mock_pm.return_value = {"bouts": {"fight2": {"source": "pm"}}}

        result = fetch_all_ufc_odds()
        assert "fight1" in result["bouts"]
        assert "fight2" in result["bouts"]
        assert "_fetched_at" in result


@pytest.mark.asyncio
class TestFetchOddsForEvent:
    @patch("data.providers.odds_provider._fetch_polymarket_odds")
    @patch("data.providers.odds_provider._fetch_draftkings_odds")
    async def test_returns_none_when_empty(self, mock_dk, mock_pm):
        mock_dk.return_value = {"bouts": {}}
        mock_pm.return_value = {"bouts": {}}
        result = await fetch_odds_for_event("test_event")
        assert result is None

    @patch("data.providers.odds_provider._fetch_polymarket_odds")
    @patch("data.providers.odds_provider._fetch_draftkings_odds")
    async def test_returns_merged_when_data(self, mock_dk, mock_pm):
        mock_dk.return_value = {"bouts": {"fight1": {"source": "dk"}}}
        mock_pm.return_value = {"bouts": {}}
        result = await fetch_odds_for_event("test_event")
        assert result is not None
        assert "fight1" in result["bouts"]
        assert "draftkings" in result["_sources"]
