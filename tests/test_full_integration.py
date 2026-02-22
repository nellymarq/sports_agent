# tests/test_full_integration.py

import os
import sys
from unittest.mock import patch, MagicMock
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tests.mock_llm import MockLLM
from router_agent import router_agent
from supervisor import supervisor_agent
from orchestrator import orchestrator
from tools import TOOL_REGISTRY


@pytest.mark.asyncio
async def test_full_integration_end_to_end():
    llm = MockLLM()

    user_input = (
        "Give me a full stylistic, strategic, and outcome breakdown for "
        "Alexander Volkanovski vs Islam Makhachev."
    )
    history = ["Previous question about Volkanovski", "Previous question about Makhachev"]
    retrieved_context = ""

    # ------------------ Router ------------------
    router_output = await router_agent(llm, user_input)
    specialists = router_output["specialists"]
    assert len(specialists) > 0
    for core in ["style", "form", "sentiment", "weightcut"]:
        assert core in specialists

    # ------------------ Supervisor ------------------
    task_plan = await supervisor_agent(
        llm=llm,
        router_output=router_output,
        user_input=user_input,
        history=history,
        retrieved_context=retrieved_context,
    )

    assert "tasks" in task_plan
    tasks = task_plan["tasks"]

    # Extract only tasks that actually have a specialist
    task_specialists = [t["specialist"] for t in tasks if "specialist" in t]

    # Every routed specialist must appear
    for s in specialists:
        assert s in task_specialists

    # Supervisor may add extra tasks
    assert len(tasks) >= len(specialists)

    # ------------------ Orchestrator ------------------
    with patch("orchestrator.MEMORY_STORE") as mock_memory_store, patch(
        "orchestrator.store_vectorized_memory"
    ) as mock_store_vectorized:

        mock_memory_store.write_short_term = MagicMock()
        mock_memory_store.write_long_term = MagicMock()
        mock_memory_store.write_evidence = MagicMock()
        mock_memory_store.write_specialist_note = MagicMock()

        final_output_str = await orchestrator(
            llm=llm,
            tool_registry=TOOL_REGISTRY,
            task_plan=task_plan,
            test_mode=False,  # prediction must run
        )

        # ------------------ Final Output ------------------
        assert isinstance(final_output_str, str)
        assert len(final_output_str.strip()) > 0

        # ------------------ Memory Writes ------------------
        assert mock_memory_store.write_short_term.called
        assert mock_memory_store.write_long_term.called
        assert mock_memory_store.write_specialist_note.called

        # ------------------ Vector Store Write ------------------
        assert mock_store_vectorized.called
        args, kwargs = mock_store_vectorized.call_args
        assert isinstance(args[0], str)

        metadata = kwargs.get("metadata", {})
        assert "primary_fighter" in metadata
        assert "fighters" in metadata
