# specialists/__init__.py
# Export all specialists so orchestrator + tests can import them cleanly.

from .style_specialist import run_style_specialist
from .form_specialist import run_form_specialist
from .sentiment_specialist import run_sentiment_specialist
from .weightcut_specialist import run_weightcut_specialist
from .general_specialist import run_general_specialist
from .metadata_specialist import run_metadata_specialist
from .pace_specialist import run_pace_specialist
from .grappling_specialist import run_grappling_specialist
from .fight_iq_specialist import run_fight_iq_specialist
from .scramble_specialist import run_scramble_specialist
from .damage_specialist import run_damage_specialist
from .gameplan_specialist import run_gameplan_specialist
from .judging_specialist import run_judging_specialist
from .knowledge_specialist import run_knowledge_specialist

# === NEW DEBUG SPECIALISTS ===
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

    # Debug specialists
    "run_routing_debug_specialist",
    "run_coordinator_debug_specialist",
    "run_critic_debug_specialist",
    "run_memory_debug_specialist",
]
