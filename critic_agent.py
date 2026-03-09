# critic_agent.py
# Chunked critic pipeline for large multi-specialist outputs, now metadata- and memory-aware

from typing import List, Optional
from logger import info, debug, error

from data.metadata import SpecialistOutput, FinalOutput

CRITIC_SYSTEM_PROMPT_BASE = """
You are the final-stage critic for a multi-specialist UFC analytics engine.
Your job is to refine clarity, cohesion, and flow without changing meaning.
Do not add new facts. Do not remove meaningful analysis.

CRITICAL: Subject Consistency
- The analysis must stay focused on the fighters specified in the user question.
- If the text appears to analyze a different fighter or matchup than requested,
  you must correct the narrative to match the requested fighters if possible,
  or clearly state that the content appears mismatched and cannot be trusted.

MEMORY CONTEXT
- You may be given long-term (semantic) and recent (episodic) memory.
- Use these only to correct obvious factual drift (e.g., wrong stance, wrong weight class),
  not to invent new analysis.
"""

CHUNK_SIZE = 3500


def chunk_text(text: str, size: int = CHUNK_SIZE) -> List[str]:
    return [text[i:i + size] for i in range(0, len(text), size)]


async def _critic_pass(
    llm,
    text: str,
    user_input: str,
    fighters,
    semantic_memory=None,
    episodic_memory=None,
) -> str:
    fighters_str = ", ".join(fighters) if fighters else "unknown"

    memory_context = ""
    if semantic_memory:
        memory_context += f"\n\nRelevant long-term fighter knowledge:\n{semantic_memory}"
    if episodic_memory:
        memory_context += "\n\nRecent episodic memory:\n" + "\n".join(episodic_memory)

    system_prompt = (
        CRITIC_SYSTEM_PROMPT_BASE
        + "\n\nUser question:\n"
        + user_input
        + "\n\nExtracted fighters:\n"
        + fighters_str
        + memory_context
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                "Refine the following analysis. Improve clarity, flow, and transitions "
                "without changing meaning. Ensure the subject matches the user question "
                "and extracted fighters where possible. If parts of the text clearly "
                "refer to different fighters or matchups, explicitly flag them as "
                "mismatched and unreliable:\n\n" + text
            ),
        },
    ]

    msg = await llm.chat(messages)

    content = (
        msg.get("content", "") if isinstance(msg, dict)
        else getattr(msg, "content", "")
    )
    return str(content).strip()


async def critic_review(
    llm,
    coordinator_output: SpecialistOutput,
    prediction_output: Optional[SpecialistOutput],
    user_input: str,
    fighters,
    semantic_memory=None,
    episodic_memory=None,
) -> FinalOutput:

    info("Critic agent invoked")

    if not coordinator_output.content or not coordinator_output.content.strip():
        error("Critic received empty coordinator output")
        return FinalOutput.create(
            content="No content available for final review.",
            merged_from=[coordinator_output.id],
            evidence=coordinator_output.evidence,
            confidence=0.0,
            lineage={"parents": [coordinator_output.id], "error": True},
            metadata={},
        )

    # Combine coordinator + prediction (if present)
    combined_text = coordinator_output.content

    if prediction_output and prediction_output.content:
        combined_text += (
            "\n\n\n=== STRUCTURED PREDICTION ===\n"
            + prediction_output.content.strip()
            + "\n=== END PREDICTION ===\n"
        )

    chunks = chunk_text(combined_text)
    debug(f"Critic: splitting into {len(chunks)} chunks")

    polished_chunks = []

    for idx, chunk in enumerate(chunks):
        info(f"Critic: refining chunk {idx + 1}/{len(chunks)}")
        try:
            refined = await _critic_pass(
                llm,
                chunk,
                user_input=user_input,
                fighters=fighters,
                semantic_memory=semantic_memory,
                episodic_memory=episodic_memory,
            )
            polished_chunks.append(refined)
        except Exception as e:
            error(f"Critic chunk {idx + 1} failed: {e}")
            polished_chunks.append(chunk)

    merged_polished = "\n\n".join(polished_chunks)

    info("Critic: running final cohesion pass")
    try:
        final_text = await _critic_pass(
            llm,
            merged_polished,
            user_input=user_input,
            fighters=fighters,
            semantic_memory=semantic_memory,
            episodic_memory=episodic_memory,
        )
    except Exception as e:
        error(f"Final critic pass failed: {e}")
        final_text = merged_polished

    parent_ids = [coordinator_output.id]
    all_evidence = list(coordinator_output.evidence)

    if prediction_output:
        parent_ids.append(prediction_output.id)
        all_evidence.extend(prediction_output.evidence)

    lineage = {
        "parents": parent_ids,
        "merge_strategy": "critic_refinement_memory_aware_with_prediction",
        "query": user_input,
        "fighters": fighters,
    }

    # Calibrate confidence from inputs rather than hardcoding
    coord_conf = coordinator_output.confidence or 0.5
    pred_conf = prediction_output.confidence if prediction_output else None
    if pred_conf is not None:
        # Weighted average: coordinator 40%, prediction 60%
        final_conf = 0.4 * coord_conf + 0.6 * pred_conf
    else:
        final_conf = coord_conf
    # Clamp to [0, 1]
    final_conf = max(0.0, min(1.0, final_conf))

    metadata = {
        "source": "critic",
        "chunk_count": len(chunks),
        "has_prediction": prediction_output is not None,
        "coordinator_confidence": coord_conf,
        "prediction_confidence": pred_conf,
    }

    return FinalOutput.create(
        content=final_text,
        merged_from=parent_ids,
        evidence=all_evidence,
        confidence=final_conf,
        lineage=lineage,
        metadata=metadata,
    )
