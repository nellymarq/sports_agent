# orchestrator.py
# Central orchestrator: executes specialist plan, merges, sends to critic, updates memory

import asyncio
from typing import Dict, Any, List

from logger import info, debug, error
from specialists import (
    run_style_specialist,
    run_form_specialist,
    run_sentiment_specialist,
    run_weightcut_specialist,
    run_general_specialist,
    run_metadata_specialist,
    run_pace_specialist,
    run_grappling_specialist,
    run_fight_iq_specialist,
    run_scramble_specialist,
    run_damage_specialist,
    run_gameplan_specialist,
    run_judging_specialist,
    run_knowledge_specialist,
)
from coordinator_agent import coordinator_merge
from critic_agent import critic_review
from memory_agent import (
    get_semantic,
    get_recent_episodic,
    summarize_and_store,
    add_semantic,
)
from fighter_utils import extract_fighter_name

SPECIALIST_REGISTRY = {
    "style": run_style_specialist,
    "form": run_form_specialist,
    "sentiment": run_sentiment_specialist,
    "weightcut": run_weightcut_specialist,
    "general": run_general_specialist,
    "metadata": run_metadata_specialist,
    "pace": run_pace_specialist,
    "grappling": run_grappling_specialist,
    "fight_iq": run_fight_iq_specialist,
    "scramble": run_scramble_specialist,
    "damage": run_damage_specialist,
    "gameplan": run_gameplan_specialist,
    "judging": run_judging_specialist,
    "knowledge": run_knowledge_specialist,
}


async def orchestrator(
    llm,
    tool_registry: Dict[str, Any],
    task_plan: Dict[str, Any],
    test_mode: bool = False,
) -> str:
    """
    Executes the supervisor's task plan:
    - runs the requested specialists
    - merges outputs via coordinator
    - sends merged report to critic for final polish
    - updates long-term memory
    """

    info("Orchestrator: starting execution")

    # ============================
    # TEST MODE: bypass everything
    # ============================
    if test_mode:
        return {
            "final": "[MOCK FINAL OUTPUT]",
            "specialists": {},
            "test_mode": True,
        }

    user_input = task_plan.get("user_input", "")
    history = task_plan.get("history", [])
    retrieved_context = task_plan.get("retrieved_context", "")
    tasks: List[Dict[str, Any]] = task_plan.get("tasks", [])

    # Memory retrieval
    fighter = extract_fighter_name(user_input)
    semantic_memory = get_semantic(fighter)
    episodic_memory = get_recent_episodic(5)

    specialist_outputs: List[str] = []

    for task in tasks:
        name = task.get("name")
        specialist_key = task.get("specialist")

        if not specialist_key:
            debug(f"Orchestrator: task '{name}' has no specialist key, skipping")
            continue

        specialist_fn = SPECIALIST_REGISTRY.get(specialist_key)
        if not specialist_fn:
            error(f"Orchestrator: unknown specialist '{specialist_key}' in task '{name}'")
            continue

        info(f"Orchestrator: running specialist '{specialist_key}' for task '{name}'")

        try:
            output = await specialist_fn(
                llm=llm,
                tool_registry=tool_registry,
                user_input=user_input,
                history=history,
                retrieved_context=retrieved_context,
                semantic_memory=semantic_memory,
                episodic_memory=episodic_memory,
            )
            specialist_outputs.append(output if isinstance(output, str) else str(output))

        except Exception as e:
            error(f"Orchestrator: specialist '{specialist_key}' failed: {e}")
            specialist_outputs.append(f"[ERROR from {specialist_key}: {e}]")

    merged = await coordinator_merge(
        llm,
        specialist_outputs,
        semantic_memory=semantic_memory,
        episodic_memory=episodic_memory,
    )

    try:
        final_output = await critic_review(llm, merged)
    except Exception as e:
        error(f"Critic error: {e}")
        final_output = f"Critic error: {e}"

    # Update memory after run
    await summarize_and_store(llm, "Summarize this UFC analysis session:", [final_output])

    if fighter != "unknown":
        await add_semantic(fighter, final_output)

    info("Orchestrator completed successfully")
    return final_output


async def run_agent_orchestrator(llm, tool_registry, task_plan):
    """Async entrypoint used by app.py"""
    return await orchestrator(llm, tool_registry, task_plan)


def run_orchestrator_sync(llm, tool_registry, task_plan):
    """Sync wrapper for CLI or non-async callers"""
    return asyncio.run(run_agent_orchestrator(llm, tool_registry, task_plan))
