# specialists/__init__.py
# Export all specialists so orchestrator + tests can import them cleanly.
#
# The 15 standard domain specialists are generated from a shared base class
# (base_specialist.py) — only the specialist name differs between them.
# Debug specialists and prediction_specialist have unique logic and remain
# in their own files.

from .base_specialist import make_specialist

# --- Standard domain specialists (generated from shared base) ---
run_style_specialist = make_specialist("Style")
run_form_specialist = make_specialist("Form")
run_sentiment_specialist = make_specialist("Sentiment")
run_weightcut_specialist = make_specialist("Weightcut")
run_general_specialist = make_specialist("General")
run_metadata_specialist = make_specialist("Metadata")
run_pace_specialist = make_specialist("Pace")
run_grappling_specialist = make_specialist("Grappling")
run_fight_iq_specialist = make_specialist("Fight IQ")
run_scramble_specialist = make_specialist("Scramble")
run_damage_specialist = make_specialist("Damage")
run_gameplan_specialist = make_specialist("Gameplan")
run_judging_specialist = make_specialist("Judging")
run_knowledge_specialist = make_specialist("Knowledge")
run_clinch_specialist = make_specialist("Clinch")

# --- Debug specialists (unique logic, separate files) ---
from .routing_debug_specialist import run_routing_debug_specialist
from .coordinator_debug_specialist import run_coordinator_debug_specialist
from .critic_debug_specialist import run_critic_debug_specialist
from .memory_debug_specialist import run_memory_debug_specialist

__all__ = [
    "run_style_specialist",
    "run_form_specialist",
    "run_sentiment_specialist",
    "run_weightcut_specialist",
    "run_general_specialist",
    "run_metadata_specialist",
    "run_pace_specialist",
    "run_grappling_specialist",
    "run_fight_iq_specialist",
    "run_scramble_specialist",
    "run_damage_specialist",
    "run_gameplan_specialist",
    "run_judging_specialist",
    "run_knowledge_specialist",
    "run_clinch_specialist",

    # Debug specialists
    "run_routing_debug_specialist",
    "run_coordinator_debug_specialist",
    "run_critic_debug_specialist",
    "run_memory_debug_specialist",
]
