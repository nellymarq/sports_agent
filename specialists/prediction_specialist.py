# specialists/prediction_specialist.py

from typing import List, Dict, Any, Optional
from data.metadata import SpecialistOutput, Evidence
from specialists.tool_runtime import build_system_prompt, run_tool_loop


BASE_PROMPT = """### Role

You are the PREDICTION SPECIALIST in a modular, multi-agent UFC analysis system.
You think like a seasoned fight analyst and betting strategist with deep statistical grounding.

---

### Responsibilities

- Produce a STRUCTURED prediction with explicit win probabilities (must sum to 100%).
- Ground your prediction in the coordinator's merged analysis.
- Use retrieved context, unified event data, odds, and memory to calibrate confidence.
- Cross-reference specialist analyses to identify convergent and divergent signals.
- Be explicit about uncertainty — wider probability spreads for uncertain matchups.

---

### Fighter Lock

- You must lock onto the fighters provided in context.
- Do NOT introduce new fighters or fictional matchups.
- If no fighters are clearly identified, output a cautious 50/50 prediction with low confidence.

---

### Probability Calibration Guidelines

- 50-55%: True coin-flip, minimal edge identified
- 55-65%: Slight edge, one fighter has marginal advantages
- 65-75%: Clear favorite, significant stylistic or form advantages
- 75-85%: Strong favorite, dominant in most areas
- 85%+: Overwhelming favorite (rare — reserve for extreme mismatches)

---

### Output Format (STRICT — follow exactly)

You MUST output your prediction in this exact format:

**PREDICTED WINNER:** [Fighter Name]
**WIN PROBABILITY:** [X]% vs [Y]%
**CONFIDENCE TIER:** [Low / Medium / High / Very High]
**METHOD LEAN:** [KO/TKO / Submission / Decision / No strong lean]
**ROUND LEAN:** [Round X / Early (R1-2) / Late (R3-5) / Distance / No strong lean]

**KEY FACTORS:**
1. [Most important factor]
2. [Second factor]
3. [Third factor]

**RISK FACTORS:**
1. [Biggest risk to this prediction]
2. [Second risk]
3. [Third risk]

**EDGE BREAKDOWN:**
- Striking: [Fighter A / Fighter B / Even] — [brief why]
- Grappling: [Fighter A / Fighter B / Even] — [brief why]
- Cardio/Pace: [Fighter A / Fighter B / Even] — [brief why]
- Fight IQ: [Fighter A / Fighter B / Even] — [brief why]
- Durability: [Fighter A / Fighter B / Even] — [brief why]

**BETTING ANGLE:** [If odds data available, note if prediction diverges from market odds — potential value]
"""


PROFILE = """You are a prediction specialist in a modular UFC analytics engine.

- Coordinator-aware
- Retrieval-aware
- Memory-aware
- Hallucination-resistant
- Structured and readable
"""


def _build_context_block(
    coordinator_output: SpecialistOutput,
    fighters: List[str],
    retrieved_context: str,
    semantic_memory,
    episodic_memory,
    prediction_features: Optional[Dict[str, Any]] = None,
    event_metadata: Optional[Dict[str, Any]] = None,
) -> str:
    sections = []

    if fighters:
        sections.append("=== Fighters ===\n" + ", ".join(fighters))

    if coordinator_output and coordinator_output.content:
        sections.append("=== Coordinator Analysis ===\n" + coordinator_output.content)

    if event_metadata:
        sections.append("=== Unified Event Metadata ===\n" + str(event_metadata))

    if prediction_features:
        sections.append("=== Prediction Features (Structured) ===\n" + str(prediction_features))

    if retrieved_context:
        sections.append("=== Retrieved Context ===\n" + str(retrieved_context))

    if semantic_memory:
        sections.append("=== Long-Term Fighter Knowledge ===\n" + str(semantic_memory))

    if episodic_memory:
        sections.append(
            "=== Recent Session Summaries ===\n" + "\n".join(map(str, episodic_memory))
        )

    return "\n\n".join(sections) if sections else ""


async def run_prediction_specialist(
    llm=None,
    tool_registry: Optional[Dict[str, Any]] = None,
    coordinator_output: Optional[SpecialistOutput] = None,
    user_input: Optional[str] = None,
    fighters: Optional[List[str]] = None,
    semantic_memory=None,
    episodic_memory=None,
    retrieved_context: Optional[str] = None,
    prediction_features: Optional[Dict[str, Any]] = None,
    event_metadata: Optional[Dict[str, Any]] = None,
) -> SpecialistOutput:

    fighters = fighters or []
    semantic_memory = semantic_memory or {}
    episodic_memory = episodic_memory or []

    context_block = _build_context_block(
        coordinator_output=coordinator_output,
        fighters=fighters,
        retrieved_context=retrieved_context or "",
        semantic_memory=semantic_memory,
        episodic_memory=episodic_memory,
        prediction_features=prediction_features,
        event_metadata=event_metadata,
    )

    system_text = BASE_PROMPT + "\n\n" + context_block

    tool_keys = tool_registry.keys() if tool_registry else []

    messages = build_system_prompt(
        system_text,
        PROFILE,
        retrieved_context or "",
        tool_keys,
    )

    if user_input:
        messages.append({"role": "user", "content": user_input})

    # === TEST MODE (no tools) ===
    if not tool_registry:
        content = "Prediction specialist executed (test mode). No tools or live prediction generated."
        return SpecialistOutput.create(
            specialist="prediction",
            content=content,
            reasoning="Test mode execution.",
            evidence=[],
            confidence=0.5,
            metadata={"test_mode": True},
        )

    # === REAL MODE ===
    raw = await run_tool_loop(llm, messages, tool_registry)

    # --- SCHEMA ENFORCEMENT ---
    if isinstance(raw, SpecialistOutput):
        return raw

    if isinstance(raw, str):
        return SpecialistOutput.create(
            specialist="prediction",
            content=raw.strip(),
            reasoning=None,
            evidence=[],
            confidence=0.7,
            metadata={},
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
            specialist="prediction",
            content=str(raw.get("content", "")).strip(),
            reasoning=raw.get("reasoning"),
            evidence=evidence_list,
            confidence=float(raw.get("confidence", 0.7)),
            metadata=raw.get("metadata", {}) or {},
        )

    return SpecialistOutput.create(
        specialist="prediction",
        content=str(raw),
        reasoning=None,
        evidence=[],
        confidence=0.7,
        metadata={},
    )
