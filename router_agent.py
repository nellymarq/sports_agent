# router_agent.py
# 14-specialist dynamic routing + memory awareness

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
]

FULL_SPECIALIST_LIST = CORE_FOUR + DYNAMIC_SPECIALISTS


async def router_agent(
    llm,
    user_input: str,
    semantic_memory=None,
    episodic_memory=None,
) -> dict:
    """
    Determines which specialists should run.
    - Always includes core four.
    - Dynamically adds specialists based on keywords.
    - Full-analysis mode triggers all 14 specialists.
    - Memory-aware: semantic + episodic memory can trigger full mode.
    """

    info("Router agent invoked")

    text = user_input.lower().strip()

    # If we already have long-term fighter knowledge → full mode
    if semantic_memory:
        info("Router: semantic memory found → FULL 14-SPECIALIST MODE")
        return {
            "mode": "autonomous",
            "specialists": FULL_SPECIALIST_LIST.copy(),
        }

    # If recent episodic memory suggests deep prior context → full mode
    joined_epi = " ".join(episodic_memory or []).lower()
    if any(k in joined_epi for k in ["full analysis", "deep dive", "comprehensive"]):
        info("Router: episodic memory suggests deep prior context → FULL MODE")
        return {
            "mode": "autonomous",
            "specialists": FULL_SPECIALIST_LIST.copy(),
        }

    full_triggers = [
        "matchup",
        "breakdown",
        "full analysis",
        "full report",
        "scouting",
        "profile",
        "vs",
        "versus",
        "how does",
        "compare",
        "analysis",
        "stylistic",
        "fight iq",
        "gameplan",
        "scramble",
        "durability",
        "judging",
        "knowledge graph",
    ]

    for t in full_triggers:
        if t in text:
            info("Router: FULL 14-SPECIALIST MODE (input trigger)")
            return {
                "mode": "autonomous",
                "specialists": FULL_SPECIALIST_LIST.copy(),
            }

    specialists = CORE_FOUR.copy()

    if any(w in text for w in ["reach", "height", "age", "stance", "frame", "dimensions", "metadata"]):
        specialists.append("metadata")

    if any(w in text for w in ["pace", "pressure", "tempo", "output", "volume"]):
        specialists.append("pace")

    if any(w in text for w in ["grappling", "wrestling", "scramble", "takedown", "ground"]):
        specialists.append("grappling")

    if any(w in text for w in ["fight iq", "decision-making", "ringcraft", "adaptation"]):
        specialists.append("fight_iq")

    if any(w in text for w in ["scramble", "chain wrestling", "mat return", "reversal"]):
        specialists.append("scramble")

    if any(w in text for w in ["durability", "chin", "attrition", "damage", "recovery"]):
        specialists.append("damage")

    if any(w in text for w in ["gameplan", "strategy", "approach", "tactics"]):
        specialists.append("gameplan")

    if any(w in text for w in ["judging", "scorecard", "unified rules", "optics"]):
        specialists.append("judging")

    if any(w in text for w in ["knowledge", "archetype", "long-term", "evolution"]):
        specialists.append("knowledge")

    specialists = list(dict.fromkeys(specialists))

    info(f"Router selected specialists: {specialists}")

    return {
        "mode": "autonomous",
        "specialists": specialists,
    }
