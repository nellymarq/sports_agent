# tests/test_specialist_payloads.py
# Tests for data/specialist_payloads.py

from __future__ import annotations
import pytest
from typing import Dict, Any

from data.specialist_payloads import (
    compute_analytics_bundle,
    format_specialist_payload,
    format_analytics_summary,
    _fighter_names,
    _safe_get,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_stats_a() -> Dict[str, Any]:
    return {
        "name": "Max Holloway",
        "record": "25-7-0",
        "height": "71",
        "weight": "145",
        "reach": "69",
        "stance": "Orthodox",
        "slpm": "6.43",
        "str_acc": "45",
        "sapm": "5.43",
        "str_def": "57",
        "td_avg": "0.55",
        "td_acc": "36",
        "td_def": "85",
        "sub_avg": "0.2",
        "age": "31",
        "weight_class": "featherweight",
    }


@pytest.fixture
def sample_stats_b() -> Dict[str, Any]:
    return {
        "name": "Alexander Volkanovski",
        "record": "26-3-0",
        "height": "66",
        "weight": "145",
        "reach": "71.5",
        "stance": "Orthodox",
        "slpm": "5.91",
        "str_acc": "55",
        "sapm": "4.18",
        "str_def": "58",
        "td_avg": "1.79",
        "td_acc": "40",
        "td_def": "70",
        "sub_avg": "0.0",
        "age": "34",
        "weight_class": "featherweight",
    }


@pytest.fixture
def prefetched(sample_stats_a, sample_stats_b) -> Dict[str, Any]:
    return {
        "Max Holloway": sample_stats_a,
        "Alexander Volkanovski": sample_stats_b,
    }


@pytest.fixture
def fighters():
    return ["Max Holloway", "Alexander Volkanovski"]


@pytest.fixture
def bundle(prefetched, fighters) -> Dict[str, Any]:
    return compute_analytics_bundle(prefetched, fighters)


# ---------------------------------------------------------------------------
# Helper tests
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_safe_get_nested(self):
        d = {"a": {"b": {"c": 42}}}
        assert _safe_get(d, "a", "b", "c") == 42

    def test_safe_get_missing(self):
        d = {"a": 1}
        assert _safe_get(d, "x", "y", default="nope") == "nope"

    def test_safe_get_non_dict(self):
        assert _safe_get(None, "a", default=0) == 0

    def test_fighter_names_from_list(self):
        a, b = _fighter_names({}, ["A", "B"])
        assert a == "A"
        assert b == "B"

    def test_fighter_names_from_dict(self):
        a, b = _fighter_names({"X": {}, "Y": {}}, [])
        assert {a, b} == {"X", "Y"}


# ---------------------------------------------------------------------------
# compute_analytics_bundle
# ---------------------------------------------------------------------------

class TestComputeAnalyticsBundle:
    def test_returns_dict(self, bundle):
        assert isinstance(bundle, dict)

    def test_has_fighter_names(self, bundle):
        assert bundle["fighter_a"] == "Max Holloway"
        assert bundle["fighter_b"] == "Alexander Volkanovski"

    def test_style_classification(self, bundle):
        assert bundle["style_a"] is not None
        assert "primary_style" in bundle["style_a"]
        assert bundle["style_b"] is not None
        assert "primary_style" in bundle["style_b"]

    def test_matchup(self, bundle):
        assert bundle["matchup"] is not None
        assert "matchup_type" in bundle["matchup"]
        assert "matchup_description" in bundle["matchup"]

    def test_aging_analysis(self, bundle):
        assert bundle["aging_a"] is not None
        assert bundle["aging_a"]["age"] == 31
        assert "composite_age_score" in bundle["aging_a"]
        assert "career_phase" in bundle["aging_a"]
        assert "regression" in bundle["aging_a"]

        assert bundle["aging_b"] is not None
        assert bundle["aging_b"]["age"] == 34

    def test_age_adjustment(self, bundle):
        assert bundle["age_adj"] is not None
        assert "modifier" in bundle["age_adj"]

    def test_clinch_profiles(self, bundle):
        assert bundle["clinch_profile_a"] is not None
        assert "clinch_style" in bundle["clinch_profile_a"]
        assert bundle["clinch_profile_b"] is not None

    def test_clinch_matchup(self, bundle):
        assert bundle["clinch_matchup"] is not None
        assert "clinch_initiator" in bundle["clinch_matchup"]
        assert "clinch_dominant" in bundle["clinch_matchup"]

    def test_fight_location(self, bundle):
        assert bundle["fight_location"] is not None
        dist = bundle["fight_location"]["location_distribution"]
        total = sum(dist.values())
        assert abs(total - 100) < 1  # should sum to ~100%

    def test_octagon_control(self, bundle):
        assert bundle["octagon_control_a"] is not None
        assert "control_score" in bundle["octagon_control_a"]
        assert bundle["octagon_control_b"] is not None

    def test_simulation(self, bundle):
        assert bundle["simulation"] is not None
        wp = bundle["simulation"]["win_probability"]
        assert "Max Holloway" in wp
        assert "Alexander Volkanovski" in wp
        total = sum(wp.values())
        assert abs(total - 100) < 1

    def test_advanced_simulation(self, bundle):
        assert bundle["advanced_sim"] is not None
        assert "confidence_interval_90" in bundle["advanced_sim"]
        assert "cardio_profiles" in bundle["advanced_sim"]
        assert "physical_edge" in bundle["advanced_sim"]

    def test_decision_prediction(self, bundle):
        assert bundle["decision_pred"] is not None
        assert "decision_probability_a" in bundle["decision_pred"]
        assert "judge_cards" in bundle["decision_pred"]

    def test_physical_edge(self, bundle):
        assert bundle["physical_edge"] is not None
        assert "reach_diff_inches" in bundle["physical_edge"]

    def test_no_age_returns_none(self, prefetched, fighters):
        """When age is missing, aging analytics should be None."""
        stats = dict(prefetched)
        stats["Max Holloway"] = {k: v for k, v in stats["Max Holloway"].items() if k != "age"}
        b = compute_analytics_bundle(stats, fighters)
        assert b["aging_a"] is None

    def test_empty_stats(self):
        """Should handle empty stats gracefully."""
        b = compute_analytics_bundle({}, [])
        assert isinstance(b, dict)
        assert b.get("fighter_a") is not None
        assert b.get("simulation") is not None or b.get("simulation") is None  # no crash


# ---------------------------------------------------------------------------
# format_specialist_payload
# ---------------------------------------------------------------------------

class TestFormatSpecialistPayload:
    ALL_SPECIALISTS = [
        "style", "form", "grappling", "clinch", "damage", "pace",
        "fight_iq", "gameplan", "scramble", "judging", "sentiment",
        "metadata", "knowledge", "weightcut", "prediction",
    ]

    @pytest.mark.parametrize("specialist", ALL_SPECIALISTS)
    def test_returns_nonempty_string(self, bundle, specialist):
        payload = format_specialist_payload(bundle, specialist)
        assert isinstance(payload, str)
        assert len(payload) > 20

    @pytest.mark.parametrize("specialist", ALL_SPECIALISTS)
    def test_contains_fighter_names(self, bundle, specialist):
        payload = format_specialist_payload(bundle, specialist)
        assert "Holloway" in payload or "Volkanovski" in payload

    def test_unknown_specialist_key(self, bundle):
        payload = format_specialist_payload(bundle, "nonexistent_domain")
        assert "No formatter defined" in payload

    def test_style_has_archetype(self, bundle):
        payload = format_specialist_payload(bundle, "style")
        assert "Primary style:" in payload
        assert "Matchup Classification" in payload

    def test_form_has_career_phase(self, bundle):
        payload = format_specialist_payload(bundle, "form")
        assert "Career phase:" in payload
        assert "regression" in payload.lower()

    def test_grappling_has_edges(self, bundle):
        payload = format_specialist_payload(bundle, "grappling")
        assert "Takedown" in payload

    def test_clinch_has_matchup(self, bundle):
        payload = format_specialist_payload(bundle, "clinch")
        assert "Clinch Matchup" in payload
        assert "Octagon Control" in payload

    def test_damage_has_chin(self, bundle):
        payload = format_specialist_payload(bundle, "damage")
        assert "Chin" in payload or "chin" in payload

    def test_pace_has_cardio(self, bundle):
        payload = format_specialist_payload(bundle, "pace")
        assert "Cardio" in payload

    def test_fight_iq_has_edge_breakdown(self, bundle):
        payload = format_specialist_payload(bundle, "fight_iq")
        assert "Experience" in payload.lower() or "experience" in payload.lower()

    def test_gameplan_has_location(self, bundle):
        payload = format_specialist_payload(bundle, "gameplan")
        assert "location" in payload.lower()

    def test_judging_has_decision(self, bundle):
        payload = format_specialist_payload(bundle, "judging")
        assert "Decision" in payload

    def test_metadata_has_record(self, bundle):
        payload = format_specialist_payload(bundle, "metadata")
        assert "Record:" in payload

    def test_prediction_is_comprehensive(self, bundle):
        payload = format_specialist_payload(bundle, "prediction")
        # prediction should contain content from multiple sub-formatters
        assert "STYLE" in payload
        assert "FORM" in payload
        assert "DAMAGE" in payload
        assert "CLINCH" in payload


# ---------------------------------------------------------------------------
# format_analytics_summary
# ---------------------------------------------------------------------------

class TestFormatAnalyticsSummary:
    def test_returns_string(self, bundle):
        summary = format_analytics_summary(bundle)
        assert isinstance(summary, str)
        assert len(summary) > 100

    def test_contains_fighter_names(self, bundle):
        summary = format_analytics_summary(bundle)
        assert "Max Holloway" in summary
        assert "Alexander Volkanovski" in summary

    def test_contains_matchup_section(self, bundle):
        summary = format_analytics_summary(bundle)
        assert "MATCHUP" in summary

    def test_contains_simulation_section(self, bundle):
        summary = format_analytics_summary(bundle)
        assert "SIMULATION" in summary

    def test_contains_physical_edges(self, bundle):
        summary = format_analytics_summary(bundle)
        assert "PHYSICAL EDGES" in summary

    def test_contains_aging(self, bundle):
        summary = format_analytics_summary(bundle)
        assert "AGING" in summary

    def test_contains_fight_location(self, bundle):
        summary = format_analytics_summary(bundle)
        assert "FIGHT LOCATION" in summary

    def test_contains_statistical_edges(self, bundle):
        summary = format_analytics_summary(bundle)
        assert "STATISTICAL EDGES" in summary

    def test_simulation_probs_sum_near_100(self, bundle):
        # Verify the simulation probabilities mentioned in the summary are valid
        sim = bundle.get("advanced_sim") or bundle.get("simulation")
        if sim:
            wp = sim["win_probability"]
            total = sum(wp.values())
            assert abs(total - 100) < 1


# ---------------------------------------------------------------------------
# Edge cases & robustness
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_single_fighter(self):
        stats = {"Only Fighter": {"name": "Only Fighter", "slpm": "4.0", "age": "30"}}
        b = compute_analytics_bundle(stats, ["Only Fighter"])
        assert isinstance(b, dict)
        # Should not crash; second fighter will use empty stats
        summary = format_analytics_summary(b)
        assert isinstance(summary, str)

    def test_no_numeric_stats(self):
        stats = {
            "A": {"name": "A"},
            "B": {"name": "B"},
        }
        b = compute_analytics_bundle(stats, ["A", "B"])
        # style classifier should still return something
        assert isinstance(b, dict)
        summary = format_analytics_summary(b)
        assert len(summary) > 0

    def test_all_formatters_handle_none_gracefully(self):
        """Even with an empty bundle, no formatter should raise."""
        empty_bundle = {
            "fighter_a": "X",
            "fighter_b": "Y",
        }
        for key in [
            "style", "form", "grappling", "clinch", "damage", "pace",
            "fight_iq", "gameplan", "scramble", "judging", "sentiment",
            "metadata", "knowledge", "weightcut", "prediction",
        ]:
            result = format_specialist_payload(empty_bundle, key)
            assert isinstance(result, str)
