# coordinator_agent.py
# Metadata-aware coordinator with memory awareness, subject consistency,
# confidence-aware merging, AND enhanced diagnostics tightly integrated with router output.

from typing import List, Dict, Any
from logger import info, debug, error

from data.metadata import SpecialistOutput, Evidence

SECTION_ORDER = [
    "Overview",
    "Style & Form",
    "Pace & Pressure",
    "Grappling & Scramble Dynamics",
    "Fight IQ & Gameplan",
    "Damage & Durability",
    "Judging Tendencies",
    "Metadata Snapshot",
    "Summary Takeaways",
]

COORDINATOR_SYSTEM_PROMPT = """
You merge all specialist outputs into a single, cohesive UFC analysis optimized for prediction accuracy.

Your responsibilities:
- Combine insights smoothly and avoid repetition.
- Preserve nuance from each specialist.
- Maintain a technical, analyst-style tone.
- Never invent new facts.
- Never contradict specialist outputs without explicit justification.
- Realign any off-topic content to the correct fighters.
- Explicitly flag contradictions or uncertainty.
- Produce a clean narrative, not JSON.

Subject Consistency:
- The user question and extracted fighter names define the subject.
- If specialists drift, correct the narrative or note mismatches.

Confidence-Weighted Merging:
- Specialists are ordered by confidence score (highest first).
- HIGH WEIGHT specialists (conf >= 0.8) should anchor the narrative.
- MEDIUM WEIGHT specialists (0.5-0.8) provide supporting detail.
- LOW WEIGHT specialists (< 0.5) should be noted but treated with caution.
- When specialists contradict, prefer the higher-confidence source and explicitly note the disagreement.
- If multiple high-confidence specialists converge on a conclusion, emphasize this convergence.

Convergence & Conflict Detection:
- Count how many specialists favor Fighter A vs Fighter B in their analysis.
- If 70%+ of specialists converge on one fighter, state this convergence clearly.
- If specialists are split, present both sides fairly and note the disagreement.
- Flag any specialist whose analysis contradicts the majority.

Prediction Optimization:
- Your merged analysis will be fed to a prediction specialist.
- Ensure you clearly surface: stylistic advantages/disadvantages, recent form trajectory, durability concerns, pace dynamics, and any significant edges.
- Be specific about measurable advantages (reach, output volume, takedown defense %).
- Include any pre-fetched fighter stats (record, SLpM, accuracy, recent fights) from context.
- If odds/implied probabilities are available, include them.

CRITICAL: End your analysis with a brief "EDGE SUMMARY" section that lists:
- Which fighter has the edge in each domain (striking, grappling, cardio, fight IQ, durability)
- An overall lean (which fighter has more edges)
This summary is essential for the prediction specialist.
"""


def _build_structured_block(specialist_outputs: List[SpecialistOutput]) -> str:
    # Sort by confidence descending so higher-confidence analyses appear first
    sorted_outputs = sorted(specialist_outputs, key=lambda s: s.confidence, reverse=True)

    # Compute convergence stats
    high_conf = [s for s in sorted_outputs if s.confidence >= 0.8]
    med_conf = [s for s in sorted_outputs if 0.5 <= s.confidence < 0.8]
    low_conf = [s for s in sorted_outputs if s.confidence < 0.5]

    lines = [
        f"Specialist Outputs ({len(sorted_outputs)} total: "
        f"{len(high_conf)} high-conf, {len(med_conf)} medium, {len(low_conf)} low):\n"
    ]

    for idx, s in enumerate(sorted_outputs, start=1):
        weight_label = "HIGH WEIGHT" if s.confidence >= 0.8 else "MEDIUM WEIGHT" if s.confidence >= 0.5 else "LOW WEIGHT"
        lines.append(f"### SPECIALIST {idx} | {s.specialist} | conf={s.confidence:.2f} | {weight_label} ###")
        if s.evidence:
            lines.append(f"[evidence count]: {len(s.evidence)}")
        lines.append(s.content.strip())
        lines.append("")
    return "\n".join(lines)


def _compute_overall_confidence(specialist_outputs: List[SpecialistOutput]) -> float:
    if not specialist_outputs:
        return 0.0
    total = sum(max(0.0, min(1.0, s.confidence or 0.0)) for s in specialist_outputs)
    return total / len(specialist_outputs)


def _build_diagnostics_block(
    specialist_outputs: List[SpecialistOutput],
    router_output: Dict[str, Any],
) -> str:
    """
    Enhanced diagnostics:
    - Which specialists ran
    - Confidence scores
    - Error flags
    - Evidence counts
    - Router question type
    - Router-selected specialists
    - Router debug specialists
    """
    lines = ["=== PIPELINE DIAGNOSTICS ==="]

    # Router-level diagnostics
    qtype = router_output.get("question_type", "unknown")
    selected = router_output.get("specialists", [])
    debug_specs = router_output.get("debug_specialists", [])

    lines.append(f"Router question_type: {qtype}")
    lines.append(f"Router selected specialists: {selected}")
    lines.append(f"Router debug specialists: {debug_specs}")
    lines.append("")

    # Specialist-level diagnostics
    for s in specialist_outputs:
        err = bool(s.metadata.get("error") or s.lineage.get("error"))
        lines.append(
            f"- specialist={s.specialist} | conf={s.confidence:.2f} | "
            f"error={err} | evidence_count={len(s.evidence)}"
        )

    return "\n".join(lines)


async def coordinator_merge(
    llm,
    specialist_outputs: List[SpecialistOutput],
    semantic_memory: str,
    episodic_memory,
    user_input: str,
    fighters,
    router_output: Dict[str, Any] = None,   # NEW: router output injected for diagnostics
) -> SpecialistOutput:

    info("Coordinator: merging specialist outputs")

    if not specialist_outputs:
        error("Coordinator: no specialist outputs provided")
        return SpecialistOutput.create(
            specialist="coordinator",
            content="No specialist outputs available to merge.",
            reasoning=None,
            evidence=[],
            confidence=0.0,
            lineage={"parents": [], "specialist": "coordinator", "error": True},
            metadata={},
        )

    router_output = router_output or {}

    structured_block = _build_structured_block(specialist_outputs)

    memory_context = ""
    if semantic_memory:
        memory_context += f"\n\nRelevant long-term fighter knowledge:\n{semantic_memory}"
    if episodic_memory:
        memory_context += "\n\nRecent episodic memory:\n" + "\n".join(episodic_memory)

    fighters_str = ", ".join(fighters) if fighters else "unknown"
    overall_conf = _compute_overall_confidence(specialist_outputs)

    system_prompt = (
        COORDINATOR_SYSTEM_PROMPT
        + "\n\nUser question:\n"
        + user_input
        + "\n\nExtracted fighters:\n"
        + fighters_str
        + f"\n\nOverall specialist confidence (rough average): {overall_conf:.2f}"
        + memory_context
        + "\n\n"
        + structured_block
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                "Merge all insights into a single UFC analysis. "
                "Follow this section order:\n"
                + "\n".join(f"- {s}" for s in SECTION_ORDER)
                + "\n\nIf specialists contradict each other, prefer higher-confidence analysis "
                "and explicitly note remaining uncertainties."
            ),
        },
    ]

    try:
        reply = await llm.chat(messages)

        merged = (
            reply.get("content", "") if isinstance(reply, dict)
            else getattr(reply, "content", "")
        ).strip()

        debug(f"Coordinator merged output preview: {merged[:300]}...")

        # Build diagnostics
        diagnostics_block = _build_diagnostics_block(
            specialist_outputs=specialist_outputs,
            router_output=router_output,
        )

        # Append diagnostics only if debug specialists were requested
        debug_specs = router_output.get("debug_specialists", [])
        if debug_specs:
            merged += "\n\n\n=== DEBUG OUTPUT ===\n"
            merged += diagnostics_block + "\n"

            # Append explicit debug specialists
            for s in specialist_outputs:
                if s.specialist in debug_specs:
                    merged += f"\n\n--- {s.specialist.upper()} ---\n{s.content.strip()}\n"

        # Build lineage + evidence
        parent_ids = [s.id for s in specialist_outputs]
        all_evidence: List[Evidence] = []
        for s in specialist_outputs:
            all_evidence.extend(s.evidence)

        lineage = {
            "parents": parent_ids,
            "specialist": "coordinator",
            "merge_strategy": "sectioned_merge_confidence_aware_with_router_diagnostics",
            "query": user_input,
            "fighters": fighters,
        }

        return SpecialistOutput.create(
            specialist="coordinator",
            content=merged,
            reasoning=None,
            evidence=all_evidence,
            confidence=overall_conf,
            lineage=lineage,
            metadata={
                "section_order": SECTION_ORDER,
                "overall_specialist_confidence": overall_conf,
                "specialist_count": len(specialist_outputs),
                "debug_appended": bool(debug_specs),
            },
        )

    except Exception as e:
        error(f"Coordinator LLM error: {e}")
        return SpecialistOutput.create(
            specialist="coordinator",
            content="Coordinator failed to merge specialist outputs.",
            reasoning=None,
            evidence=[],
            confidence=0.0,
            lineage={"parents": [], "specialist": "coordinator", "error": True},
            metadata={"error_message": str(e)},
        )
