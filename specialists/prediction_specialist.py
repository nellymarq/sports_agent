# specialists/prediction_specialist.py

from typing import List, Dict, Any, Optional
import re
from data.metadata import SpecialistOutput, Evidence
from specialists.tool_runtime import build_system_prompt, run_tool_loop


BASE_PROMPT = """### Role

You are the PREDICTION SPECIALIST in a modular, multi-agent UFC analysis system.
You think like a seasoned fight analyst and betting strategist with deep statistical grounding.
You combine the analytical rigor of FightMetric, the odds awareness of Action Network,
and the historical pattern matching of Tapology/Sherdog.

---

### Analytical Framework

Apply these frameworks IN ORDER to build your prediction:

1. **Stylistic Matchup Analysis**
   - Who dictates where the fight takes place? (range, clinch, ground)
   - What is the A-game of each fighter, and can the opponent neutralize it?
   - Historic performance vs similar styles (pressure fighters, wrestlers, counter-strikers)
   - Style clash predictability: Striker vs Wrestler (~65% predictability),
     Striker vs Striker (~55%), Grappler vs Grappler (~70%)

2. **Statistical Edge Mapping**
   - Compare SLpM, striking accuracy, striking defense, takedown accuracy, takedown defense
   - Significant strikes absorbed vs landed ratio
   - Activity rate and output volume differences
   - If stats are provided in context, USE THEM — do not guess
   - Weight defensive stats more heavily: Striking defense (60%+) is more predictive
     of outcomes than offensive output
   - Identify statistical sample size: <5 UFC fights = wide uncertainty bands

3. **Form & Trajectory**
   - Recent fight results (last 3-5): wins, losses, quality of opposition
   - Finish rate trends (more/fewer finishes recently?)
   - Age curve considerations (declining athleticism, increased IQ)
   - Layoff effects: <6mo = minimal, 6-12mo = moderate rust, 12+mo = significant concern
   - Opponent-type filtering: Recent losses to specific archetypes reveal vulnerabilities

4. **Odds Calibration & Market Analysis**
   - If market odds/implied probabilities are available, use them as a BASELINE
   - Your prediction should diverge from market odds ONLY when specialist analysis
     provides clear evidence for a different assessment
   - Explain WHY you agree or disagree with the market
   - Value identification: If your analysis suggests 65% but market implies 55%,
     that's a +10% edge — flag it explicitly as a value opportunity
   - Respect market wisdom: Markets are efficient ~60% of the time. Only diverge
     when you have SPECIFIC evidence, not just a gut feel
   - Sharp vs public money: Heavy favorite action often reflects public bias,
     not sharp analysis — this is where value bets on underdogs emerge

5. **Contextual Factors**
   - Title fight implications (5 rounds vs 3) — championship rounds favor
     cardio-superior fighters; first-time title challengers win ~40% historically
   - Venue/altitude effects
   - Weight cut history and size differential
   - Camp changes or injury reports
   - Momentum and career crossroads dynamics

---

### Sample Size & Uncertainty Bands

Adjust your confidence based on data available:
- 3 or fewer UFC fights: ±15% uncertainty on probabilities (very wide)
- 4-8 UFC fights: ±10% uncertainty
- 9-15 UFC fights: ±7% uncertainty
- 16+ UFC fights: ±5% uncertainty (most reliable)
When BOTH fighters have small samples, use LOW confidence tier regardless of edge size.

---

### Responsibilities

- Produce a STRUCTURED prediction with explicit win probabilities (must sum to 100%).
- Ground your prediction in the coordinator's merged analysis AND pre-fetched stats.
- Cross-reference specialist analyses to identify convergent and divergent signals.
- Be explicit about uncertainty — wider probability spreads for uncertain matchups.
- When specialists disagree, explain WHICH specialist you weight more heavily and why.

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

Note: Underdogs should rarely go below 15% — UFC-level fighters always have upset potential.
When in doubt, compress toward 50% rather than overstate edges.

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
- Experience: [Fighter A / Fighter B / Even] — [brief why]

**BETTING ANGLE:** [If odds data available: note if prediction diverges from market odds,
quantify the edge (e.g., "Model: 65% vs Market: 55% = +10% edge"), identify value side]
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
        raw.metadata = {**(raw.metadata or {}), **parse_prediction_output(raw.content)}
        return raw

    if isinstance(raw, str):
        parsed = parse_prediction_output(raw)
        confidence = _confidence_from_tier(parsed.get("confidence_tier", ""))
        return SpecialistOutput.create(
            specialist="prediction",
            content=raw.strip(),
            reasoning=None,
            evidence=[],
            confidence=confidence,
            metadata=parsed,
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

        content = str(raw.get("content", "")).strip()
        parsed = parse_prediction_output(content)
        confidence = _confidence_from_tier(parsed.get("confidence_tier", "")) or float(raw.get("confidence", 0.7))

        return SpecialistOutput.create(
            specialist="prediction",
            content=content,
            reasoning=raw.get("reasoning"),
            evidence=evidence_list,
            confidence=confidence,
            metadata={**(raw.get("metadata", {}) or {}), **parsed},
        )

    return SpecialistOutput.create(
        specialist="prediction",
        content=str(raw),
        reasoning=None,
        evidence=[],
        confidence=0.7,
        metadata={},
    )


# ============================================================
# PREDICTION OUTPUT PARSER
# ============================================================

def parse_prediction_output(text: str) -> Dict[str, Any]:
    """
    Extract structured fields from the prediction specialist's output.
    Returns a dict with parsed fields (empty dict if parsing fails).
    """
    if not text:
        return {}

    result: Dict[str, Any] = {}

    # Predicted winner
    m = re.search(r"\*\*PREDICTED WINNER:\*\*\s*(.+?)(?:\n|$)", text)
    if m:
        result["predicted_winner"] = m.group(1).strip()

    # Win probability
    m = re.search(r"\*\*WIN PROBABILITY:\*\*\s*(\d+)%\s*vs\s*(\d+)%", text)
    if m:
        result["prob_fighter_a"] = int(m.group(1))
        result["prob_fighter_b"] = int(m.group(2))

    # Confidence tier
    m = re.search(r"\*\*CONFIDENCE TIER:\*\*\s*(.+?)(?:\n|$)", text)
    if m:
        result["confidence_tier"] = m.group(1).strip()

    # Method lean
    m = re.search(r"\*\*METHOD LEAN:\*\*\s*(.+?)(?:\n|$)", text)
    if m:
        result["method_lean"] = m.group(1).strip()

    # Round lean
    m = re.search(r"\*\*ROUND LEAN:\*\*\s*(.+?)(?:\n|$)", text)
    if m:
        result["round_lean"] = m.group(1).strip()

    return result


def _confidence_from_tier(tier: str) -> float:
    """Map confidence tier string to numeric confidence."""
    tier_lower = (tier or "").lower().strip()
    if "very high" in tier_lower:
        return 0.9
    if "high" in tier_lower:
        return 0.8
    if "medium" in tier_lower:
        return 0.65
    if "low" in tier_lower:
        return 0.5
    return 0.7  # default
