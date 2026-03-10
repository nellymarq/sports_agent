# tests/test_fighter_canonical.py
# Tests for fighter canonicalization and history service.

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.fighter_canonical import FighterCanonicalizer, CanonicalFighter
from data.events_schema import FighterRef


class TestFighterCanonicalizer:
    def _make_canonicalizer(self):
        mock_db = MagicMock()
        mock_db.get_fighter_history.return_value = []
        mock_db.get_shared_opponents.return_value = []
        return FighterCanonicalizer(history_db=mock_db)

    def test_normalize_name(self):
        assert FighterCanonicalizer._normalize_name("  Alex  Pereira  ") == "alex pereira"
        assert FighterCanonicalizer._normalize_name("ISLAM MAKHACHEV") == "islam makhachev"

    def test_hash_deterministic(self):
        h1 = FighterCanonicalizer._hash_name("Alex Pereira")
        h2 = FighterCanonicalizer._hash_name("Alex Pereira")
        assert h1 == h2

    def test_hash_case_insensitive(self):
        h1 = FighterCanonicalizer._hash_name("Alex Pereira")
        h2 = FighterCanonicalizer._hash_name("alex pereira")
        assert h1 == h2

    def test_hash_whitespace_insensitive(self):
        h1 = FighterCanonicalizer._hash_name("Alex  Pereira")
        h2 = FighterCanonicalizer._hash_name("Alex Pereira")
        assert h1 == h2

    def test_resolve_fighter_id(self):
        canon = self._make_canonicalizer()
        fid = canon.resolve_fighter_id("Alex Pereira")
        assert isinstance(fid, str)
        assert len(fid) > 0

    def test_override(self):
        canon = self._make_canonicalizer()
        canon.register_override("Poatan", "pereira_custom_id")
        assert canon.resolve_fighter_id("Poatan") == "pereira_custom_id"
        # Original name still uses hash
        assert canon.resolve_fighter_id("Alex Pereira") != "pereira_custom_id"

    def test_build_canonical_fighter(self):
        canon = self._make_canonicalizer()
        cf = canon.build_canonical_fighter("Islam Makhachev", {"nickname": "The Eagle Jr"})
        assert isinstance(cf, CanonicalFighter)
        assert cf.canonical_name == "Islam Makhachev"
        assert cf.nickname == "The Eagle Jr"
        assert cf.fighter_id is not None

    def test_to_fighter_ref(self):
        canon = self._make_canonicalizer()
        ref = canon.to_fighter_ref("Alex Pereira", {
            "nickname": "Poatan",
            "record": "11-2-0",
            "stance": "Orthodox",
        })
        assert isinstance(ref, FighterRef)
        assert ref.name == "Alex Pereira"
        assert ref.fighter_id is not None
        assert ref.record == "11-2-0"


class TestHistorySummary:
    def test_empty_history(self):
        mock_db = MagicMock()
        mock_db.get_fighter_history.return_value = []
        canon = FighterCanonicalizer(history_db=mock_db)
        summary = canon.get_history_summary("fake_id")
        assert summary["last_5"] == []
        assert summary["streak"] is None
        assert summary["method_distribution"] == {}

    def test_win_streak(self):
        mock_db = MagicMock()
        mock_db.get_fighter_history.return_value = [
            {"result": "WIN", "method": "KO/TKO", "round": "1"},
            {"result": "WIN", "method": "Decision", "round": "3"},
            {"result": "WIN", "method": "Submission", "round": "2"},
            {"result": "LOSS", "method": "Decision", "round": "5"},
        ]
        canon = FighterCanonicalizer(history_db=mock_db)
        summary = canon.get_history_summary("test_id")
        assert summary["streak"] == "W3"
        assert len(summary["last_5"]) == 4

    def test_loss_streak(self):
        mock_db = MagicMock()
        mock_db.get_fighter_history.return_value = [
            {"result": "LOSS", "method": "KO/TKO", "round": "1"},
            {"result": "LOSS", "method": "Submission", "round": "2"},
            {"result": "WIN", "method": "Decision", "round": "3"},
        ]
        canon = FighterCanonicalizer(history_db=mock_db)
        summary = canon.get_history_summary("test_id")
        assert summary["streak"] == "L2"

    def test_method_distribution(self):
        mock_db = MagicMock()
        mock_db.get_fighter_history.return_value = [
            {"result": "WIN", "method": "KO/TKO", "round": "1"},
            {"result": "WIN", "method": "KO/TKO", "round": "2"},
            {"result": "WIN", "method": "Decision", "round": "3"},
        ]
        canon = FighterCanonicalizer(history_db=mock_db)
        summary = canon.get_history_summary("test_id")
        assert summary["method_distribution"]["KO/TKO"] == 2
        assert summary["method_distribution"]["Decision"] == 1

    def test_round_distribution(self):
        mock_db = MagicMock()
        mock_db.get_fighter_history.return_value = [
            {"result": "WIN", "method": "KO/TKO", "round": "1"},
            {"result": "WIN", "method": "KO/TKO", "round": "1"},
            {"result": "WIN", "method": "Decision", "round": "3"},
        ]
        canon = FighterCanonicalizer(history_db=mock_db)
        summary = canon.get_history_summary("test_id")
        assert summary["round_distribution"]["1"] == 2
        assert summary["round_distribution"]["3"] == 1

    def test_shared_opponents(self):
        mock_db = MagicMock()
        mock_db.get_shared_opponents.return_value = ["opp_1", "opp_2"]
        canon = FighterCanonicalizer(history_db=mock_db)
        result = canon.get_pair_shared_opponents("fighter_a", "fighter_b")
        assert len(result["shared_opponent_ids"]) == 2


class TestFighterHistoryService:
    def test_enrich_fighter_ref(self):
        from data.fighter_history_service import FighterHistoryService

        mock_db = MagicMock()
        mock_db.get_fighter_history.return_value = [
            {"result": "WIN", "method": "KO/TKO", "round": "1"},
        ]
        service = FighterHistoryService(history_db=mock_db)

        ref = FighterRef(name="Alex Pereira")
        enriched = service._enrich_fighter_ref(ref)
        assert enriched.fighter_id is not None
        assert "history_summary" in enriched.metadata

    def test_enrich_empty_name(self):
        from data.fighter_history_service import FighterHistoryService

        mock_db = MagicMock()
        service = FighterHistoryService(history_db=mock_db)

        ref = FighterRef(name="")
        enriched = service._enrich_fighter_ref(ref)
        assert enriched.name == ""

    def test_build_specialist_payload(self):
        from data.fighter_history_service import FighterHistoryService
        from data.events_schema import Event, Bout, FighterRef

        mock_db = MagicMock()
        mock_db.get_fighter_history.return_value = []
        service = FighterHistoryService(history_db=mock_db)

        event = Event(
            id="ufc_313",
            code="UFC 313",
            name="UFC 313",
            main_event=Bout(
                bout_id="bout_1",
                order=1,
                is_main_event=True,
                fighters=[
                    FighterRef(name="Alex Pereira"),
                    FighterRef(name="Magomed Ankalaev"),
                ],
            ),
        )

        enriched = service.enrich_event(event)
        payload = service.build_specialist_payload(enriched)

        assert payload["event_id"] == "ufc_313"
        assert payload["main_event"] is not None
        assert len(payload["main_event"]["fighters"]) == 2
        assert payload["main_event"]["fighters"][0]["name"] == "Alex Pereira"
        assert "history_summary" in payload["main_event"]["fighters"][0]
