# tests/test_supervisor.py
# Unit tests for supervisor agent: task plan generation.

import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from supervisor import supervisor_agent
from tests.mock_llm import MockLLM


class TestSupervisorAgent:
    @pytest.mark.asyncio
    async def test_builds_task_plan(self):
        llm = MockLLM()
        router_output = {
            "mode": "autonomous",
            "specialists": ["style", "form", "sentiment"],
            "question_type": "who_wins",
            "debug_specialists": [],
        }
        plan = await supervisor_agent(
            llm=llm,
            router_output=router_output,
            user_input="Who wins?",
            history=[],
            retrieved_context="",
        )
        assert "tasks" in plan
        tasks = plan["tasks"]
        # 3 specialists + 1 coordinator + 1 critic = 5
        assert len(tasks) == 5

    @pytest.mark.asyncio
    async def test_dependency_chain(self):
        llm = MockLLM()
        router_output = {
            "mode": "autonomous",
            "specialists": ["style", "form"],
            "question_type": "who_wins",
            "debug_specialists": [],
        }
        plan = await supervisor_agent(
            llm=llm,
            router_output=router_output,
            user_input="test",
            history=[],
        )
        tasks = plan["tasks"]

        # Find coordinator and critic
        coordinator = [t for t in tasks if t.get("task_type") == "coordinator_merge"]
        critic = [t for t in tasks if t.get("task_type") == "critic_review"]

        assert len(coordinator) == 1
        assert len(critic) == 1

        # Coordinator depends on all specialist ids
        specialist_ids = [t["id"] for t in tasks if t.get("task_type") == "specialist"]
        assert set(coordinator[0]["depends_on"]) == set(specialist_ids)

        # Critic depends on coordinator
        assert critic[0]["depends_on"] == [coordinator[0]["id"]]

    @pytest.mark.asyncio
    async def test_test_mode_no_coordinator_critic(self):
        llm = MockLLM()
        router_output = {
            "mode": "autonomous",
            "specialists": ["style"],
            "question_type": "general",
            "debug_specialists": [],
        }
        plan = await supervisor_agent(
            llm=llm,
            router_output=router_output,
            user_input="test",
            history=[],
            test_mode=True,
        )
        tasks = plan["tasks"]
        # Only specialist tasks, no coordinator/critic
        assert all(t.get("task_type") == "specialist" for t in tasks)

    @pytest.mark.asyncio
    async def test_empty_specialists(self):
        llm = MockLLM()
        router_output = {
            "mode": "autonomous",
            "specialists": [],
            "question_type": "general",
            "debug_specialists": [],
        }
        plan = await supervisor_agent(
            llm=llm,
            router_output=router_output,
            user_input="test",
            history=[],
        )
        assert plan["tasks"] == []

    @pytest.mark.asyncio
    async def test_preserves_metadata(self):
        llm = MockLLM()
        router_output = {
            "mode": "autonomous",
            "specialists": ["style"],
            "question_type": "who_wins",
            "debug_specialists": ["routing_debug"],
        }
        plan = await supervisor_agent(
            llm=llm,
            router_output=router_output,
            user_input="test query",
            history=["h1"],
            retrieved_context="context",
        )
        assert plan["user_input"] == "test query"
        assert plan["question_type"] == "who_wins"
        assert plan["debug_specialists"] == ["routing_debug"]


class TestSupervisorTaskGraph:
    """Tests for the individual task builder functions."""

    def test_build_specialist_task(self):
        from supervisor import _build_specialist_task
        task = _build_specialist_task(
            task_id=0,
            specialist="style",
            user_input="Who wins?",
            history=["prev"],
            retrieved_context="ctx",
        )
        assert task["id"] == 0
        assert task["task_type"] == "specialist"
        assert task["specialist"] == "style"
        assert task["user_input"] == "Who wins?"
        assert task["depends_on"] == []
        assert task["history"] == ["prev"]
        assert task["retrieved_context"] == "ctx"

    def test_build_coordinator_task(self):
        from supervisor import _build_coordinator_task
        task = _build_coordinator_task(task_id=5, parent_ids=[0, 1, 2, 3, 4])
        assert task["id"] == 5
        assert task["task_type"] == "coordinator_merge"
        assert task["depends_on"] == [0, 1, 2, 3, 4]

    def test_build_critic_task(self):
        from supervisor import _build_critic_task
        task = _build_critic_task(task_id=6, coordinator_id=5)
        assert task["id"] == 6
        assert task["task_type"] == "critic_review"
        assert task["depends_on"] == [5]

    @pytest.mark.asyncio
    async def test_full_specialist_list_ids_sequential(self):
        """Task IDs should be sequential from 0."""
        llm = MockLLM()
        specs = ["style", "form", "sentiment", "weightcut", "metadata",
                 "pace", "grappling", "fight_iq", "scramble"]
        router_output = {
            "mode": "autonomous",
            "specialists": specs,
            "question_type": "who_wins",
            "debug_specialists": [],
        }
        plan = await supervisor_agent(llm, router_output, "test", [])
        tasks = plan["tasks"]
        for i, t in enumerate(tasks):
            assert t["id"] == i

    @pytest.mark.asyncio
    async def test_single_specialist_graph(self):
        """With 1 specialist: specialist(0) -> coordinator(1) -> critic(2)."""
        llm = MockLLM()
        router_output = {
            "mode": "autonomous",
            "specialists": ["style"],
            "question_type": "general",
            "debug_specialists": [],
        }
        plan = await supervisor_agent(llm, router_output, "test", [])
        tasks = plan["tasks"]
        assert len(tasks) == 3
        assert tasks[0]["task_type"] == "specialist"
        assert tasks[1]["task_type"] == "coordinator_merge"
        assert tasks[1]["depends_on"] == [0]
        assert tasks[2]["task_type"] == "critic_review"
        assert tasks[2]["depends_on"] == [1]

    @pytest.mark.asyncio
    async def test_mode_preserved(self):
        llm = MockLLM()
        router_output = {
            "mode": "autonomous",
            "specialists": ["style"],
            "question_type": "general",
            "debug_specialists": [],
        }
        plan = await supervisor_agent(llm, router_output, "test", [])
        assert plan["mode"] == "autonomous"

    @pytest.mark.asyncio
    async def test_retrieved_context_passed_to_specialists(self):
        llm = MockLLM()
        router_output = {
            "mode": "autonomous",
            "specialists": ["style", "form"],
            "question_type": "general",
            "debug_specialists": [],
        }
        plan = await supervisor_agent(
            llm, router_output, "test", [],
            retrieved_context="fighter stats here",
        )
        specialist_tasks = [t for t in plan["tasks"] if t["task_type"] == "specialist"]
        for t in specialist_tasks:
            assert t["retrieved_context"] == "fighter stats here"
