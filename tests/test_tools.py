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
