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
   - Venue/altitude effects (Mexico City = significant cardio concern)
   - Weight cut history and size differential
   - Camp changes or injury reports
   - Momentum and career crossroads dynamics

6. **Momentum & Win Streak Analysis**
   - Active win streaks of 3+ fights: ~5% prediction boost (momentum factor)
   - Coming off a loss: context matters — a competitive loss to an elite opponent
     is less predictive than a dominant loss to a gatekeeper
   - Two consecutive losses: significant concern (~8-10% negative adjustment)
   - Finish rate regression: fighters with >80% finish rate in first 5-8 fights
     often regress to 50-60% against ranked opposition — do not overweight early finishes
   - Late-career fighters (35+) on win streaks: discount momentum if opposition quality dropped

7. **Division Depth & Ranking Context**
   - Top 5 vs Top 5: tighter spreads (rarely >70/30), higher unpredictability
   - Ranked vs Unranked: wider spreads acceptable, but UFC-level unranked fighters
     still upset at ~25-30% rates
   - Champion vs Challenger: champions have ~55-60% historical win rate in title defenses
   - Moving up in weight: fighters moving up historically win ~45% (size disadvantage)
   - Moving down in weight: fighters moving down win ~60% but watch for cut-related issues

### Enhanced Data Sources (when available in prediction_features):
8. **Style matchup classification**: Use archetype analysis (pressure_striker vs counter_striker etc.)
   to ground your style analysis in data, not inference.
9. **Aging curve data**: If career_phase, chin_health, or regression flags are present,
   use them to adjust win probability. Declining fighters get -5-10% adjustment.
10. **Fight simulation results**: If Monte Carlo simulation data is present, use it as
    a statistical anchor. Your prediction should not deviate more than 15% from simulation baseline.
11. **Clinch dynamics**: If clinch_matchup or fight_location data is present, factor in
    where the fight will take place (range/clinch/ground distribution).
12. **ELO ratings**: If ELO data is present, use it as a baseline power ranking indicator.

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

### Upset Detection Flags

Watch for these high-upset-probability patterns:
- **Aging champion syndrome**: Champion is 35+ with 3+ defenses, challenger is 28-31 in peak
  (historically ~45% upset rate in this scenario)
- **Style kryptonite**: Opponent's style directly counters the favorite's primary weapon
  (e.g., elite wrestler vs striker with 40% TD defense — upset rate ~40%)
- **Weight cut red flags**: If the favorite has a history of difficult cuts or missed weight,
  the underdog gets a 5-10% boost
- **Motivation gap**: Favorite has already achieved career goals vs hungry underdog
  with everything to prove
- **Short-notice replacement**: Replacement fighters who are sharp and active actually
  win ~35% of the time — do not dismiss them
- **Altitude/travel factor**: Fighter traveling internationally for the first time or
  fighting at altitude when they train at sea level
- **Post-layoff comeback**: Fighters returning after 18+ months away lose at ~55% rate,
  even if they were dominant before

When 2+ upset flags are triggered, compress the spread by at least 5-10%.

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

**METHOD PROBABILITIES:**
- KO/TKO: [X]%
- Submission: [Y]%
- Decision: [Z]%
(Must sum to 100%. Base rates: ~30% KO/TKO, ~10% Submission, ~55% Decision, ~5% Other.
Adjust based on fighter profiles — e.g., heavy hitters increase KO%, BJJ specialists increase Sub%.)

**ROUND PROBABILITIES:** [Only if 3-round fight or 5-round fight is known]
- R1 finish: [X]%
- R2 finish: [Y]%
- R3 finish: [Z]%
- R4 finish: [A]% (5-round only)
- R5 finish: [B]% (5-round only)
- Goes to decision: [C]%
(Must sum to 100%. Base: ~15% R1, ~12% R2, ~10% R3 finish for 3-rounders.)

**BETTING ANGLE:** [If odds data available: note if prediction diverges from market odds,
quantify the edge (e.g., "Model: 65% vs Market: 55% = +10% edge"), identify value side]

**LIVE LINE SUGGESTION:** [Over/Under rounds lean if applicable, prop bet angles worth considering]
"""


PROFILE = """You are a prediction specialist in a modular UFC analytics engine.

- Coordinator-aware
- Retrieval-aware
- Memory-aware
- Hallucination-resistant
- Structured and readable
"""


def _extract_structured_analytics(prediction_features: Dict[str, Any]) -> List[str]:
    """
    Extract enhanced analytics fields from prediction_features into
    human-readable summary lines for injection into the specialist context.
    Handles both bout-level and fighter-level analytics gracefully.
    """
    lines: List[str] = []

    def _format_bout(bout: Dict[str, Any], label: str) -> None:
        fighters = bout.get("fighters", [])

        # --- Fighter-level analytics ---
        for f in fighters:
            name = f.get("name", "Unknown")

            # Style classification
            style = f.get("style")
            if style:
                primary = style.get("primary_style", "unknown")
                secondary = style.get("secondary_style")
                primary_score = style.get("primary_score", "")
                style_str = f"  [{name}] Style: {primary} ({primary_score})"
                if secondary:
                    style_str += f" / secondary: {secondary} ({style.get('secondary_score', '')})"
                lines.append(style_str)

            # Aging curve
            aging = f.get("aging")
            if aging:
                phase_info = aging.get("career_phase", {})
                phase = phase_info.get("phase", "unknown")
                composite = aging.get("composite_age_score", "N/A")
                chin = aging.get("chin_health", {})
                chin_val = chin.get("chin_health", "N/A") if chin else "N/A"
                vulnerability = chin.get("vulnerability", "N/A") if chin else "N/A"
                regression = aging.get("regression", {})
                reg_flags = regression.get("flags", []) if regression else []
                is_regressing = regression.get("is_regressing", False) if regression else False

                lines.append(
                    f"  [{name}] Age analysis: phase={phase}, composite_score={composite}, "
                    f"chin_health={chin_val} ({vulnerability})"
                )
                if is_regressing:
                    lines.append(
                        f"  [{name}] REGRESSION WARNING: score={regression.get('regression_score')}, "
                        f"type={regression.get('regression_type')}, flags={reg_flags}"
                    )

            # Clinch profile
            clinch_prof = f.get("clinch_profile")
            if clinch_prof:
                lines.append(
                    f"  [{name}] Clinch: style={clinch_prof.get('clinch_style')}, "
                    f"tendency={clinch_prof.get('clinch_tendency')}, "
                    f"prefers_clinch={clinch_prof.get('prefers_clinch')}"
                )

            # Octagon control
            oct_ctrl = f.get("octagon_control")
            if oct_ctrl:
                lines.append(
                    f"  [{name}] Octagon control: score={oct_ctrl.get('control_score')}, "
                    f"style={oct_ctrl.get('control_style')}, "
                    f"pressure={oct_ctrl.get('pressure_rating')}, "
                    f"footwork={oct_ctrl.get('footwork_rating')}"
                )

        # --- Bout-level analytics ---
        style_mu = bout.get("style_matchup")
        if style_mu:
            lines.append(
                f"  [Matchup] Type: {style_mu.get('matchup_type')} — "
                f"{style_mu.get('matchup_description', '')}"
            )

        clinch_mu = bout.get("clinch_matchup")
        if clinch_mu:
            lines.append(
                f"  [Clinch matchup] Initiator: {clinch_mu.get('clinch_initiator')}, "
                f"Dominant: {clinch_mu.get('clinch_dominant')}, "
                f"Est. clinch time: {clinch_mu.get('clinch_time_estimate_pct')}%, "
                f"Finish prob: {clinch_mu.get('clinch_finish_probability')}"
            )

        fight_loc = bout.get("fight_location")
        if fight_loc:
            dist = fight_loc.get("location_distribution", {})
            lines.append(
                f"  [Fight location] Primary: {fight_loc.get('primary_location')} — "
                f"Range: {dist.get('range', '?')}%, "
                f"Clinch: {dist.get('clinch', '?')}%, "
                f"Ground: {dist.get('ground', '?')}%"
            )

        age_adj = bout.get("age_adjustment")
        if age_adj:
            lines.append(
                f"  [Age adjustment] Modifier: {age_adj.get('modifier_pct')}, "
                f"A ({age_adj.get('phase_a')}, age {age_adj.get('age_a')}) vs "
                f"B ({age_adj.get('phase_b')}, age {age_adj.get('age_b')}), "
                f"gap={age_adj.get('age_gap')} yrs"
            )
            reasons = age_adj.get("reasons", [])
            if reasons:
                lines.append(f"    Reasons: {'; '.join(reasons)}")

    # Process main_event, co_main_event, and card bouts
    main = prediction_features.get("main_event")
    if main:
        lines.append("[Main Event Analytics]")
        _format_bout(main, "Main Event")

    co_main = prediction_features.get("co_main_event")
    if co_main:
        lines.append("[Co-Main Event Analytics]")
        _format_bout(co_main, "Co-Main Event")

    card = prediction_features.get("card", [])
    for i, bout in enumerate(card):
        # Check if this bout has any enhanced analytics
        fighters = bout.get("fighters", [])
        has_analytics = any(
            f.get("style") or f.get("aging") or f.get("clinch_profile") or f.get("octagon_control")
            for f in fighters
        ) or bout.get("style_matchup") or bout.get("clinch_matchup") or bout.get("fight_location") or bout.get("age_adjustment")

        if has_analytics:
            lines.append(f"[Card Bout {i + 1} Analytics]")
            _format_bout(bout, f"Card Bout {i + 1}")

    # Handle case where prediction_features is a single bout (not event-level)
    if not main and not co_main and not card:
        fighters = prediction_features.get("fighters", [])
        if fighters:
            _format_bout(prediction_features, "Bout")

    return lines


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

        # Extract enhanced analytics into a readable section
        analytics_lines = _extract_structured_analytics(prediction_features)
        if analytics_lines:
            sections.append("=== Enhanced Analytics Summary ===\n" + "\n".join(analytics_lines))

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

    # Betting angle
    m = re.search(r"\*\*BETTING ANGLE:\*\*\s*(.+?)(?:\n\*\*|$)", text, re.DOTALL)
    if m:
        result["betting_angle"] = m.group(1).strip()

    # Live line suggestion
    m = re.search(r"\*\*LIVE LINE SUGGESTION:\*\*\s*(.+?)(?:\n\*\*|$)", text, re.DOTALL)
    if m:
        result["live_line_suggestion"] = m.group(1).strip()

    # Method probabilities
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
        result["method_probabilities"] = method_probs

    # Round probabilities
    round_probs = {}
    for rnd in range(1, 6):
        m = re.search(rf"R{rnd} finish:\s*(\d+)%", text)
        if m:
            round_probs[f"r{rnd}"] = int(m.group(1))
    m = re.search(r"Goes to decision:\s*(\d+)%", text)
    if m:
        round_probs["decision"] = int(m.group(1))
    if round_probs:
        result["round_probabilities"] = round_probs

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
