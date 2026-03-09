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
