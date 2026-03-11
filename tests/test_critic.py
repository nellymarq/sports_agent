# tests/test_critic.py
# Unit tests for critic agent: chunking, refinement, output types.

import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from critic_agent import critic_review, chunk_text, validate_prediction_consistency, CHUNK_SIZE
from data.metadata import SpecialistOutput, FinalOutput
from tests.mock_llm import MockLLM


class TestChunking:
    def test_short_text_single_chunk(self):
        chunks = chunk_text("short text", size=100)
        assert len(chunks) == 1
        assert chunks[0] == "short text"

    def test_long_text_multiple_chunks(self):
        text = "a" * 10000
        chunks = chunk_text(text, size=3500)
        assert len(chunks) == 3  # 10000 / 3500 = 2.86 -> 3

    def test_empty_text(self):
        chunks = chunk_text("")
        assert chunks == []  # range(0, 0, CHUNK_SIZE) yields nothing

    def test_exact_chunk_size(self):
        text = "x" * CHUNK_SIZE
        chunks = chunk_text(text)
        assert len(chunks) == 1


class TestCriticReview:
    @pytest.mark.asyncio
    async def test_returns_final_output(self):
        llm = MockLLM()
        coordinator = SpecialistOutput.create(
            specialist="coordinator",
            content="This is the merged analysis.",
            confidence=0.8,
        )
        result = await critic_review(
            llm=llm,
            coordinator_output=coordinator,
            prediction_output=None,
            user_input="Who wins?",
            fighters=["Pereira", "Ankalaev"],
        )
        assert isinstance(result, FinalOutput)
        assert result.content.strip() != ""

    @pytest.mark.asyncio
    async def test_empty_coordinator_output(self):
        llm = MockLLM()
        coordinator = SpecialistOutput.create(
            specialist="coordinator",
            content="",
            confidence=0.0,
        )
        result = await critic_review(
            llm=llm,
            coordinator_output=coordinator,
            prediction_output=None,
            user_input="test",
            fighters=[],
        )
        assert isinstance(result, FinalOutput)
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_includes_prediction(self):
        llm = MockLLM()
        coordinator = SpecialistOutput.create(
            specialist="coordinator",
            content="Analysis content here.",
            confidence=0.8,
        )
        prediction = SpecialistOutput.create(
            specialist="prediction",
            content="Prediction: Pereira wins 65%",
            confidence=0.7,
        )
        result = await critic_review(
            llm=llm,
            coordinator_output=coordinator,
            prediction_output=prediction,
            user_input="test",
            fighters=["Pereira"],
        )
        assert isinstance(result, FinalOutput)
        assert prediction.id in result.merged_from

    @pytest.mark.asyncio
    async def test_preserves_evidence(self):
        from data.metadata import Evidence
        llm = MockLLM()
        ev = Evidence.create(source="test", content="evidence")
        coordinator = SpecialistOutput.create(
            specialist="coordinator",
            content="Test analysis",
            confidence=0.8,
            evidence=[ev],
        )
        result = await critic_review(
            llm=llm,
            coordinator_output=coordinator,
            prediction_output=None,
            user_input="test",
            fighters=[],
        )
        assert len(result.evidence) >= 1

    @pytest.mark.asyncio
    async def test_confidence_calibrated_from_inputs(self):
        llm = MockLLM()
        coordinator = SpecialistOutput.create(
            specialist="coordinator", content="Analysis", confidence=0.8,
        )
        prediction = SpecialistOutput.create(
            specialist="prediction", content="Prediction text", confidence=0.9,
        )
        result = await critic_review(
            llm=llm,
            coordinator_output=coordinator,
            prediction_output=prediction,
            user_input="test",
            fighters=["A", "B"],
        )
        # 0.4*0.8 + 0.6*0.9 = 0.86
        assert abs(result.confidence - 0.86) < 0.01

    @pytest.mark.asyncio
    async def test_confidence_coordinator_only(self):
        llm = MockLLM()
        coordinator = SpecialistOutput.create(
            specialist="coordinator", content="Analysis", confidence=0.7,
        )
        result = await critic_review(
            llm=llm,
            coordinator_output=coordinator,
            prediction_output=None,
            user_input="test",
            fighters=[],
        )
        assert abs(result.confidence - 0.7) < 0.01

    @pytest.mark.asyncio
    async def test_metadata_includes_validation(self):
        llm = MockLLM()
        coordinator = SpecialistOutput.create(
            specialist="coordinator", content="Analysis", confidence=0.8,
        )
        result = await critic_review(
            llm=llm,
            coordinator_output=coordinator,
            prediction_output=None,
            user_input="test",
            fighters=[],
        )
        assert "validation_warnings" in result.metadata
        assert "validation_warning_count" in result.metadata


class TestValidatePredictionConsistency:
    def test_no_warnings_for_clean_output(self):
        text = (
            "**WIN PROBABILITY:** 65% vs 35%\n"
            "**CONFIDENCE TIER:** High\n"
            "**METHOD PROBABILITIES:**\n"
            "- KO/TKO: 35%\n"
            "- Submission: 10%\n"
            "- Decision: 55%\n"
            "**ROUND PROBABILITIES:**\n"
            "- R1 finish: 12%\n"
            "- R2 finish: 10%\n"
            "- R3 finish: 8%\n"
            "- Goes to decision: 70%\n"
        )
        warnings = validate_prediction_consistency(text)
        assert len(warnings) == 0

    def test_method_sum_error(self):
        text = (
            "- KO/TKO: 50%\n"
            "- Submission: 30%\n"
            "- Decision: 40%\n"
        )
        warnings = validate_prediction_consistency(text)
        types = [w["type"] for w in warnings]
        assert "method_sum_error" in types
        method_warn = next(w for w in warnings if w["type"] == "method_sum_error")
        assert method_warn["severity"] == "high"
        assert "120%" in method_warn["message"]

    def test_method_sum_within_tolerance(self):
        text = (
            "- KO/TKO: 33%\n"
            "- Submission: 10%\n"
            "- Decision: 55%\n"
        )
        warnings = validate_prediction_consistency(text)
        method_warns = [w for w in warnings if w["type"] == "method_sum_error"]
        assert len(method_warns) == 0  # 98% is within 5% tolerance

    def test_round_sum_error(self):
        text = (
            "- R1 finish: 30%\n"
            "- R2 finish: 30%\n"
            "- R3 finish: 30%\n"
            "- Goes to decision: 30%\n"
        )
        warnings = validate_prediction_consistency(text)
        types = [w["type"] for w in warnings]
        assert "round_sum_error" in types

    def test_win_prob_sum_error(self):
        text = "**WIN PROBABILITY:** 60% vs 60%\n**CONFIDENCE TIER:** Medium\n"
        warnings = validate_prediction_consistency(text)
        types = [w["type"] for w in warnings]
        assert "win_prob_sum_error" in types

    def test_win_prob_sum_correct(self):
        text = "**WIN PROBABILITY:** 62% vs 38%\n**CONFIDENCE TIER:** Medium\n"
        warnings = validate_prediction_consistency(text)
        prob_warns = [w for w in warnings if w["type"] == "win_prob_sum_error"]
        assert len(prob_warns) == 0

    def test_very_high_confidence_low_prob(self):
        text = "**WIN PROBABILITY:** 58% vs 42%\n**CONFIDENCE TIER:** Very High\n"
        warnings = validate_prediction_consistency(text)
        types = [w["type"] for w in warnings]
        assert "tier_probability_mismatch" in types

    def test_low_confidence_high_prob(self):
        text = "**WIN PROBABILITY:** 75% vs 25%\n**CONFIDENCE TIER:** Low\n"
        warnings = validate_prediction_consistency(text)
        types = [w["type"] for w in warnings]
        assert "tier_probability_mismatch" in types

    def test_high_confidence_matching_prob(self):
        text = "**WIN PROBABILITY:** 70% vs 30%\n**CONFIDENCE TIER:** High\n"
        warnings = validate_prediction_consistency(text)
        tier_warns = [w for w in warnings if w["type"] == "tier_probability_mismatch"]
        assert len(tier_warns) == 0

    def test_probability_floor_violation(self):
        text = "**WIN PROBABILITY:** 93% vs 7%\n**CONFIDENCE TIER:** Very High\n"
        warnings = validate_prediction_consistency(text)
        types = [w["type"] for w in warnings]
        assert "probability_floor_violation" in types

    def test_probability_above_floor(self):
        text = "**WIN PROBABILITY:** 82% vs 18%\n**CONFIDENCE TIER:** Very High\n"
        warnings = validate_prediction_consistency(text)
        floor_warns = [w for w in warnings if w["type"] == "probability_floor_violation"]
        assert len(floor_warns) == 0

    def test_empty_text(self):
        warnings = validate_prediction_consistency("")
        assert warnings == []

    def test_no_structured_fields(self):
        warnings = validate_prediction_consistency("Just plain analysis text with no numbers.")
        assert warnings == []

    def test_five_round_probabilities(self):
        text = (
            "- R1 finish: 10%\n"
            "- R2 finish: 10%\n"
            "- R3 finish: 8%\n"
            "- R4 finish: 7%\n"
            "- R5 finish: 5%\n"
            "- Goes to decision: 60%\n"
        )
        warnings = validate_prediction_consistency(text)
        assert len(warnings) == 0

    def test_multiple_warnings_combined(self):
        text = (
            "**WIN PROBABILITY:** 60% vs 60%\n"
            "**CONFIDENCE TIER:** Very High\n"
            "- KO/TKO: 50%\n"
            "- Submission: 40%\n"
            "- Decision: 40%\n"
        )
        warnings = validate_prediction_consistency(text)
        assert len(warnings) >= 3  # win_prob_sum, tier_mismatch, method_sum
