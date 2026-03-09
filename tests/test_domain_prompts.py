# tests/test_domain_prompts.py
# Tests for domain-specific specialist prompt guidance.

import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from specialists.domain_prompts import get_domain_guidance, DOMAIN_GUIDANCE


class TestDomainGuidance:
    def test_all_core_specialists_have_guidance(self):
        core = ["style", "form", "grappling", "damage", "pace",
                "fight_iq", "gameplan", "judging", "scramble",
                "sentiment", "weightcut", "metadata", "knowledge"]
        for spec in core:
            guidance = get_domain_guidance(spec)
            assert guidance, f"No domain guidance for {spec}"
            assert len(guidance) > 100, f"Domain guidance too short for {spec}"

    def test_unknown_specialist_returns_empty(self):
        assert get_domain_guidance("nonexistent") == ""
        assert get_domain_guidance("") == ""

    def test_style_contains_archetype(self):
        g = get_domain_guidance("style")
        assert "archetype" in g.lower()
        assert "striker" in g.lower()

    def test_grappling_contains_takedown(self):
        g = get_domain_guidance("grappling")
        assert "takedown" in g.lower()
        assert "wrestling" in g.lower()

    def test_damage_contains_durability(self):
        g = get_domain_guidance("damage")
        assert "durability" in g.lower()
        assert "chin" in g.lower()

    def test_pace_contains_cardio(self):
        g = get_domain_guidance("pace")
        assert "cardio" in g.lower()
        assert "volume" in g.lower()

    def test_fight_iq_contains_adaptability(self):
        g = get_domain_guidance("fight_iq")
        assert "adapt" in g.lower()

    def test_gameplan_contains_path_to_victory(self):
        g = get_domain_guidance("gameplan")
        assert "path to victory" in g.lower()
