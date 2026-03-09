# tests/test_router_agent.py
# Unit tests for router_agent question type detection and specialist selection.

import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from router_agent import (
    router_agent,
    _detect_question_type,
    _base_keyword_routing,
    _intent_enhanced_routing,
    _memory_suggests_full_mode,
    CORE_FOUR,
    FULL_SPECIALIST_LIST,
)
from tests.mock_llm import MockLLM


# ============================================================
# Question Type Detection
# ============================================================

class TestQuestionTypeDetection:
    def test_who_wins(self):
        assert _detect_question_type("Who wins Pereira vs Ankalaev?") == "who_wins"

    def test_who_wins_variant(self):
        assert _detect_question_type("Who would win between Jones and Aspinall?") == "who_wins"

    def test_event_who_wins(self):
        assert _detect_question_type("Who wins the UFC 313 main event?") == "event_who_wins"

    def test_event_who_wins_next(self):
        assert _detect_question_type("Who wins the next UFC main event?") == "event_who_wins"

    def test_style_profile(self):
        assert _detect_question_type("What kind of fighter is Pereira?") == "style_profile"

    def test_weakness(self):
        assert _detect_question_type("What's Pereira's weakness?") == "weakness"

    def test_gameplan(self):
        assert _detect_question_type("What's the gameplan to beat Makhachev?") == "gameplan"

    def test_general_fallback(self):
        assert _detect_question_type("Tell me about the UFC") == "general"

    def test_vs_triggers_who_wins(self):
        assert _detect_question_type("Volkanovski vs Topuria breakdown") == "who_wins"

    def test_matchup_triggers_who_wins(self):
        assert _detect_question_type("Pereira matchup analysis") == "who_wins"


# ============================================================
# Keyword Routing
# ============================================================

class TestKeywordRouting:
    def test_core_four_always_included(self):
        result = _base_keyword_routing("basic question")
        for core in CORE_FOUR:
            assert core in result

    def test_grappling_keywords(self):
        result = _base_keyword_routing("How is his wrestling?")
        assert "grappling" in result

    def test_pace_keywords(self):
        result = _base_keyword_routing("What about output volume?")
        assert "pace" in result

    def test_damage_keywords(self):
        result = _base_keyword_routing("How's his chin durability?")
        assert "damage" in result

    def test_fight_iq_keywords(self):
        result = _base_keyword_routing("Does he have fight iq?")
        assert "fight_iq" in result

    def test_no_duplicates(self):
        result = _base_keyword_routing("grappling wrestling takedown ground")
        assert len(result) == len(set(result))


# ============================================================
# Intent-Enhanced Routing
# ============================================================

class TestIntentRouting:
    def test_who_wins_gets_all_specialists(self):
        current = CORE_FOUR.copy()
        result = _intent_enhanced_routing("who_wins", current)
        assert len(result) == len(FULL_SPECIALIST_LIST)

    def test_style_profile_adds_specific(self):
        result = _intent_enhanced_routing("style_profile", CORE_FOUR.copy())
        assert "metadata" in result
        assert "knowledge" in result

    def test_weakness_adds_specific(self):
        result = _intent_enhanced_routing("weakness", CORE_FOUR.copy())
        assert "damage" in result
        assert "grappling" in result


# ============================================================
# Memory-Driven Full Mode
# ============================================================

class TestMemoryFullMode:
    def test_semantic_memory_triggers_full(self):
        assert _memory_suggests_full_mode("some fighter knowledge", []) is True

    def test_episodic_triggers_full(self):
        assert _memory_suggests_full_mode("", ["did a full analysis last time"]) is True

    def test_empty_memory_no_full(self):
        assert _memory_suggests_full_mode("", []) is False


# ============================================================
# Full Router Agent
# ============================================================

class TestRouterAgent:
    @pytest.mark.asyncio
    async def test_returns_valid_structure(self):
        llm = MockLLM()
        result = await router_agent(llm, "Who wins Pereira vs Ankalaev?")
        assert "mode" in result
        assert "specialists" in result
        assert "question_type" in result
        assert "debug_specialists" in result

    @pytest.mark.asyncio
    async def test_who_wins_gets_full_specialists(self):
        llm = MockLLM()
        result = await router_agent(llm, "Who wins Pereira vs Ankalaev?")
        assert len(result["specialists"]) == len(FULL_SPECIALIST_LIST)

    @pytest.mark.asyncio
    async def test_debug_triggers(self):
        llm = MockLLM()
        result = await router_agent(llm, "Explain routing for Pereira vs Ankalaev")
        assert "routing_debug" in result["debug_specialists"]

    @pytest.mark.asyncio
    async def test_empty_input(self):
        llm = MockLLM()
        result = await router_agent(llm, "")
        assert isinstance(result["specialists"], list)
