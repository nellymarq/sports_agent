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

    @pytest.mark.asyncio
    async def test_memory_full_mode(self):
        llm = MockLLM()
        result = await router_agent(
            llm, "Tell me about Islam",
            semantic_memory="Islam Makhachev analysis context",
        )
        assert len(result["specialists"]) == len(FULL_SPECIALIST_LIST)

    @pytest.mark.asyncio
    async def test_multiple_debug_triggers(self):
        llm = MockLLM()
        result = await router_agent(llm, "explain routing and explain critic")
        assert "routing_debug" in result["debug_specialists"]
        assert "critic_debug" in result["debug_specialists"]


# ============================================================
# Extended Question Type Detection
# ============================================================

class TestQuestionTypeExtended:
    def test_predict(self):
        assert _detect_question_type("Predict the outcome") == "who_wins"

    def test_prediction(self):
        assert _detect_question_type("Give me your prediction") == "who_wins"

    def test_pick(self):
        assert _detect_question_type("Who's your pick?") == "who_wins"

    def test_exploit_is_weakness(self):
        assert _detect_question_type("What can you exploit?") == "weakness"

    def test_game_plan_two_words(self):
        assert _detect_question_type("What's the game plan?") == "gameplan"

    def test_path_to_victory(self):
        assert _detect_question_type("Path to victory for Ankalaev") == "gameplan"

    def test_full_card(self):
        # "break down" triggers who_wins before "full card" check
        assert _detect_question_type("Break down the full card") == "who_wins"

    def test_entire_card(self):
        # "analyze" triggers who_wins before "entire card" check
        assert _detect_question_type("Analyze the entire card") == "who_wins"

    def test_odds_is_who_wins(self):
        assert _detect_question_type("What are the odds?") == "who_wins"

    def test_value_bet(self):
        assert _detect_question_type("Any value bets?") == "who_wins"

    def test_betting(self):
        assert _detect_question_type("What should I be betting on?") == "who_wins"

    def test_analyze(self):
        assert _detect_question_type("Analyze this fight") == "who_wins"

    def test_how_does_he_fight(self):
        assert _detect_question_type("How does he fight?") == "style_profile"

    def test_how_do_you_beat(self):
        assert _detect_question_type("How do you beat Makhachev?") == "weakness"

    def test_how_should_strategy(self):
        assert _detect_question_type("How should Poirier approach this?") == "gameplan"

    def test_ufc_who_wins(self):
        assert _detect_question_type("UFC 316 who wins?") == "event_who_wins"

    def test_card_breakdown(self):
        # "breakdown" triggers who_wins before "card breakdown" check
        assert _detect_question_type("Card breakdown for Saturday") == "who_wins"

    def test_all_fights_card(self):
        # "all fights" matches event_who_wins when no earlier trigger fires
        assert _detect_question_type("Show me all fights on the card") == "event_who_wins"


# ============================================================
# Extended Keyword Routing
# ============================================================

class TestKeywordRoutingExtended:
    def test_metadata_reach(self):
        assert "metadata" in _base_keyword_routing("What's his reach?")

    def test_metadata_stance(self):
        assert "metadata" in _base_keyword_routing("He's a southpaw stance")

    def test_scramble_chain_wrestling(self):
        assert "scramble" in _base_keyword_routing("chain wrestling ability")

    def test_judging_scorecard(self):
        assert "judging" in _base_keyword_routing("scorecard prediction")

    def test_knowledge_career_arc(self):
        assert "knowledge" in _base_keyword_routing("career arc trajectory")

    def test_gameplan_tactics(self):
        assert "gameplan" in _base_keyword_routing("tactical approach")

    def test_multiple_specialists(self):
        result = _base_keyword_routing("wrestling pace pressure ground")
        assert "grappling" in result
        assert "pace" in result

    def test_order_core_four_first(self):
        result = _base_keyword_routing("grappling pace damage")
        for i, s in enumerate(CORE_FOUR):
            assert result[i] == s


# ============================================================
# Intent Routing Extended
# ============================================================

class TestIntentRoutingExtended:
    def test_event_who_wins_gets_all(self):
        result = _intent_enhanced_routing("event_who_wins", CORE_FOUR.copy())
        assert len(result) == len(FULL_SPECIALIST_LIST)

    def test_gameplan_adds_specific(self):
        result = _intent_enhanced_routing("gameplan", CORE_FOUR.copy())
        assert "gameplan" in result
        assert "fight_iq" in result
        assert "pace" in result
        assert "grappling" in result
        assert "damage" in result

    def test_preserves_full_specialist_order(self):
        result = _intent_enhanced_routing("who_wins", CORE_FOUR.copy())
        for i in range(len(result) - 1):
            idx_a = FULL_SPECIALIST_LIST.index(result[i])
            idx_b = FULL_SPECIALIST_LIST.index(result[i + 1])
            assert idx_a < idx_b
