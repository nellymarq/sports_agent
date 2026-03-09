# tests/test_coordinator.py
# Unit tests for coordinator agent: confidence weighting, structured blocks, merging.

import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from coordinator_agent import (
    coordinator_merge,
    _build_structured_block,
    _compute_overall_confidence,
    _build_diagnostics_block,
)
from data.metadata import SpecialistOutput
from tests.mock_llm import MockLLM


class TestStructuredBlock:
    def test_sorts_by_confidence(self):
        outputs = [
            SpecialistOutput.create(specialist="low", content="low conf", confidence=0.3),
            SpecialistOutput.create(specialist="high", content="high conf", confidence=0.9),
            SpecialistOutput.create(specialist="mid", content="mid conf", confidence=0.6),
        ]
        block = _build_structured_block(outputs)
        # HIGH should appear first
        high_pos = block.index("high")
        low_pos = block.index("low")
        assert high_pos < low_pos

    def test_weight_labels(self):
        outputs = [
            SpecialistOutput.create(specialist="a", content="test", confidence=0.9),
            SpecialistOutput.create(specialist="b", content="test", confidence=0.6),
            SpecialistOutput.create(specialist="c", content="test", confidence=0.3),
        ]
        block = _build_structured_block(outputs)
        assert "HIGH WEIGHT" in block
        assert "MEDIUM WEIGHT" in block
        assert "LOW WEIGHT" in block

    def test_evidence_count_shown(self):
        from data.metadata import Evidence
        ev = Evidence.create(source="test", content="fact")
        output = SpecialistOutput.create(
            specialist="style", content="analysis", confidence=0.8, evidence=[ev]
        )
        block = _build_structured_block([output])
        assert "[evidence count]: 1" in block


class TestConfidenceComputation:
    def test_average_confidence(self):
        outputs = [
            SpecialistOutput.create(specialist="a", content="x", confidence=0.8),
            SpecialistOutput.create(specialist="b", content="y", confidence=0.6),
        ]
        assert abs(_compute_overall_confidence(outputs) - 0.7) < 0.01

    def test_empty_list(self):
        assert _compute_overall_confidence([]) == 0.0

    def test_clamps_values(self):
        outputs = [
            SpecialistOutput.create(specialist="a", content="x", confidence=1.0),
            SpecialistOutput.create(specialist="b", content="y", confidence=0.0),
        ]
        assert abs(_compute_overall_confidence(outputs) - 0.5) < 0.01


class TestDiagnosticsBlock:
    def test_includes_router_info(self):
        outputs = [
            SpecialistOutput.create(specialist="style", content="test", confidence=0.7)
        ]
        router_output = {
            "question_type": "who_wins",
            "specialists": ["style"],
            "debug_specialists": [],
        }
        block = _build_diagnostics_block(outputs, router_output)
        assert "who_wins" in block
        assert "style" in block


class TestCoordinatorMerge:
    @pytest.mark.asyncio
    async def test_returns_specialist_output(self):
        llm = MockLLM()
        outputs = [
            SpecialistOutput.create(specialist="style", content="Style analysis", confidence=0.8),
            SpecialistOutput.create(specialist="form", content="Form analysis", confidence=0.7),
        ]
        result = await coordinator_merge(
            llm=llm,
            specialist_outputs=outputs,
            semantic_memory="",
            episodic_memory=[],
            user_input="Who wins?",
            fighters=["Pereira", "Ankalaev"],
        )
        assert isinstance(result, SpecialistOutput)
        assert result.specialist == "coordinator"
        assert result.content.strip() != ""

    @pytest.mark.asyncio
    async def test_empty_outputs(self):
        llm = MockLLM()
        result = await coordinator_merge(
            llm=llm,
            specialist_outputs=[],
            semantic_memory="",
            episodic_memory=[],
            user_input="test",
            fighters=[],
        )
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_preserves_evidence(self):
        from data.metadata import Evidence
        llm = MockLLM()
        ev = Evidence.create(source="ufc_stats", content="19-1 record")
        outputs = [
            SpecialistOutput.create(
                specialist="style", content="test", confidence=0.8, evidence=[ev]
            ),
        ]
        result = await coordinator_merge(
            llm=llm,
            specialist_outputs=outputs,
            semantic_memory="",
            episodic_memory=[],
            user_input="test",
            fighters=["Pereira"],
        )
        assert len(result.evidence) == 1
