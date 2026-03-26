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
    "Clinch & Cage Control",
    "Grappling & Scramble Dynamics",
    "Fight IQ & Gameplan",
    "Damage & Durability",
    "Judging Tendencies",
    "Aging & Career Phase",
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

Conflict Resolution Protocol:
- When two HIGH-confidence specialists contradict, do NOT simply note the disagreement.
  Instead, analyze WHY they disagree — they may be evaluating different dimensions
  (e.g., striking edge vs grappling edge). Synthesize the specific reasoning from each.
- When a specialist's conclusion conflicts with their own evidence (e.g., "Fighter A
  has reach advantage" but "Fighter B controls range"), flag this internal inconsistency.
- Give extra weight to specialists whose analysis is grounded in specific statistics
  vs those making general assessments.

Evidence Quality Tiering:
- Tag each analytical claim with its evidence tier:
  [STATS] — backed by specific fighter statistics (SLpM, accuracy, record)
  [SIMULATION] — backed by Monte Carlo simulation results
  [ANALYSIS] — analyst inference from patterns and expertise
- Prioritize [STATS] and [SIMULATION] evidence over [ANALYSIS] in conflict resolution.
- When building the EDGE SUMMARY, note the evidence tier for each edge.

Prediction Optimization:
- Your merged analysis will be fed to a prediction specialist.
- Ensure you clearly surface: stylistic advantages/disadvantages, recent form trajectory, durability concerns, pace dynamics, and any significant edges.
- Be specific about measurable advantages (reach, output volume, takedown defense %).
- Include any pre-fetched fighter stats (record, SLpM, accuracy, recent fights) from context.
- If odds/implied probabilities are available, include them.

CRITICAL: End your analysis with an "EDGE SUMMARY" section in this exact format:

EDGE SUMMARY:
- Striking: [Fighter Name or Even] — [brief reason]
- Grappling: [Fighter Name or Even] — [brief reason]
- Cardio/Pace: [Fighter Name or Even] — [brief reason]
- Fight IQ: [Fighter Name or Even] — [brief reason]
- Durability: [Fighter Name or Even] — [brief reason]
- Experience: [Fighter Name or Even] — [brief reason]

OVERALL LEAN: [Fighter Name] ([X] of [Y] edges)
CONVERGENCE: [X] of [Y] specialists lean toward [Fighter Name] ([Z]% confidence-weighted)
UPSET FLAGS: [List any upset conditions detected, or "None"]

This structured format is essential for the prediction specialist. Use exact fighter names, not pronouns.
"""


def _detect_fighter_leans(specialist_outputs: List[SpecialistOutput], fighters: List[str]) -> Dict[str, Any]:
    """
    Detect which fighter each specialist leans toward by analyzing content.
    Uses confidence-weighted voting: higher-confidence specialists count more.
    Returns convergence data for the coordinator.
    """
    if not fighters or len(fighters) < 2:
        return {"convergence_pct": 0, "consensus_fighter": "unknown", "leans": {}}

    f_a = fighters[0].lower()
    f_b = fighters[1].lower()
    leans: Dict[str, str] = {}
    lean_details: Dict[str, Dict[str, Any]] = {}

    for s in specialist_outputs:
        content = s.content.lower()
        edge_keywords = ["advantage", "edge", "superior", "better", "stronger", "favors", "wins"]
        concern_keywords = ["concern", "weakness", "vulnerable", "struggles", "poor", "limited"]

        # Positive edge signals (fighter mentioned near edge keywords)
        a_pos = sum(
            1 for kw in edge_keywords
            if f_a in content and kw in content[max(0, content.find(f_a) - 100):content.find(f_a) + 100]
        )
        b_pos = sum(
            1 for kw in edge_keywords
            if f_b in content and kw in content[max(0, content.find(f_b) - 100):content.find(f_b) + 100]
        )

        # Negative concern signals (fighter mentioned near concern keywords)
        a_neg = sum(
            1 for kw in concern_keywords
            if f_a in content and kw in content[max(0, content.find(f_a) - 100):content.find(f_a) + 100]
        )
        b_neg = sum(
            1 for kw in concern_keywords
            if f_b in content and kw in content[max(0, content.find(f_b) - 100):content.find(f_b) + 100]
        )

        # Net score: positive mentions minus negative mentions for opponent
        a_score = a_pos + b_neg
        b_score = b_pos + a_neg

        if a_score > b_score:
            leans[s.specialist] = fighters[0]
        elif b_score > a_score:
            leans[s.specialist] = fighters[1]
        else:
            leans[s.specialist] = "neutral"

        lean_details[s.specialist] = {
            "lean": leans[s.specialist],
            "confidence": s.confidence,
            "weight": s.confidence,  # confidence IS the vote weight
            "a_signals": a_score,
            "b_signals": b_score,
        }

    # Unweighted counts
    a_count = sum(1 for v in leans.values() if v == fighters[0])
    b_count = sum(1 for v in leans.values() if v == fighters[1])
    neutral_count = sum(1 for v in leans.values() if v == "neutral")
    total = len(leans) or 1

    # Confidence-weighted vote totals
    a_weighted = sum(
        d["confidence"] for d in lean_details.values() if d["lean"] == fighters[0]
    )
    b_weighted = sum(
        d["confidence"] for d in lean_details.values() if d["lean"] == fighters[1]
    )
    total_weight = a_weighted + b_weighted or 1.0

    # Weighted convergence
    weighted_pct = round(max(a_weighted, b_weighted) / total_weight * 100, 1)

    return {
        "leans": leans,
        "lean_details": lean_details,
        "fighter_a_count": a_count,
        "fighter_b_count": b_count,
        "neutral_count": neutral_count,
        "convergence_pct": round(max(a_count, b_count) / total * 100, 1),
        "weighted_convergence_pct": weighted_pct,
        "fighter_a_weighted": round(a_weighted, 2),
        "fighter_b_weighted": round(b_weighted, 2),
        "consensus_fighter": fighters[0] if a_weighted > b_weighted else fighters[1] if b_weighted > a_weighted else "split",
    }


def _validate_consensus(specialist_outputs: List[SpecialistOutput], fighters: List[str]) -> List[str]:
    """
    Check for internal contradictions across specialists.
    Returns list of contradiction warnings.
    """
    contradictions = []

    if not fighters or len(fighters) < 2:
        return contradictions

    f_a = fighters[0].lower()
    f_b = fighters[1].lower()

    edge_keywords = ["advantage", "edge", "superior", "better", "stronger", "favors"]
    concern_keywords = ["concern", "weakness", "vulnerable", "struggles", "poor", "limited"]

    # Domain keywords to detect which area a specialist is discussing
    domains = {
        "striking": ["striking", "standup", "boxing", "kicks", "punch", "slpm"],
        "grappling": ["grappling", "wrestling", "takedown", "ground", "submission"],
        "cardio": ["cardio", "pace", "endurance", "gas", "fatigue", "stamina"],
        "durability": ["durability", "chin", "damage", "absorb", "knockout"],
    }

    # Check 1: Internal contradictions — same specialist says a fighter has an edge
    # AND flags concerns for that fighter in the same domain
    for s in specialist_outputs:
        content_lower = s.content.lower()
        for domain_name, domain_kws in domains.items():
            # Check if this specialist discusses this domain
            if not any(kw in content_lower for kw in domain_kws):
                continue

            for fighter_name, fighter_label in [(f_a, fighters[0]), (f_b, fighters[1])]:
                has_edge = False
                has_concern = False

                # Scan sentences for edge/concern signals near fighter name
                sentences = content_lower.replace("\n", " ").split(".")
                for sentence in sentences:
                    if fighter_name not in sentence:
                        continue
                    if not any(kw in sentence for kw in domain_kws):
                        continue
                    if any(kw in sentence for kw in edge_keywords):
                        has_edge = True
                    if any(kw in sentence for kw in concern_keywords):
                        has_concern = True

                if has_edge and has_concern:
                    contradictions.append(
                        f"{s.specialist} gives {fighter_label} both an edge and flags concerns "
                        f"in {domain_name} — internal inconsistency"
                    )

    # Check 2: Cross-specialist disagreement on who is favored
    leans = _detect_fighter_leans(specialist_outputs, fighters)
    lean_details = leans.get("lean_details", {})
    a_supporters = [spec for spec, d in lean_details.items() if d["lean"] == fighters[0]]
    b_supporters = [spec for spec, d in lean_details.items() if d["lean"] == fighters[1]]

    if a_supporters and b_supporters:
        contradictions.append(
            f"Specialists disagree on favored fighter: "
            f"{', '.join(a_supporters)} favor {fighters[0]} while "
            f"{', '.join(b_supporters)} favor {fighters[1]}"
        )

    return contradictions


def _build_structured_block(specialist_outputs: List[SpecialistOutput], fighters: List[str] = None) -> str:
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

    # Add convergence analysis
    convergence = _detect_fighter_leans(sorted_outputs, fighters or [])
    if convergence.get("consensus_fighter") != "unknown":
        lines.append("=== PRE-MERGE CONVERGENCE ANALYSIS ===")
        lines.append(f"Consensus: {convergence['consensus_fighter']} "
                     f"({convergence['convergence_pct']}% unweighted, "
                     f"{convergence.get('weighted_convergence_pct', 0)}% confidence-weighted)")
        lines.append(f"Fighter A leans: {convergence['fighter_a_count']} "
                     f"(weighted: {convergence.get('fighter_a_weighted', 0)}), "
                     f"Fighter B leans: {convergence['fighter_b_count']} "
                     f"(weighted: {convergence.get('fighter_b_weighted', 0)}), "
                     f"Neutral: {convergence['neutral_count']}")
        for spec, details in convergence.get("lean_details", {}).items():
            lines.append(f"  - {spec}: {details['lean']} "
                         f"(conf={details['confidence']:.2f}, "
                         f"signals: A={details['a_signals']}, B={details['b_signals']})")
        lines.append("")

    # Consensus validation: detect and surface contradictions
    contradictions = _validate_consensus(sorted_outputs, fighters or [])
    if contradictions:
        lines.append("=== SPECIALIST CONTRADICTIONS (must address) ===")
        for c in contradictions:
            lines.append(f"  - {c}")
        lines.append("")

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
    analytics_summary: str = None,           # NEW: pre-computed analytics data
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

    structured_block = _build_structured_block(specialist_outputs, fighters=fighters)

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

    if analytics_summary:
        system_prompt += "\n\n=== PRE-COMPUTED ANALYTICS (use as ground truth) ===\n" + analytics_summary

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

        # Compute convergence for metadata
        convergence = _detect_fighter_leans(specialist_outputs, fighters or [])

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
                "convergence": convergence,
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
