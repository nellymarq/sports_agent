# coordinator.py
# LLM-powered coordinator with memory awareness

from logger import info, debug, error

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
"""


def _build_structured_block(specialist_outputs):
    """
    Convert raw specialist outputs into a structured block
    the LLM can reason about.
    """
    lines = ["Specialist Outputs:\n"]
    for idx, text in enumerate(specialist_outputs, start=1):
        lines.append(f"### SPECIALIST {idx} ###")
        lines.append(text.strip())
        lines.append("")
    return "\n".join(lines)


async def coordinator_merge(llm, specialist_outputs, semantic_memory: str, episodic_memory):
    """
    LLM-powered coordinator with memory:
    - Builds a structured prompt
    - Injects semantic + episodic memory
    - Requests section-aware merged analysis
    """

    info("Coordinator: merging specialist outputs")

    structured_block = _build_structured_block(specialist_outputs)

    memory_context = ""
    if semantic_memory:
        memory_context += f"\n\nRelevant long-term fighter knowledge:\n{semantic_memory}"
    if episodic_memory:
        memory_context += "\n\nRecent episodic memory:\n" + "\n".join(episodic_memory)

    system_prompt = COORDINATOR_SYSTEM_PROMPT + memory_context + "\n\n" + structured_block

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                "Merge all insights into a single UFC analysis. "
                "Follow this section order:\n"
                + "\n".join(f"- {s}" for s in SECTION_ORDER)
            ),
        },
    ]

    try:
        reply = await llm.chat(messages)
        merged = reply.content.strip()
        debug(f"Coordinator merged output preview: {merged[:300]}...")
        return merged

    except Exception as e:
        error(f"Coordinator LLM error: {e}")
        return "Coordinator failed to merge specialist outputs."
