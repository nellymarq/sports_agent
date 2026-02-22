# coordinator_agent.py
# Metadata-aware coordinator with memory awareness, subject consistency,
# confidence-aware merging, AND optional debug-section output.

from typing import List
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
You are the COORDINATOR AGENT for a multi-specialist UFC analytics engine.

Your responsibilities:
- Merge all specialist outputs into a single, cohesive analysis.
- Identify overlapping insights and combine them smoothly.
- Preserve nuance from each specialist.
- Avoid repetition.
- Organize the final answer into clear, analyst-style sections.
- Maintain a professional, technical tone.
- Do NOT invent new facts.
- Do NOT contradict specialist outputs.
- Do NOT remove meaningful analysis.
- Produce a clean narrative, not JSON.

CRITICAL: Subject Consistency
- The user question and extracted fighter names define the subject of analysis.
- Ensure the final analysis focuses on those fighters only.
- If specialist outputs drift to other fighters, realign the narrative to the correct fighters
  or explicitly note that some content appears mismatched and should be ignored.

CONFIDENCE & CONTRADICTIONS
- Each specialist has a confidence score.
- When specialists disagree, prefer higher-confidence, better-supported analysis.
- If contradictions remain, explicitly flag them as analyst-level uncertainty.
"""


def _build_structured_block(specialist_outputs: List[SpecialistOutput]) -> str:
    lines = ["Specialist Outputs (with confidence and notes):\n"]
    for idx, s in enumerate(specialist_outputs, start=1):
        lines.append(f"### SPECIALIST {idx} | {s.specialist} | conf={s.confidence:.2f} ###")
        if s.metadata:
            lines.append(f"[metadata]: {s.metadata}")
        lines.append(s.content.strip())
        lines.append("")
    return "\n".join(lines)


def _compute_overall_confidence(specialist_outputs: List[SpecialistOutput]) -> float:
    if not specialist_outputs:
        return 0.0
    total = sum(max(0.0, min(1.0, s.confidence or 0.0)) for s in specialist_outputs)
    return total / len(specialist_outputs)


async def coordinator_merge(
    llm,
    specialist_outputs: List[SpecialistOutput],
    semantic_memory: str,
    episodic_memory,
    user_input: str,
    fighters,
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

    # Build structured block for LLM
    structured_block = _build_structured_block(specialist_outputs)

    # Memory context
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

        # Safe extraction for MockLLM compatibility
        merged = (
            reply.get("content", "") if isinstance(reply, dict)
            else getattr(reply, "content", "")
        ).strip()

        debug(f"Coordinator merged output preview: {merged[:300]}...")

        # === NEW: Append debug specialist outputs ===
        debug_outputs = [
            s for s in specialist_outputs
            if s.specialist in (
                "routing_debug",
                "coordinator_debug",
                "critic_debug",
                "memory_debug",
            )
        ]

        if debug_outputs:
            merged += "\n\n\n=== DEBUG OUTPUT ===\n"
            for s in debug_outputs:
                merged += f"\n\n--- {s.specialist.upper()} ---\n{s.content.strip()}\n"

        # Build lineage + evidence
        parent_ids = [s.id for s in specialist_outputs]
        all_evidence: List[Evidence] = []
        for s in specialist_outputs:
            all_evidence.extend(s.evidence)

        lineage = {
            "parents": parent_ids,
            "specialist": "coordinator",
            "merge_strategy": "sectioned_merge_confidence_aware_with_debug_append",
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
                "debug_appended": bool(debug_outputs),
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
