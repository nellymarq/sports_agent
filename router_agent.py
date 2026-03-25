# router_agent.py
# S-tier dynamic routing with robust debug specialist triggers
# and style-aware specialist selection.

from typing import List, Dict, Any, Optional
from logger import info, debug, error

CORE_FOUR = ["style", "form", "sentiment", "weightcut"]

DYNAMIC_SPECIALISTS = [
    "metadata",
    "pace",
    "grappling",
    "fight_iq",
    "scramble",
    "damage",
    "gameplan",
    "judging",
    "knowledge",
    "clinch",
]

DEBUG_SPECIALISTS = [
    "routing_debug",
    "coordinator_debug",
    "critic_debug",
    "memory_debug",
]

FULL_SPECIALIST_LIST = CORE_FOUR + DYNAMIC_SPECIALISTS


def _normalize(text: str) -> str:
    return (text or "").lower().strip()


def _detect_question_type(text: str) -> str:
    t = _normalize(text)

    # Event-aware detection
    if "ufc" in t and "main event" in t:
        return "event_who_wins"
    if "next ufc" in t:
        return "event_who_wins"
    if any(k in t for k in ["ufc ", "ufc-", "ufc:"]) and any(
        kw in t for kw in ["who wins", "who takes", "who do you favor"]
    ):
        return "event_who_wins"

    if any(k in t for k in ["who wins", "who takes", "who do you favor", "who would win", "predict", "prediction", "pick"]):
        return "who_wins"
    if any(k in t for k in ["style", "archetype", "how does he fight", "what kind of fighter", "fighting style"]):
        return "style_profile"
    if any(k in t for k in ["weakness", "vulnerable", "susceptible", "path to beat", "how do you beat", "exploit"]):
        return "weakness"
    if any(k in t for k in ["gameplan", "strategy", "approach", "path to victory", "how should", "keys to victory", "game plan"]):
        return "gameplan"
    if any(k in t for k in ["breakdown", "full analysis", "scouting", "profile", "vs", "versus", "matchup", "break down", "analyze"]):
        return "who_wins"
    if any(k in t for k in ["odds", "value bet", "value bets", "betting", "edge"]):
        return "who_wins"
    if any(k in t for k in ["card breakdown", "full card", "entire card", "all fights"]):
        return "event_who_wins"

    return "general"


def _memory_suggests_full_mode(semantic_memory: str, episodic_memory: List[str]) -> bool:
    if semantic_memory:
        return True

    joined_epi = _normalize(" ".join(episodic_memory or []))
    if any(k in joined_epi for k in ["full analysis", "deep dive", "comprehensive", "scouting report"]):
        return True

    return False


def _base_keyword_routing(text: str) -> List[str]:
    specialists = CORE_FOUR.copy()
    t = _normalize(text)

    if any(w in t for w in ["reach", "height", "age", "stance", "frame", "dimensions", "metadata", "physicals"]):
        specialists.append("metadata")

    if any(w in t for w in ["pace", "pressure", "tempo", "output", "volume", "workrate"]):
        specialists.append("pace")

    if any(w in t for w in ["grappling", "wrestling", "scramble", "takedown", "ground", "clinch"]):
        specialists.append("grappling")

    if any(w in t for w in ["fight iq", "decision-making", "ringcraft", "adaptation", "reads", "adjustments"]):
        specialists.append("fight_iq")

    if any(w in t for w in ["scramble", "chain wrestling", "mat return", "reversal", "scrambling"]):
        specialists.append("scramble")

    if any(w in t for w in ["durability", "chin", "attrition", "damage", "recovery", "body work"]):
        specialists.append("damage")

    if any(w in t for w in ["gameplan", "strategy", "approach", "tactics", "path to victory"]):
        specialists.append("gameplan")

    if any(w in t for w in ["judging", "scorecard", "unified rules", "optics", "robbery"]):
        specialists.append("judging")

    if any(w in t for w in ["knowledge", "archetype", "long-term", "evolution", "career arc"]):
        specialists.append("knowledge")

    if any(w in t for w in ["clinch", "dirty boxing", "cage control", "cage wrestling", "fence", "underhook"]):
        specialists.append("clinch")

    return list(dict.fromkeys(specialists))


def _intent_enhanced_routing(question_type: str, current: List[str]) -> List[str]:
    specialists = set(current)

    if question_type in ("who_wins", "event_who_wins"):
        specialists.update(DYNAMIC_SPECIALISTS)

    elif question_type == "style_profile":
        specialists.update(["style", "metadata", "pace", "knowledge"])

    elif question_type == "weakness":
        specialists.update(["damage", "grappling", "fight_iq", "pace"])

    elif question_type == "gameplan":
        specialists.update(["gameplan", "fight_iq", "pace", "grappling", "damage"])

    ordered = [s for s in FULL_SPECIALIST_LIST if s in specialists]
    return ordered


def _style_enhanced_routing(
    specialists: List[str],
    fighter_stats: Optional[List[Dict[str, Any]]] = None,
) -> List[str]:
    """
    Enhance specialist selection based on fighter style classifications.
    Only applies when prefetched fighter stats are available.
    """
    if not fighter_stats or len(fighter_stats) < 2:
        return specialists

    try:
        from data.style_classifier import classify_matchup
        matchup = classify_matchup(fighter_stats[0], fighter_stats[1])
        recommended = matchup.get("recommended_specialists", [])

        # Add recommended specialists that aren't already included
        enhanced = list(specialists)
        for spec in recommended:
            if spec not in enhanced and spec in FULL_SPECIALIST_LIST:
                enhanced.append(spec)

        # Reorder to match FULL_SPECIALIST_LIST order
        ordered = [s for s in FULL_SPECIALIST_LIST if s in enhanced]
        # Add any extras not in FULL_SPECIALIST_LIST (like debug)
        for s in enhanced:
            if s not in ordered:
                ordered.append(s)

        return ordered
    except Exception:
        return specialists


async def router_agent(
    llm,
    user_input: str,
    semantic_memory=None,
    episodic_memory=None,
    fighter_stats: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    S-tier router:
    - Uses question type + keyword routing
    - Memory-aware full-mode
    - Robust debug triggers
    - Returns:
        - mode
        - specialists
        - question_type
        - debug_specialists
    """
    info("Router agent invoked")

    text = _normalize(user_input)
    sem = semantic_memory or ""
    epi = episodic_memory or []

    debug_triggers = {
        "routing_debug": [
            "explain routing",
            "routing",
            "routing debug",
            "why these specialists",
        ],
        "coordinator_debug": [
            "explain coordinator",
            "coordinator",
            "coordinator debug",
        ],
        "critic_debug": [
            "explain critic",
            "critic",
            "critic debug",
        ],
        "memory_debug": [
            "explain memory",
            "memory",
            "memory debug",
        ],
    }

    requested_debug: List[str] = []
    for dbg, triggers in debug_triggers.items():
        for trig in triggers:
            if trig in text:
                requested_debug.append(dbg)
                break

    requested_debug = [d for d in dict.fromkeys(requested_debug) if d in DEBUG_SPECIALISTS]

    qtype = _detect_question_type(text)
    debug(f"Router: detected question type = {qtype}")

    # MEMORY-DRIVEN FULL MODE
    if _memory_suggests_full_mode(sem, epi):
        specialists = FULL_SPECIALIST_LIST.copy() + requested_debug
        specialists = list(dict.fromkeys(specialists))
        info(f"Router selected specialists (memory full-mode): {specialists}")
        return {
            "mode": "autonomous",
            "specialists": specialists,
            "question_type": qtype,
            "debug_specialists": requested_debug,
        }

    # INPUT-DRIVEN FULL MODE
    full_triggers = [
        "matchup", "breakdown", "full analysis", "full report", "scouting",
        "profile", "vs", "versus", "how does", "compare", "analysis",
        "stylistic", "fight iq", "gameplan", "scramble", "durability",
        "judging", "knowledge graph", "who wins", "who would win",
        "main event", "predict", "prediction", "break down", "analyze",
        "odds", "value bet", "betting", "full card",
    ]

    if any(t in text for t in full_triggers) and qtype in ("who_wins", "event_who_wins", "general"):
        specialists = FULL_SPECIALIST_LIST.copy() + requested_debug
        specialists = list(dict.fromkeys(specialists))
        info(f"Router selected specialists (input full-mode): {specialists}")
        return {
            "mode": "autonomous",
            "specialists": specialists,
            "question_type": qtype,
            "debug_specialists": requested_debug,
        }

    # KEYWORD-BASED ROUTING
    specialists = _base_keyword_routing(text)
    specialists = _intent_enhanced_routing(qtype, specialists)

    # STYLE-AWARE ENHANCEMENT (when fighter stats available)
    if fighter_stats:
        specialists = _style_enhanced_routing(specialists, fighter_stats)

    specialists.extend(requested_debug)
    specialists = list(dict.fromkeys(specialists))

    info(f"Router selected specialists: {specialists}")
    return {
        "mode": "autonomous",
        "specialists": specialists,
        "question_type": qtype,
        "debug_specialists": requested_debug,
    }
