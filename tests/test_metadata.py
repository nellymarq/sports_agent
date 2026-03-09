# tests/test_metadata.py
# Unit tests for data schema: Evidence, SpecialistOutput, FinalOutput.

import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from data.metadata import Evidence, SpecialistOutput, FinalOutput, _validate_confidence


class TestValidateConfidence:
    def test_valid_range(self):
        _validate_confidence(0.0)
        _validate_confidence(0.5)
        _validate_confidence(1.0)

    def test_out_of_range(self):
        with pytest.raises(ValueError):
            _validate_confidence(1.1)
        with pytest.raises(ValueError):
            _validate_confidence(-0.1)


class TestEvidence:
    def test_create(self):
        ev = Evidence.create(source="ufc_stats", content="19-1 record")
        assert ev.source == "ufc_stats"
        assert ev.content == "19-1 record"
        assert ev.confidence == 0.7  # default
        assert ev.id is not None
        assert ev.timestamp > 0

    def test_custom_confidence(self):
        ev = Evidence.create(source="test", content="data", confidence=0.9)
        assert ev.confidence == 0.9

    def test_provenance(self):
        ev = Evidence.create(
            source="test", content="data",
            provenance={"url": "https://example.com"}
        )
        assert ev.provenance["url"] == "https://example.com"


class TestSpecialistOutput:
    def test_create(self):
        so = SpecialistOutput.create(
            specialist="style",
            content="Style analysis content",
        )
        assert so.specialist == "style"
        assert so.content == "Style analysis content"
        assert so.confidence == 0.7
        assert so.id is not None

    def test_with_evidence(self):
        ev = Evidence.create(source="test", content="fact")
        so = SpecialistOutput.create(
            specialist="form",
            content="Form analysis",
            evidence=[ev],
            confidence=0.85,
        )
        assert len(so.evidence) == 1
        assert so.confidence == 0.85

    def test_unique_ids(self):
        so1 = SpecialistOutput.create(specialist="a", content="x")
        so2 = SpecialistOutput.create(specialist="b", content="y")
        assert so1.id != so2.id


class TestFinalOutput:
    def test_create(self):
        fo = FinalOutput.create(
            content="Final analysis",
            merged_from=["id1", "id2"],
            evidence=[],
        )
        assert fo.content == "Final analysis"
        assert fo.merged_from == ["id1", "id2"]
        assert fo.confidence == 0.8  # default

    def test_lineage(self):
        fo = FinalOutput.create(
            content="test",
            merged_from=["id1"],
            evidence=[],
            lineage={"strategy": "critic_merge"},
        )
        assert fo.lineage["strategy"] == "critic_merge"
