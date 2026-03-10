# tests/test_tools_utils.py
# Tests for tools utility functions and cache layer.

import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import (
    american_to_implied_prob,
    implied_prob_pair,
    _cache_get,
    _cache_set,
    _CACHE,
    UFCStatsTool,
    ESPNUFCTool,
    DraftKingsTool,
    PolymarketTool,
    TOOL_REGISTRY,
)


class TestAmericanToImpliedProb:
    def test_favorite(self):
        prob = american_to_implied_prob("-200")
        assert abs(prob - 0.6667) < 0.01

    def test_underdog(self):
        prob = american_to_implied_prob("+200")
        assert abs(prob - 0.3333) < 0.01

    def test_even(self):
        prob = american_to_implied_prob("+100")
        assert abs(prob - 0.5) < 0.01

    def test_heavy_favorite(self):
        prob = american_to_implied_prob("-500")
        assert abs(prob - 0.8333) < 0.01

    def test_heavy_underdog(self):
        prob = american_to_implied_prob("+500")
        assert abs(prob - 0.1667) < 0.01

    def test_invalid(self):
        assert american_to_implied_prob("abc") is None

    def test_empty(self):
        assert american_to_implied_prob("") is None

    def test_zero(self):
        assert american_to_implied_prob("0") is None

    def test_with_plus(self):
        prob = american_to_implied_prob("+150")
        assert prob is not None
        assert 0 < prob < 1


class TestImpliedProbPair:
    def test_basic_pair(self):
        result = implied_prob_pair("-200", "+170")
        assert result["favorite_prob"] is not None
        assert result["underdog_prob"] is not None
        # Should sum to 1 after vig removal
        assert abs(result["favorite_prob"] + result["underdog_prob"] - 1.0) < 0.001

    def test_even_odds(self):
        result = implied_prob_pair("-110", "-110")
        assert abs(result["favorite_prob"] - 0.5) < 0.01

    def test_invalid_one_side(self):
        result = implied_prob_pair("bad", "+200")
        # Should not normalize when one side is None
        assert result["favorite_prob"] is None


class TestToolCache:
    def setup_method(self):
        _CACHE.clear()

    def test_set_and_get(self):
        _cache_set("test_key", {"data": "value"})
        result = _cache_get("test_key")
        assert result == {"data": "value"}

    def test_cache_miss(self):
        result = _cache_get("nonexistent")
        assert result is None

    def test_cache_overwrite(self):
        _cache_set("key", "v1")
        _cache_set("key", "v2")
        assert _cache_get("key") == "v2"


class TestToolRegistry:
    def test_all_tools_registered(self):
        assert "ufc_stats" in TOOL_REGISTRY
        assert "espn_ufc" in TOOL_REGISTRY
        assert "draftkings_odds" in TOOL_REGISTRY
        assert "polymarket" in TOOL_REGISTRY

    def test_tool_names(self):
        assert UFCStatsTool.name == "ufc_stats"
        assert ESPNUFCTool.name == "espn_ufc"
        assert DraftKingsTool.name == "draftkings_odds"
        assert PolymarketTool.name == "polymarket"


class TestUFCStatsToolParsing:
    def test_empty_fighter_name(self):
        tool = UFCStatsTool()
        result = tool.invoke({"fighter_name": ""})
        assert "error" in result

    def test_missing_fighter_name(self):
        tool = UFCStatsTool()
        result = tool.invoke({})
        assert "error" in result

    def test_parse_fighter_row(self):
        from bs4 import BeautifulSoup
        tool = UFCStatsTool()
        html = """<tr>
            <td><a href="http://test.com/fighter/1">Alex Pereira</a></td>
            <td>Poatan</td>
            <td>6' 4"</td>
            <td>205 lbs.</td>
            <td>74"</td>
            <td>Orthodox</td>
            <td>11-2-0</td>
            <td>5.47</td>
            <td>56%</td>
            <td>3.81</td>
            <td>54%</td>
        </tr>"""
        row = BeautifulSoup(html, "html.parser").find("tr")
        parsed = tool._parse_fighter_row(row)
        assert parsed is not None
        assert parsed["name"] == "Alex Pereira"
        assert parsed["nickname"] == "Poatan"
        assert parsed["height"] == "6' 4\""
        assert parsed["record"] == "11-2-0"
        assert parsed["detail_url"] == "http://test.com/fighter/1"

    def test_parse_fighter_row_insufficient_cols(self):
        from bs4 import BeautifulSoup
        tool = UFCStatsTool()
        html = "<tr><td>Name</td><td>Nick</td></tr>"
        row = BeautifulSoup(html, "html.parser").find("tr")
        assert tool._parse_fighter_row(row) is None


class TestESPNToolErrors:
    def test_empty_fighter(self):
        tool = ESPNUFCTool()
        result = tool.invoke({"fighter_name": ""})
        assert "error" in result


class TestDraftKingsToolErrors:
    def test_empty_fighter_returns_all(self):
        """With empty fighter, should try to return all odds."""
        tool = DraftKingsTool()
        _CACHE.clear()
        with patch("tools._safe_get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.json.return_value = {"eventGroup": {"events": []}}
            mock_get.return_value = mock_resp

            result = tool.invoke({"fighter_name": ""})
            assert result["source"] == "DraftKings Sportsbook"

    def test_api_failure(self):
        tool = DraftKingsTool()
        _CACHE.clear()
        with patch("tools._safe_get", side_effect=Exception("timeout")):
            result = tool.invoke({"fighter_name": "test"})
            assert "error" in result
            assert result["live_data"] is False


class TestPolymarketToolErrors:
    def test_api_failure(self):
        tool = PolymarketTool()
        _CACHE.clear()
        with patch("tools._safe_get", side_effect=Exception("timeout")):
            result = tool.invoke({"fighter_name": "test"})
            assert "error" in result
            assert result["live_data"] is False
