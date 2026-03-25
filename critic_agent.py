# critic_agent.py
# Chunked critic pipeline for large multi-specialist outputs, now metadata- and memory-aware

import re
from typing import List, Optional, Dict, Any
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

Logical Consistency Check:
- If the analysis states a fighter has an advantage in a domain but then concludes they
  lose that matchup, flag this as an internal inconsistency.
- If the prediction winner contradicts the edge breakdown (e.g., Fighter B predicted to win
  but Fighter A has 4 of 5 edges), add a note flagging this tension.
- If specific statistics are cited that don't match the conclusion drawn from them,
  note the discrepancy.
- Ensure the confidence tier matches the probability: Low should be near 50-55%,
  High should be 65-80%, Very High should be 80%+.

Evidence Quality Check:
- If claims are made without citing specific statistics or fight results, mark them
  as "analytical assessment" rather than "data-backed" by adding [analyst assessment]
  to unsourced claims that sound factual.
- Do NOT add these markers to general analysis — only to specific factual claims
  (records, stats, fight outcomes) that lack source data.

Prediction Calibration Check:
- If **WIN PROBABILITY** is present, verify it matches the analysis:
  - 50-55%: Analysis should describe a very close, uncertain matchup
  - 55-65%: Analysis should show a slight edge but acknowledge risks
  - 65-75%: Analysis should show clear advantages in multiple domains
  - 75-85%: Analysis should show dominant advantages across most domains
  - 85%+: Reserved for extreme mismatches only — flag if edge analysis doesn't support this
- If METHOD LEAN says "KO/TKO" but analysis describes mostly grappling advantages, flag
- If METHOD PROBABILITIES don't roughly match the analysis narrative, flag
- If ROUND LEAN contradicts pace/cardio analysis (e.g., "late stoppage" but cardio issues), flag

Method Distribution Sanity:
- KO/TKO + Submission + Decision should sum to ~100% (allow 5% margin for rounding)
- If a fighter is described as a "heavy-handed striker" but KO/TKO probability is <20%, flag
- If a fighter is described as "elite grappler/BJJ" but Submission probability is <5%, flag

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


def validate_edge_conclusion_consistency(text: str) -> List[Dict[str, Any]]:
    """Check that the predicted winner aligns with edge analysis."""
    warnings: List[Dict[str, Any]] = []

    # Extract edge claims like "Fighter A has the striking edge" or "Edge: Fighter B"
    edge_pattern = re.findall(
        r"(\b[\w\.\'\-]+(?:\s[\w\.\'\-]+)?)\s+has\s+the\s+\w+\s+edge"
        r"|edge[:\s]+(\b[\w\.\'\-]+(?:\s[\w\.\'\-]+)?)",
        text, re.IGNORECASE,
    )

    # Count edges per fighter name (normalize to lowercase)
    edge_counts: Dict[str, int] = {}
    for groups in edge_pattern:
        name = (groups[0] or groups[1]).strip().lower()
        if name:
            edge_counts[name] = edge_counts.get(name, 0) + 1

    if not edge_counts:
        return warnings

    # Extract predicted winner from common prediction patterns
    winner_match = re.search(
        r"\*\*(?:PREDICTED\s+)?WINNER:\*\*\s*(.+?)(?:\n|$)"
        r"|(?:PICK|PREDICTION)[:\s]+(\b[\w\.\'\-]+(?:\s[\w\.\'\-]+)?)\b",
        text, re.IGNORECASE,
    )
    if not winner_match:
        return warnings

    predicted_winner = (winner_match.group(1) or winner_match.group(2)).strip().lower()

    # Find the fighter with the most edges
    max_edge_fighter = max(edge_counts, key=edge_counts.get)
    max_edges = edge_counts[max_edge_fighter]

    # Check if predicted winner is in edge_counts
    winner_edges = 0
    winner_key = None
    for name, count in edge_counts.items():
        if name in predicted_winner or predicted_winner in name:
            winner_edges = count
            winner_key = name
            break

    if winner_key is None:
        # Could not match predicted winner to edge analysis names
        return warnings

    # Compare: does the predicted winner have fewer edges?
    other_edges = max_edges if winner_key != max_edge_fighter else 0
    if winner_key != max_edge_fighter:
        other_edges = max_edges

    if winner_edges < other_edges:
        # Determine severity based on lopsidedness
        if other_edges - winner_edges >= 3 and other_edges >= 4:
            severity = "high"
            label = "Strong edge-conclusion mismatch"
        else:
            severity = "medium"
            label = "Edge-conclusion inconsistency"

        warnings.append({
            "type": "edge_conclusion_mismatch",
            "severity": severity,
            "message": (
                f"{label}: predicted winner has {winner_edges} edge(s) "
                f"but {max_edge_fighter} has {max_edges} edge(s)"
            ),
            "winner_edges": winner_edges,
            "max_edge_fighter": max_edge_fighter,
            "max_edges": max_edges,
        })

    return warnings


def validate_against_base_rates(text: str) -> List[Dict[str, Any]]:
    """
    Check prediction against known UFC base rates.
    - Title fights: favorites win ~65% (not 80%+)
    - Top-5 vs Top-5: closer to 55-60%, not 75%+
    - Underdog win rate: ~35% in UFC (don't go below 20% lightly)
    """
    warnings: List[Dict[str, Any]] = []

    # Extract win probability
    m_prob = re.search(r"\*\*WIN PROBABILITY:\*\*\s*(\d+)%\s*vs\s*(\d+)%", text)
    if not m_prob:
        return warnings

    prob_a = int(m_prob.group(1))
    prob_b = int(m_prob.group(2))
    higher_prob = max(prob_a, prob_b)
    lower_prob = min(prob_a, prob_b)

    # Detect title fight context
    is_title_fight = bool(re.search(
        r"title\s+fight|championship\s+bout|title\s+bout|for\s+the\s+(?:\w+\s+)?title",
        text, re.IGNORECASE,
    ))

    # Detect top-5 vs top-5 context
    is_top5_matchup = bool(re.search(
        r"top[\s-]?5\s+vs\s+top[\s-]?5|ranked\s+#?[1-5]\s+vs\s+#?[1-5]"
        r"|both\s+(?:are\s+)?top[\s-]?5",
        text, re.IGNORECASE,
    ))

    if is_title_fight and higher_prob > 80:
        warnings.append({
            "type": "base_rate_title_fight",
            "severity": "medium",
            "message": (
                f"Title fight favorite at {higher_prob}% exceeds historical "
                f"base rate (~65% favorites win in title fights)"
            ),
        })

    if is_top5_matchup and higher_prob > 75:
        warnings.append({
            "type": "base_rate_top5",
            "severity": "medium",
            "message": (
                f"Top-5 vs Top-5 matchup at {higher_prob}% exceeds historical "
                f"base rate (~55-60% for elite matchups)"
            ),
        })

    if lower_prob < 20:
        warnings.append({
            "type": "base_rate_underdog_floor",
            "severity": "medium",
            "message": (
                f"Underdog probability at {lower_prob}% is below UFC historical "
                f"upset rate (~35%). Probabilities below 20% should be rare."
            ),
        })

    return warnings


def validate_prediction_consistency(text: str) -> List[Dict[str, Any]]:
    """
    Post-hoc quantitative validation of the prediction output.
    Returns a list of warnings/flags found.
    """
    warnings: List[Dict[str, Any]] = []

    # Check method probabilities sum to ~100%
    method_probs = {}
    for method_key, pattern in [
        ("ko_tko", r"KO/TKO:\s*(\d+)%"),
        ("submission", r"Submission:\s*(\d+)%"),
        ("decision", r"Decision:\s*(\d+)%"),
    ]:
        m = re.search(pattern, text)
        if m:
            method_probs[method_key] = int(m.group(1))

    if method_probs:
        total = sum(method_probs.values())
        if abs(total - 100) > 5:
            warnings.append({
                "type": "method_sum_error",
                "severity": "high",
                "message": f"Method probabilities sum to {total}%, should be ~100%",
                "values": method_probs,
            })

    # Check round probabilities sum to ~100%
    round_probs = {}
    for rnd in range(1, 6):
        m = re.search(rf"R{rnd} finish:\s*(\d+)%", text)
        if m:
            round_probs[f"r{rnd}"] = int(m.group(1))
    m = re.search(r"Goes to decision:\s*(\d+)%", text)
    if m:
        round_probs["decision"] = int(m.group(1))

    if round_probs:
        total = sum(round_probs.values())
        if abs(total - 100) > 5:
            warnings.append({
                "type": "round_sum_error",
                "severity": "high",
                "message": f"Round probabilities sum to {total}%, should be ~100%",
                "values": round_probs,
            })

    # Check win probability vs confidence tier consistency
    m_prob = re.search(r"\*\*WIN PROBABILITY:\*\*\s*(\d+)%\s*vs\s*(\d+)%", text)
    m_tier = re.search(r"\*\*CONFIDENCE TIER:\*\*\s*(.+?)(?:\n|$)", text)

    if m_prob and m_tier:
        higher_prob = max(int(m_prob.group(1)), int(m_prob.group(2)))
        tier = m_tier.group(1).strip().lower()

        if "very high" in tier and higher_prob < 75:
            warnings.append({
                "type": "tier_probability_mismatch",
                "severity": "medium",
                "message": f"Very High confidence with only {higher_prob}% probability",
            })
        elif "low" in tier and higher_prob > 65:
            warnings.append({
                "type": "tier_probability_mismatch",
                "severity": "medium",
                "message": f"Low confidence with {higher_prob}% probability seems underconfident",
            })

        # Check probabilities sum to 100%
        prob_sum = int(m_prob.group(1)) + int(m_prob.group(2))
        if abs(prob_sum - 100) > 2:
            warnings.append({
                "type": "win_prob_sum_error",
                "severity": "high",
                "message": f"Win probabilities sum to {prob_sum}%, must be 100%",
            })

    # Check for probabilities below UFC floor (15%)
    if m_prob:
        lower_prob = min(int(m_prob.group(1)), int(m_prob.group(2)))
        if lower_prob < 10:
            warnings.append({
                "type": "probability_floor_violation",
                "severity": "medium",
                "message": f"Underdog probability at {lower_prob}% is below UFC floor (~15%)",
            })

    # Archetype-method consistency checks
    ko_pct = method_probs.get("ko_tko")
    sub_pct = method_probs.get("submission")
    dec_pct = method_probs.get("decision")

    if ko_pct is not None and ko_pct < 20:
        if re.search(r"heavy[- ]handed\s+striker|knockout\s+artist", text, re.IGNORECASE):
            warnings.append({
                "type": "archetype_method_mismatch",
                "severity": "medium",
                "message": (
                    f"Fighter described as heavy-handed striker/knockout artist "
                    f"but KO/TKO probability is only {ko_pct}%"
                ),
            })

    if sub_pct is not None and sub_pct < 5:
        if re.search(r"elite\s+grappler|submission\s+specialist", text, re.IGNORECASE):
            warnings.append({
                "type": "archetype_method_mismatch",
                "severity": "medium",
                "message": (
                    f"Fighter described as elite grappler/submission specialist "
                    f"but Submission probability is only {sub_pct}%"
                ),
            })

    if dec_pct is not None and dec_pct < 40:
        if re.search(r"point\s+fighter|decision\s+machine", text, re.IGNORECASE):
            warnings.append({
                "type": "archetype_method_mismatch",
                "severity": "medium",
                "message": (
                    f"Fighter described as point fighter/decision machine "
                    f"but Decision probability is only {dec_pct}%"
                ),
            })

    return warnings


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

    # Run quantitative validation on the final output
    validation_warnings = validate_prediction_consistency(final_text)

    # Run edge-to-conclusion and base-rate validations
    edge_warnings = validate_edge_conclusion_consistency(final_text)
    base_rate_warnings = validate_against_base_rates(final_text)
    validation_warnings.extend(edge_warnings)
    validation_warnings.extend(base_rate_warnings)

    if validation_warnings:
        info(f"Critic: found {len(validation_warnings)} validation warnings")
        # Append warnings to the output if there are high-severity ones
        high_severity = [w for w in validation_warnings if w.get("severity") == "high"]
        if high_severity:
            warning_text = "\n\n**VALIDATION NOTES:**\n"
            for w in high_severity:
                warning_text += f"- {w['message']}\n"
            final_text += warning_text

    # Apply confidence penalty for validation issues
    if validation_warnings:
        high_count = sum(1 for w in validation_warnings if w["severity"] == "high")
        med_count = sum(1 for w in validation_warnings if w["severity"] == "medium")
        penalty = high_count * 0.08 + med_count * 0.03
        final_conf = max(0.1, final_conf - penalty)

    metadata = {
        "source": "critic",
        "chunk_count": len(chunks),
        "has_prediction": prediction_output is not None,
        "coordinator_confidence": coord_conf,
        "prediction_confidence": pred_conf,
        "validation_warnings": validation_warnings,
        "validation_warning_count": len(validation_warnings),
    }

    return FinalOutput.create(
        content=final_text,
        merged_from=parent_ids,
        evidence=all_evidence,
        confidence=final_conf,
        lineage=lineage,
        metadata=metadata,
    )
