import os
import asyncio
import time
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH)

import logging
_logger = logging.getLogger("engine_entry")
_logger.debug(f"Loaded .env from: {ENV_PATH}")

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
# PIPELINE PROFILING
# ============================================================

from typing import Any, Callable, Dict, List, Optional
from data.input_validator import validate_user_input

# Store recent pipeline timings for /stats
_pipeline_timings: List[Dict[str, float]] = []
_MAX_TIMING_HISTORY = 20


def get_pipeline_timings() -> List[Dict]:
    """Return recent pipeline stage timings."""
    return list(_pipeline_timings)


# ============================================================
# HELPER: MINIMAL TASK PLAN FOR DEGRADED RETRY
# ============================================================


def _build_minimal_task_plan(original_plan: Dict[str, Any]) -> Dict[str, Any]:
    """Build a minimal task plan with only core four specialists."""
    core_four = {"style", "form", "sentiment", "weightcut"}
    minimal = dict(original_plan)
    if "tasks" in minimal:
        minimal["tasks"] = [
            t for t in minimal["tasks"]
            if t.get("task_type") != "specialist" or t.get("specialist") in core_four
            or t.get("task_type") in ("coordinator_merge", "critic_review")
        ]
        # Re-index task IDs preserving specialist → coordinator → critic order
        specialist_ids = []
        for i, t in enumerate(minimal["tasks"]):
            t["id"] = i
            if t.get("task_type") == "specialist":
                t["depends_on"] = []
                specialist_ids.append(i)
            elif t.get("task_type") in ("coordinator_merge", "critic_review"):
                t["depends_on"] = list(specialist_ids)
            else:
                t["depends_on"] = []
    return minimal


# ============================================================
# FULL MULTI-AGENT PIPELINE (ASYNC)
# ============================================================


async def _run_full_pipeline(
    user_input: str,
    on_stage: Optional[Callable[[str], None]] = None,
) -> str:
    try:
        return await asyncio.wait_for(
            _run_full_pipeline_impl(user_input, on_stage),
            timeout=300.0  # 5 minute max
        )
    except asyncio.TimeoutError:
        return "[ERROR] Analysis timed out after 5 minutes. Try a simpler query."


async def _run_full_pipeline_impl(
    user_input: str,
    on_stage: Optional[Callable[[str], None]] = None,
) -> str:
    # --- Input validation ---
    validation = validate_user_input(user_input)
    if not validation["valid"]:
        return f"[INPUT ERROR] {validation['error']}"
    user_input = validation["sanitized"]
    if validation.get("warnings"):
        _logger.warning(
            "Input warnings: %s", "; ".join(validation["warnings"])
        )

    history_pairs = load_history()
    history = [f"{role}: {content}" for role, content in history_pairs]
    episodic_memory_text = "\n".join(history) if history else ""

    stage_times: Dict[str, float] = {}
    _current_stage_start = [time.monotonic()]

    def _stage(name: str) -> None:
        now = time.monotonic()
        # Record elapsed time for previous stage
        if stage_times:
            last_key = list(stage_times.keys())[-1]
            stage_times[last_key] = round(now - _current_stage_start[0], 2)
        stage_times[name] = 0.0
        _current_stage_start[0] = now
        _logger.info(f"Pipeline stage: {name}")
        if on_stage:
            on_stage(name)

    pipeline_t0 = time.monotonic()

    # 1. Retrieval
    _stage("retrieval")
    try:
        retrieved_summary = await retrieval_agent(
            llm=ACTIVE_LLM,
            user_input=user_input,
            history=history_pairs,
            semantic_memory=None,
            episodic_memory=None,
        )
    except Exception as e:
        _logger.error(f"Retrieval failed: {e}")
        retrieved_summary = ""  # Continue without retrieval

    # 2. Router
    _stage("routing")
    try:
        routing = await router_agent(
            llm=ACTIVE_LLM,
            user_input=user_input,
            semantic_memory="",
            episodic_memory=episodic_memory_text,
        )
    except Exception as e:
        _logger.error(f"Router failed: {e}")
        # Fallback: use default full analysis routing
        routing = {"question_type": "who_wins", "specialists": ["style", "form", "sentiment", "weightcut", "metadata", "pace", "grappling", "damage"], "debug_specialists": []}

    # 3. Supervisor
    _stage("supervisor")
    task_plan = await supervisor_agent(
        llm=ACTIVE_LLM,
        router_output=routing,
        user_input=user_input,
        history=history,
        retrieved_context=retrieved_summary or "",
        test_mode=USE_TEST_MODE,
    )

    # 4. Orchestrator (uses GPT‑OSS 20B)
    _stage("orchestrator")
    try:
        result = await orchestrator(
            llm=LLM_ROUTING,                  # router/supervisor/specialists/critic
            prediction_llm=LLM_ORCHESTRATOR,  # orchestrator + prediction specialist
            tool_registry=TOOL_REGISTRY,
            task_plan=task_plan,
            test_mode=USE_TEST_MODE,
        )
    except Exception as e:
        _logger.error(f"Orchestrator failed: {e}. Retrying with reduced specialist set...")
        _stage("orchestrator_retry")
        try:
            # Build minimal task plan with core four only
            minimal_plan = _build_minimal_task_plan(task_plan)
            result = await orchestrator(
                llm=LLM_ROUTING,
                prediction_llm=LLM_ORCHESTRATOR,
                tool_registry=TOOL_REGISTRY,
                task_plan=minimal_plan,
                test_mode=USE_TEST_MODE,
            )
            result = "[DEGRADED MODE - some specialists unavailable]\n\n" + result
        except Exception as e2:
            _logger.error(f"Retry also failed: {e2}")
            result = f"[ERROR] Analysis pipeline failed. Primary error: {e}. Retry error: {e2}"

    # Finalize timing for last stage
    now = time.monotonic()
    if stage_times:
        last_key = list(stage_times.keys())[-1]
        stage_times[last_key] = round(now - _current_stage_start[0], 2)

    stage_times["total"] = round(now - pipeline_t0, 2)

    _logger.info(f"Pipeline timings: {stage_times}")

    # Store for /stats endpoint
    _pipeline_timings.append(stage_times)
    if len(_pipeline_timings) > _MAX_TIMING_HISTORY:
        _pipeline_timings.pop(0)

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
