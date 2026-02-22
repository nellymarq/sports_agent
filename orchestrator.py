# orchestrator.py — final consolidated version with inline memory writes
# Compatible with router_agent + supervisor_agent task graph and tests.

import asyncio
from typing import Dict, Any, List

from logger import info, debug, error

# === SPECIALISTS ===
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
    run_routing_debug_specialist,
    run_coordinator_debug_specialist,
    run_critic_debug_specialist,
    run_memory_debug_specialist,
)
from specialists.prediction_specialist import run_prediction_specialist

# === AGENTS ===
from coordinator_agent import coordinator_merge
from critic_agent import critic_review

# === MEMORY ===
from memory_agent import (
    get_semantic,
    get_recent_episodic,
    summarize_and_store,
    add_semantic,
    store_vectorized_memory,
)
from memory.memory_api import MemoryStore

# === DATA + RETRIEVAL ===
from fighter_utils import extract_fighters
from retrieval_pipeline import get_retrieved_context
from data.metadata import Evidence, SpecialistOutput, FinalOutput

# === MEMORY STORE INSTANCE (patchable in tests) ===
MEMORY_STORE = MemoryStore()

# === SPECIALIST REGISTRY ===
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
    "routing_debug": run_routing_debug_specialist,
    "coordinator_debug": run_coordinator_debug_specialist,
    "critic_debug": run_critic_debug_specialist,
    "memory_debug": run_memory_debug_specialist,
}

# =====================================================================
#                           TASK VALIDATION
# =====================================================================

def _validate_task_plan(task_plan: Dict[str, Any]) -> List[str]:
    """
    Validate that all *specialist* tasks reference known specialists.
    Non-specialist tasks (coordinator/critic) are allowed and ignored here.
    """
    errors = []
    if "tasks" not in task_plan:
        errors.append("Task plan missing 'tasks' key.")
        return errors

    for t in task_plan["tasks"]:
        if t.get("task_type") == "specialist":
            if "specialist" not in t:
                errors.append(f"Specialist task missing 'specialist': {t}")
            elif t["specialist"] not in SPECIALIST_REGISTRY:
                errors.append(f"Unknown specialist: {t['specialist']}")
    return errors

# =====================================================================
#                           SPECIALIST RUNNER
# =====================================================================

async def _run_single_specialist(
    specialist_key: str,
    name: str,
    llm,
    tool_registry: Dict[str, Any],
    user_input: str,
    history,
    retrieved_context: str,
    semantic_memory,
    episodic_memory,
    context: Dict[str, Any],
) -> SpecialistOutput:

    specialist_fn = SPECIALIST_REGISTRY.get(specialist_key)
    if not specialist_fn:
        return SpecialistOutput.create(
            specialist=specialist_key,
            content=f"[ERROR] Unknown specialist '{specialist_key}'",
            reasoning=None,
            evidence=[],
            confidence=0.0,
            lineage={"specialist": specialist_key, "error": True},
            metadata={"error_message": "unknown_specialist"},
        )

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

        # === SCHEMA ENFORCEMENT ===
        if isinstance(output, SpecialistOutput):
            return output

        if isinstance(output, str):
            return SpecialistOutput.create(
                specialist=specialist_key,
                content=output.strip(),
                reasoning=None,
                evidence=[],
                confidence=0.7,
                lineage={"specialist": specialist_key, "task_name": name},
                metadata={},
            )

        if isinstance(output, dict):
            evidence_list = []
            for ev in output.get("evidence", []) or []:
                evidence_list.append(
                    Evidence.create(
                        source=ev.get("source", "unknown"),
                        content=ev.get("content", ""),
                        confidence=float(ev.get("confidence", 0.7)),
                        provenance=ev.get("provenance", {}),
                    )
                )

            return SpecialistOutput.create(
                specialist=specialist_key,
                content=str(output.get("content", "")).strip(),
                reasoning=output.get("reasoning"),
                evidence=evidence_list,
                confidence=float(output.get("confidence", 0.7)),
                lineage={"specialist": specialist_key, "task_name": name},
                metadata=output.get("metadata", {}) or {},
            )

        return SpecialistOutput.create(
            specialist=specialist_key,
            content=str(output),
            reasoning=None,
            evidence=[],
            confidence=0.7,
            lineage={"specialist": specialist_key, "task_name": name},
            metadata={},
        )

    except Exception as e:
        error(f"Specialist '{specialist_key}' failed: {e}")
        return SpecialistOutput.create(
            specialist=specialist_key,
            content=f"[ERROR] Specialist '{specialist_key}' failed.",
            reasoning=None,
            evidence=[],
            confidence=0.0,
            lineage={"specialist": specialist_key, "error": True},
            metadata={"error_message": str(e)},
        )

# =====================================================================
#                           ORCHESTRATOR
# =====================================================================

async def orchestrator(llm, tool_registry, task_plan, test_mode: bool = False) -> str:
    info("Orchestrator: starting execution")

    # === VALIDATE TASK PLAN ===
    validation_errors = _validate_task_plan(task_plan)
    if validation_errors:
        return "\n".join(f"[TASK PLAN ERROR] {e}" for e in validation_errors)

    user_input = task_plan.get("user_input", "")
    history = task_plan.get("history", [])
    retrieved_context = task_plan.get("retrieved_context", "")
    tasks = task_plan.get("tasks", [])

    # Only run specialist tasks; coordinator/critic tasks are handled internally
    specialist_tasks = [
        t for t in tasks
        if t.get("task_type") == "specialist" and "specialist" in t
    ]

    fighters, primary_fighter = extract_fighters(user_input)

    # === STRUCTURED MEMORY ===
    semantic_memory = get_semantic(primary_fighter) or {}
    episodic_memory = get_recent_episodic(5) or []

    # === RETRIEVAL ===
    if not retrieved_context:
        retrieved_context = get_retrieved_context(
            user_input=user_input,
            fighter=primary_fighter if primary_fighter != "unknown" else "",
        )

    context = {
        "history_length": len(history),
        "semantic_memory_present": bool(semantic_memory),
        "episodic_count": len(episodic_memory),
        "retrieved_context_present": bool(retrieved_context),
        "fighters": fighters,
        "primary_fighter": primary_fighter,
    }

    # === TEST MODE SHORT-CIRCUIT ===
    if test_mode and not specialist_tasks:
        return "[TEST MODE] No tasks provided."

    # === SPECIALIST EXECUTION ===
    async def _run_task(t):
        return await _run_single_specialist(
            specialist_key=t["specialist"],
            name=t.get("name", ""),
            llm=llm,
            tool_registry=tool_registry,
            user_input=user_input,
            history=history,
            retrieved_context=retrieved_context,
            semantic_memory=semantic_memory,
            episodic_memory=episodic_memory,
            context=context,
        )

    specialist_outputs = await asyncio.gather(*[_run_task(t) for t in specialist_tasks])

    # === COORDINATOR ===
    coordinator_output = await coordinator_merge(
        llm=llm,
        specialist_outputs=specialist_outputs,
        semantic_memory=semantic_memory,
        episodic_memory=episodic_memory,
        user_input=user_input,
        fighters=fighters,
    )

    # ENFORCE SpecialistOutput TYPE (defensive)
    if isinstance(coordinator_output, str):
        coordinator_output = SpecialistOutput.create(
            specialist="coordinator",
            content=coordinator_output,
            reasoning=None,
            evidence=[],
            confidence=0.7,
            lineage={"source": "coordinator_fallback"},
            metadata={},
        )

    # === DEBUG MODE DETECTION ===
    debug_mode_active = any(
        s.specialist
        in (
            "routing_debug",
            "coordinator_debug",
            "critic_debug",
            "memory_debug",
        )
        for s in specialist_outputs
    )

    # === PREDICTION ===
    if test_mode or debug_mode_active:
        prediction_output = None
    else:
        prediction_output = await run_prediction_specialist(
            llm=llm,
            coordinator_output=coordinator_output,
            user_input=user_input,
            fighters=fighters,
            semantic_memory=semantic_memory,
            episodic_memory=episodic_memory,
            retrieved_context=retrieved_context,
        )

    # === CRITIC ===
    final_output_meta = await critic_review(
        llm=llm,
        coordinator_output=coordinator_output,
        prediction_output=prediction_output,
        user_input=user_input,
        fighters=fighters,
        semantic_memory=semantic_memory,
        episodic_memory=episodic_memory,
    )

    # ENFORCE FinalOutput TYPE (defensive)
    if isinstance(final_output_meta, str):
        final_output_meta = FinalOutput.create(
            content=final_output_meta,
            merged_from=[],
            evidence=[],
            confidence=0.7,
            lineage={"source": "critic_fallback"},
            metadata={},
        )

    final_output_str = final_output_meta.content

    # =====================================================================
    #                           INLINE MEMORY WRITES
    # =====================================================================

    MEMORY_STORE.write_short_term(
        {
            "type": "interaction",
            "query": user_input,
            "final_output_id": final_output_meta.id,
            "specialist_output_ids": [s.id for s in specialist_outputs],
            "confidence": final_output_meta.confidence,
            "context": context,
        }
    )

    MEMORY_STORE.write_long_term(
        {
            "type": "summary",
            "query": user_input,
            "final_output_id": final_output_meta.id,
            "content": final_output_meta.content,
            "confidence": final_output_meta.confidence,
            "lineage": final_output_meta.lineage,
        }
    )

    for ev in final_output_meta.evidence:
        MEMORY_STORE.write_evidence(ev)

    for s in specialist_outputs:
        MEMORY_STORE.write_specialist_note(
            s.specialist,
            {
                "type": "specialist_run",
                "query": user_input,
                "output_id": s.id,
                "content": s.content,
                "confidence": s.confidence,
                "lineage": s.lineage,
                "metadata": s.metadata,
            },
        )

    # =====================================================================

    await summarize_and_store(llm, "Summarize this UFC analysis session:", [final_output_str])

    if primary_fighter != "unknown":
        await add_semantic(primary_fighter, final_output_str)

    try:
        store_vectorized_memory(
            final_output_str,
            metadata={
                "primary_fighter": primary_fighter or "unknown",
                "fighters": fighters,
                "source": "final_output",
            },
        )
    except Exception as e:
        error(f"Vector store write failed: {e}")

    return final_output_str

# =====================================================================
#                           SYNC WRAPPERS
# =====================================================================

async def run_agent_orchestrator(llm, tool_registry, task_plan, test_mode: bool = False):
    return await orchestrator(llm, tool_registry, task_plan, test_mode=test_mode)

def run_orchestrator_sync(llm, tool_registry, task_plan, test_mode: bool = False):
    return asyncio.run(run_agent_orchestrator(llm, tool_registry, task_plan, test_mode=test_mode))
