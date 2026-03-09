# tests/test_tool_runtime.py
# Unit tests for specialist tool runtime: truncation, prompt building, tool loop.

import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from specialists.tool_runtime import (
    estimate_tokens,
    truncate_text,
    truncate_messages,
    build_system_prompt,
    parse_tool_call,
    run_tool_loop,
)
from tests.mock_llm import MockLLM


class TestTokenEstimation:
    def test_empty(self):
        assert estimate_tokens("") == 0

    def test_basic(self):
        assert estimate_tokens("hello world") > 0

    def test_roughly_correct(self):
        text = "a" * 400
        tokens = estimate_tokens(text)
        assert 90 <= tokens <= 110  # ~100 tokens for 400 chars


class TestTruncation:
    def test_short_text_unchanged(self):
        assert truncate_text("short", 100) == "short"

    def test_long_text_truncated(self):
        text = "a" * 10000
        result = truncate_text(text, 100)
        assert len(result) < len(text)
        assert "TRUNCATED" in result

    def test_exact_boundary(self):
        text = "a" * 400  # exactly 100 tokens
        result = truncate_text(text, 100)
        assert result == text


class TestMessageTruncation:
    def test_fits_under_limit(self):
        msgs = [{"content": "short message"}]
        result = truncate_messages(msgs, 1000)
        assert len(result) == 1

    def test_drops_oldest(self):
        msgs = [
            {"content": "a" * 4000},  # ~1000 tokens
            {"content": "b" * 4000},  # ~1000 tokens
            {"content": "c" * 4000},  # ~1000 tokens
        ]
        result = truncate_messages(msgs, 2500)
        assert len(result) < 3
        # Most recent should survive
        assert result[-1]["content"].startswith("c")


class TestBuildSystemPrompt:
    def test_returns_list(self):
        result = build_system_prompt("base", "profile", "context", ["tool1"])
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["role"] == "system"

    def test_includes_tools(self):
        result = build_system_prompt("base", "profile", "context", ["ufc_stats", "espn_ufc"])
        assert "ufc_stats" in result[0]["content"]
        assert "espn_ufc" in result[0]["content"]

    def test_no_tools(self):
        result = build_system_prompt("base", "profile", "context", [])
        assert "None" in result[0]["content"]


class TestParseToolCall:
    def test_no_tool_calls(self):
        class FakeReply:
            tool_calls = None
        assert parse_tool_call(FakeReply()) is None

    def test_empty_tool_calls(self):
        class FakeReply:
            tool_calls = []
        assert parse_tool_call(FakeReply()) is None


class TestRunToolLoop:
    @pytest.mark.asyncio
    async def test_basic_no_tools(self):
        """MockLLM returns plain text, no tool calls."""
        llm = MockLLM()
        messages = [{"role": "user", "content": "test"}]
        result = await run_tool_loop(llm, messages, {})
        assert result == "Mock response"

    @pytest.mark.asyncio
    async def test_with_invoke_based_tool(self):
        """Test that tools with .invoke() method work."""
        class FakeTool:
            name = "test_tool"
            def invoke(self, args):
                return {"result": "tool output"}

        # MockLLM doesn't trigger tool calls, so this just verifies
        # the tool loop completes without errors
        llm = MockLLM()
        messages = [{"role": "user", "content": "test"}]
        registry = {"test_tool": FakeTool()}
        result = await run_tool_loop(llm, messages, registry)
        assert result == "Mock response"
