# orchestrator.py — DAG-based execution with inline memory writes
# Compatible with router_agent + supervisor_agent task graph and tests.

import asyncio
import time
import traceback
from typing import Dict, Any, List, Set, Optional
import re

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
    run_clinch_specialist,
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
from event_utils import get_event_fighters
from data.metadata import Evidence, SpecialistOutput, FinalOutput

# === UNIFIED EVENT PIPELINE ===
from pipeline.event_pipeline import EventPipeline

# === PRE-FETCH ===
from tools.prefetch import prefetch_fighter_stats, format_prefetched_stats, build_fighter_comparison

# === DOMAIN PROMPTS ===
from specialists.domain_prompts import get_domain_guidance

# === ANALYTICS PAYLOADS ===
try:
    from data.specialist_payloads import compute_analytics_bundle, format_specialist_payload, format_analytics_summary
except ImportError:
    compute_analytics_bundle = None
    format_specialist_payload = None
    format_analytics_summary = None

# === PREDICTION TRACKING ===
from prediction_tracker import record_prediction

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
    "clinch": run_clinch_specialist,
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
#                           EVENT RESOLUTION
# =====================================================================

def _resolve_event_id_from_text(text: str) -> Optional[str]:
    """
    Best-effort: extract 'UFC 313' -> 'ufc_313' style event_id.
    """
    t = (text or "").lower()
    m = re.search(r"ufc[\s_\-]*([0-9]{2,4})", t)
    if not m:
        return None
    num = m.group(1)
    return f"ufc_{num}"

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

    _spec_start = time.monotonic()

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

    # Inject domain-specific guidance into retrieved context
    domain_guidance = get_domain_guidance(specialist_key)
    enriched_context = retrieved_context
    if domain_guidance:
        enriched_context = domain_guidance + "\n\n" + (retrieved_context or "")

    # Inject domain-specific analytics payload
    analytics_bundle = context.get("analytics_bundle", {})
    if analytics_bundle and format_specialist_payload:
        try:
            specialist_payload = format_specialist_payload(analytics_bundle, specialist_key)
            if specialist_payload:
                enriched_context = specialist_payload + "\n\n" + enriched_context
        except Exception as _e:
            debug(f"Specialist payload injection failed for {specialist_key}: {_e}")

    # Inject relevant specialist memory notes from previous analyses
    try:
        specialist_notes = context.get("specialist_notes", {})
        spec_note = specialist_notes.get(specialist_key, "")
        if spec_note:
            enriched_context = f"=== Previous Analysis Memory ===\n{spec_note}\n\n" + enriched_context
    except Exception as _e:
        debug(f"Specialist memory injection failed for {specialist_key}: {_e}")

    try:
        output = await asyncio.wait_for(
            specialist_fn(
                llm=llm,
                tool_registry=tool_registry,
                user_input=user_input,
                history=history,
                retrieved_context=enriched_context,
                semantic_memory=semantic_memory,
                episodic_memory=episodic_memory,
                context=context,
            ),
            timeout=60.0,  # 60s max per specialist
        )

        # === SCHEMA ENFORCEMENT ===
        _elapsed = round(time.monotonic() - _spec_start, 3)

        if isinstance(output, SpecialistOutput):
            output.metadata = {**(output.metadata or {}), "execution_time_s": _elapsed}
            return output

        if isinstance(output, str):
            return SpecialistOutput.create(
                specialist=specialist_key,
                content=output.strip(),
                reasoning=None,
                evidence=[],
                confidence=0.7,
                lineage={"specialist": specialist_key, "task_name": name},
                metadata={"execution_time_s": _elapsed},
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

            meta = output.get("metadata", {}) or {}
            meta["execution_time_s"] = _elapsed
            return SpecialistOutput.create(
                specialist=specialist_key,
                content=str(output.get("content", "")).strip(),
                reasoning=output.get("reasoning"),
                evidence=evidence_list,
                confidence=float(output.get("confidence", 0.7)),
                lineage={"specialist": specialist_key, "task_name": name},
                metadata=meta,
            )

        return SpecialistOutput.create(
            specialist=specialist_key,
            content=str(output),
            reasoning=None,
            evidence=[],
            confidence=0.7,
            lineage={"specialist": specialist_key, "task_name": name},
            metadata={"execution_time_s": _elapsed},
        )

    except Exception as e:
        _elapsed = round(time.monotonic() - _spec_start, 3)
        error(f"Specialist '{specialist_key}' failed: {e}")
        return SpecialistOutput.create(
            specialist=specialist_key,
            content=f"[ERROR] Specialist '{specialist_key}' failed.",
            reasoning=None,
            evidence=[],
            confidence=0.0,
            lineage={"specialist": specialist_key, "error": True},
            metadata={"error_message": str(e), "error_type": type(e).__name__, "error_traceback": traceback.format_exc(), "execution_time_s": _elapsed},
        )

# =====================================================================
#                           ORCHESTRATOR (DAG)
# =====================================================================

async def orchestrator(
    llm,
    tool_registry,
    task_plan,
    test_mode: bool = False,
    prediction_llm=None,
) -> str:
    """
    Backward-compatible signature:
    - old calls: orchestrator(llm, tool_registry, task_plan, test_mode=True/False)
    - new calls: orchestrator(llm, tool_registry, task_plan, test_mode, prediction_llm=...)
    """
    _t_start = time.monotonic()
    info("Orchestrator: starting execution (DAG mode)")

    # Default: use same LLM for prediction if none provided (tests, doctor)
    if prediction_llm is None:
        prediction_llm = llm

    # === VALIDATE TASK PLAN ===
    validation_errors = _validate_task_plan(task_plan)
    if validation_errors:
        return "\n".join(f"[TASK PLAN ERROR] {e}" for e in validation_errors)

    user_input = task_plan.get("user_input", "")
    history = task_plan.get("history", [])
    retrieved_context = task_plan.get("retrieved_context", "")
    tasks = task_plan.get("tasks", [])

    # Early test-mode short-circuit
    if test_mode and not tasks:
        return "[TEST MODE] No tasks provided."

    # Ensure tasks have ids and depends_on
    for idx, t in enumerate(tasks):
        t.setdefault("id", idx)
        t.setdefault("depends_on", [])

    tasks_by_id: Dict[int, Dict[str, Any]] = {t["id"]: t for t in tasks}
    completed: Set[int] = set()

    fighters, primary_fighter = extract_fighters(user_input)

    # === UNIFIED EVENT PIPELINE ===
    pipeline = EventPipeline()
    unified_event = None
    unified_metadata_payload = None
    unified_prediction_payload = None

    try:
        event_id = _resolve_event_id_from_text(user_input)
        if event_id:
            unified_event = await pipeline.load_unified_event(event_id)
        else:
            unified_event = await pipeline.load_unified_next_event()

        if unified_event:
            unified_metadata_payload = await pipeline.build_metadata_payload(unified_event.id)
            unified_prediction_payload = await pipeline.build_prediction_payload(unified_event.id)
    except Exception as e:
        error(f"Unified event pipeline failed (non-fatal): {e}")
        unified_event = None
        unified_metadata_payload = None
        unified_prediction_payload = None

    # Derive fighters from event data if user mentioned a UFC event but no fighter names
    if not fighters:
        event_id = _resolve_event_id_from_text(user_input)
        if event_id:
            event_fighters = get_event_fighters(event_id)
            if event_fighters:
                fighters = event_fighters
                primary_fighter = fighters[0]
                info(f"Orchestrator: derived fighters from event {event_id}: {fighters}")

    # Fallback: derive from unified event object
    if unified_event and not fighters:
        try:
            ev_dict = unified_event.to_dict()
        except Exception as _exc:
            debug(f"Event dict conversion failed: {_exc}")
            ev_dict = None

        if isinstance(ev_dict, dict):
            main_ev = ev_dict.get("main_event")
            # Handle dict format: {"fighters": [{"name": "A"}, {"name": "B"}]}
            if isinstance(main_ev, dict):
                me_fighters = main_ev.get("fighters", [])
                derived = []
                for f in me_fighters:
                    if isinstance(f, dict):
                        derived.append(f.get("name", ""))
                    elif isinstance(f, str):
                        derived.append(f)
                derived = [n for n in derived if n]
                if len(derived) >= 2:
                    fighters = derived
                    primary_fighter = derived[0]
                    info(f"Orchestrator: derived fighters from unified event: {fighters}")
            # Handle string format: "Fighter A vs Fighter B"
            elif isinstance(main_ev, str) and "vs" in main_ev.lower():
                text = main_ev.replace("VS.", "vs.").replace("VS", "vs")
                parts = text.split("vs")
                if len(parts) == 2:
                    left = parts[0].strip()
                    right = parts[1].strip()
                    derived = [n for n in (left, right) if n]
                    if derived:
                        fighters = derived
                        primary_fighter = derived[0]

    # === PRE-FETCH FIGHTER STATS ===
    prefetched_stats = {}
    prefetched_context = ""
    if fighters and not test_mode:
        try:
            prefetched_stats = prefetch_fighter_stats(fighters)
            prefetched_context = format_prefetched_stats(prefetched_stats)
            comparison = build_fighter_comparison(prefetched_stats)
            if comparison:
                prefetched_context = comparison + "\n\n" + prefetched_context
        except Exception as e:
            error(f"Fighter stats prefetch failed (non-fatal): {e}")

    # === PRE-COMPUTE ANALYTICS BUNDLE ===
    analytics_bundle = {}
    if prefetched_stats and len(fighters) >= 2:
        try:
            if compute_analytics_bundle and format_analytics_summary:
                analytics_bundle = compute_analytics_bundle(prefetched_stats, fighters)
                analytics_summary = format_analytics_summary(analytics_bundle)
                if analytics_summary:
                    prefetched_context = analytics_summary + "\n\n" + prefetched_context
        except Exception as e:
            error(f"Analytics bundle computation failed (non-fatal): {e}")

    # === STRUCTURED MEMORY ===
    # Load semantic memory for ALL identified fighters (not just primary)
    semantic_parts = []
    for fighter in fighters:
        try:
            fighter_mem = get_semantic(fighter)
            if fighter_mem:
                semantic_parts.append(f"=== {fighter} ===\n{fighter_mem}")
        except Exception as _exc:
            debug(f"Non-fatal: {_exc}")
    semantic_memory = "\n\n".join(semantic_parts) if semantic_parts else ""

    episodic_memory = get_recent_episodic(5) or []

    # Also load any specialist notes from previous analyses
    specialist_notes = {}
    for spec_key in ["style", "form", "damage", "grappling", "pace"]:
        try:
            notes = MEMORY_STORE.get_specialist_history(spec_key)
            if notes:
                recent = notes[-1] if notes else None
                if recent and isinstance(recent, dict):
                    specialist_notes[spec_key] = recent.get("content", "")[:500]
        except Exception as _exc:
            debug(f"Non-fatal: {_exc}")

    # === RETRIEVAL ===
    if not retrieved_context:
        retrieved_context = get_retrieved_context(
            user_input=user_input,
            fighter=primary_fighter if primary_fighter != "unknown" else "",
            fighters=fighters,
        )

    # Prepend pre-fetched stats to retrieved context
    if prefetched_context:
        retrieved_context = prefetched_context + "\n\n" + retrieved_context

    context = {
        "history_length": len(history),
        "semantic_memory_present": bool(semantic_memory),
        "episodic_count": len(episodic_memory),
        "retrieved_context_present": bool(retrieved_context),
        "fighters": fighters,
        "primary_fighter": primary_fighter,
        "unified_event": unified_event.to_dict() if unified_event else None,
        "unified_metadata": unified_metadata_payload,
        "unified_prediction": unified_prediction_payload,
        "prefetched_stats": prefetched_stats,
        "analytics_bundle": analytics_bundle,
        "specialist_notes": specialist_notes,
    }

    # === DAG EXECUTION STATE ===
    specialist_outputs: List[SpecialistOutput] = []
    coordinator_output: SpecialistOutput | None = None
    prediction_output: SpecialistOutput | None = None
    final_output_meta: FinalOutput | None = None

    # Router metadata (for diagnostics in coordinator)
    router_output = {
        "question_type": task_plan.get("question_type"),
        "specialists": task_plan.get("specialists", []),
        "debug_specialists": task_plan.get("debug_specialists", []),
    }

    # === DAG EXECUTION LOOP (PARALLEL) ===
    while len(completed) < len(tasks):
        # Collect all tasks whose dependencies are satisfied
        ready = []
        for t in tasks:
            tid = t["id"]
            if tid in completed:
                continue
            deps = t.get("depends_on") or []
            if all(d in completed for d in deps):
                ready.append(t)

        if not ready:
            error("Orchestrator: DAG execution stalled (cyclic or unsatisfiable dependencies).")
            break

        # Separate by type for batch execution
        specialist_batch = [t for t in ready if t.get("task_type") == "specialist"]
        other_tasks = [t for t in ready if t.get("task_type") != "specialist"]

        # Run all ready specialists in parallel
        if specialist_batch:
            _t_batch = time.monotonic()
            info(f"Orchestrator: launching {len(specialist_batch)} specialists in parallel")

            async def _run_spec(t):
                # Enrich user_input with fighter names for specialist context
                enriched_input = user_input
                if fighters and "vs" not in user_input.lower():
                    enriched_input = f"{user_input}\n\n[Fighters: {', '.join(fighters)}]"

                return t["id"], await _run_single_specialist(
                    specialist_key=t["specialist"],
                    name=t.get("name", t["specialist"]),
                    llm=llm,
                    tool_registry=tool_registry,
                    user_input=enriched_input,
                    history=history,
                    retrieved_context=retrieved_context,
                    semantic_memory=semantic_memory,
                    episodic_memory=episodic_memory,
                    context=context,
                )

            results = await asyncio.gather(
                *[_run_spec(t) for t in specialist_batch],
                return_exceptions=True,
            )

            for i, result in enumerate(results):
                t = specialist_batch[i]
                tid = t["id"]
                if isinstance(result, Exception):
                    error(f"Specialist '{t['specialist']}' raised exception: {result}")
                    specialist_outputs.append(SpecialistOutput.create(
                        specialist=t["specialist"],
                        content=f"[ERROR] Specialist '{t['specialist']}' failed.",
                        reasoning=None,
                        evidence=[],
                        confidence=0.0,
                        lineage={"specialist": t["specialist"], "error": True},
                        metadata={"error_message": str(result)},
                    ))
                else:
                    _, output = result
                    specialist_outputs.append(output)
                completed.add(tid)

            info(f"Orchestrator: specialist batch completed in {time.monotonic() - _t_batch:.2f}s")

        # Run non-specialist tasks (coordinator, critic) sequentially
        for t in other_tasks:
            tid = t["id"]
            task_type = t.get("task_type")

            # ---------------- COORDINATOR TASK ----------------
            if task_type == "coordinator_merge":
                # Build analytics summary for coordinator grounding
                _coord_analytics = None
                if analytics_bundle and format_analytics_summary:
                    try:
                        _coord_analytics = format_analytics_summary(analytics_bundle)
                    except Exception as _exc:
                        debug(f"Non-fatal: {_exc}")

                coordinator_output = await coordinator_merge(
                    llm=llm,
                    specialist_outputs=specialist_outputs,
                    semantic_memory=semantic_memory,
                    episodic_memory=episodic_memory,
                    user_input=user_input,
                    fighters=fighters,
                    router_output=router_output,
                    analytics_summary=_coord_analytics,
                )

                # Enforce SpecialistOutput type
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

                # Analytics summary is now passed to coordinator LLM via analytics_summary param

                # DEBUG MODE DETECTION
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

                # PREDICTION (only once coordinator is ready)
                if not test_mode and not debug_mode_active:
                    # Build prediction features, merging unified prediction with analytics bundle
                    prediction_features = context.get("unified_prediction")
                    if analytics_bundle:
                        try:
                            if prediction_features and isinstance(prediction_features, dict):
                                prediction_features = {**prediction_features, "analytics_bundle": analytics_bundle}
                            elif analytics_bundle:
                                prediction_features = {"analytics_bundle": analytics_bundle}
                        except Exception as _exc:
                            debug(f"Analytics merge into prediction failed: {_exc}")

                    prediction_output = await run_prediction_specialist(
                        llm=prediction_llm,
                        tool_registry=tool_registry,
                        coordinator_output=coordinator_output,
                        user_input=user_input,
                        fighters=fighters,
                        semantic_memory=semantic_memory,
                        episodic_memory=episodic_memory,
                        retrieved_context=retrieved_context,
                        prediction_features=prediction_features,
                        event_metadata=context.get("unified_metadata"),
                    )

                    # --- SCHEMA ENFORCEMENT FOR PREDICTION ---
                    if isinstance(prediction_output, str):
                        prediction_output = SpecialistOutput.create(
                            specialist="prediction",
                            content=prediction_output.strip(),
                            reasoning=None,
                            evidence=[],
                            confidence=0.7,
                            lineage={
                                "specialist": "prediction",
                                "source": "orchestrator_wrap",
                            },
                            metadata={},
                        )
                    elif isinstance(prediction_output, dict):
                        evidence_list = []
                        for ev in prediction_output.get("evidence", []) or []:
                            evidence_list.append(
                                Evidence.create(
                                    source=ev.get("source", "unknown"),
                                    content=ev.get("content", ""),
                                    confidence=float(ev.get("confidence", 0.7)),
                                    provenance=ev.get("provenance", {}),
                                )
                            )

                        prediction_output = SpecialistOutput.create(
                            specialist="prediction",
                            content=str(prediction_output.get("content", "")).strip(),
                            reasoning=prediction_output.get("reasoning"),
                            evidence=evidence_list,
                            confidence=float(prediction_output.get("confidence", 0.7)),
                            lineage={
                                "specialist": "prediction",
                                "source": "orchestrator_wrap",
                            },
                            metadata=prediction_output.get("metadata", {}) or {},
                        )
                    elif prediction_output is not None and not isinstance(
                        prediction_output, SpecialistOutput
                    ):
                        prediction_output = SpecialistOutput.create(
                            specialist="prediction",
                            content=str(prediction_output),
                            reasoning=None,
                            evidence=[],
                            confidence=0.7,
                            lineage={
                                "specialist": "prediction",
                                "source": "orchestrator_wrap",
                            },
                            metadata={},
                        )

                # Track prediction for calibration
                if prediction_output and isinstance(prediction_output, SpecialistOutput):
                    pred_meta = prediction_output.metadata or {}
                    if pred_meta.get("predicted_winner") and len(fighters) >= 2:
                        try:
                            event_id = _resolve_event_id_from_text(user_input) or "unknown"
                            record_prediction(
                                event_id=event_id,
                                fighter_a=fighters[0],
                                fighter_b=fighters[1] if len(fighters) > 1 else "unknown",
                                predicted_winner=pred_meta["predicted_winner"],
                                win_probability=pred_meta.get("prob_fighter_a", 50) / 100.0 if pred_meta.get("prob_fighter_a", 50) > 1 else pred_meta.get("prob_fighter_a", 0.5),
                                confidence_tier=pred_meta.get("confidence_tier", ""),
                                method_lean=pred_meta.get("method_lean", ""),
                            )
                        except Exception as e:
                            error(f"Prediction tracking failed (non-fatal): {e}")

                completed.add(tid)
                continue

            # ---------------- CRITIC TASK ----------------
            if task_type == "critic_review":
                final_output_meta = await critic_review(
                    llm=llm,
                    coordinator_output=coordinator_output,
                    prediction_output=prediction_output,
                    user_input=user_input,
                    fighters=fighters,
                    semantic_memory=semantic_memory,
                    episodic_memory=episodic_memory,
                )

                # Enforce FinalOutput type
                if isinstance(final_output_meta, str):
                    final_output_meta = FinalOutput.create(
                        content=final_output_meta,
                        merged_from=[],
                        evidence=[],
                        confidence=0.7,
                        lineage={"source": "critic_fallback"},
                        metadata={},
                    )

                completed.add(tid)
                continue

            # Unknown task types
            error(f"Orchestrator: unknown task_type '{task_type}' for task id={tid}")
            completed.add(tid)

    # Fallback: if critic didn't run, use coordinator output
    if final_output_meta is None and coordinator_output is not None:
        final_output_meta = FinalOutput.create(
            content=coordinator_output.content,
            merged_from=[coordinator_output.id],
            evidence=coordinator_output.evidence,
            confidence=coordinator_output.confidence,
            lineage={"source": "coordinator_only", "parents": [coordinator_output.id]},
            metadata={},
        )

    if final_output_meta is None:
        return "[ERROR] Orchestrator failed to produce a final output."

    _total_elapsed = round(time.monotonic() - _t_start, 2)
    info(f"Orchestrator: pipeline completed in {_total_elapsed:.2f}s")

    # === SPECIALIST TIMING SUMMARY ===
    specialist_timings = {}
    for s in specialist_outputs:
        t_s = (s.metadata or {}).get("execution_time_s")
        if t_s is not None:
            specialist_timings[s.specialist] = t_s
    if specialist_timings:
        slowest = max(specialist_timings, key=specialist_timings.get)
        fastest = min(specialist_timings, key=specialist_timings.get)
        info(
            f"Orchestrator: specialist timings — "
            f"slowest={slowest} ({specialist_timings[slowest]}s), "
            f"fastest={fastest} ({specialist_timings[fastest]}s), "
            f"total_pipeline={_total_elapsed}s"
        )

    # Attach timing to final output metadata
    if final_output_meta.metadata is None:
        final_output_meta.metadata = {}
    final_output_meta.metadata["specialist_timings"] = specialist_timings
    final_output_meta.metadata["pipeline_time_s"] = _total_elapsed

    final_output_str = final_output_meta.content

    # =====================================================================
    #                           MEMORY MAINTENANCE
    # =====================================================================

    # Decay stale long-term memories (older than 30 days)
    MEMORY_STORE.decay_long_term(threshold_seconds=30 * 24 * 3600)
    MEMORY_STORE.dedupe_long_term()
    MEMORY_STORE.cap_long_term(max_entries=500)
    MEMORY_STORE.decay_short_term(threshold_seconds=86400)

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

    # Write structured analytics memory for future retrieval
    if analytics_bundle and fighters:
        try:
            sim_winner = ""
            sim_data = analytics_bundle.get("simulation", {})
            win_prob = sim_data.get("win_probability", {}) if sim_data else {}
            if win_prob:
                sim_winner = list(win_prob.keys())[0]
            MEMORY_STORE.write_long_term({
                "type": "analytics_snapshot",
                "fighters": fighters,
                "matchup_type": analytics_bundle.get("matchup", {}).get("matchup_type", ""),
                "simulation_winner": sim_winner,
                "confidence": final_output_meta.confidence,
            })
        except Exception as _exc:
            debug(f"Non-fatal: {_exc}")

    # =====================================================================

    await summarize_and_store(llm, "Summarize this UFC analysis session:", [final_output_str])

    # Store semantic memory for all fighters (not just primary)
    for fighter in fighters:
        if fighter and fighter != "unknown":
            try:
                await add_semantic(fighter, final_output_str)
            except Exception as _exc:
                debug(f"Non-fatal: {_exc}")
    if not fighters and primary_fighter != "unknown":
        try:
            await add_semantic(primary_fighter, final_output_str)
        except Exception as _exc:
            debug(f"Non-fatal: {_exc}")

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

async def run_agent_orchestrator(
    llm,
    tool_registry,
    task_plan,
    test_mode: bool = False,
    prediction_llm=None,
):
    return await orchestrator(
        llm=llm,
        tool_registry=tool_registry,
        task_plan=task_plan,
        test_mode=test_mode,
        prediction_llm=prediction_llm,
    )


def run_orchestrator_sync(
    llm,
    tool_registry,
    task_plan,
    test_mode: bool = False,
    prediction_llm=None,
):
    return asyncio.run(
        run_agent_orchestrator(
            llm=llm,
            tool_registry=tool_registry,
            task_plan=task_plan,
            test_mode=test_mode,
            prediction_llm=prediction_llm,
        )
    )
