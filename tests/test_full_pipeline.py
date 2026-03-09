# --- Ensure project root is on sys.path ---
import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
# ------------------------------------------

import pytest

from tests.mock_llm import MockLLM
from router_agent import router_agent
from supervisor import supervisor_agent
from orchestrator import orchestrator
from tools import TOOL_REGISTRY


@pytest.mark.asyncio
async def test_full_pipeline():
    llm = MockLLM()

    user_input = "Give me a full stylistic and strategic breakdown."
    history = []
    retrieved_context = ""

    # Router
    router_output = await router_agent(llm, user_input)
    assert isinstance(router_output, dict)
    assert "specialists" in router_output

    # Supervisor
    task_plan = await supervisor_agent(
        llm=llm,
        router_output=router_output,
        user_input=user_input,
        history=history,
        retrieved_context=retrieved_context,
    )
    assert isinstance(task_plan, dict)

    # Orchestrator (test mode)
    final_output = await orchestrator(
        llm=llm,
	prediction_llm=llm,
        tool_registry=TOOL_REGISTRY,
        task_plan=task_plan,
        test_mode=True,
    )

    # NEW EXPECTATION: orchestrator returns a STRING
    assert isinstance(final_output, str)
    assert len(final_output) > 0
