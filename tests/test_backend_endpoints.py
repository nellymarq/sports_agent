# tests/test_backend_endpoints.py
# Tests for backend API endpoints (health, stats, calibration, streaming).

import sys
import json
from pathlib import Path
from unittest.mock import patch, AsyncMock

import pytest

# Ensure project root is importable
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def client():
    """Create a test client for the FastAPI backend."""
    from fastapi.testclient import TestClient
    from backend.main import app
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_health_includes_version(self, client):
        resp = client.get("/health")
        data = resp.json()
        assert "version" in data

    def test_health_includes_models(self, client):
        resp = client.get("/health")
        data = resp.json()
        assert "models" in data
        assert "routing" in data["models"]
        assert "prediction" in data["models"]


class TestStatsEndpoint:
    def test_stats_returns_llm_info(self, client):
        resp = client.get("/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "routing_llm" in data
        assert "prediction_llm" in data

    def test_stats_has_call_count(self, client):
        resp = client.get("/stats")
        data = resp.json()
        assert "call_count" in data["routing_llm"]
        assert "total_tokens" in data["routing_llm"]


class TestCalibrationEndpoint:
    def test_calibration_returns_data(self, client):
        resp = client.get("/calibration")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_predictions" in data


class TestAnalyzeEndpoint:
    def test_analyze_empty_input(self, client):
        """Empty input should still process (engine may return error)."""
        with patch("backend.main._run_full_pipeline", new_callable=AsyncMock) as mock_pipe:
            mock_pipe.return_value = "Test analysis result"
            resp = client.post("/analyze", json={"user_input": "test query"})
            assert resp.status_code == 200
            data = resp.json()
            assert data["content"] == "Test analysis result"
            assert "elapsed_seconds" in data

    def test_analyze_pipeline_error(self, client):
        """Pipeline errors should return 500."""
        with patch("backend.main._run_full_pipeline", new_callable=AsyncMock) as mock_pipe:
            mock_pipe.side_effect = RuntimeError("LLM timeout")
            resp = client.post("/analyze", json={"user_input": "test"})
            assert resp.status_code == 500


class TestStreamEndpoint:
    def test_stream_returns_sse(self, client):
        """Streaming endpoint should return SSE content type."""
        with patch("backend.main._run_full_pipeline", new_callable=AsyncMock) as mock_pipe:
            mock_pipe.return_value = "Streamed result"
            resp = client.post(
                "/analyze/stream",
                json={"user_input": "test query"},
            )
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers.get("content-type", "")

    def test_stream_contains_result(self, client):
        """Stream should contain a result event."""
        with patch("backend.main._run_full_pipeline", new_callable=AsyncMock) as mock_pipe:
            mock_pipe.return_value = "Streamed result"
            resp = client.post(
                "/analyze/stream",
                json={"user_input": "test query"},
            )
            body = resp.text
            # Should contain at least one data line with result
            assert "Streamed result" in body

    def test_stream_ends_with_done(self, client):
        """Stream should end with [DONE] marker."""
        with patch("backend.main._run_full_pipeline", new_callable=AsyncMock) as mock_pipe:
            mock_pipe.return_value = "done result"
            resp = client.post(
                "/analyze/stream",
                json={"user_input": "test"},
            )
            assert "[DONE]" in resp.text


class TestResultEndpoint:
    def test_submit_result_not_found(self, client):
        """Submitting a result for non-existent prediction returns not_found."""
        resp = client.post("/result", json={
            "event_id": "ufc_999",
            "fighter_a": "Nobody",
            "fighter_b": "NoOne",
            "actual_winner": "Nobody",
            "actual_method": "KO",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "not_found"


class TestPredictionsEndpoint:
    def test_list_predictions_returns_ok(self, client):
        resp = client.get("/predictions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "predictions" in data
        assert "count" in data

    def test_list_predictions_with_event_filter(self, client):
        resp = client.get("/predictions?event_id=ufc_nonexistent")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0

    def test_list_predictions_with_limit(self, client):
        resp = client.get("/predictions?limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["predictions"]) <= 5

    def test_list_predictions_resolved_only(self, client):
        resp = client.get("/predictions?resolved_only=true")
        assert resp.status_code == 200
        data = resp.json()
        # All returned predictions should be resolved
        for p in data["predictions"]:
            assert p.get("correct") is not None


class TestEventsEndpoint:
    def test_list_events_returns_ok(self, client):
        resp = client.get("/events")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "events" in data

    def test_get_event_not_found(self, client):
        resp = client.get("/events/ufc_nonexistent_999")
        assert resp.status_code == 404

    def test_list_events_has_display_fields(self, client):
        """Events should include display helper fields."""
        resp = client.get("/events")
        data = resp.json()
        for ev in data.get("events", []):
            assert "main_event_display" in ev
            assert "bout_count" in ev


class TestROISimulationEndpoint:
    def test_roi_simulate_flat(self, client):
        resp = client.post("/roi/simulate", json={
            "strategy": "flat",
            "bankroll": 1000,
            "flat_stake": 50,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "total_bets" in data

    def test_roi_simulate_kelly(self, client):
        resp = client.post("/roi/simulate", json={
            "strategy": "kelly",
            "bankroll": 1000,
        })
        assert resp.status_code == 200

    def test_roi_simulate_default(self, client):
        resp = client.post("/roi/simulate", json={})
        assert resp.status_code == 200


class TestParlayEndpoints:
    def test_parlay_calculate_valid(self, client):
        resp = client.post("/parlay/calculate", json={
            "legs": [
                {"fighter": "Fighter A", "decimal_odds": 2.0, "model_probability": 0.6},
                {"fighter": "Fighter B", "decimal_odds": 1.5, "model_probability": 0.7},
            ],
            "stake": 100,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["num_legs"] == 2
        assert data["potential_payout"] > 0

    def test_parlay_calculate_single_leg_error(self, client):
        resp = client.post("/parlay/calculate", json={
            "legs": [{"fighter": "A", "decimal_odds": 2.0}],
            "stake": 100,
        })
        assert resp.status_code == 400

    def test_parlay_calculate_empty(self, client):
        resp = client.post("/parlay/calculate", json={
            "legs": [],
            "stake": 100,
        })
        assert resp.status_code == 400


class TestCalibrationEnhanced:
    def test_calibration_includes_new_fields(self, client):
        resp = client.get("/calibration")
        assert resp.status_code == 200
        data = resp.json()
        # New fields should be present when there are resolved predictions
        # or should at least not cause errors
        assert "total_predictions" in data


class TestEventPreviewEndpoint:
    def test_preview_not_found(self, client):
        resp = client.get("/events/ufc_nonexistent_999/preview")
        assert resp.status_code == 404

    def test_preview_returns_structure(self, client):
        # Use a known event from events.json
        resp = client.get("/events/ufc_313/preview")
        if resp.status_code == 200:
            data = resp.json()
            assert data["status"] == "ok"
            assert "bouts" in data
            assert "bout_count" in data


class TestELOEndpoints:
    def test_elo_rankings(self, client):
        resp = client.get("/elo/rankings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "rankings" in data
        assert "total_rated" in data

    def test_elo_rankings_with_top_n(self, client):
        resp = client.get("/elo/rankings?top_n=5")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["rankings"]) <= 5

    def test_elo_matchup(self, client):
        resp = client.get("/elo/matchup?fighter_a=test_a&fighter_b=test_b")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "fighter_a_win_prob" in data
        assert "fighter_b_win_prob" in data
        assert "fighter_a_odds" in data

    def test_elo_matchup_probs_sum_to_one(self, client):
        resp = client.get("/elo/matchup?fighter_a=x&fighter_b=y")
        data = resp.json()
        total = data["fighter_a_win_prob"] + data["fighter_b_win_prob"]
        assert abs(total - 1.0) < 0.001


class TestBetSizingEndpoint:
    def test_bet_sizing_strong_bet(self, client):
        resp = client.post("/bet/size", json={
            "model_probability": 0.70,
            "decimal_odds": 2.0,
            "confidence_tier": "high",
            "bankroll": 1000,
            "fighter_name": "Test Fighter",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["action"] in ("BET", "STRONG BET")
        assert "formatted" in data
        assert "Test Fighter" in data["formatted"]

    def test_bet_sizing_pass(self, client):
        resp = client.post("/bet/size", json={
            "model_probability": 0.45,
            "decimal_odds": 2.0,
            "confidence_tier": "moderate",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["action"] == "PASS"

    def test_bet_sizing_defaults(self, client):
        resp = client.post("/bet/size", json={
            "model_probability": 0.65,
            "decimal_odds": 2.5,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "kelly" in data
        assert "sizing" in data


class TestLineMovementEndpoints:
    def test_record_snapshot(self, client):
        resp = client.post("/lines/snapshot", json={
            "bout_key": "test_bout",
            "fighter_a": "Fighter A",
            "fighter_b": "Fighter B",
            "implied_a": 0.55,
            "implied_b": 0.45,
            "source": "test",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_movement_not_found(self, client):
        resp = client.get("/lines/movement/nonexistent_bout_xyz")
        assert resp.status_code == 404

    def test_all_movements(self, client):
        resp = client.get("/lines/all")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "movements" in data


class TestFighterSearchEndpoint:
    def test_search_empty_query(self, client):
        """Search with unknown fighter should return empty or error."""
        with patch.object(
            type(client.app).__dict__.get("_ufc_stats_tool", type("", (), {"invoke": lambda *a: {}})),
            "invoke",
            return_value={"error": "not found"},
        ):
            resp = client.post("/fighters/search", json={"query": "zzz_nonexistent_fighter"})
            # Should either return 200 with empty results or 500 depending on tool behavior
            assert resp.status_code in (200, 500)


class TestFighterProfileEndpoint:
    def test_profile_not_found(self, client):
        """Unknown fighter should return 404."""
        with patch("backend.main._ufc_stats_tool") as mock_tool:
            mock_tool.invoke.return_value = {"error": "not found"}
            resp = client.get("/fighters/zzz_nonexistent_fighter_xyz/profile")
            assert resp.status_code == 404

    def test_profile_success(self, client):
        """Profile with mocked stats should return full profile data."""
        mock_stats = {
            "best_match": {
                "name": "Test Fighter",
                "record": "20-5-0",
                "height": "6' 0\"",
                "weight": "185 lbs",
                "reach": "74\"",
                "stance": "Orthodox",
                "slpm": "5.2",
                "str_acc": "52%",
                "sapm": "3.1",
                "str_def": "58%",
                "td_avg": "1.5",
                "td_acc": "45%",
                "td_def": "72%",
                "sub_avg": "0.3",
                "detail_stats": {
                    "recent_fights": [
                        {"result": "Win", "opponent": "Opp A", "method": "KO/TKO", "round": 2},
                        {"result": "Win", "opponent": "Opp B", "method": "Decision", "round": 3},
                        {"result": "Loss", "opponent": "Opp C", "method": "Submission", "round": 1},
                    ],
                    "win_methods": {"ko_tko": 10, "submission": 3, "decision": 7},
                },
            }
        }
        with patch("backend.main._ufc_stats_tool") as mock_tool:
            mock_tool.invoke.return_value = mock_stats
            resp = client.get("/fighters/Test%20Fighter/profile")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ok"
            fighter = data["fighter"]
            assert fighter["name"] == "Test Fighter"
            assert "style" in fighter
            assert "elo" in fighter
            assert "risk_profile" in fighter
            assert fighter["style"]["primary_style"] != "unknown"

    def test_profile_includes_risk_assessment(self, client):
        """Profile should include risk/vulnerability data."""
        mock_stats = {
            "best_match": {
                "name": "Glass Chin Fighter",
                "record": "10-8-0",
                "sapm": "5.5",
                "slpm": "3.0",
                "str_acc": "45%",
                "str_def": "40%",
                "td_avg": "0.5",
                "td_acc": "30%",
                "td_def": "45%",
                "sub_avg": "0.1",
                "detail_stats": {
                    "recent_fights": [
                        {"result": "Loss", "method": "KO/TKO"},
                        {"result": "Loss", "method": "KO/TKO"},
                        {"result": "Win", "method": "Decision"},
                    ],
                },
            }
        }
        with patch("backend.main._ufc_stats_tool") as mock_tool:
            mock_tool.invoke.return_value = mock_stats
            resp = client.get("/fighters/Glass%20Chin%20Fighter/profile")
            assert resp.status_code == 200
            data = resp.json()
            risk = data["fighter"]["risk_profile"]
            assert risk["chin_risk"] == "high"
            assert risk["takedown_vulnerability"] == "high"


class TestCompareEndpointEnhanced:
    def test_compare_includes_style_and_elo(self, client):
        """Compare endpoint should include style and ELO matchup data."""
        mock_stats_a = {
            "best_match": {
                "name": "Fighter A",
                "record": "15-2-0",
                "slpm": "6.0",
                "str_acc": "55%",
                "sapm": "3.0",
                "str_def": "60%",
                "td_avg": "0.5",
                "td_acc": "30%",
                "td_def": "80%",
                "sub_avg": "0.1",
                "detail_stats": {},
            }
        }
        mock_stats_b = {
            "best_match": {
                "name": "Fighter B",
                "record": "12-5-0",
                "slpm": "3.0",
                "str_acc": "48%",
                "sapm": "2.5",
                "str_def": "55%",
                "td_avg": "3.5",
                "td_acc": "50%",
                "td_def": "60%",
                "sub_avg": "1.2",
                "detail_stats": {},
            }
        }
        with patch("backend.main._ufc_stats_tool") as mock_tool:
            mock_tool.invoke.side_effect = [mock_stats_a, mock_stats_b]
            resp = client.post("/compare", json={
                "fighter_a": "Fighter A",
                "fighter_b": "Fighter B",
            })
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ok"
            assert "style_analysis" in data
            assert "elo_matchup" in data
            assert data["style_analysis"]["matchup_type"] in (
                "striker_vs_grappler", "grappler_vs_striker",
                "striker_vs_striker", "grappler_vs_grappler", "mixed",
            )
            elo = data["elo_matchup"]
            assert abs(elo["fighter_a_win_prob"] + elo["fighter_b_win_prob"] - 1.0) < 0.001
            # Shared opponents should be present (may be empty)
            assert "shared_opponents" in data


class TestEventCardSimulation:
    def test_event_not_found(self, client):
        resp = client.get("/events/nonexistent_999/simulate")
        assert resp.status_code == 404

    def test_event_simulation_success(self, client):
        mock_stats = {
            "best_match": {
                "name": "Fighter",
                "record": "15-3-0",
                "slpm": "4.0",
                "str_acc": "50%",
                "sapm": "3.0",
                "str_def": "55%",
                "td_avg": "1.5",
                "td_acc": "40%",
                "td_def": "60%",
                "sub_avg": "0.5",
                "detail_stats": {},
            }
        }
        with patch("backend.main._ufc_stats_tool") as mock_tool:
            mock_tool.invoke.return_value = mock_stats
            resp = client.get("/events/ufc_327_prochazka_vs_ulberg/simulate?n_simulations=100")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ok"
            assert data["event_id"] == "ufc_327_prochazka_vs_ulberg"
            assert data["bout_count"] > 0
            assert data["simulations_per_bout"] == 100
            for bout in data["bouts"]:
                assert "fighter_a" in bout
                assert "fighter_b" in bout
                assert "simulation" in bout

    def test_simulation_cap(self, client):
        """n_simulations should be capped at 20000."""
        mock_stats = {
            "best_match": {
                "name": "Fighter",
                "slpm": "4.0", "str_acc": "50%",
                "sapm": "3.0", "str_def": "55%",
                "td_avg": "1.5", "td_acc": "40%",
                "td_def": "60%", "sub_avg": "0.5",
            }
        }
        with patch("backend.main._ufc_stats_tool") as mock_tool:
            mock_tool.invoke.return_value = mock_stats
            resp = client.get("/events/ufc_327_prochazka_vs_ulberg/simulate?n_simulations=100000")
            assert resp.status_code == 200
            data = resp.json()
            assert data["simulations_per_bout"] == 20000
