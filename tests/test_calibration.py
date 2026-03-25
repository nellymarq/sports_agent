"""Tests for data/calibration.py — advanced calibration and backtesting."""
import pytest
from data.calibration import (
    compute_feature_importance,
    decompose_calibration_error,
    analyze_upset_patterns,
    suggest_calibration_adjustment,
    compare_against_market,
    analyze_prediction_streaks,
    accuracy_by_dimension,
    generate_calibration_report,
)


def _make_predictions(n=20, accuracy=0.65):
    """Generate test prediction data."""
    import random
    rng = random.Random(42)
    preds = []
    for i in range(n):
        prob = rng.uniform(0.5, 0.85)
        correct = rng.random() < accuracy
        preds.append({
            "win_probability": prob,
            "correct": correct,
            "predicted_winner": f"Fighter_{i}",
            "confidence_tier": rng.choice(["High", "Medium", "Low"]),
            "method_lean": rng.choice(["KO/TKO", "Decision", "Submission", "No strong lean"]),
            "weight_class": rng.choice(["Lightweight", "Welterweight", "Middleweight"]),
            "timestamp": 1000 + i * 100,
            "metadata": {"market_implied": rng.uniform(0.4, 0.8)},
        })
    return preds


class TestFeatureImportance:
    def test_returns_ranked_features(self):
        preds = _make_predictions(30)
        result = compute_feature_importance(preds)
        assert len(result) > 0
        assert "feature" in result[0]
        assert "accuracy" in result[0]

    def test_empty_predictions(self):
        assert compute_feature_importance([]) == []

    def test_all_correct(self):
        preds = [{"win_probability": 0.7, "correct": True, "confidence_tier": "High", "method_lean": "KO"} for _ in range(10)]
        result = compute_feature_importance(preds)
        for f in result:
            assert f["accuracy"] == 1.0


class TestDecomposeCalibrationError:
    def test_basic_decomposition(self):
        preds = _make_predictions(50)
        result = decompose_calibration_error(preds)
        assert "reliability" in result
        assert "resolution" in result
        assert "sharpness" in result
        assert "brier_score" in result

    def test_interpretation_labels(self):
        preds = _make_predictions(30)
        result = decompose_calibration_error(preds)
        for key in ["reliability", "resolution", "sharpness"]:
            assert key in result["interpretation"]

    def test_empty_predictions(self):
        result = decompose_calibration_error([])
        assert "error" in result


class TestUpsetPatterns:
    def test_basic_analysis(self):
        preds = _make_predictions(30, accuracy=0.5)  # 50% accuracy = many upsets
        result = analyze_upset_patterns(preds)
        assert result["total_upsets"] > 0
        assert "by_weight_class" in result

    def test_no_upsets(self):
        preds = [{"correct": True, "win_probability": 0.7, "weight_class": "LW", "method_lean": "KO"} for _ in range(10)]
        result = analyze_upset_patterns(preds)
        assert result["upsets"] == 0

    def test_high_confidence_upset_tracking(self):
        preds = [
            {"correct": False, "win_probability": 0.80, "weight_class": "LW", "method_lean": "KO"},
            {"correct": True, "win_probability": 0.75, "weight_class": "LW", "method_lean": "Dec"},
        ]
        result = analyze_upset_patterns(preds)
        assert result["high_confidence_upsets"]["count"] == 1


class TestCalibrationAdjustment:
    def test_overconfident_model(self):
        # Model predicts high but gets many wrong
        preds = [{"win_probability": 0.80, "correct": i % 3 == 0} for i in range(30)]
        result = suggest_calibration_adjustment(preds)
        assert result["direction"] == "overconfident"

    def test_too_few_predictions(self):
        result = suggest_calibration_adjustment([{"win_probability": 0.6, "correct": True}] * 5)
        assert "message" in result

    def test_well_calibrated(self):
        # Model predicts correctly proportional to confidence
        preds = []
        for i in range(30):
            prob = 0.5 + (i / 60)
            preds.append({"win_probability": prob, "correct": i % 2 == 0})
        result = suggest_calibration_adjustment(preds)
        assert "direction" in result


class TestMarketComparison:
    def test_with_market_data(self):
        preds = _make_predictions(20)
        result = compare_against_market(preds)
        assert "model_brier_score" in result
        assert "market_brier_score" in result

    def test_without_market_data(self):
        preds = [{"win_probability": 0.6, "correct": True, "metadata": {}}]
        result = compare_against_market(preds)
        assert "message" in result


class TestPredictionStreaks:
    def test_basic_streaks(self):
        preds = _make_predictions(20)
        result = analyze_prediction_streaks(preds)
        assert "longest_correct_streak" in result
        assert "hot_cold_indicator" in result

    def test_empty_predictions(self):
        result = analyze_prediction_streaks([])
        assert "message" in result

    def test_all_correct_is_hot(self):
        preds = [{"correct": True, "timestamp": i} for i in range(10)]
        result = analyze_prediction_streaks(preds)
        assert result["hot_cold_indicator"] == "hot"

    def test_all_wrong_is_cold(self):
        preds = [{"correct": False, "timestamp": i} for i in range(10)]
        result = analyze_prediction_streaks(preds)
        assert result["hot_cold_indicator"] == "cold"


class TestAccuracyByDimension:
    def test_returns_all_dimensions(self):
        preds = _make_predictions(20)
        result = accuracy_by_dimension(preds)
        assert "weight_class" in result
        assert "confidence_tier" in result
        assert "method_lean" in result
        assert "probability_bucket" in result


class TestGenerateReport:
    def test_report_is_markdown(self):
        preds = _make_predictions(30)
        report = generate_calibration_report(preds)
        assert "# Advanced Calibration Report" in report
        assert "Accuracy" in report

    def test_empty_report(self):
        report = generate_calibration_report([])
        assert "No resolved predictions" in report
