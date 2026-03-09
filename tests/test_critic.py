# tests/test_critic.py
# Unit tests for critic agent: chunking, refinement, output types.

import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from critic_agent import critic_review, chunk_text, CHUNK_SIZE
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
