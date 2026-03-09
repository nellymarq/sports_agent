# tests/test_comparison.py
# Tests for head-to-head fighter comparison utility.

import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tools.comparison import (
    build_comparison,
    _parse_record,
    _parse_pct,
    _parse_float,
    _edge_label,
)


class TestParsers:
    def test_parse_record(self):
        r = _parse_record("27-1-0")
        assert r == {"wins": 27, "losses": 1, "draws": 0}

    def test_parse_record_two_parts(self):
        r = _parse_record("10-2")
        assert r["wins"] == 10
        assert r["losses"] == 2

    def test_parse_record_invalid(self):
        r = _parse_record("invalid")
        assert r["wins"] == 0

    def test_parse_pct(self):
        assert _parse_pct("55%") == 0.55
        assert _parse_pct("100%") == 1.0
        assert _parse_pct("abc") is None

    def test_parse_float(self):
        assert _parse_float("5.2") == 5.2
        assert _parse_float("abc") is None

    def test_edge_label_higher_better(self):
        assert _edge_label(0.6, 0.4) == "Fighter A"
        assert _edge_label(0.4, 0.6) == "Fighter B"
        assert _edge_label(0.5, 0.51) == "Even"

    def test_edge_label_lower_better(self):
        assert _edge_label(3.0, 5.0, higher_is_better=False) == "Fighter A"

    def test_edge_label_none(self):
        assert _edge_label(None, 0.5) == "N/A"


class TestBuildComparison:
    def test_basic_comparison(self):
        a = {
            "name": "Pereira",
            "record": "11-2",
            "height": "6'4\"",
            "reach": "79\"",
            "stance": "Orthodox",
            "slpm": "5.2",
            "str_acc": "55%",
            "sapm": "3.1",
            "str_def": "60%",
        }
        b = {
            "name": "Ankalaev",
            "record": "19-1",
            "height": "6'3\"",
            "reach": "75\"",
            "stance": "Orthodox",
            "slpm": "3.8",
            "str_acc": "51%",
            "sapm": "2.5",
            "str_def": "62%",
        }
        result = build_comparison(a, b)
        assert "Pereira" in result
        assert "Ankalaev" in result
        assert "HEAD-TO-HEAD" in result
        assert "SLpM" in result
        assert "Edge Count" in result

    def test_comparison_with_recent_fights(self):
        a = {
            "name": "Fighter A",
            "record": "10-0",
            "detail_stats": {
                "recent_fights": [
                    {"result": "W", "opponent": "Opp1", "method": "KO", "round": "1"},
                    {"result": "W", "opponent": "Opp2", "method": "Dec", "round": "3"},
                ]
            },
        }
        b = {"name": "Fighter B", "record": "8-2"}
        result = build_comparison(a, b)
        assert "Last 2: 2W-0L" in result
        assert "Opp1" in result

    def test_empty_stats(self):
        a = {"name": "A"}
        b = {"name": "B"}
        result = build_comparison(a, b)
        assert "A vs B" in result
