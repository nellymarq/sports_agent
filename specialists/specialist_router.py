# -*- coding: utf-8 -*-
# specialist_router.py
# Final-form routing logic for UFC questions → specialists.

from __future__ import annotations

from typing import Any, Dict, List

from fighter_utils import extract_fighters
from fighter_metadata import get_profile


# ------------------------------------------------------------
# Simple intent classification
# ------------------------------------------------------------

def _classify_intent(query: str, fighter_count: int) -> str:
    """
    Classify the user's intent at a coarse level.
    Returns one of: 'matchup', 'single_fighter', 'general'.
    """
    q = (query or "").lower()

    matchup_keywords = [
        "vs",
        "versus",
        "fight",
        "matchup",
        "who wins",
        "how does",
        "stylistically",
        "gameplan",
        "path to victory",
        "keys to victory",
    ]
    single_keywords = [
        "breakdown",
        "analyze",
        "analysis",
        "style",
        "strengths",
        "weaknesses",
        "how good is",
        "what do you think of",
    ]

    if fighter_count >= 2:
        return "matchup"

    if fighter_count == 1:
        if any(k in q for k in matchup_keywords):
            return "matchup"
        if any(k in q for k in single_keywords):
            return "single_fighter"

    return "general"


# ------------------------------------------------------------
# Specialist selection
# ------------------------------------------------------------

def _specialists_for_matchup() -> List[str]:
    return [
        "metadata_analysis",
        "style_analysis",
        "form_analysis",
        "weightcut_analysis",
        "gameplan_analysis",
        "critic_review",
        "coordinator_merge",
    ]


def _specialists_for_single() -> List[str]:
    return [
        "metadata_analysis",
        "style_analysis",
        "form_analysis",
        "sentiment_analysis",
        "critic_review",
        "coordinator_merge",
    ]


def _specialists_for_general() -> List[str]:
    return [
        "metadata_analysis",
        "sentiment_analysis",
        "critic_review",
        "coordinator_merge",
    ]


# ------------------------------------------------------------
# Public router API
# ------------------------------------------------------------

def route_ufc_query(user_query: str) -> Dict[str, Any]:
    """
    Final-form router:
      - extracts fighters from the query
      - classifies intent
      - selects specialists
      - returns a deterministic routing plan

    Output schema:
    {
        "mode": "single" | "multi",
        "intent": "matchup" | "single_fighter" | "general",
        "specialists": [str, ...],
        "fighters": [str, ...],
        "primary": str | None,
        "task": str,
        "raw_query": str,
    }
    """
    fighters, primary = extract_fighters(user_query)
    fighters = list(dict.fromkeys(fighters))  # dedupe, preserve order
    fighter_count = len(fighters)

    intent = _classify_intent(user_query, fighter_count)

    if intent == "matchup" and fighter_count >= 2:
        mode = "multi"
        specialists = _specialists_for_matchup()
    elif intent == "single_fighter" and fighter_count == 1:
        mode = "single"
        specialists = _specialists_for_single()
    elif fighter_count >= 2:
        # Fallback: multi-fighter general question
        mode = "multi"
        specialists = _specialists_for_matchup()
        intent = "matchup"
    elif fighter_count == 1:
        mode = "single"
        specialists = _specialists_for_single()
        intent = "single_fighter"
    else:
        mode = "single"
        specialists = _specialists_for_general()
        primary = None

    # Optionally validate primary fighter via metadata (best-effort)
    if primary:
        profile = get_profile(primary)
        if profile is None:
            # If resolution fails, keep primary as-is but don't crash
            pass

    # Build a concise task description for specialists
    if mode == "multi" and len(fighters) >= 2:
        task = (
            f"Analyze the matchup between {fighters[0]} and {fighters[1]} "
            f"based on the user query."
        )
    elif mode == "single" and fighter_count == 1:
        task = f"Analyze {fighters[0]} based on the user query."
    else:
        task = "Answer the user's general UFC question as accurately as possible."

    return {
        "mode": mode,
        "intent": intent,
        "specialists": specialists,
        "fighters": fighters,
        "primary": primary,
        "task": task,
        "raw_query": user_query,
    }
