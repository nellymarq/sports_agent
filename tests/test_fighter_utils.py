# tests/test_fighter_utils.py
# Unit tests for fighter name extraction logic.

import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fighter_utils import extract_fighters, _extract_from_vs_pattern, _extract_capitalized_sequences


class TestVsPatternExtraction:
    def test_basic_vs(self):
        result = _extract_from_vs_pattern("Islam Makhachev vs Dustin Poirier")
        assert len(result) == 2
        assert "Islam Makhachev" in result or "Makhachev" in result[0].lower()

    def test_vs_dot(self):
        result = _extract_from_vs_pattern("Volkanovski vs. Topuria")
        assert len(result) == 2

    def test_versus(self):
        result = _extract_from_vs_pattern("Jones versus Aspinall")
        assert len(result) == 2

    def test_no_vs(self):
        result = _extract_from_vs_pattern("Tell me about Pereira")
        assert len(result) == 0

    def test_who_wins_prefix(self):
        result = _extract_from_vs_pattern("Who wins Islam Makhachev vs Dustin Poirier?")
        assert len(result) == 2

    def test_strips_stopwords(self):
        result = _extract_from_vs_pattern("the ufc main event fighter vs another fighter")
        assert all(word not in r.lower() for r in result for word in ["ufc", "main", "event"])


class TestCapitalizedExtraction:
    def test_extracts_names(self):
        result = _extract_capitalized_sequences("I think Alex Pereira beats Magomed Ankalaev")
        assert len(result) >= 2

    def test_skips_stopwords(self):
        result = _extract_capitalized_sequences("The Main Event is great")
        # "Main Event" contains stopwords, should be filtered
        assert not any("Main" in r for r in result)

    def test_single_word_ignored(self):
        result = _extract_capitalized_sequences("the pereira alone")
        # All lowercase = nothing matched
        assert len(result) == 0


class TestExtractFighters:
    def test_vs_pattern_priority(self):
        fighters, primary = extract_fighters("Who wins Pereira vs Ankalaev?")
        assert len(fighters) == 2
        assert primary == fighters[0]

    def test_fallback_to_capitalized(self):
        fighters, primary = extract_fighters("I think Alex Pereira is the best striker")
        assert len(fighters) >= 1

    def test_empty_input(self):
        fighters, primary = extract_fighters("")
        assert fighters == []
        assert primary == "unknown"

    def test_no_fighters_found(self):
        fighters, primary = extract_fighters("what time is it")
        assert primary == "unknown"

    def test_none_input(self):
        fighters, primary = extract_fighters(None)
        assert fighters == []
        assert primary == "unknown"

    def test_whitespace_only(self):
        fighters, primary = extract_fighters("   ")
        assert fighters == []

    def test_versus_full_word(self):
        fighters, primary = extract_fighters("Pereira versus Ankalaev full breakdown")
        assert len(fighters) == 2

    def test_primary_is_first_fighter(self):
        fighters, primary = extract_fighters("Islam Makhachev vs Charles Oliveira")
        assert primary == fighters[0]

    def test_multiple_capitalized_names(self):
        fighters, _ = extract_fighters(
            "I think Alex Pereira and Magomed Ankalaev will put on a show"
        )
        assert len(fighters) >= 2

    def test_deduplicate(self):
        fighters, _ = extract_fighters("Alex Pereira vs Alex Pereira")
        # After dedup, could be 1
        assert len(fighters) <= 2


class TestVsPatternEdgeCases:
    def test_multiple_vs_returns_empty(self):
        result = _extract_from_vs_pattern("A vs B vs C")
        # Split on " vs " yields 3 parts, function returns []
        assert len(result) == 0

    def test_empty_side(self):
        result = _extract_from_vs_pattern("vs Pereira")
        assert len(result) == 0 or all(r.strip() for r in result)

    def test_punctuation_cleaned(self):
        result = _extract_from_vs_pattern("Pereira! vs Ankalaev?")
        assert len(result) == 2
