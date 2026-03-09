# tests/test_prefetch.py
# Unit tests for fighter stats prefetch.

import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from unittest.mock import patch, MagicMock
from tools.prefetch import prefetch_fighter_stats, format_prefetched_stats


class TestPrefetch:
    def test_empty_fighters(self):
        result = prefetch_fighter_stats([])
        assert result == {}

    def test_unknown_fighter_skipped(self):
        result = prefetch_fighter_stats(["unknown"])
        assert result == {}

    @patch("tools.prefetch.TOOL_REGISTRY", {
        "ufc_stats": MagicMock(invoke=MagicMock(return_value={
            "source": "UFCStats",
            "best_match": {
                "record": "10-2",
                "height": "6'4\"",
                "reach": "79\"",
                "stance": "Orthodox",
                "slpm": "5.2",
                "str_acc": "55%",
                "sapm": "3.1",
                "str_def": "60%",
                "weight": "205",
                "detail_stats": {"recent_fights": [
                    {"result": "W", "opponent": "Smith", "method": "KO", "round": "2"}
                ]},
            },
        })),
        "draftkings_odds": MagicMock(invoke=MagicMock(return_value={
            "source": "DraftKings",
            "fighter_odds": [{"market": "Moneyline", "odds_american": "-200", "implied_probability": 0.6667}],
        })),
    })
    def test_prefetch_returns_stats(self):
        result = prefetch_fighter_stats(["Alex Pereira"])
        assert "Alex Pereira" in result
        data = result["Alex Pereira"]
        assert data["record"] == "10-2"
        assert data["reach"] == "79\""
        assert data["odds_source"] == "DraftKings"

    @patch("tools.prefetch.TOOL_REGISTRY", {
        "ufc_stats": MagicMock(invoke=MagicMock(side_effect=Exception("Network error"))),
    })
    def test_prefetch_handles_tool_error(self):
        result = prefetch_fighter_stats(["Test Fighter"])
        assert "Test Fighter" in result
        # Should have name but no stats due to error
        assert result["Test Fighter"]["name"] == "Test Fighter"


class TestFormatPrefetchedStats:
    def test_empty_stats(self):
        assert format_prefetched_stats({}) == ""

    def test_formats_fighter_data(self):
        stats = {
            "Jon Jones": {
                "name": "Jon Jones",
                "record": "27-1",
                "height": "6'4\"",
                "reach": "84\"",
            }
        }
        output = format_prefetched_stats(stats)
        assert "Jon Jones" in output
        assert "27-1" in output
        assert "84\"" in output

    def test_formats_recent_fights(self):
        stats = {
            "Fighter": {
                "name": "Fighter",
                "detail_stats": {
                    "recent_fights": [
                        {"result": "W", "opponent": "Opp", "method": "KO", "round": "1"}
                    ]
                },
            }
        }
        output = format_prefetched_stats(stats)
        assert "W vs Opp" in output
        assert "KO" in output
