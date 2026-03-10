# tests/test_event_utils.py
# Tests for event utility functions (pure logic, no network).

import sys
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from event_utils import (
    _parse_date,
    merge_event_data,
    _apply_patches,
    _safe_load_json,
    get_event_by_code,
    get_event_fighters,
)


class TestParseDate:
    def test_iso_format(self):
        dt = _parse_date("2025-03-08")
        assert dt is not None
        assert dt.year == 2025
        assert dt.month == 3
        assert dt.day == 8

    def test_iso_with_time(self):
        dt = _parse_date("2025-03-08T20:00:00")
        assert dt is not None
        assert dt.hour == 20

    def test_human_format(self):
        dt = _parse_date("Mar 08, 2025")
        assert dt is not None
        assert dt.month == 3

    def test_human_full_month(self):
        dt = _parse_date("March 08, 2025")
        assert dt is not None
        assert dt.month == 3

    def test_empty_string(self):
        assert _parse_date("") is None

    def test_none(self):
        assert _parse_date(None) is None

    def test_invalid(self):
        assert _parse_date("not a date") is None

    def test_partial_date(self):
        assert _parse_date("2025") is None


class TestMergeEventData:
    def test_basic_merge(self):
        base = {"id": "ufc_313", "name": "UFC 313", "location": "Vegas"}
        patch = {"location": "New York"}
        merged = merge_event_data(base, patch)
        assert merged["location"] == "New York"
        assert merged["name"] == "UFC 313"

    def test_merge_preserves_base(self):
        base = {"id": "ufc_313", "name": "UFC 313", "card": [{"fighters": ["A", "B"]}]}
        patch = {}
        merged = merge_event_data(base, patch)
        assert merged == base

    def test_added_fights(self):
        base = {"id": "ufc_313", "card": [{"fighters": ["A", "B"]}]}
        patch = {"added_fights": [{"fighters": ["C", "D"]}]}
        merged = merge_event_data(base, patch)
        assert len(merged["card"]) == 2

    def test_removed_fights(self):
        bout = {"fighters": ["A", "B"]}
        base = {"id": "ufc_313", "card": [bout, {"fighters": ["C", "D"]}]}
        patch = {"removed_fights": [bout]}
        merged = merge_event_data(base, patch)
        assert len(merged["card"]) == 1
        assert merged["card"][0]["fighters"] == ["C", "D"]

    def test_main_event_override(self):
        base = {"id": "ufc_313", "main_event": {"fighters": ["A", "B"]}}
        patch = {"main_event": {"fighters": ["X", "Y"]}}
        merged = merge_event_data(base, patch)
        assert merged["main_event"]["fighters"] == ["X", "Y"]

    def test_does_not_mutate_base(self):
        base = {"id": "ufc_313", "name": "UFC 313", "card": []}
        patch = {"name": "Changed"}
        merge_event_data(base, patch)
        assert base["name"] == "UFC 313"


class TestApplyPatches:
    def test_applies_matching_patch(self):
        events = [{"id": "ufc_313", "name": "UFC 313", "location": "Vegas"}]
        patches = [{"id": "ufc_313", "location": "New York"}]
        result = _apply_patches(events, patches)
        assert result[0]["location"] == "New York"

    def test_ignores_unknown_patch(self):
        events = [{"id": "ufc_313", "name": "UFC 313"}]
        patches = [{"id": "ufc_999", "name": "Unknown"}]
        result = _apply_patches(events, patches)
        assert len(result) == 1
        assert result[0]["name"] == "UFC 313"

    def test_multiple_patches(self):
        events = [
            {"id": "ufc_313", "name": "UFC 313", "location": "Vegas"},
            {"id": "ufc_314", "name": "UFC 314", "location": "Dallas"},
        ]
        patches = [
            {"id": "ufc_313", "location": "New York"},
            {"id": "ufc_314", "location": "Houston"},
        ]
        result = _apply_patches(events, patches)
        by_id = {e["id"]: e for e in result}
        assert by_id["ufc_313"]["location"] == "New York"
        assert by_id["ufc_314"]["location"] == "Houston"

    def test_empty_patches(self):
        events = [{"id": "ufc_313", "name": "UFC 313"}]
        result = _apply_patches(events, [])
        assert result == events

    def test_patch_without_id_skipped(self):
        events = [{"id": "ufc_313", "name": "UFC 313"}]
        patches = [{"name": "No ID"}]
        result = _apply_patches(events, patches)
        assert result[0]["name"] == "UFC 313"


class TestSafeLoadJson:
    def test_load_valid(self, tmp_path):
        p = tmp_path / "test.json"
        p.write_text(json.dumps([{"id": "test"}]))
        result = _safe_load_json(str(p), default=[])
        assert result == [{"id": "test"}]

    def test_missing_file(self, tmp_path):
        p = tmp_path / "missing.json"
        result = _safe_load_json(str(p), default=[])
        assert result == []

    def test_invalid_json(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("not json {{{")
        result = _safe_load_json(str(p), default="fallback")
        assert result == "fallback"


class TestGetEventFighters:
    def test_main_event_fighters(self):
        with patch("event_utils.get_event_by_code") as mock:
            mock.return_value = {
                "id": "ufc_313",
                "main_event": {"fighters": ["Alex Pereira", "Magomed Ankalaev"]},
            }
            fighters = get_event_fighters("ufc_313")
            assert fighters == ["Alex Pereira", "Magomed Ankalaev"]

    def test_falls_back_to_co_main(self):
        with patch("event_utils.get_event_by_code") as mock:
            mock.return_value = {
                "id": "ufc_313",
                "main_event": {"fighters": []},
                "co_main_event": {"fighters": ["C", "D"]},
            }
            fighters = get_event_fighters("ufc_313")
            assert fighters == ["C", "D"]

    def test_falls_back_to_card(self):
        with patch("event_utils.get_event_by_code") as mock:
            mock.return_value = {
                "id": "ufc_313",
                "main_event": {},
                "co_main_event": {},
                "card": [{"fighters": ["E", "F"]}],
            }
            fighters = get_event_fighters("ufc_313")
            assert fighters == ["E", "F"]

    def test_no_event(self):
        with patch("event_utils.get_event_by_code") as mock:
            mock.return_value = None
            fighters = get_event_fighters("ufc_999")
            assert fighters == []

    def test_handles_fighter_dicts(self):
        with patch("event_utils.get_event_by_code") as mock:
            mock.return_value = {
                "id": "ufc_313",
                "main_event": {
                    "fighters": [
                        {"name": "Alex Pereira"},
                        {"name": "Magomed Ankalaev"},
                    ]
                },
            }
            fighters = get_event_fighters("ufc_313")
            assert fighters == ["Alex Pereira", "Magomed Ankalaev"]
