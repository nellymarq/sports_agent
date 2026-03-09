# specialists/template/specialist_template_debug.py

from specialists.tool_runtime import (
    build_system_prompt,
    run_tool_loop,
)
from data.metadata import SpecialistOutput, Evidence

BASE_PROMPT_DEBUG = """### Role

You are a DEBUG SPECIALIST in a modular UFC analytics engine.

You do not analyze fights. You inspect system behavior:
- Routing
- Coordination
- Critic behavior
- Memory usage

You surface anomalies, contradictions, and missing information.

---

### Responsibilities

- Inspect context, memory, and intermediate outputs.
- Identify routing anomalies, coordination issues, critic inconsistencies, memory gaps.
- Summarize what the system appears to be doing.
- Suggest concrete debugging steps.

---

### Use of Retrieved Context and Memory

Treat all inputs as debug artifacts.
Quote or summarize them only to explain system behavior.
Flag contradictions or suspicious patterns.

---

### Output Format (Diagnostics)

1. High-Level Diagnostic Summary
2. Notable Signals
3. Potential Issues
4. Suggested Debugging Steps
5. Risk Assessment
"""

PROFILE_DEBUG = """You are a diagnostic specialist focused on internal system behavior.

- You do not analyze fights.
- You inspect routing, coordination, critic behavior, and memory usage.
- You surface anomalies and contradictions.
- You speak clearly and concretely.
"""

async def FUNCTION_NAME(
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

    sections = []

    if retrieved_context:
        sections.append("=== Retrieved Context ===\n" + str(retrieved_context))

    if semantic_memory:
        sections.append("=== Semantic Memory ===\n" + str(semantic_memory))

    if episodic_memory:
        sections.append("=== Episodic Memory ===\n" + "\n".join(map(str, episodic_memory)))

    if coordinator_output:
        sections.append("=== Coordinator Output ===\n" + str(coordinator_output))

    if fighters:
        sections.append("=== Extracted Fighters ===\n" + str(fighters))

    debug_block = "\n\n".join(sections) if sections else ""

    system_text = BASE_PROMPT_DEBUG + "\n\n" + debug_block

    tool_keys = tool_registry.keys() if tool_registry else []

    messages = build_system_prompt(
        system_text,
        PROFILE_DEBUG,
        retrieved_context,
        tool_keys,
    )

    for h in history:
        if isinstance(h, dict) and "role" in h and "content" in h:
            messages.append(h)
        else:
            messages.append({"role": "user", "content": str(h)})

    messages.append({"role": "user", "content": user_input or ""})

    # === TEST MODE ===
    if not tool_registry:
        return SpecialistOutput.create(
            specialist="DEBUG SPECIALIST",
            content="Debug specialist executed (test mode).",
            reasoning="Test mode execution.",
            evidence=[],
            confidence=0.5,
        )

    # === REAL MODE ===
    raw = await run_tool_loop(llm, messages, tool_registry)

    # --- SCHEMA ENFORCEMENT ---
    if isinstance(raw, SpecialistOutput):
        return raw

    if isinstance(raw, str):
        return SpecialistOutput.create(
            specialist="DEBUG SPECIALIST",
            content=raw.strip(),
            reasoning=None,
            evidence=[],
            confidence=0.7,
        )

    if isinstance(raw, dict):
        evidence_list = []
        for ev in raw.get("evidence", []) or []:
            evidence_list.append(
                Evidence.create(
                    source=ev.get("source", "unknown"),
                    content=ev.get("content", ""),
                    confidence=float(ev.get("confidence", 0.7)),
                    provenance=ev.get("provenance", {}),
                )
            )

        return SpecialistOutput.create(
            specialist="DEBUG SPECIALIST",
            content=str(raw.get("content", "")).strip(),
            reasoning=raw.get("reasoning"),
            evidence=evidence_list,
            confidence=float(raw.get("confidence", 0.7)),
            metadata=raw.get("metadata", {}) or {},
        )

    return SpecialistOutput.create(
        specialist="DEBUG SPECIALIST",
        content=str(raw),
        reasoning=None,
        evidence=[],
        confidence=0.7,
    )
