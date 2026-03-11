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
    _compute_log_loss,
    _compute_calibration_curve,
    _compute_confidence_weighted_accuracy,
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

    def test_calibration_includes_log_loss(self):
        record_prediction("e1", "A", "B", "A", 0.7)
        record_prediction("e2", "C", "D", "C", 0.6)
        record_result("e1", "A", "B", "A")
        record_result("e2", "C", "D", "D")

        stats = get_calibration_stats()
        assert "log_loss" in stats
        assert stats["log_loss"] is not None
        assert stats["log_loss"] > 0

    def test_calibration_includes_calibration_curve(self):
        record_prediction("e1", "A", "B", "A", 0.55)
        record_prediction("e2", "C", "D", "C", 0.65)
        record_prediction("e3", "E", "F", "E", 0.75)
        record_result("e1", "A", "B", "A")
        record_result("e2", "C", "D", "C")
        record_result("e3", "E", "F", "E")

        stats = get_calibration_stats()
        assert "calibration_curve" in stats
        assert len(stats["calibration_curve"]) > 0
        for point in stats["calibration_curve"]:
            assert "predicted_avg" in point
            assert "actual_rate" in point
            assert "count" in point

    def test_calibration_includes_confidence_weighted(self):
        record_prediction("e1", "A", "B", "A", 0.85)  # high confidence
        record_prediction("e2", "C", "D", "C", 0.52)  # low confidence
        record_result("e1", "A", "B", "A")  # correct on high conf
        record_result("e2", "C", "D", "D")  # wrong on low conf

        stats = get_calibration_stats()
        assert "confidence_weighted_accuracy" in stats
        assert stats["confidence_weighted_accuracy"] is not None
        # Should be > 0.5 since we got the high-confidence one right
        assert stats["confidence_weighted_accuracy"] > 0.5


class TestLogLoss:
    def test_log_loss_empty(self):
        assert _compute_log_loss([]) is None

    def test_log_loss_perfect(self):
        resolved = [
            {"correct": True, "win_probability": 0.99},
            {"correct": True, "win_probability": 0.95},
        ]
        ll = _compute_log_loss(resolved)
        assert ll is not None
        assert ll < 0.1  # near perfect

    def test_log_loss_bad(self):
        resolved = [
            {"correct": False, "win_probability": 0.95},
            {"correct": False, "win_probability": 0.90},
        ]
        ll = _compute_log_loss(resolved)
        assert ll is not None
        assert ll > 1.0  # high loss for wrong + confident

    def test_log_loss_random_baseline(self):
        """50% predictions should give ~0.693 log loss."""
        resolved = [{"correct": True, "win_probability": 0.5} for _ in range(20)]
        ll = _compute_log_loss(resolved)
        assert abs(ll - 0.693) < 0.01


class TestCalibrationCurve:
    def test_curve_empty(self):
        assert _compute_calibration_curve([]) == []

    def test_curve_bins(self):
        resolved = [
            {"correct": True, "win_probability": 0.55},
            {"correct": False, "win_probability": 0.56},
            {"correct": True, "win_probability": 0.75},
            {"correct": True, "win_probability": 0.78},
        ]
        curve = _compute_calibration_curve(resolved)
        assert len(curve) >= 2
        for point in curve:
            assert 0 <= point["actual_rate"] <= 1
            assert point["count"] > 0

    def test_curve_gap_calculation(self):
        """Perfect calibration should have gap near 0."""
        resolved = [
            {"correct": True, "win_probability": 0.55},
            {"correct": False, "win_probability": 0.55},
            # ~50% actual at 55% predicted => gap ~ -0.05
        ]
        curve = _compute_calibration_curve(resolved)
        if curve:
            assert abs(curve[0]["gap"]) < 0.15


class TestConfidenceWeightedAccuracy:
    def test_cwa_empty(self):
        assert _compute_confidence_weighted_accuracy([]) is None

    def test_cwa_high_confidence_correct(self):
        """All correct at high confidence should be ~1.0."""
        resolved = [
            {"correct": True, "win_probability": 0.90},
            {"correct": True, "win_probability": 0.85},
        ]
        cwa = _compute_confidence_weighted_accuracy(resolved)
        assert cwa is not None
        assert cwa > 0.9

    def test_cwa_high_confidence_wrong(self):
        """All wrong at high confidence should be ~0.0."""
        resolved = [
            {"correct": False, "win_probability": 0.90},
            {"correct": False, "win_probability": 0.85},
        ]
        cwa = _compute_confidence_weighted_accuracy(resolved)
        assert cwa is not None
        assert cwa < 0.1

    def test_cwa_mixed(self):
        """Right when confident, wrong when uncertain should be high."""
        resolved = [
            {"correct": True, "win_probability": 0.85},   # high conf, correct (weight 0.7)
            {"correct": False, "win_probability": 0.52},   # low conf, wrong (weight ~0.1)
        ]
        cwa = _compute_confidence_weighted_accuracy(resolved)
        assert cwa is not None
        assert cwa > 0.7
