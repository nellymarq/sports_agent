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
    _compute_rolling_accuracy,
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

    def test_weight_class_tracking(self):
        record_prediction("e1", "A", "B", "A", 0.7, weight_class="Lightweight")
        record_prediction("e2", "C", "D", "C", 0.65, weight_class="Heavyweight")

        record_result("e1", "A", "B", "A")
        record_result("e2", "C", "D", "D")

        stats = get_calibration_stats()
        assert "by_weight_class" in stats
        assert stats["by_weight_class"]["Lightweight"]["accuracy"] == 1.0
        assert stats["by_weight_class"]["Heavyweight"]["accuracy"] == 0.0

    def test_method_probabilities_stored(self):
        entry = record_prediction(
            "e1", "A", "B", "A", 0.7,
            method_probabilities={"ko_tko": 40, "submission": 10, "decision": 50},
        )
        assert entry["method_probabilities"]["ko_tko"] == 40

    def test_round_probabilities_stored(self):
        entry = record_prediction(
            "e1", "A", "B", "A", 0.7,
            round_probabilities={"r1": 20, "r2": 15, "r3": 10, "decision": 55},
        )
        assert entry["round_probabilities"]["r1"] == 20

    def test_record_result_with_round(self):
        record_prediction("e1", "A", "B", "A", 0.7, method_lean="KO/TKO")
        updated = record_result("e1", "A", "B", "A", actual_method="KO", actual_round=2)
        assert updated["actual_round"] == 2
        assert updated["method_correct"] is True

    def test_method_correct_tracking(self):
        record_prediction("e1", "A", "B", "A", 0.7, method_lean="Decision")
        updated = record_result("e1", "A", "B", "A", actual_method="KO/TKO")
        assert updated["method_correct"] is False

    def test_method_correct_no_lean(self):
        record_prediction("e1", "A", "B", "A", 0.7, method_lean="No strong lean")
        updated = record_result("e1", "A", "B", "A", actual_method="Decision")
        assert updated["method_correct"] is None

    def test_favorite_underdog_accuracy(self):
        record_prediction("e1", "A", "B", "A", 0.75)  # favorite
        record_prediction("e2", "C", "D", "D", 0.35)  # underdog pick (prob < 0.4 inverted)

        record_result("e1", "A", "B", "A")  # correct fav
        record_result("e2", "C", "D", "D")  # correct dog

        stats = get_calibration_stats()
        assert "favorite_accuracy" in stats
        assert "underdog_accuracy" in stats
        assert stats["favorite_accuracy"]["total"] >= 1

    def test_method_distribution_score(self):
        record_prediction(
            "e1", "A", "B", "A", 0.7,
            method_probabilities={"ko_tko": 60, "submission": 10, "decision": 30},
        )
        record_result("e1", "A", "B", "A", actual_method="KO/TKO")

        stats = get_calibration_stats()
        assert stats["method_distribution_score"] is not None
        # 60% prob on correct method => -log(0.6) ≈ 0.51
        assert stats["method_distribution_score"] < 1.0

    def test_rolling_accuracy_empty(self):
        assert _compute_rolling_accuracy([]) == []

    def test_rolling_accuracy_single(self):
        assert _compute_rolling_accuracy([{"correct": True, "win_probability": 0.7, "timestamp": 1}]) == []

    def test_rolling_accuracy_multiple(self):
        resolved = [
            {"correct": True, "win_probability": 0.7, "timestamp": 1},
            {"correct": False, "win_probability": 0.6, "timestamp": 2},
            {"correct": True, "win_probability": 0.8, "timestamp": 3},
            {"correct": True, "win_probability": 0.65, "timestamp": 4},
        ]
        trend = _compute_rolling_accuracy(resolved, window=3)
        assert len(trend) == 4
        assert trend[0]["index"] == 1
        assert trend[0]["cumulative_accuracy"] == 1.0  # 1/1
        assert trend[-1]["cumulative_accuracy"] == 0.75  # 3/4
        # Rolling window of 3 for last point: [F, T, T] = 2/3
        assert trend[-1]["rolling_accuracy"] == round(2/3, 3)

    def test_calibration_includes_trend(self):
        record_prediction("e1", "A", "B", "A", 0.7)
        record_prediction("e2", "C", "D", "C", 0.6)
        record_result("e1", "A", "B", "A", "KO")
        record_result("e2", "C", "D", "D", "Decision")

        stats = get_calibration_stats()
        assert "accuracy_trend" in stats
        assert len(stats["accuracy_trend"]) == 2
