# tests/test_line_tracker.py
# Tests for line movement tracker.

import os
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from data.line_tracker import (
    record_odds_snapshot,
    get_line_movement,
    get_all_movements,
    _detect_steam_move,
    _classify_movement,
    _classify_magnitude,
    format_line_movement,
    _load_history,
    _save_history,
    LINE_HISTORY_PATH,
)
from unittest.mock import patch


class TestLineTracker:
    def setup_method(self):
        """Clear line history before each test."""
        if os.path.exists(LINE_HISTORY_PATH):
            os.remove(LINE_HISTORY_PATH)

    def teardown_method(self):
        if os.path.exists(LINE_HISTORY_PATH):
            os.remove(LINE_HISTORY_PATH)

    def test_record_snapshot(self):
        snap = record_odds_snapshot(
            "pereira_vs_ankalaev",
            "Pereira", "Ankalaev",
            odds_a=1.65, odds_b=2.30,
            implied_a=0.606, implied_b=0.435,
            source="draftkings",
        )
        assert snap["fighter_a"] == "Pereira"
        assert snap["source"] == "draftkings"
        assert "timestamp" in snap

    def test_get_line_movement_no_data(self):
        assert get_line_movement("nonexistent") is None

    def test_get_line_movement_single_snapshot(self):
        record_odds_snapshot("bout1", "A", "B", odds_a=2.0, odds_b=1.8, implied_a=0.50, implied_b=0.56)
        result = get_line_movement("bout1")
        assert result is not None
        assert result["snapshot_count"] == 1
        assert result["opening"]["implied_a"] == 0.50

    def test_line_movement_multiple_snapshots(self):
        # Opening line
        record_odds_snapshot("bout2", "A", "B", implied_a=0.50, implied_b=0.50)
        # Movement: money coming in on A
        record_odds_snapshot("bout2", "A", "B", implied_a=0.60, implied_b=0.40)

        result = get_line_movement("bout2")
        assert result["snapshot_count"] == 2
        assert result["movement"]["fighter_a_shift"] == pytest.approx(0.10)
        assert result["movement"]["direction"] == "fighter_a_steaming"
        assert result["movement"]["magnitude"] in ("moderate", "significant")

    def test_stable_line(self):
        record_odds_snapshot("bout3", "A", "B", implied_a=0.55, implied_b=0.45)
        record_odds_snapshot("bout3", "A", "B", implied_a=0.56, implied_b=0.44)

        result = get_line_movement("bout3")
        assert result["movement"]["direction"] == "stable"
        assert result["movement"]["magnitude"] == "negligible"

    def test_get_all_movements(self):
        record_odds_snapshot("bout_a", "X", "Y", implied_a=0.5, implied_b=0.5)
        record_odds_snapshot("bout_b", "P", "Q", implied_a=0.6, implied_b=0.4)

        movements = get_all_movements()
        assert len(movements) == 2

    def test_format_line_movement(self):
        record_odds_snapshot("bout4", "Jones", "Stipe", implied_a=0.70, implied_b=0.30)
        record_odds_snapshot("bout4", "Jones", "Stipe", implied_a=0.75, implied_b=0.25)

        movement = get_line_movement("bout4")
        text = format_line_movement(movement)
        assert "Jones" in text
        assert "Stipe" in text
        assert "LINE MOVEMENT" in text

    def test_format_none(self):
        assert format_line_movement(None) == "No line data available."


class TestClassifiers:
    def test_movement_stable(self):
        assert _classify_movement(0.01) == "stable"

    def test_movement_a_steaming(self):
        assert _classify_movement(0.05) == "fighter_a_steaming"

    def test_movement_b_steaming(self):
        assert _classify_movement(-0.05) == "fighter_b_steaming"

    def test_magnitude_negligible(self):
        assert _classify_magnitude(0.01) == "negligible"

    def test_magnitude_minor(self):
        assert _classify_magnitude(0.03) == "minor"

    def test_magnitude_moderate(self):
        assert _classify_magnitude(0.07) == "moderate"

    def test_magnitude_significant(self):
        assert _classify_magnitude(0.12) == "significant"

    def test_magnitude_major(self):
        assert _classify_magnitude(0.20) == "major"


class TestSteamMoveDetection:
    def test_no_steam_move(self):
        snapshots = [
            {"timestamp": 1000, "implied_a": 0.50},
            {"timestamp": 2000, "implied_a": 0.52},
        ]
        result = _detect_steam_move(snapshots)
        assert result["detected"] is False

    def test_steam_move_detected(self):
        snapshots = [
            {"timestamp": 1000, "implied_a": 0.50},
            {"timestamp": 2000, "implied_a": 0.58},  # 8% shift in 1000s
        ]
        result = _detect_steam_move(snapshots)
        assert result["detected"] is True
        assert abs(result["shift"]) >= 0.05

    def test_slow_move_not_steam(self):
        """Movement over long time period is not a steam move."""
        snapshots = [
            {"timestamp": 1000, "implied_a": 0.50},
            {"timestamp": 100000, "implied_a": 0.60},  # Too slow
        ]
        result = _detect_steam_move(snapshots)
        assert result["detected"] is False
