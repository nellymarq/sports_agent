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
