# tests/test_shared_opponents.py
# Tests for shared opponent analysis.

import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from unittest.mock import MagicMock, patch
from data.shared_opponents import (
    get_shared_opponent_analysis,
    format_shared_opponent_report,
    _normalize_method,
)


class TestNormalizeMethod:
    def test_ko(self):
        assert _normalize_method("KO") == "KO/TKO"

    def test_tko(self):
        assert _normalize_method("TKO") == "KO/TKO"

    def test_submission(self):
        assert _normalize_method("Submission") == "Submission"

    def test_decision(self):
        assert _normalize_method("Unanimous Decision") == "Decision"

    def test_split_decision(self):
        assert _normalize_method("Split Decision") == "Decision"

    def test_other(self):
        assert _normalize_method("DQ") == "Other"

    def test_empty(self):
        assert _normalize_method("") == "Other"

    def test_none(self):
        assert _normalize_method(None) == "Other"


class TestSharedOpponentAnalysis:
    def _make_db(self, shared_ids, history_a, history_b):
        db = MagicMock()
        db.get_shared_opponents.return_value = shared_ids
        db.get_fighter_history.side_effect = lambda fid: (
            history_a if fid == "fighter_a" else history_b
        )
        return db

    def test_no_shared_opponents(self):
        db = self._make_db([], [], [])
        result = get_shared_opponent_analysis("fighter_a", "fighter_b", "A", "B", db=db)
        assert result["summary"]["count"] == 0
        assert result["summary"]["edge"] == "insufficient_data"

    def test_both_beat_same_opponent(self):
        db = self._make_db(
            ["opp_1"],
            [{"opponent_id": "opp_1", "result": "W", "method": "KO", "round": 1, "date": "2024-01-01"}],
            [{"opponent_id": "opp_1", "result": "W", "method": "Decision", "round": 3, "date": "2024-02-01"}],
        )
        result = get_shared_opponent_analysis("fighter_a", "fighter_b", "A", "B", db=db)
        assert result["summary"]["count"] == 1
        assert result["summary"]["fighter_a_wins"] == 1
        assert result["summary"]["fighter_b_wins"] == 1
        assert result["summary"]["edge"] == "even"

    def test_fighter_a_advantage(self):
        db = self._make_db(
            ["opp_1", "opp_2"],
            [
                {"opponent_id": "opp_1", "result": "W", "method": "KO", "round": 1, "date": "2024-01-01"},
                {"opponent_id": "opp_2", "result": "W", "method": "Sub", "round": 2, "date": "2024-02-01"},
            ],
            [
                {"opponent_id": "opp_1", "result": "L", "method": "KO", "round": 2, "date": "2024-03-01"},
                {"opponent_id": "opp_2", "result": "L", "method": "Dec", "round": 3, "date": "2024-04-01"},
            ],
        )
        result = get_shared_opponent_analysis("fighter_a", "fighter_b", "A", "B", db=db)
        assert result["summary"]["fighter_a_wins"] == 2
        assert result["summary"]["fighter_b_wins"] == 0
        assert result["summary"]["edge"] == "fighter_a"

    def test_finish_tracking(self):
        db = self._make_db(
            ["opp_1"],
            [{"opponent_id": "opp_1", "result": "W", "method": "KO", "round": 1, "date": "2024-01-01"}],
            [{"opponent_id": "opp_1", "result": "W", "method": "Decision", "round": 3, "date": "2024-02-01"}],
        )
        result = get_shared_opponent_analysis("fighter_a", "fighter_b", "A", "B", db=db)
        assert result["summary"]["fighter_a_finishes"] == 1
        assert result["summary"]["fighter_b_finishes"] == 0

    def test_faster_finish_tracking(self):
        db = self._make_db(
            ["opp_1"],
            [{"opponent_id": "opp_1", "result": "W", "method": "KO", "round": 1, "date": "2024-01-01"}],
            [{"opponent_id": "opp_1", "result": "W", "method": "TKO", "round": 3, "date": "2024-02-01"}],
        )
        result = get_shared_opponent_analysis("fighter_a", "fighter_b", "A", "B", db=db)
        assert result["summary"]["fighter_a_faster_finishes"] == 1
        assert result["summary"]["fighter_b_faster_finishes"] == 0

    def test_duplicate_shared_opponents_deduped(self):
        db = self._make_db(
            ["opp_1", "opp_1", "opp_1"],
            [{"opponent_id": "opp_1", "result": "W", "method": "KO", "round": 1, "date": "2024-01-01"}],
            [{"opponent_id": "opp_1", "result": "W", "method": "Dec", "round": 3, "date": "2024-02-01"}],
        )
        result = get_shared_opponent_analysis("fighter_a", "fighter_b", "A", "B", db=db)
        assert len(result["shared_opponents"]) == 1

    def test_comparison_details(self):
        db = self._make_db(
            ["opp_1"],
            [{"opponent_id": "opp_1", "result": "W", "method": "Submission", "round": 2, "date": "2024-01-01"}],
            [{"opponent_id": "opp_1", "result": "L", "method": "KO", "round": 1, "date": "2024-02-01"}],
        )
        result = get_shared_opponent_analysis("fighter_a", "fighter_b", "A", "B", db=db)
        comp = result["comparisons"][0]
        assert comp["fighter_a"]["result"] == "W"
        assert comp["fighter_a"]["method"] == "Submission"
        assert comp["fighter_a"]["round"] == 2
        assert comp["fighter_b"]["result"] == "L"

    def test_missing_round_handled(self):
        db = self._make_db(
            ["opp_1"],
            [{"opponent_id": "opp_1", "result": "W", "method": "KO", "round": None, "date": "2024-01-01"}],
            [{"opponent_id": "opp_1", "result": "L", "method": "Dec", "round": "N/A", "date": "2024-02-01"}],
        )
        result = get_shared_opponent_analysis("fighter_a", "fighter_b", "A", "B", db=db)
        comp = result["comparisons"][0]
        assert comp["fighter_a"]["round"] is None
        assert comp["fighter_b"]["round"] is None


class TestFormatReport:
    def test_empty_report(self):
        analysis = {
            "fighter_a": "A",
            "fighter_b": "B",
            "summary": {"count": 0, "edge": "insufficient_data"},
            "comparisons": [],
            "shared_opponents": [],
        }
        report = format_shared_opponent_report(analysis)
        assert "No shared opponents" in report

    def test_report_with_data(self):
        analysis = {
            "fighter_a": "Pereira",
            "fighter_b": "Ankalaev",
            "shared_opponents": ["opp_1"],
            "comparisons": [
                {
                    "opponent_id": "opp_1",
                    "fighter_a": {"result": "W", "method": "KO/TKO", "round": 1, "date": "2024-01-01"},
                    "fighter_b": {"result": "W", "method": "Decision", "round": None, "date": "2024-02-01"},
                }
            ],
            "summary": {
                "count": 1,
                "edge": "even",
                "fighter_a_wins": 1,
                "fighter_b_wins": 1,
                "fighter_a_finishes": 1,
                "fighter_b_finishes": 0,
                "fighter_a_faster_finishes": 0,
                "fighter_b_faster_finishes": 0,
            },
        }
        report = format_shared_opponent_report(analysis)
        assert "SHARED OPPONENT ANALYSIS" in report
        assert "Pereira" in report
        assert "Ankalaev" in report
        assert "Common opponents: 1" in report
        assert "Edge: Even" in report

    def test_report_shows_edge(self):
        analysis = {
            "fighter_a": "A",
            "fighter_b": "B",
            "shared_opponents": ["opp_1"],
            "comparisons": [
                {
                    "opponent_id": "opp_1",
                    "fighter_a": {"result": "W", "method": "KO/TKO", "round": 1, "date": "2024-01-01"},
                    "fighter_b": {"result": "L", "method": "KO/TKO", "round": 2, "date": "2024-02-01"},
                }
            ],
            "summary": {
                "count": 1,
                "edge": "fighter_a",
                "fighter_a_wins": 1,
                "fighter_b_wins": 0,
                "fighter_a_finishes": 1,
                "fighter_b_finishes": 0,
                "fighter_a_faster_finishes": 0,
                "fighter_b_faster_finishes": 0,
            },
        }
        report = format_shared_opponent_report(analysis)
        assert "Edge: A" in report
