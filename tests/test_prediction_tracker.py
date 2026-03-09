# tests/test_prediction_tracker.py
# Tests for prediction tracking and calibration.

import os, sys, json
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from unittest.mock import patch
from prediction_tracker import (
    record_prediction,
    record_result,
    get_calibration_stats,
    _load_predictions,
    _save_predictions,
    PREDICTIONS_PATH,
)


class TestPredictionTracker:
    def setup_method(self):
        """Clear predictions before each test."""
        _save_predictions([])

    def teardown_method(self):
        """Clean up after tests."""
        if os.path.exists(PREDICTIONS_PATH):
            _save_predictions([])

    def test_record_prediction(self):
        entry = record_prediction(
            event_id="ufc_313",
            fighter_a="Pereira",
            fighter_b="Ankalaev",
            predicted_winner="Pereira",
            win_probability=0.65,
            confidence_tier="High",
            method_lean="KO/TKO",
        )
        assert entry["predicted_winner"] == "Pereira"
        assert entry["win_probability"] == 0.65
        assert entry["actual_winner"] is None

        preds = _load_predictions()
        assert len(preds) == 1

    def test_record_result_correct(self):
        record_prediction(
            event_id="ufc_313",
            fighter_a="Pereira",
            fighter_b="Ankalaev",
            predicted_winner="Pereira",
            win_probability=0.65,
        )
        updated = record_result(
            event_id="ufc_313",
            fighter_a="Pereira",
            fighter_b="Ankalaev",
            actual_winner="Pereira",
            actual_method="KO",
        )
        assert updated is not None
        assert updated["correct"] is True

    def test_record_result_incorrect(self):
        record_prediction(
            event_id="ufc_313",
            fighter_a="Pereira",
            fighter_b="Ankalaev",
            predicted_winner="Pereira",
            win_probability=0.65,
        )
        updated = record_result(
            event_id="ufc_313",
            fighter_a="Pereira",
            fighter_b="Ankalaev",
            actual_winner="Ankalaev",
        )
        assert updated is not None
        assert updated["correct"] is False

    def test_record_result_not_found(self):
        result = record_result(
            event_id="ufc_999",
            fighter_a="X",
            fighter_b="Y",
            actual_winner="X",
        )
        assert result is None

    def test_calibration_no_data(self):
        stats = get_calibration_stats()
        assert stats["resolved"] == 0
        assert stats["accuracy"] is None

    def test_calibration_with_data(self):
        # Record 3 predictions
        record_prediction("e1", "A", "B", "A", 0.7, "High")
        record_prediction("e2", "C", "D", "C", 0.55, "Low")
        record_prediction("e3", "E", "F", "E", 0.85, "Very High")

        # Resolve 2 of them
        record_result("e1", "A", "B", "A")  # correct
        record_result("e2", "C", "D", "D")  # incorrect

        stats = get_calibration_stats()
        assert stats["total_predictions"] == 3
        assert stats["resolved"] == 2
        assert stats["correct"] == 1
        assert stats["accuracy"] == 0.5
        assert "brier_score" in stats
        assert "by_tier" in stats

    def test_calibration_by_tier(self):
        record_prediction("e1", "A", "B", "A", 0.8, "High")
        record_prediction("e2", "C", "D", "C", 0.8, "High")
        record_prediction("e3", "E", "F", "E", 0.55, "Low")

        record_result("e1", "A", "B", "A")  # correct
        record_result("e2", "C", "D", "C")  # correct
        record_result("e3", "E", "F", "F")  # incorrect

        stats = get_calibration_stats()
        assert stats["by_tier"]["High"] == 1.0
        assert stats["by_tier"]["Low"] == 0.0

    def test_calibration_by_probability_bucket(self):
        record_prediction("e1", "A", "B", "A", 0.55)
        record_prediction("e2", "C", "D", "C", 0.75)

        record_result("e1", "A", "B", "A")  # correct at 55%
        record_result("e2", "C", "D", "C")  # correct at 75%

        stats = get_calibration_stats()
        assert "50-60%" in stats["by_probability"]
        assert stats["by_probability"]["50-60%"]["accuracy"] == 1.0
        assert "70-80%" in stats["by_probability"]
