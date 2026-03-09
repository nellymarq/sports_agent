import os
import asyncio
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH)

print("DEBUG (engine_entry): Loaded .env from:", ENV_PATH)
print("DEBUG (engine_entry): GROQ_API_KEY =", os.getenv("GROQ_API_KEY"))

# -------------------------------------------------
# Import engine components
# -------------------------------------------------
from llm import GroqLLM
from tests.mock_llm import MockLLM

from tools import TOOL_REGISTRY
from orchestrator import orchestrator
from router_agent import router_agent
from supervisor import supervisor_agent
from retrieval_agent import retrieval_agent
from state_manager import (
    clear_task_queue,
    load_history,
    append_to_history,
)

# ============================================================
# CONFIG: LIVE vs TEST
# ============================================================

USE_TEST_MODE = False

# Two-model hybrid setup:
# - Routing, supervisor, specialists, critic → 8B Instant
# - Orchestrator (final synthesis) → GPT‑OSS 20B
LLM_ROUTING = GroqLLM(model="llama-3.1-8b-instant", max_tokens=1536)
LLM_ORCHESTRATOR = GroqLLM(model="gpt-oss-20b", max_tokens=2048)

if USE_TEST_MODE:
    ACTIVE_LLM = MockLLM()
else:
    ACTIVE_LLM = LLM_ROUTING


# ============================================================
# FULL MULTI-AGENT PIPELINE (ASYNC)
# ============================================================

async def _run_full_pipeline(user_input: str) -> str:
    history_pairs = load_history()
    history = [f"{role}: {content}" for role, content in history_pairs]
    episodic_memory_text = "\n".join(history) if history else ""

    # 1. Retrieval
    retrieved_summary = await retrieval_agent(
        llm=ACTIVE_LLM,
        user_input=user_input,
        history=history_pairs,
        semantic_memory=None,
        episodic_memory=None,
    )

    # 2. Router
    routing = await router_agent(
        llm=ACTIVE_LLM,
        user_input=user_input,
        semantic_memory="",
        episodic_memory=episodic_memory_text,
    )

    # 3. Supervisor
    task_plan = await supervisor_agent(
        llm=ACTIVE_LLM,
        router_output=routing,
        user_input=user_input,
        history=history,
        retrieved_context=retrieved_summary or "",
        test_mode=USE_TEST_MODE,
    )

    # 4. Orchestrator (uses GPT‑OSS 20B)
    result = await orchestrator(
        llm=LLM_ROUTING,                  # router/supervisor/specialists/critic
        prediction_llm=LLM_ORCHESTRATOR,  # orchestrator + prediction specialist
        tool_registry=TOOL_REGISTRY,
        task_plan=task_plan,
        test_mode=USE_TEST_MODE,
    )

    append_to_history("assistant", result)
    return result


# ============================================================
# SYNC WRAPPER (legacy)
# ============================================================

def run_orchestrator_sync(user_input: str) -> str:
    clear_task_queue()
    return asyncio.run(_run_full_pipeline(user_input))


# ============================================================
# CLI ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m engine_entry \"your question here\"")
        sys.exit(1)

    user_input = " ".join(sys.argv[1:])
    output = run_orchestrator_sync(user_input)
    print("\n=== ENGINE OUTPUT ===\n")
    print(output)
