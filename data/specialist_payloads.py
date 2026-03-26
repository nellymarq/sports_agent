# data/specialist_payloads.py
# Builds domain-specific analytics payloads for each specialist.
# Bridges the gap between pre-computed analytics (aging curves, style
# classification, clinch analysis, fight simulation, ELO ratings) and the
# specialist LLMs that previously received only raw text context.

from __future__ import annotations
from typing import Dict, Any, List, Optional


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _safe_get(d: Any, *keys: str, default: Any = None) -> Any:
    """Nested dict accessor that never raises."""
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k, default)
    return cur


def _parse_int(val: Any) -> Optional[int]:
    if val is None:
        return None
    try:
        return int(str(val).strip())
    except (ValueError, TypeError):
        return None


def _parse_float(val: Any) -> Optional[float]:
    if val is None:
        return None
    try:
        return float(str(val).replace("%", "").strip())
    except (ValueError, TypeError):
        return None


def _fighter_names(prefetched_stats: Dict[str, Any], fighters: List[str]):
    """Return the two fighter names, falling back to prefetched keys."""
    if fighters and len(fighters) >= 2:
        return fighters[0], fighters[1]
    keys = list(prefetched_stats.keys())
    if len(keys) >= 2:
        return keys[0], keys[1]
    if len(keys) == 1:
        return keys[0], "Unknown"
    return "Fighter A", "Fighter B"


# ---------------------------------------------------------------------------
# 1. MASTER ANALYTICS BUNDLE
# ---------------------------------------------------------------------------

def compute_analytics_bundle(
    prefetched_stats: Dict[str, Any],
    fighters: List[str],
) -> Dict[str, Any]:
    """
    Compute ALL analytics in one pass from prefetched fighter stats.

    Args:
        prefetched_stats: Dict keyed by fighter name, values are stat dicts
                          (from tools/prefetch.py).
        fighters: List of fighter name strings (len >= 2).

    Returns:
        Dict with all computed analytics; every sub-key is populated on a
        best-effort basis (non-fatal try/except around each call).
    """
    bundle: Dict[str, Any] = {}
    name_a, name_b = _fighter_names(prefetched_stats, fighters)
    stats_a = prefetched_stats.get(name_a, {})
    stats_b = prefetched_stats.get(name_b, {})

    # Inject name keys so downstream modules can reference them
    stats_a_with_name = {**stats_a, "name": name_a}
    stats_b_with_name = {**stats_b, "name": name_b}

    bundle["fighter_a"] = name_a
    bundle["fighter_b"] = name_b
    bundle["_errors"] = []

    # --- Style classification ---
    try:
        from data.style_classifier import classify_style
        bundle["style_a"] = classify_style(stats_a)
    except Exception as e:
        bundle["style_a"] = None
        bundle["_errors"].append(f"style_a: {type(e).__name__}: {e}")

    try:
        from data.style_classifier import classify_style
        bundle["style_b"] = classify_style(stats_b)
    except Exception as e:
        bundle["style_b"] = None
        bundle["_errors"].append(f"style_b: {type(e).__name__}: {e}")

    try:
        from data.style_classifier import classify_matchup
        bundle["matchup"] = classify_matchup(stats_a, stats_b)
    except Exception as e:
        bundle["matchup"] = None
        bundle["_errors"].append(f"matchup: {type(e).__name__}: {e}")

    # --- Aging analysis ---
    age_a = _parse_int(stats_a.get("age"))
    age_b = _parse_int(stats_b.get("age"))
    weight_class = stats_a.get("weight_class") or stats_b.get("weight_class") or ""

    if age_a is not None:
        try:
            from data.aging_curve import full_age_analysis
            bundle["aging_a"] = full_age_analysis(
                age=age_a,
                weight_class=weight_class,
                record=stats_a.get("record", ""),
                fighter_stats=stats_a,
            )
        except Exception as e:
            bundle["aging_a"] = None
            bundle["_errors"].append(f"aging_a: {type(e).__name__}: {e}")
    else:
        bundle["aging_a"] = None

    if age_b is not None:
        try:
            from data.aging_curve import full_age_analysis
            bundle["aging_b"] = full_age_analysis(
                age=age_b,
                weight_class=weight_class,
                record=stats_b.get("record", ""),
                fighter_stats=stats_b,
            )
        except Exception as e:
            bundle["aging_b"] = None
            bundle["_errors"].append(f"aging_b: {type(e).__name__}: {e}")
    else:
        bundle["aging_b"] = None

    if age_a is not None and age_b is not None:
        try:
            from data.aging_curve import age_adjustment
            phase_a = _safe_get(bundle, "aging_a", "career_phase", "phase")
            phase_b = _safe_get(bundle, "aging_b", "career_phase", "phase")
            bundle["age_adj"] = age_adjustment(
                age_a, age_b,
                weight_class=weight_class,
                phase_a=phase_a,
                phase_b=phase_b,
            )
        except Exception as e:
            bundle["age_adj"] = None
            bundle["_errors"].append(f"age_adj: {type(e).__name__}: {e}")
    else:
        bundle["age_adj"] = None

    # --- Clinch / cage control ---
    try:
        from data.cage_control import analyze_clinch_profile
        bundle["clinch_profile_a"] = analyze_clinch_profile(stats_a)
    except Exception as e:
        bundle["clinch_profile_a"] = None
        bundle["_errors"].append(f"clinch_profile_a: {type(e).__name__}: {e}")

    try:
        from data.cage_control import analyze_clinch_profile
        bundle["clinch_profile_b"] = analyze_clinch_profile(stats_b)
    except Exception as e:
        bundle["clinch_profile_b"] = None
        bundle["_errors"].append(f"clinch_profile_b: {type(e).__name__}: {e}")

    try:
        from data.cage_control import analyze_clinch_matchup
        bundle["clinch_matchup"] = analyze_clinch_matchup(stats_a_with_name, stats_b_with_name)
    except Exception as e:
        bundle["clinch_matchup"] = None
        bundle["_errors"].append(f"clinch_matchup: {type(e).__name__}: {e}")

    try:
        from data.cage_control import predict_fight_location
        bundle["fight_location"] = predict_fight_location(stats_a, stats_b)
    except Exception as e:
        bundle["fight_location"] = None
        bundle["_errors"].append(f"fight_location: {type(e).__name__}: {e}")

    try:
        from data.cage_control import compute_octagon_control_score
        bundle["octagon_control_a"] = compute_octagon_control_score(stats_a)
    except Exception as e:
        bundle["octagon_control_a"] = None
        bundle["_errors"].append(f"octagon_control_a: {type(e).__name__}: {e}")

    try:
        from data.cage_control import compute_octagon_control_score
        bundle["octagon_control_b"] = compute_octagon_control_score(stats_b)
    except Exception as e:
        bundle["octagon_control_b"] = None
        bundle["_errors"].append(f"octagon_control_b: {type(e).__name__}: {e}")

    # --- Fight simulation ---
    matchup_type = _safe_get(bundle, "matchup", "matchup_type") or "mixed"

    try:
        from data.fight_simulation import simulate_fight
        bundle["simulation"] = simulate_fight(
            stats_a_with_name, stats_b_with_name,
            matchup_type=matchup_type,
        )
    except Exception as e:
        bundle["simulation"] = None
        bundle["_errors"].append(f"simulation: {type(e).__name__}: {e}")

    try:
        from data.fight_simulation import simulate_fight_advanced
        bundle["advanced_sim"] = simulate_fight_advanced(
            stats_a_with_name, stats_b_with_name,
            matchup_type=matchup_type,
        )
    except Exception as e:
        bundle["advanced_sim"] = None
        bundle["_errors"].append(f"advanced_sim: {type(e).__name__}: {e}")

    # --- Decision prediction ---
    try:
        from data.judge_model import predict_decision
        bundle["decision_pred"] = predict_decision(stats_a, stats_b)
    except Exception as e:
        bundle["decision_pred"] = None
        bundle["_errors"].append(f"decision_pred: {type(e).__name__}: {e}")

    # --- Physical edge (computed inside advanced sim, surface it) ---
    try:
        from data.fight_simulation import compute_physical_edge
        bundle["physical_edge"] = compute_physical_edge(stats_a, stats_b)
    except Exception as e:
        bundle["physical_edge"] = None
        bundle["_errors"].append(f"physical_edge: {type(e).__name__}: {e}")

    # Attach raw stats for reference
    bundle["stats_a"] = stats_a
    bundle["stats_b"] = stats_b

    return bundle


# ---------------------------------------------------------------------------
# 2. FORMAT SPECIALIST PAYLOAD
# ---------------------------------------------------------------------------

def format_specialist_payload(
    analytics_bundle: Dict[str, Any],
    specialist_key: str,
) -> str:
    """
    Return a formatted text payload targeted at a specific specialist domain.

    Args:
        analytics_bundle: Output of compute_analytics_bundle.
        specialist_key: One of the specialist domain keys (e.g. "style",
                        "form", "grappling", "clinch", etc.).

    Returns:
        A clean, readable text block the specialist LLM can parse.
    """
    b = analytics_bundle
    name_a = b.get("fighter_a", "Fighter A")
    name_b = b.get("fighter_b", "Fighter B")

    formatter = _SPECIALIST_FORMATTERS.get(specialist_key)
    if formatter is None:
        return f"[No formatter defined for specialist '{specialist_key}']\n"

    try:
        return formatter(b, name_a, name_b)
    except Exception as exc:
        return f"[Error formatting payload for '{specialist_key}': {exc}]\n"


# --- Individual specialist formatters ---

def _fmt_style(b: Dict, na: str, nb: str) -> str:
    lines = [f"=== STYLE ANALYTICS: {na} vs {nb} ===", ""]

    for label, key in [(na, "style_a"), (nb, "style_b")]:
        s = b.get(key)
        if s:
            lines.append(f"-- {label} --")
            lines.append(f"  Primary style: {s.get('primary_style', 'unknown')} (score {s.get('primary_score', '?')})")
            lines.append(f"  Description: {s.get('primary_description', '')}")
            if s.get("secondary_style"):
                lines.append(f"  Secondary style: {s['secondary_style']} (score {s.get('secondary_score', '?')})")
            scores = s.get("style_scores", {})
            if scores:
                lines.append("  Archetype scores: " + ", ".join(
                    f"{k}={v}" for k, v in scores.items()
                ))
            lines.append("")

    m = b.get("matchup")
    if m:
        lines.append(f"-- Matchup Classification --")
        lines.append(f"  Type: {m.get('matchup_type', 'unknown')}")
        lines.append(f"  Description: {m.get('matchup_description', '')}")
        rec = m.get("recommended_specialists", [])
        if rec:
            lines.append(f"  Recommended specialists: {', '.join(rec)}")
        lines.append("")

    return "\n".join(lines)


def _fmt_form(b: Dict, na: str, nb: str) -> str:
    lines = [f"=== FORM & AGING ANALYTICS: {na} vs {nb} ===", ""]

    for label, aging_key in [(na, "aging_a"), (nb, "aging_b")]:
        ag = b.get(aging_key)
        if not ag:
            lines.append(f"-- {label}: age data unavailable --")
            lines.append("")
            continue
        lines.append(f"-- {label} (age {ag.get('age', '?')}) --")
        lines.append(f"  Composite age score: {ag.get('composite_age_score', '?')}/100")

        cp = ag.get("career_phase", {})
        if cp:
            lines.append(f"  Career phase: {cp.get('phase', '?')} - {cp.get('description', '')}")
            lines.append(f"  Prediction note: {cp.get('prediction_note', '')}")
            lines.append(f"  In peak window: {cp.get('in_peak_window', '?')}")

        reg = ag.get("regression", {})
        if reg:
            lines.append(f"  Regression score: {reg.get('regression_score', 0)}")
            lines.append(f"  Regressing: {reg.get('is_regressing', False)}")
            if reg.get("flags"):
                lines.append(f"  Regression flags: {', '.join(reg['flags'])}")
            lines.append(f"  Years past peak: {reg.get('years_past_peak', 0)}")
        lines.append("")

    adj = b.get("age_adj")
    if adj:
        lines.append("-- Age Adjustment --")
        lines.append(f"  Modifier: {adj.get('modifier_pct', '0%')}")
        for r in adj.get("reasons", []):
            lines.append(f"    - {r}")
        lines.append("")

    return "\n".join(lines)


def _fmt_grappling(b: Dict, na: str, nb: str) -> str:
    lines = [f"=== GRAPPLING ANALYTICS: {na} vs {nb} ===", ""]

    for label, key in [(na, "clinch_profile_a"), (nb, "clinch_profile_b")]:
        cp = b.get(key)
        if cp:
            lines.append(f"-- {label} Clinch Profile --")
            lines.append(f"  Clinch style: {cp.get('clinch_style', '?')}")
            lines.append(f"  Clinch tendency: {cp.get('clinch_tendency', '?')}")
            lines.append(f"  Description: {cp.get('description', '')}")
            lines.append(f"  Prefers clinch: {cp.get('prefers_clinch', False)}")
            lines.append("")

    fl = b.get("fight_location")
    if fl:
        lines.append("-- Fight Location Prediction --")
        dist = fl.get("location_distribution", {})
        lines.append(f"  Range: {dist.get('range', '?')}%")
        lines.append(f"  Clinch: {dist.get('clinch', '?')}%")
        lines.append(f"  Ground: {dist.get('ground', '?')}%")
        lines.append(f"  Primary: {fl.get('primary_location', '?')}")
        lines.append(f"  {fl.get('fight_location_description', '')}")
        lines.append("")

    # Grappling stat edges from simulation
    sim = b.get("simulation") or b.get("advanced_sim")
    if sim:
        edge = sim.get("statistical_edge", {})
        td_off = edge.get("takedown_offense", 0)
        td_def = edge.get("takedown_defense", 0)
        sub = edge.get("submission_threat", 0)
        lines.append("-- Grappling Stat Edges ({} perspective) --".format(na))
        lines.append(f"  Takedown offense edge: {td_off:+.3f}")
        lines.append(f"  Takedown defense edge: {td_def:+.3f}")
        lines.append(f"  Submission threat edge: {sub:+.3f}")
        lines.append("")

    return "\n".join(lines)


def _fmt_clinch(b: Dict, na: str, nb: str) -> str:
    lines = [f"=== CLINCH ANALYTICS: {na} vs {nb} ===", ""]

    cm = b.get("clinch_matchup")
    if cm:
        lines.append("-- Clinch Matchup --")
        lines.append(f"  Clinch initiator: {cm.get('clinch_initiator', '?')}")
        lines.append(f"  Clinch dominant: {cm.get('clinch_dominant', '?')}")
        lines.append(f"  Clinch time estimate: {cm.get('clinch_time_estimate_pct', '?')}%")
        lines.append(f"  Clinch finish probability: {cm.get('clinch_finish_probability', '?')}")
        ctrl = cm.get("control_scores", {})
        lines.append(f"  Control scores: {na}={ctrl.get('a', '?')}, {nb}={ctrl.get('b', '?')}")
        lines.append("")

    for label, key in [(na, "clinch_profile_a"), (nb, "clinch_profile_b")]:
        cp = b.get(key)
        if cp:
            lines.append(f"-- {label} Clinch Profile --")
            lines.append(f"  Style: {cp.get('clinch_style', '?')} - {cp.get('description', '')}")
            lines.append(f"  Tendency: {cp.get('clinch_tendency', '?')}")
            lines.append("")

    for label, key in [(na, "octagon_control_a"), (nb, "octagon_control_b")]:
        oc = b.get(key)
        if oc:
            lines.append(f"-- {label} Octagon Control --")
            lines.append(f"  Control score: {oc.get('control_score', '?')}")
            lines.append(f"  Pressure rating: {oc.get('pressure_rating', '?')}")
            lines.append(f"  Footwork rating: {oc.get('footwork_rating', '?')}")
            lines.append(f"  Style: {oc.get('control_style', '?')} - {oc.get('description', '')}")
            lines.append("")

    fl = b.get("fight_location")
    if fl:
        lines.append("-- Fight Location --")
        dist = fl.get("location_distribution", {})
        lines.append(f"  Range {dist.get('range', '?')}% | Clinch {dist.get('clinch', '?')}% | Ground {dist.get('ground', '?')}%")
        lines.append("")

    return "\n".join(lines)


def _fmt_damage(b: Dict, na: str, nb: str) -> str:
    lines = [f"=== DAMAGE ANALYTICS: {na} vs {nb} ===", ""]

    # Chin health from aging data
    for label, aging_key in [(na, "aging_a"), (nb, "aging_b")]:
        ag = b.get(aging_key)
        if ag:
            chin = ag.get("chin_health", {})
            lines.append(f"-- {label} Chin Health --")
            lines.append(f"  Chin health score: {chin.get('chin_health', '?')}")
            lines.append(f"  Vulnerability: {chin.get('vulnerability', '?')}")
            lines.append(f"  KO susceptibility modifier: {chin.get('ko_susceptibility_modifier', '?')}")
            factors = chin.get("factors", {})
            if factors:
                lines.append(f"  KO losses impact: {factors.get('ko_losses_impact', 0)}")
                lines.append(f"  Age impact: {factors.get('age_impact', 0)}")
                lines.append(f"  Accumulated damage: {factors.get('accumulated_damage', 0)}")
            lines.append("")

    # Striking power indicators from stats
    for label, stats_key in [(na, "stats_a"), (nb, "stats_b")]:
        st = b.get(stats_key, {})
        slpm = _parse_float(st.get("slpm"))
        str_acc = _parse_float(st.get("str_acc"))
        sapm = _parse_float(st.get("sapm"))
        str_def = _parse_float(st.get("str_def"))
        if slpm is not None:
            lines.append(f"-- {label} Striking Power Indicators --")
            lines.append(f"  SLpM: {slpm}")
            lines.append(f"  Str accuracy: {str_acc}%")
            lines.append(f"  SApM: {sapm}")
            lines.append(f"  Str defense: {str_def}%")
            # Effective output
            if str_acc is not None:
                eff = round(slpm * str_acc / 100, 2)
                lines.append(f"  Effective striking output: {eff} sig. strikes landed/min")
            lines.append("")

    # Durability vectors from aging skill multipliers
    for label, aging_key in [(na, "aging_a"), (nb, "aging_b")]:
        ag = b.get(aging_key)
        if ag:
            sm = ag.get("skill_multipliers", {})
            lines.append(f"-- {label} Durability Vector --")
            lines.append(f"  Chin multiplier: {sm.get('chin', '?')}")
            lines.append(f"  Reflexes multiplier: {sm.get('reflexes', '?')}")
            lines.append(f"  Speed multiplier: {sm.get('speed', '?')}")
            lines.append("")

    # Simulation KO data
    sim = b.get("simulation")
    if sim:
        md = sim.get("method_distribution", {})
        lines.append("-- KO/TKO Probability (simulation) --")
        lines.append(f"  Overall KO/TKO rate: {md.get('ko_tko', '?')}%")
        wmb = sim.get("winner_method_breakdown", {})
        for name in [na, nb]:
            mb = wmb.get(name, {})
            if mb:
                lines.append(f"  {name} KO/TKO if wins: {mb.get('ko_tko', '?')}%")
        lines.append("")

    return "\n".join(lines)


def _fmt_pace(b: Dict, na: str, nb: str) -> str:
    lines = [f"=== PACE & CARDIO ANALYTICS: {na} vs {nb} ===", ""]

    adv = b.get("advanced_sim")
    if adv:
        cp = adv.get("cardio_profiles", {})
        lines.append("-- Cardio Profiles --")
        lines.append(f"  {na}: {cp.get(na, '?')}")
        lines.append(f"  {nb}: {cp.get(nb, '?')}")
        lines.append("")

        # Fatigue projection via round distribution
        rd = adv.get("round_distribution", {})
        lines.append("-- Round Distribution (finish probability) --")
        for rnd, pct in sorted(rd.items()):
            lines.append(f"  {rnd}: {pct}%")
        lines.append("")

    fl = b.get("fight_location")
    if fl:
        dist = fl.get("location_distribution", {})
        lines.append("-- Fight Location Distribution --")
        lines.append(f"  Range: {dist.get('range', '?')}%")
        lines.append(f"  Clinch: {dist.get('clinch', '?')}%")
        lines.append(f"  Ground: {dist.get('ground', '?')}%")
        lines.append("")

    # Output differential as pace proxy
    for label, stats_key in [(na, "stats_a"), (nb, "stats_b")]:
        st = b.get(stats_key, {})
        slpm = _parse_float(st.get("slpm"))
        sapm = _parse_float(st.get("sapm"))
        if slpm is not None and sapm is not None:
            diff = round(slpm - sapm, 2)
            lines.append(f"  {label} output differential (SLpM - SApM): {diff:+.2f}")
    lines.append("")

    return "\n".join(lines)


def _fmt_fight_iq(b: Dict, na: str, nb: str) -> str:
    lines = [f"=== FIGHT IQ ANALYTICS: {na} vs {nb} ===", ""]

    m = b.get("matchup")
    if m:
        lines.append(f"Matchup type: {m.get('matchup_type', '?')}")
        lines.append(f"Description: {m.get('matchup_description', '')}")
        lines.append("")

    # Experience differential from simulation
    sim = b.get("simulation") or b.get("advanced_sim")
    if sim:
        edge = sim.get("statistical_edge", {})
        exp_edge = edge.get("experience", 0)
        lines.append(f"Experience edge ({na} perspective): {exp_edge:+.3f}")
        lines.append("")

    # Career phases
    for label, aging_key in [(na, "aging_a"), (nb, "aging_b")]:
        ag = b.get(aging_key)
        if ag:
            cp = ag.get("career_phase", {})
            sm = ag.get("skill_multipliers", {})
            lines.append(f"-- {label} --")
            lines.append(f"  Career phase: {cp.get('phase', '?')} - {cp.get('description', '')}")
            lines.append(f"  Fight IQ multiplier: {sm.get('fight_iq', '?')}")
            lines.append(f"  Technique multiplier: {sm.get('technique', '?')}")
            lines.append("")

    # Simulation edge breakdown
    if sim:
        lines.append("-- Simulation Edge Breakdown --")
        for dim, val in sim.get("statistical_edge", {}).items():
            lines.append(f"  {dim}: {val:+.3f}")
        lines.append("")

    return "\n".join(lines)


def _fmt_gameplan(b: Dict, na: str, nb: str) -> str:
    lines = [f"=== GAMEPLAN ANALYTICS: {na} vs {nb} ===", ""]

    m = b.get("matchup")
    if m:
        lines.append(f"Matchup: {m.get('matchup_type', '?')} - {m.get('matchup_description', '')}")
        lines.append("")

    fl = b.get("fight_location")
    if fl:
        lines.append(f"Fight location prediction: {fl.get('fight_location_description', '?')}")
        dist = fl.get("location_distribution", {})
        lines.append(f"  Range {dist.get('range', '?')}% | Clinch {dist.get('clinch', '?')}% | Ground {dist.get('ground', '?')}%")
        lines.append("")

    sim = b.get("simulation")
    if sim:
        wp = sim.get("win_probability", {})
        lines.append("-- Simulation Results --")
        for name, prob in wp.items():
            lines.append(f"  {name}: {prob}%")
        md = sim.get("method_distribution", {})
        lines.append(f"  Method dist: KO/TKO {md.get('ko_tko', '?')}% | Sub {md.get('submission', '?')}% | Dec {md.get('decision', '?')}%")
        lines.append("")

    # Strengths/weaknesses from style + stats
    for label, style_key, stats_key in [
        (na, "style_a", "stats_a"), (nb, "style_b", "stats_b")
    ]:
        s = b.get(style_key)
        st = b.get(stats_key, {})
        if s:
            lines.append(f"-- {label} Profile --")
            lines.append(f"  Style: {s.get('primary_style', '?')} - {s.get('primary_description', '')}")
            slpm = _parse_float(st.get("slpm"))
            str_def = _parse_float(st.get("str_def"))
            td_avg = _parse_float(st.get("td_avg"))
            td_def = _parse_float(st.get("td_def"))
            strengths = []
            weaknesses = []
            if slpm is not None and slpm > 5.0:
                strengths.append(f"high striking volume ({slpm} SLpM)")
            if str_def is not None and str_def > 60:
                strengths.append(f"strong striking defense ({str_def}%)")
            if td_avg is not None and td_avg > 3.0:
                strengths.append(f"elite takedown offense ({td_avg}/15min)")
            if td_def is not None and td_def > 75:
                strengths.append(f"elite takedown defense ({td_def}%)")
            if str_def is not None and str_def < 48:
                weaknesses.append(f"poor striking defense ({str_def}%)")
            if td_def is not None and td_def < 55:
                weaknesses.append(f"vulnerable to takedowns ({td_def}%)")
            if slpm is not None and slpm < 2.5:
                weaknesses.append(f"low output ({slpm} SLpM)")
            if strengths:
                lines.append(f"  Strengths: {'; '.join(strengths)}")
            if weaknesses:
                lines.append(f"  Weaknesses: {'; '.join(weaknesses)}")
            lines.append("")

    return "\n".join(lines)


def _fmt_scramble(b: Dict, na: str, nb: str) -> str:
    lines = [f"=== SCRAMBLE ANALYTICS: {na} vs {nb} ===", ""]

    cm = b.get("clinch_matchup")
    if cm:
        lines.append("-- Clinch Matchup --")
        lines.append(f"  Initiator: {cm.get('clinch_initiator', '?')}")
        lines.append(f"  Dominant: {cm.get('clinch_dominant', '?')}")
        lines.append(f"  Clinch time: {cm.get('clinch_time_estimate_pct', '?')}%")
        lines.append(f"  Clinch finish prob: {cm.get('clinch_finish_probability', '?')}")
        ctrl = cm.get("control_scores", {})
        lines.append(f"  Control: {na}={ctrl.get('a', '?')}, {nb}={ctrl.get('b', '?')}")
        lines.append("")

    sim = b.get("simulation") or b.get("advanced_sim")
    if sim:
        edge = sim.get("statistical_edge", {})
        lines.append("-- Grappling Stat Edges --")
        lines.append(f"  Takedown offense: {edge.get('takedown_offense', 0):+.3f}")
        lines.append(f"  Takedown defense: {edge.get('takedown_defense', 0):+.3f}")
        lines.append(f"  Submission threat: {edge.get('submission_threat', 0):+.3f}")
        lines.append("")

    return "\n".join(lines)


def _fmt_judging(b: Dict, na: str, nb: str) -> str:
    lines = [f"=== JUDGING ANALYTICS: {na} vs {nb} ===", ""]

    dp = b.get("decision_pred")
    if dp:
        lines.append("-- Decision Prediction --")
        lines.append(f"  {na} decision win prob: {dp.get('decision_probability_a', '?')}")
        lines.append(f"  {nb} decision win prob: {dp.get('decision_probability_b', '?')}")
        dt = dp.get("decision_type", {})
        if dt:
            lines.append(f"  Decision type: Unanimous {dt.get('unanimous', '?')}% | Split {dt.get('split', '?')}% | Majority {dt.get('majority', '?')}%")
        lines.append(f"  10-8 round likelihood: {dp.get('ten_eight_likelihood', '?')}")
        lines.append("")

        cards = dp.get("judge_cards", [])
        if cards:
            lines.append("-- Judge Cards --")
            for card in cards:
                lines.append(f"  {card.get('judge', '?')}: {na} {card.get('rounds_for_a', '?')} - {nb} {card.get('rounds_for_b', '?')} (leans {card.get('leans_toward', '?')})")
            lines.append("")

    fl = b.get("fight_location")
    if fl:
        dist = fl.get("location_distribution", {})
        lines.append("-- Fight Location (time spent) --")
        lines.append(f"  Range: {dist.get('range', '?')}%")
        lines.append(f"  Clinch: {dist.get('clinch', '?')}%")
        lines.append(f"  Ground: {dist.get('ground', '?')}%")
        lines.append("")

    return "\n".join(lines)


def _fmt_sentiment(b: Dict, na: str, nb: str) -> str:
    lines = [f"=== SENTIMENT & MARKET ANALYTICS: {na} vs {nb} ===", ""]

    sim = b.get("simulation") or b.get("advanced_sim")
    if sim:
        wp = sim.get("win_probability", {})
        lines.append("-- Simulation Win Probabilities --")
        for name, prob in wp.items():
            lines.append(f"  {name}: {prob}%")
        lines.append("")

    adv = b.get("advanced_sim")
    if adv:
        ci = adv.get("confidence_interval_90", {})
        if ci:
            lines.append(f"-- 90% Confidence Interval ({na}) --")
            lines.append(f"  Lower: {ci.get('lower', '?')}%")
            lines.append(f"  Mean: {ci.get('mean', '?')}%")
            lines.append(f"  Upper: {ci.get('upper', '?')}%")
            lines.append("")

    # Market / odds data from prefetched stats
    for label, stats_key in [(na, "stats_a"), (nb, "stats_b")]:
        st = b.get(stats_key, {})
        odds = st.get("odds")
        if odds:
            lines.append(f"-- {label} Market Odds --")
            if isinstance(odds, dict):
                for k, v in odds.items():
                    lines.append(f"  {k}: {v}")
            else:
                lines.append(f"  {odds}")
            lines.append("")

    return "\n".join(lines)


def _fmt_metadata(b: Dict, na: str, nb: str) -> str:
    lines = [f"=== METADATA ANALYTICS: {na} vs {nb} ===", ""]

    for label, aging_key, stats_key in [
        (na, "aging_a", "stats_a"), (nb, "aging_b", "stats_b")
    ]:
        ag = b.get(aging_key)
        st = b.get(stats_key, {})
        lines.append(f"-- {label} --")
        lines.append(f"  Record: {st.get('record', 'N/A')}")
        if ag:
            lines.append(f"  Age: {ag.get('age', '?')}")
            cp = ag.get("career_phase", {})
            lines.append(f"  Career phase: {cp.get('phase', '?')}")
            lines.append(f"  Composite age score: {ag.get('composite_age_score', '?')}/100")
        else:
            lines.append(f"  Age: {st.get('age', 'N/A')}")
        lines.append(f"  Height: {st.get('height', 'N/A')}")
        lines.append(f"  Reach: {st.get('reach', 'N/A')}")
        lines.append(f"  Stance: {st.get('stance', 'N/A')}")
        lines.append(f"  Weight: {st.get('weight', 'N/A')}")
        lines.append("")

    return "\n".join(lines)


def _fmt_knowledge(b: Dict, na: str, nb: str) -> str:
    lines = [f"=== KNOWLEDGE ANALYTICS: {na} vs {nb} ===", ""]

    # Shared opponent analysis is external; note availability
    lines.append("-- Shared Opponent Analysis --")
    lines.append("  (Requires HistoryDB; include via get_shared_opponent_analysis if available)")
    lines.append("")

    m = b.get("matchup")
    if m:
        lines.append("-- Historical Matchup Patterns --")
        lines.append(f"  Matchup type: {m.get('matchup_type', '?')}")
        lines.append(f"  Description: {m.get('matchup_description', '')}")
        sa = _safe_get(m, "fighter_a_style")
        sb = _safe_get(m, "fighter_b_style")
        if sa:
            lines.append(f"  {na} primary archetype: {sa.get('primary_style', '?')}")
        if sb:
            lines.append(f"  {nb} primary archetype: {sb.get('primary_style', '?')}")
        lines.append("")

    return "\n".join(lines)


def _fmt_weightcut(b: Dict, na: str, nb: str) -> str:
    lines = [f"=== WEIGHT CUT ANALYTICS: {na} vs {nb} ===", ""]

    for label, aging_key, stats_key in [
        (na, "aging_a", "stats_a"), (nb, "aging_b", "stats_b")
    ]:
        ag = b.get(aging_key)
        st = b.get(stats_key, {})
        lines.append(f"-- {label} --")
        lines.append(f"  Weight: {st.get('weight', 'N/A')}")
        lines.append(f"  Height: {st.get('height', 'N/A')}")
        lines.append(f"  Reach: {st.get('reach', 'N/A')}")
        if ag:
            lines.append(f"  Age: {ag.get('age', '?')}")
            lines.append(f"  Composite age score: {ag.get('composite_age_score', '?')}/100")
            sm = ag.get("skill_multipliers", {})
            lines.append(f"  Cardio multiplier: {sm.get('cardio', '?')}")
        lines.append(f"  Weight class: {st.get('weight_class', 'N/A')}")
        lines.append("")

    pe = b.get("physical_edge")
    if pe:
        lines.append("-- Physical Edges --")
        lines.append(f"  Reach differential: {pe.get('reach_diff_inches', 0)} inches")
        lines.append(f"  Height differential: {pe.get('height_diff_inches', 0)} inches")
        lines.append(f"  Reach significant: {pe.get('reach_significant', False)}")
        lines.append("")

    return "\n".join(lines)


def _fmt_prediction(b: Dict, na: str, nb: str) -> str:
    """Full bundle dump for the prediction specialist."""
    sections = [
        _fmt_style(b, na, nb),
        _fmt_form(b, na, nb),
        _fmt_damage(b, na, nb),
        _fmt_clinch(b, na, nb),
        _fmt_gameplan(b, na, nb),
        _fmt_pace(b, na, nb),
        _fmt_judging(b, na, nb),
        _fmt_sentiment(b, na, nb),
    ]
    header = f"=== FULL PREDICTION ANALYTICS: {na} vs {nb} ===\n"
    return header + "\n".join(sections)


# Registry mapping specialist key -> formatter function
_SPECIALIST_FORMATTERS = {
    "style": _fmt_style,
    "form": _fmt_form,
    "grappling": _fmt_grappling,
    "clinch": _fmt_clinch,
    "damage": _fmt_damage,
    "pace": _fmt_pace,
    "fight_iq": _fmt_fight_iq,
    "gameplan": _fmt_gameplan,
    "scramble": _fmt_scramble,
    "judging": _fmt_judging,
    "sentiment": _fmt_sentiment,
    "metadata": _fmt_metadata,
    "knowledge": _fmt_knowledge,
    "weightcut": _fmt_weightcut,
    "prediction": _fmt_prediction,
}


# ---------------------------------------------------------------------------
# 3. FORMAT ANALYTICS SUMMARY
# ---------------------------------------------------------------------------

def format_analytics_summary(analytics_bundle: Dict[str, Any]) -> str:
    """
    Return a clean text summary of ALL analytics for the coordinator/user.

    Includes:
    - Style matchup classification
    - Physical edges (reach, height)
    - Aging profiles for both fighters
    - Simulation win probabilities + confidence interval
    - Method distribution
    - Fight location prediction
    - Key statistical edges
    """
    b = analytics_bundle
    na = b.get("fighter_a", "Fighter A")
    nb = b.get("fighter_b", "Fighter B")

    lines = [
        "=" * 60,
        f"  ANALYTICS SUMMARY: {na} vs {nb}",
        "=" * 60,
        "",
    ]

    # Style matchup
    m = b.get("matchup")
    if m:
        lines.append(f"MATCHUP: {m.get('matchup_type', '?')}")
        lines.append(f"  {m.get('matchup_description', '')}")
        sa = _safe_get(m, "fighter_a_style")
        sb = _safe_get(m, "fighter_b_style")
        if sa:
            lines.append(f"  {na}: {sa.get('primary_style', '?')} ({sa.get('primary_score', '?')})")
        if sb:
            lines.append(f"  {nb}: {sb.get('primary_style', '?')} ({sb.get('primary_score', '?')})")
        lines.append("")

    # Physical edges
    pe = b.get("physical_edge")
    if pe:
        reach_diff = pe.get("reach_diff_inches", 0)
        height_diff = pe.get("height_diff_inches", 0)
        lines.append("PHYSICAL EDGES:")
        if reach_diff != 0:
            leader = na if reach_diff > 0 else nb
            lines.append(f"  Reach: {leader} +{abs(reach_diff)} inches{' (SIGNIFICANT)' if pe.get('reach_significant') else ''}")
        else:
            lines.append("  Reach: Even")
        if height_diff != 0:
            leader = na if height_diff > 0 else nb
            lines.append(f"  Height: {leader} +{abs(height_diff)} inches")
        else:
            lines.append("  Height: Even")
        lines.append("")

    # Aging profiles
    for label, aging_key in [(na, "aging_a"), (nb, "aging_b")]:
        ag = b.get(aging_key)
        if ag:
            cp = ag.get("career_phase", {})
            reg = ag.get("regression", {})
            lines.append(f"AGING - {label} (age {ag.get('age', '?')}):")
            lines.append(f"  Phase: {cp.get('phase', '?')} | Score: {ag.get('composite_age_score', '?')}/100")
            if reg.get("is_regressing"):
                lines.append(f"  WARNING: Showing regression (score {reg.get('regression_score', '?')}, flags: {', '.join(reg.get('flags', []))})")
            lines.append(f"  {cp.get('prediction_note', '')}")
            lines.append("")

    # Simulation results
    sim = b.get("advanced_sim") or b.get("simulation")
    if sim:
        wp = sim.get("win_probability", {})
        lines.append("SIMULATION:")
        for name, prob in wp.items():
            lines.append(f"  {name}: {prob}%")

        ci = None
        if b.get("advanced_sim"):
            ci = b["advanced_sim"].get("confidence_interval_90")
        if ci:
            lines.append(f"  90% CI ({na}): {ci.get('lower', '?')}% - {ci.get('upper', '?')}%")

        md = sim.get("method_distribution", {})
        lines.append(f"  Methods: KO/TKO {md.get('ko_tko', '?')}% | Sub {md.get('submission', '?')}% | Dec {md.get('decision', '?')}%")
        lines.append("")

    # Fight location
    fl = b.get("fight_location")
    if fl:
        dist = fl.get("location_distribution", {})
        lines.append("FIGHT LOCATION:")
        lines.append(f"  {fl.get('fight_location_description', '?')}")
        lines.append(f"  Range {dist.get('range', '?')}% | Clinch {dist.get('clinch', '?')}% | Ground {dist.get('ground', '?')}%")
        lines.append("")

    # Key statistical edges
    if sim:
        edge = sim.get("statistical_edge", {})
        lines.append("KEY STATISTICAL EDGES ({} perspective):".format(na))
        for dim, val in sorted(edge.items(), key=lambda x: abs(x[1]), reverse=True):
            if abs(val) >= 0.01:
                direction = "+" if val > 0 else ""
                lines.append(f"  {dim}: {direction}{val:.3f}")
        lines.append("")

    lines.append("=" * 60)
    return "\n".join(lines)
