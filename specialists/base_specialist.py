# specialists/base_specialist.py
# Shared base logic for all generated domain specialists.
# Each specialist only needs to provide its name — the rest is identical.

from specialists.tool_runtime import (
    build_system_prompt,
    run_tool_loop,
)
from data.metadata import SpecialistOutput, Evidence


_BASE_PROMPT_TEMPLATE = """You are the **{name} specialist** in a UFC analysis engine.

RULES:
- Only analyze the fighters named in the query. Do not reference other fighters or matchups.
- Never invent stats, records, or facts. If data is missing, omit that section — do not guess.
- Do not add meta-commentary, disclaimers, or quality warnings (no "mismatched", "unreliable", "insufficient data").
- Do not recommend tools or suggest waiting for more data. Analyze what you have.
- Use a technical analyst tone. Be concise and specific.

OUTPUT: Provide your {name} analysis in these sections (skip any with no data):
1. Summary (2-3 sentences)
2. Key Factors (specific advantages/disadvantages with numbers where available)
3. Tactical Insights (how this domain affects the fight outcome)
"""

_PROFILE = """You are a domain specialist in a modular UFC analytics engine.

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
            "=== Recent Session Summaries ===\n"
            + "\n".join(map(str, episodic_memory))
        )

    return "\n\n".join(sections) if sections else ""


def _coerce_to_specialist_output(raw, specialist_label: str) -> SpecialistOutput:
    """Convert any raw LLM output into a SpecialistOutput."""
    if isinstance(raw, SpecialistOutput):
        return raw

    if isinstance(raw, str):
        return SpecialistOutput.create(
            specialist=specialist_label,
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
            specialist=specialist_label,
            content=str(raw.get("content", "")).strip(),
            reasoning=raw.get("reasoning"),
            evidence=evidence_list,
            confidence=float(raw.get("confidence", 0.7)),
            metadata=raw.get("metadata", {}) or {},
        )

    return SpecialistOutput.create(
        specialist=specialist_label,
        content=str(raw),
        reasoning=None,
        evidence=[],
        confidence=0.7,
    )


def make_specialist(name: str):
    """
    Factory that returns an async specialist function with the universal signature.
    The only variable is the specialist *name* — all other logic is shared.
    """
    base_prompt = _BASE_PROMPT_TEMPLATE.format(name=name)
    label = f"{name} specialist"

    async def _run_specialist(
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

        system_text = base_prompt + "\n\n" + memory_block

        tool_keys = tool_registry.keys() if tool_registry else []

        messages = build_system_prompt(
            system_text,
            _PROFILE,
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
                specialist=label,
                content=f"{label} executed (test mode).",
                reasoning="Test mode execution.",
                evidence=[],
                confidence=0.5,
            )

        # === REAL MODE ===
        raw = await run_tool_loop(llm, messages, tool_registry)
        return _coerce_to_specialist_output(raw, label)

    _run_specialist.__name__ = f"run_{name.lower().replace(' ', '_')}_specialist"
    _run_specialist.__qualname__ = _run_specialist.__name__
    return _run_specialist
