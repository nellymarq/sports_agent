# tests/test_orchestrator.py
# Unit tests for orchestrator: DAG execution, parallel specialists, error handling.

import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from unittest.mock import patch, MagicMock

from orchestrator import (
    orchestrator,
    _validate_task_plan,
    _resolve_event_id_from_text,
    _run_single_specialist,
    SPECIALIST_REGISTRY,
)
from data.metadata import SpecialistOutput
from tests.mock_llm import MockLLM


# ============================================================
# Task Validation
# ============================================================

class TestTaskValidation:
    def test_missing_tasks_key(self):
        errors = _validate_task_plan({})
        assert len(errors) == 1
        assert "missing 'tasks'" in errors[0]

    def test_valid_plan(self):
        plan = {
            "tasks": [
                {"task_type": "specialist", "specialist": "style"},
            ]
        }
        errors = _validate_task_plan(plan)
        assert errors == []

    def test_unknown_specialist(self):
        plan = {
            "tasks": [
                {"task_type": "specialist", "specialist": "nonexistent_specialist"},
            ]
        }
        errors = _validate_task_plan(plan)
        assert len(errors) == 1
        assert "Unknown specialist" in errors[0]

    def test_missing_specialist_key(self):
        plan = {
            "tasks": [
                {"task_type": "specialist"},
            ]
        }
        errors = _validate_task_plan(plan)
        assert len(errors) == 1

    def test_non_specialist_tasks_ok(self):
        plan = {
            "tasks": [
                {"task_type": "coordinator_merge"},
                {"task_type": "critic_review"},
            ]
        }
        errors = _validate_task_plan(plan)
        assert errors == []


# ============================================================
# Event Resolution
# ============================================================

class TestEventResolution:
    def test_ufc_number(self):
        assert _resolve_event_id_from_text("UFC 313") == "ufc_313"

    def test_ufc_lowercase(self):
        assert _resolve_event_id_from_text("ufc 300 main event") == "ufc_300"

    def test_no_ufc(self):
        assert _resolve_event_id_from_text("who wins this fight") is None

    def test_empty_string(self):
        assert _resolve_event_id_from_text("") is None

    def test_none_input(self):
        assert _resolve_event_id_from_text(None) is None


# ============================================================
# Single Specialist Runner
# ============================================================

class TestSingleSpecialist:
    @pytest.mark.asyncio
    async def test_unknown_specialist(self):
        result = await _run_single_specialist(
            specialist_key="nonexistent",
            name="test",
            llm=MockLLM(),
            tool_registry={},
            user_input="test",
            history=[],
            retrieved_context="",
            semantic_memory="",
            episodic_memory=[],
            context={},
        )
        assert isinstance(result, SpecialistOutput)
        assert result.confidence == 0.0
        assert "ERROR" in result.content

    @pytest.mark.asyncio
    async def test_valid_specialist_test_mode(self):
        result = await _run_single_specialist(
            specialist_key="style",
            name="style",
            llm=MockLLM(),
            tool_registry={},  # empty = test mode for specialists
            user_input="test input",
            history=[],
            retrieved_context="",
            semantic_memory="",
            episodic_memory=[],
            context={},
        )
        assert isinstance(result, SpecialistOutput)
        assert result.content.strip() != ""


# ============================================================
# Orchestrator Full Run
# ============================================================

def _mock_memory_store():
    """Create a MagicMock with all memory store methods."""
    mock = MagicMock()
    mock.write_short_term = MagicMock()
    mock.write_long_term = MagicMock()
    mock.write_evidence = MagicMock()
    mock.write_specialist_note = MagicMock()
    mock.decay_long_term = MagicMock()
    mock.dedupe_long_term = MagicMock()
    mock.cap_long_term = MagicMock()
    mock.decay_short_term = MagicMock()
    return mock


class TestOrchestrator:
    @pytest.mark.asyncio
    async def test_empty_task_plan_test_mode(self):
        result = await orchestrator(
            llm=MockLLM(),
            tool_registry={},
            task_plan={"tasks": [], "user_input": "test"},
            test_mode=True,
        )
        assert "TEST MODE" in result

    @pytest.mark.asyncio
    async def test_validation_error(self):
        result = await orchestrator(
            llm=MockLLM(),
            tool_registry={},
            task_plan={},  # missing 'tasks'
        )
        assert "TASK PLAN ERROR" in result

    @pytest.mark.asyncio
    async def test_specialist_only_plan(self):
        with patch("orchestrator.MEMORY_STORE", _mock_memory_store()), \
             patch("orchestrator.store_vectorized_memory"):
            task_plan = {
                "user_input": "test",
                "history": [],
                "retrieved_context": "",
                "tasks": [
                    {"task_type": "specialist", "specialist": "style"},
                    {"task_type": "specialist", "specialist": "form"},
                ],
            }
            result = await orchestrator(
                llm=MockLLM(),
                tool_registry={},
                task_plan=task_plan,
                test_mode=True,
            )
            assert isinstance(result, str)
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        """Verify multiple specialists run without error in parallel mode."""
        with patch("orchestrator.MEMORY_STORE", _mock_memory_store()), \
             patch("orchestrator.store_vectorized_memory"):
            task_plan = {
                "user_input": "Pereira vs Ankalaev",
                "history": [],
                "retrieved_context": "",
                "tasks": [
                    {"task_type": "specialist", "specialist": s}
                    for s in ["style", "form", "sentiment", "weightcut", "pace", "grappling"]
                ],
            }
            result = await orchestrator(
                llm=MockLLM(),
                tool_registry={},
                task_plan=task_plan,
                test_mode=True,
            )
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_full_dag_with_coordinator_and_critic(self):
        """Test the full DAG: specialists -> coordinator -> critic."""
        with patch("orchestrator.MEMORY_STORE", _mock_memory_store()), \
             patch("orchestrator.store_vectorized_memory"):
            task_plan = {
                "user_input": "Pereira vs Ankalaev analysis",
                "history": [],
                "retrieved_context": "",
                "tasks": [
                    {"id": 0, "task_type": "specialist", "specialist": "style", "depends_on": []},
                    {"id": 1, "task_type": "specialist", "specialist": "form", "depends_on": []},
                    {"id": 2, "task_type": "coordinator_merge", "depends_on": [0, 1]},
                    {"id": 3, "task_type": "critic_review", "depends_on": [2]},
                ],
            }
            result = await orchestrator(
                llm=MockLLM(),
                prediction_llm=MockLLM(),
                tool_registry={},
                task_plan=task_plan,
                test_mode=False,
            )
            assert isinstance(result, str)
            assert len(result) > 0


# ============================================================
# Specialist Registry
# ============================================================

class TestSpecialistRegistry:
    def test_all_core_four_registered(self):
        for name in ["style", "form", "sentiment", "weightcut"]:
            assert name in SPECIALIST_REGISTRY

    def test_all_dynamic_registered(self):
        for name in ["metadata", "pace", "grappling", "fight_iq", "scramble",
                      "damage", "gameplan", "judging", "knowledge"]:
            assert name in SPECIALIST_REGISTRY

    def test_all_debug_registered(self):
        for name in ["routing_debug", "coordinator_debug", "critic_debug", "memory_debug"]:
            assert name in SPECIALIST_REGISTRY

    def test_all_are_callable(self):
        for name, fn in SPECIALIST_REGISTRY.items():
            assert callable(fn), f"Specialist '{name}' is not callable"
