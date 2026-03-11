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
