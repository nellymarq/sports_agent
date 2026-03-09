# tests/test_tools.py
# Unit tests for tool definitions and parsing logic.

import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tools import (
    TOOL_REGISTRY,
    UFCStatsTool,
    ESPNUFCTool,
    DraftKingsTool,
    PolymarketTool,
    american_to_implied_prob,
    implied_prob_pair,
    _cache_get,
    _cache_set,
    _CACHE,
)


class TestToolRegistry:
    def test_all_tools_registered(self):
        assert "ufc_stats" in TOOL_REGISTRY
        assert "espn_ufc" in TOOL_REGISTRY
        assert "draftkings_odds" in TOOL_REGISTRY
        assert "polymarket" in TOOL_REGISTRY

    def test_tool_count(self):
        assert len(TOOL_REGISTRY) == 4

    def test_all_tools_have_invoke(self):
        for name, tool in TOOL_REGISTRY.items():
            assert hasattr(tool, "invoke"), f"Tool '{name}' missing invoke method"

    def test_all_tools_have_name(self):
        for name, tool in TOOL_REGISTRY.items():
            assert hasattr(tool, "name")
            assert tool.name == name


class TestUFCStatsTool:
    def test_empty_fighter_error(self):
        tool = UFCStatsTool()
        result = tool.invoke({})
        assert "error" in result

    def test_blank_fighter_error(self):
        tool = UFCStatsTool()
        result = tool.invoke({"fighter_name": ""})
        assert "error" in result

    def test_invoke_returns_dict(self):
        tool = UFCStatsTool()
        # This will try to hit the real API; may fail in CI but should return a dict
        result = tool.invoke({"fighter_name": "Pereira"})
        assert isinstance(result, dict)
        assert "source" in result or "error" in result


class TestESPNTool:
    def test_empty_fighter_error(self):
        tool = ESPNUFCTool()
        result = tool.invoke({})
        assert "error" in result

    def test_invoke_returns_dict(self):
        tool = ESPNUFCTool()
        result = tool.invoke({"fighter_name": "Pereira"})
        assert isinstance(result, dict)


class TestDraftKingsTool:
    def test_invoke_returns_dict(self):
        tool = DraftKingsTool()
        result = tool.invoke({"fighter_name": "Pereira"})
        assert isinstance(result, dict)
        assert "source" in result or "error" in result

    def test_empty_fighter_ok(self):
        tool = DraftKingsTool()
        result = tool.invoke({})
        assert isinstance(result, dict)


class TestPolymarketTool:
    def test_invoke_returns_dict(self):
        tool = PolymarketTool()
        result = tool.invoke({"fighter_name": "Pereira"})
        assert isinstance(result, dict)
        assert "source" in result or "error" in result

    def test_empty_fighter_ok(self):
        tool = PolymarketTool()
        result = tool.invoke({})
        assert isinstance(result, dict)


class TestOddsUtilities:
    def test_favorite_odds(self):
        # -200 means bet $200 to win $100 => implied prob ~66.7%
        p = american_to_implied_prob("-200")
        assert p is not None
        assert 0.66 < p < 0.68

    def test_underdog_odds(self):
        # +200 means bet $100 to win $200 => implied prob ~33.3%
        p = american_to_implied_prob("+200")
        assert p is not None
        assert 0.32 < p < 0.34

    def test_even_odds(self):
        # +100 => 50%
        p = american_to_implied_prob("+100")
        assert p is not None
        assert 0.49 < p < 0.51

    def test_invalid_odds(self):
        assert american_to_implied_prob("abc") is None
        assert american_to_implied_prob("") is None

    def test_implied_pair_removes_vig(self):
        result = implied_prob_pair("-200", "+170")
        assert result["favorite_prob"] is not None
        assert result["underdog_prob"] is not None
        # After vig removal, should sum to ~1.0
        total = result["favorite_prob"] + result["underdog_prob"]
        assert 0.99 < total < 1.01

    def test_implied_pair_heavy_favorite(self):
        result = implied_prob_pair("-500", "+400")
        assert result["favorite_prob"] > 0.7


class TestResponseCache:
    def test_cache_set_and_get(self):
        _cache_set("test_key", {"data": 123})
        assert _cache_get("test_key") == {"data": 123}

    def test_cache_miss(self):
        assert _cache_get("nonexistent_key_xyz") is None

    def test_cache_expiry(self):
        import time as _time
        _CACHE["expire_test"] = (_time.time() - 9999, "old_data")
        assert _cache_get("expire_test") is None
