# tests/test_events_schema.py
# Tests for unified event schema and data layer.

import sys
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.events_schema import Event, Bout, FighterRef, BoutOdds, EventProvenance


class TestEventFromLegacy:
    def test_basic_legacy_dict(self):
        legacy = {
            "id": "ufc_313",
            "code": "UFC 313",
            "name": "UFC 313: Pereira vs Ankalaev",
            "location": "Las Vegas",
            "main_event": {"fighters": ["Alex Pereira", "Magomed Ankalaev"]},
            "co_main_event": {"fighters": ["Fighter C", "Fighter D"]},
            "card": [{"fighters": ["Fighter E", "Fighter F"]}],
        }
        event = Event.from_legacy_dict(legacy)
        assert event.id == "ufc_313"
        assert event.code == "UFC 313"
        assert event.main_event is not None
        assert len(event.main_event.fighters) == 2
        assert event.main_event.fighters[0].name == "Alex Pereira"
        assert event.co_main_event is not None
        assert len(event.card) == 1

    def test_empty_main_event(self):
        legacy = {"id": "ufc_999", "code": "UFC 999", "name": "UFC 999"}
        event = Event.from_legacy_dict(legacy)
        assert event.main_event is None
        assert event.co_main_event is None

    def test_roundtrip_legacy(self):
        legacy = {
            "id": "ufc_314",
            "code": "UFC 314",
            "name": "UFC 314",
            "location": "Vegas",
            "main_event": {"fighters": ["A", "B"]},
            "co_main_event": {"fighters": []},
            "card": [],
        }
        event = Event.from_legacy_dict(legacy)
        exported = event.to_legacy_dict()
        assert exported["id"] == "ufc_314"
        assert exported["main_event"]["fighters"] == ["A", "B"]


class TestEventToDict:
    def test_to_dict_serializable(self):
        event = Event(
            id="test_1",
            code="TEST 1",
            name="Test Event",
        )
        d = event.to_dict()
        # Should be JSON-serializable
        json_str = json.dumps(d)
        assert "test_1" in json_str

    def test_to_dict_with_bouts(self):
        event = Event(
            id="test_2",
            code="TEST 2",
            name="Test",
            main_event=Bout(
                bout_id="test_2_bout_1",
                order=1,
                is_main_event=True,
                fighters=[
                    FighterRef(name="Fighter A", record="10-0-0"),
                    FighterRef(name="Fighter B", record="8-2-0"),
                ],
                odds=BoutOdds(favorite="Fighter A", favorite_odds=-200),
            ),
        )
        d = event.to_dict()
        assert d["main_event"]["fighters"][0]["name"] == "Fighter A"
        assert d["main_event"]["odds"]["favorite"] == "Fighter A"


class TestBoutAndFighterRef:
    def test_fighter_ref_defaults(self):
        f = FighterRef(name="Test Fighter")
        assert f.name == "Test Fighter"
        assert f.fighter_id is None
        assert f.rank is None
        assert f.is_champion is False
        assert f.metadata == {}

    def test_bout_defaults(self):
        b = Bout(bout_id="b1", order=1)
        assert b.is_title_fight is False
        assert b.is_main_event is False
        assert b.fighters == []
        assert b.odds is None

    def test_bout_odds(self):
        odds = BoutOdds(
            favorite="A",
            underdog="B",
            favorite_odds=-180.0,
            underdog_odds=150.0,
            implied_prob_favorite=0.643,
            implied_prob_underdog=0.357,
        )
        assert odds.favorite == "A"
        assert odds.implied_prob_favorite == 0.643


class TestEventsJsonFile:
    def test_events_json_loads(self):
        events_path = ROOT / "data" / "events.json"
        assert events_path.exists(), "events.json should exist"
        data = json.loads(events_path.read_text())
        assert isinstance(data, list)
        assert len(data) > 0

    def test_all_events_have_id(self):
        events_path = ROOT / "data" / "events.json"
        data = json.loads(events_path.read_text())
        for ev in data:
            assert "id" in ev, f"Event missing id: {ev}"

    def test_events_parse_as_event_objects(self):
        events_path = ROOT / "data" / "events.json"
        data = json.loads(events_path.read_text())
        for ev in data:
            event = Event.from_legacy_dict(ev)
            assert event.id
            assert event.code
