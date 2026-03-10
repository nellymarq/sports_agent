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
