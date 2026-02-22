# specialists/template/specialist_template_full.py

from typing import Iterable
from specialists.tool_runtime import (
    build_system_prompt,
    run_tool_loop,
)
from data.metadata import SpecialistOutput

BASE_PROMPT = """### Role

You are the **{{SPECIALIST_NAME}} specialist** in a modular, multi-agent UFC analysis system.
You think like a seasoned fight analyst and a high-level coach. You focus only on your domain
while staying aligned with the orchestrator’s overall plan.

---

### Responsibilities

- Provide clear, structured, domain-specific analysis.
- Use retrieved context only when relevant and reliable.
- Use memory (long-term + recent summaries) to maintain continuity.
- Avoid hallucinations; state uncertainty explicitly.
- Lock onto the fighters mentioned in the query and orchestrator context.
- Communicate like an analyst + coach.

---

### Fighter Lock

- Do not introduce new fighters or fictional matchups.
- If fighter identity is unclear, say so explicitly.
- Use fighters consistently; avoid mixing attributes.

---

### Memory Use

- Semantic memory: long-term fighter knowledge.
- Episodic memory: recent session summaries.

Use memory to:
- Avoid repetition.
- Maintain continuity.
- Refine understanding over time.

---

### Hallucination Guard

- Do not invent records, camps, coaches, or outcomes.
- Do not fabricate quotes, stats, or injuries.
- Distinguish facts, inferences, and speculation.

---

### Output Format (Hybrid Structured)

1. Summary
2. Key Factors
3. Tactical Insights
4. Actionable Recommendations
5. Domain-Specific Analysis

Sections must be concrete, fighter-locked, evidence-aware, and explicit about uncertainty.
"""

PROFILE = """You are a domain specialist in a modular UFC analytics engine.

- Retrieval-aware
- Memory-aware
- Hallucination-resistant
- Structured and readable
- Aligned with orchestrator and critic
"""

def _build_memory_block(retrieved_context, semantic_memory, episodic_memory, fighters, coordinator_output):
    sections = []

    if fighters:
        sections.append("=== Fighters ===\n" + str(fighters))

    if coordinator_output:
        sections.append("=== Coordinator Summary ===\n" + str(coordinator_output))

    if retrieved_context:
        sections.append("=== Retrieved Context ===\n" + str(retrieved_context))

    if semantic_memory:
        sections.append("=== Long-Term Fighter Knowledge ===\n" + str(semantic_memory))

    if episodic_memory:
        sections.append(
            "=== Recent Session Summaries ===\n" +
            "\n".join(map(str, episodic_memory))
        )

    return "\n\n".join(sections) if sections else ""


# ============================================================
# UNIVERSAL SPECIALIST SIGNATURE
# ============================================================
async def run_knowledge_specialist(
    llm=None,
    tool_registry=None,
    user_input=None,
    history=None,
    retrieved_context=None,
    semantic_memory=None,
    episodic_memory=None,
    context=None,
    coordinator_output=None,
    fighters=None,
):
    history = history or []
    semantic_memory = semantic_memory or {}
    episodic_memory = episodic_memory or []

    memory_block = _build_memory_block(
        retrieved_context=retrieved_context,
        semantic_memory=semantic_memory,
        episodic_memory=episodic_memory,
        fighters=fighters,
        coordinator_output=coordinator_output,
    )

    system_text = BASE_PROMPT + "\n\n" + memory_block

    tool_keys = tool_registry.keys() if tool_registry else []

    messages = build_system_prompt(
        system_text,
        PROFILE,
        retrieved_context,
        tool_keys,
    )

    for h in history:
        if isinstance(h, dict) and "role" in h and "content" in h:
            messages.append(h)
        else:
            messages.append({"role": "user", "content": str(h)})

    messages.append({"role": "user", "content": user_input or ""})

    # Test mode: no tools
    if not tool_registry:
        return SpecialistOutput.create(
            specialist="{{SPECIALIST_NAME}}",
            content=f"{{SPECIALIST_NAME}} executed (test mode).",
            reasoning="Test mode execution.",
            evidence=[],
            confidence=0.5,
        )

    return await run_tool_loop(llm, messages, tool_registry)
