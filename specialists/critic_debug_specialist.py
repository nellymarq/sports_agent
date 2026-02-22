# specialists/template/specialist_template_debug.py

from specialists.tool_runtime import (
    build_system_prompt,
    run_tool_loop,
)

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

async def run_critic_debug_specialist(
    llm,
    tool_registry,
    user_input,
    history,
    retrieved_context,
    semantic_memory=None,
    episodic_memory=None,
):
    sections = []

    if retrieved_context:
        sections.append("=== Retrieved Context ===\n" + str(retrieved_context))

    if semantic_memory:
        sections.append("=== Semantic Memory ===\n" + str(semantic_memory))

    if episodic_memory:
        sections.append("=== Episodic Memory ===\n" + "\n".join(map(str, episodic_memory)))

    debug_block = "\n\n".join(sections) if sections else ""

    system_text = BASE_PROMPT_DEBUG + "\n\n" + debug_block

    messages = build_system_prompt(
        system_text,
        PROFILE_DEBUG,
        retrieved_context,
        tool_registry.keys(),
    )

    for h in history:
        if isinstance(h, dict) and "role" in h and "content" in h:
            messages.append(h)
        else:
            messages.append({"role": "user", "content": str(h)})

    messages.append({"role": "user", "content": user_input})

    return await run_tool_loop(llm, messages, tool_registry)
