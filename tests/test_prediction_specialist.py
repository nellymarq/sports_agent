# tests/test_prediction_specialist.py
# Unit tests for prediction specialist.

import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from specialists.prediction_specialist import (
    run_prediction_specialist,
    _build_context_block,
    parse_prediction_output,
    _confidence_from_tier,
)
from data.metadata import SpecialistOutput
from tests.mock_llm import MockLLM


class TestContextBlock:
    def test_includes_fighters(self):
        coordinator = SpecialistOutput.create(
            specialist="coordinator", content="analysis"
        )
        block = _build_context_block(
            coordinator_output=coordinator,
            fighters=["Pereira", "Ankalaev"],
            retrieved_context="",
            semantic_memory="",
            episodic_memory=[],
        )
        assert "Pereira" in block
        assert "Ankalaev" in block

    def test_includes_coordinator(self):
        coordinator = SpecialistOutput.create(
            specialist="coordinator", content="Coordinator merged analysis."
        )
        block = _build_context_block(
            coordinator_output=coordinator,
            fighters=[],
            retrieved_context="",
            semantic_memory="",
            episodic_memory=[],
        )
        assert "Coordinator" in block

    def test_includes_event_metadata(self):
        coordinator = SpecialistOutput.create(
            specialist="coordinator", content="test"
        )
        block = _build_context_block(
            coordinator_output=coordinator,
            fighters=[],
            retrieved_context="",
            semantic_memory="",
            episodic_memory=[],
            event_metadata={"event": "UFC 313"},
        )
        assert "UFC 313" in block

    def test_empty_context(self):
        block = _build_context_block(
            coordinator_output=None,
            fighters=[],
            retrieved_context="",
            semantic_memory="",
            episodic_memory=[],
        )
        assert block == ""


class TestPredictionSpecialist:
    @pytest.mark.asyncio
    async def test_test_mode(self):
        result = await run_prediction_specialist(
            llm=MockLLM(),
            tool_registry=None,
            coordinator_output=None,
            user_input="test",
        )
        assert isinstance(result, SpecialistOutput)
        assert result.specialist == "prediction"
        assert "test mode" in result.content.lower()

    @pytest.mark.asyncio
    async def test_with_coordinator(self):
        coordinator = SpecialistOutput.create(
            specialist="coordinator",
            content="Full fight analysis here.",
            confidence=0.8,
        )
        result = await run_prediction_specialist(
            llm=MockLLM(),
            tool_registry={"ufc_stats": None},  # non-empty triggers real mode
            coordinator_output=coordinator,
            user_input="Who wins Pereira vs Ankalaev?",
            fighters=["Pereira", "Ankalaev"],
        )
        assert isinstance(result, SpecialistOutput)
        assert result.specialist == "prediction"

    @pytest.mark.asyncio
    async def test_returns_specialist_output(self):
        result = await run_prediction_specialist(
            llm=MockLLM(),
            tool_registry={"tool": None},
            user_input="test",
        )
        assert isinstance(result, SpecialistOutput)


class TestPredictionParser:
    def test_parses_full_output(self):
        text = """**PREDICTED WINNER:** Alex Pereira
**WIN PROBABILITY:** 65% vs 35%
**CONFIDENCE TIER:** High
**METHOD LEAN:** KO/TKO
**ROUND LEAN:** Early (R1-2)
"""
        result = parse_prediction_output(text)
        assert result["predicted_winner"] == "Alex Pereira"
        assert result["prob_fighter_a"] == 65
        assert result["prob_fighter_b"] == 35
        assert result["confidence_tier"] == "High"
        assert result["method_lean"] == "KO/TKO"
        assert result["round_lean"] == "Early (R1-2)"

    def test_parses_partial_output(self):
        text = "**PREDICTED WINNER:** Islam Makhachev\nSome other text"
        result = parse_prediction_output(text)
        assert result["predicted_winner"] == "Islam Makhachev"
        assert "prob_fighter_a" not in result

    def test_empty_text(self):
        assert parse_prediction_output("") == {}

    def test_no_match(self):
        assert parse_prediction_output("Just some random text") == {}

    def test_parses_betting_angle(self):
        text = """**PREDICTED WINNER:** Pereira
**WIN PROBABILITY:** 65% vs 35%
**CONFIDENCE TIER:** High
**METHOD LEAN:** KO/TKO
**ROUND LEAN:** Early (R1-2)
**BETTING ANGLE:** Model: 65% vs Market: 55% = +10% edge on Pereira
**LIVE LINE SUGGESTION:** Over 1.5 rounds looks solid given Ankalaev's durability
"""
        result = parse_prediction_output(text)
        assert "betting_angle" in result
        assert "+10% edge" in result["betting_angle"]
        assert "live_line_suggestion" in result
        assert "Over 1.5" in result["live_line_suggestion"]

    def test_parses_without_optional_fields(self):
        text = """**PREDICTED WINNER:** Islam Makhachev
**WIN PROBABILITY:** 70% vs 30%
**CONFIDENCE TIER:** High
**METHOD LEAN:** Decision
**ROUND LEAN:** Distance
"""
        result = parse_prediction_output(text)
        assert result["predicted_winner"] == "Islam Makhachev"
        assert "betting_angle" not in result
        assert "live_line_suggestion" not in result


    def test_parses_method_probabilities(self):
        text = """**PREDICTED WINNER:** Alex Pereira
**WIN PROBABILITY:** 65% vs 35%
**CONFIDENCE TIER:** High
**METHOD LEAN:** KO/TKO
**ROUND LEAN:** Early (R1-2)

**METHOD PROBABILITIES:**
- KO/TKO: 45%
- Submission: 5%
- Decision: 50%
"""
        result = parse_prediction_output(text)
        assert "method_probabilities" in result
        mp = result["method_probabilities"]
        assert mp["ko_tko"] == 45
        assert mp["submission"] == 5
        assert mp["decision"] == 50

    def test_parses_round_probabilities(self):
        text = """**PREDICTED WINNER:** Alex Pereira
**WIN PROBABILITY:** 65% vs 35%
**CONFIDENCE TIER:** High
**METHOD LEAN:** KO/TKO
**ROUND LEAN:** Early (R1-2)

**ROUND PROBABILITIES:**
- R1 finish: 20%
- R2 finish: 15%
- R3 finish: 10%
- Goes to decision: 55%
"""
        result = parse_prediction_output(text)
        assert "round_probabilities" in result
        rp = result["round_probabilities"]
        assert rp["r1"] == 20
        assert rp["r2"] == 15
        assert rp["r3"] == 10
        assert rp["decision"] == 55

    def test_parses_five_round_probabilities(self):
        text = """**ROUND PROBABILITIES:**
- R1 finish: 15%
- R2 finish: 10%
- R3 finish: 8%
- R4 finish: 7%
- R5 finish: 5%
- Goes to decision: 55%
"""
        result = parse_prediction_output(text)
        rp = result["round_probabilities"]
        assert rp["r4"] == 7
        assert rp["r5"] == 5

    def test_no_method_probabilities_when_absent(self):
        text = """**PREDICTED WINNER:** Fighter A
**WIN PROBABILITY:** 55% vs 45%
"""
        result = parse_prediction_output(text)
        assert "method_probabilities" not in result
        assert "round_probabilities" not in result


class TestConfidenceFromTier:
    def test_very_high(self):
        assert _confidence_from_tier("Very High") == 0.9

    def test_high(self):
        assert _confidence_from_tier("High") == 0.8

    def test_medium(self):
        assert _confidence_from_tier("Medium") == 0.65

    def test_low(self):
        assert _confidence_from_tier("Low") == 0.5

    def test_default(self):
        assert _confidence_from_tier("") == 0.7
        assert _confidence_from_tier("unknown") == 0.7
