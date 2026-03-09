# tests/test_full_debug_pipeline.py
# Full end‑to‑end integration test for core + debug specialists

import pytest

from orchestrator import orchestrator
from router_agent import router_agent
from tests.mock_llm import MockLLM


@pytest.mark.asyncio
async def test_full_debug_pipeline():
    llm = MockLLM()

    user_input = (
        "Explain routing and coordinator and critic and memory for this matchup: "
        "Volkanovski vs Makhachev. Full analysis."
    )

    # Step 1: Run router to get specialists
    routing_result = await router_agent(
        llm=llm,
        user_input=user_input,
        semantic_memory="",
        episodic_memory=[],
    )

    specialists = routing_result["specialists"]

    # Debug specialists must be routed
    for dbg in ["routing_debug", "coordinator_debug", "critic_debug", "memory_debug"]:
        assert dbg in specialists, f"{dbg} was not routed"

    # Step 2: Build task_plan using router output
    task_plan = {
        "user_input": user_input,
        "history": ["previous question 1", "previous question 2"],
        "retrieved_context": "",
        "tasks": [{"name": s, "specialist": s} for s in specialists],
    }

    # Step 3: Run orchestrator
    final_output = await orchestrator(
        llm=llm,
	prediction_llm=llm,
        tool_registry={},
        task_plan=task_plan,
        test_mode=False,
    )

    # Basic pipeline assertions
    assert isinstance(final_output, str)
    assert len(final_output.strip()) > 0

    # We only care that debug specialists ran and did NOT break the pipeline.
    # We do NOT require specific debug phrases in the final output, since
    # coordinator/critic may transform or omit them.
