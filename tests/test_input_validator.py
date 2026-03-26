# tests/test_input_validator.py
# Comprehensive tests for data.input_validator module.

import unittest

from data.input_validator import (
    validate_user_input,
    validate_fighter_name,
    validate_stats_response,
)


class TestValidateUserInput(unittest.TestCase):
    """Tests for validate_user_input."""

    # --- Empty / blank ---

    def test_empty_string(self):
        r = validate_user_input("")
        self.assertFalse(r["valid"])
        self.assertIn("empty", r["error"].lower())

    def test_whitespace_only(self):
        r = validate_user_input("   \t\n  ")
        self.assertFalse(r["valid"])

    # --- Too long ---

    def test_very_long_input(self):
        r = validate_user_input("a" * 2001)
        self.assertFalse(r["valid"])
        self.assertIn("too long", r["error"].lower())

    def test_exactly_max_length(self):
        r = validate_user_input("Who wins UFC fight? " + "x" * 1980)
        self.assertTrue(r["valid"])

    # --- HTML injection ---

    def test_html_tags_stripped(self):
        r = validate_user_input("<script>alert('xss')</script>Who wins the fight?")
        self.assertTrue(r["valid"])
        self.assertNotIn("<script>", r["sanitized"])
        self.assertIn("Who wins the fight?", r["sanitized"])

    def test_nested_html(self):
        r = validate_user_input("<b><i>UFC</i></b> question about fighters")
        self.assertTrue(r["valid"])
        self.assertNotIn("<b>", r["sanitized"])
        self.assertIn("UFC", r["sanitized"])

    def test_html_only_input(self):
        r = validate_user_input("<div><span></span></div>")
        self.assertFalse(r["valid"])
        self.assertIn("sanitization", r["error"].lower())

    # --- Control characters ---

    def test_control_chars_stripped(self):
        r = validate_user_input("Who\x00wins\x07the UFC fight?")
        self.assertTrue(r["valid"])
        self.assertNotIn("\x00", r["sanitized"])
        self.assertNotIn("\x07", r["sanitized"])

    # --- Fighter name detection ---

    def test_no_fighter_indicators_warns(self):
        r = validate_user_input("What is the weather today?")
        self.assertTrue(r["valid"])
        self.assertTrue(
            any("fighter" in w.lower() or "fight" in w.lower() for w in r["warnings"])
        )

    def test_fighter_indicator_no_warning(self):
        r = validate_user_input("Who wins the fight between Khabib vs McGregor?")
        self.assertTrue(r["valid"])
        fighter_warnings = [
            w for w in r["warnings"]
            if "fighter" in w.lower() or "fight-related" in w.lower()
        ]
        self.assertEqual(len(fighter_warnings), 0)

    # --- Question clarity ---

    def test_very_short_input_warns(self):
        r = validate_user_input("UFC?")
        self.assertTrue(r["valid"])
        self.assertTrue(any("short" in w.lower() for w in r["warnings"]))

    # --- UFC context ---

    def test_generic_sport_warns(self):
        r = validate_user_input("Who will win the NBA championship?")
        self.assertTrue(r["valid"])
        self.assertTrue(any("non-UFC" in w or "non-ufc" in w.lower() for w in r["warnings"]))

    def test_ufc_question_no_sport_warning(self):
        r = validate_user_input("Who wins UFC 300 main event?")
        self.assertTrue(r["valid"])
        sport_warnings = [w for w in r["warnings"] if "non-UFC" in w]
        self.assertEqual(len(sport_warnings), 0)

    # --- Valid inputs ---

    def test_normal_question(self):
        r = validate_user_input("Compare Khabib vs McGregor UFC fight stats")
        self.assertTrue(r["valid"])
        self.assertEqual(r["sanitized"], "Compare Khabib vs McGregor UFC fight stats")

    def test_whitespace_collapsed(self):
        r = validate_user_input("  Who   wins   the   fight?  ")
        self.assertTrue(r["valid"])
        self.assertEqual(r["sanitized"], "Who wins the fight?")

    # --- Non-string input ---

    def test_non_string_input(self):
        r = validate_user_input(12345)  # type: ignore
        self.assertFalse(r["valid"])

    def test_none_input(self):
        r = validate_user_input(None)  # type: ignore
        self.assertFalse(r["valid"])

    # --- Unicode ---

    def test_unicode_input(self):
        r = validate_user_input("Who wins: Jose Aldo vs Alexander Volkanovski?")
        self.assertTrue(r["valid"])

    def test_unicode_accented(self):
        r = validate_user_input("UFC fight analysis for Jiří Procházka")
        self.assertTrue(r["valid"])
        self.assertIn("Procházka", r["sanitized"])


class TestValidateFighterName(unittest.TestCase):
    """Tests for validate_fighter_name."""

    # --- Invalid names ---

    def test_empty_name(self):
        r = validate_fighter_name("")
        self.assertFalse(r["valid"])

    def test_unknown_name(self):
        r = validate_fighter_name("unknown")
        self.assertFalse(r["valid"])

    def test_tbd_name(self):
        r = validate_fighter_name("TBD")
        self.assertFalse(r["valid"])

    def test_none_name(self):
        r = validate_fighter_name("none")
        self.assertFalse(r["valid"])

    def test_single_char(self):
        r = validate_fighter_name("A")
        self.assertFalse(r["valid"])
        self.assertIn("short", r["error"].lower())

    def test_too_long(self):
        r = validate_fighter_name("A" * 51)
        self.assertFalse(r["valid"])
        self.assertIn("long", r["error"].lower())

    # --- Special characters ---

    def test_html_in_name(self):
        r = validate_fighter_name("<script>alert(1)</script>")
        self.assertFalse(r["valid"])

    def test_brackets_in_name(self):
        r = validate_fighter_name("Fighter[1]")
        self.assertFalse(r["valid"])

    def test_semicolon_in_name(self):
        r = validate_fighter_name("Fighter; DROP TABLE")
        self.assertFalse(r["valid"])

    # --- Valid names ---

    def test_normal_name(self):
        r = validate_fighter_name("Conor McGregor")
        self.assertTrue(r["valid"])
        self.assertEqual(r["sanitized"], "Conor McGregor")

    def test_hyphenated_name(self):
        r = validate_fighter_name("Jean-Claude Van Damme")
        self.assertTrue(r["valid"])

    def test_name_with_period(self):
        # Periods are not in the special chars blocklist
        r = validate_fighter_name("B.J. Penn")
        self.assertTrue(r["valid"])

    def test_unicode_name(self):
        r = validate_fighter_name("Jiří Procházka")
        self.assertTrue(r["valid"])

    def test_name_with_apostrophe(self):
        # Apostrophes (single quotes) ARE blocked as special chars
        r = validate_fighter_name("Israel O'Malley")
        self.assertFalse(r["valid"])

    def test_name_stripped(self):
        r = validate_fighter_name("  Khabib Nurmagomedov  ")
        self.assertTrue(r["valid"])
        self.assertEqual(r["sanitized"], "Khabib Nurmagomedov")

    # --- Non-string ---

    def test_non_string(self):
        r = validate_fighter_name(42)  # type: ignore
        self.assertFalse(r["valid"])

    # --- Numbers only ---

    def test_numbers_only(self):
        r = validate_fighter_name("12345")
        # Numbers-only passes basic validation (no special chars)
        self.assertTrue(r["valid"])


class TestValidateStatsResponse(unittest.TestCase):
    """Tests for validate_stats_response."""

    def _complete_stats(self, **overrides):
        """Return a complete, valid stats dict."""
        base = {
            "record": "29-0-0",
            "slpm": "4.10",
            "str_acc": "53%",
            "sapm": "1.75",
            "str_def": "65%",
            "age": "35",
            "reach": "70",
        }
        base.update(overrides)
        return base

    # --- Not a dict ---

    def test_non_dict(self):
        r = validate_stats_response("not a dict", "Test Fighter")  # type: ignore
        self.assertFalse(r["valid"])
        self.assertEqual(r["data_quality_score"], 0.0)

    def test_empty_dict(self):
        r = validate_stats_response({}, "Test Fighter")
        self.assertFalse(r["valid"])

    # --- Missing required keys ---

    def test_missing_record(self):
        stats = {"slpm": "4.0", "str_acc": "50%"}
        r = validate_stats_response(stats, "Test Fighter")
        self.assertFalse(r["valid"])
        self.assertIn("record", r["error"])

    # --- Complete valid stats ---

    def test_complete_stats(self):
        r = validate_stats_response(self._complete_stats(), "Khabib")
        self.assertTrue(r["valid"])
        self.assertGreater(r["data_quality_score"], 0.8)

    def test_data_quality_score_in_range(self):
        r = validate_stats_response(self._complete_stats(), "Test")
        self.assertGreaterEqual(r["data_quality_score"], 0.0)
        self.assertLessEqual(r["data_quality_score"], 1.0)

    # --- Record format ---

    def test_valid_record(self):
        r = validate_stats_response(self._complete_stats(record="15-3-1"), "Test")
        self.assertTrue(r["valid"])
        record_warnings = [w for w in r["warnings"] if "record" in w.lower()]
        self.assertEqual(len(record_warnings), 0)

    def test_record_with_nc(self):
        r = validate_stats_response(
            self._complete_stats(record="15-3-0 (1 NC)"), "Test"
        )
        self.assertTrue(r["valid"])

    def test_invalid_record_format(self):
        r = validate_stats_response(self._complete_stats(record="15 wins"), "Test")
        self.assertTrue(r["valid"])  # Still valid, just warns
        self.assertTrue(any("W-L-D" in w for w in r["warnings"]))

    def test_empty_record(self):
        r = validate_stats_response(self._complete_stats(record=""), "Test")
        # Missing required key effectively
        self.assertTrue(any("empty" in w.lower() for w in r["warnings"]))

    def test_unusually_high_fights(self):
        r = validate_stats_response(self._complete_stats(record="50-35-0"), "Test")
        self.assertTrue(any("unusually high" in w.lower() for w in r["warnings"]))

    # --- Numeric fields ---

    def test_unparseable_slpm(self):
        r = validate_stats_response(self._complete_stats(slpm="abc"), "Test")
        self.assertTrue(any("slpm" in w for w in r["warnings"]))

    def test_missing_str_acc(self):
        stats = self._complete_stats()
        del stats["str_acc"]
        r = validate_stats_response(stats, "Test")
        self.assertTrue(any("str_acc" in w for w in r["warnings"]))

    def test_percent_in_str_acc(self):
        r = validate_stats_response(self._complete_stats(str_acc="53%"), "Test")
        # Should handle percent sign gracefully
        self.assertTrue(r["valid"])

    # --- Age ---

    def test_valid_age(self):
        r = validate_stats_response(self._complete_stats(age="30"), "Test")
        age_warnings = [w for w in r["warnings"] if "age" in w.lower()]
        self.assertEqual(len(age_warnings), 0)

    def test_age_too_young(self):
        r = validate_stats_response(self._complete_stats(age="15"), "Test")
        self.assertTrue(any("age" in w.lower() and "range" in w.lower() for w in r["warnings"]))

    def test_age_too_old(self):
        r = validate_stats_response(self._complete_stats(age="60"), "Test")
        self.assertTrue(any("age" in w.lower() and "range" in w.lower() for w in r["warnings"]))

    def test_non_numeric_age(self):
        r = validate_stats_response(self._complete_stats(age="thirty"), "Test")
        self.assertTrue(any("age" in w.lower() for w in r["warnings"]))

    # --- Reach ---

    def test_valid_reach(self):
        r = validate_stats_response(self._complete_stats(reach="72"), "Test")
        reach_warnings = [w for w in r["warnings"] if "reach" in w.lower()]
        self.assertEqual(len(reach_warnings), 0)

    def test_reach_too_short(self):
        r = validate_stats_response(self._complete_stats(reach="50"), "Test")
        self.assertTrue(any("reach" in w.lower() for w in r["warnings"]))

    def test_reach_too_long(self):
        r = validate_stats_response(self._complete_stats(reach="90"), "Test")
        self.assertTrue(any("reach" in w.lower() for w in r["warnings"]))

    def test_reach_with_unit(self):
        r = validate_stats_response(self._complete_stats(reach='72"'), "Test")
        self.assertTrue(r["valid"])

    # --- Low quality score warning ---

    def test_low_quality_warns(self):
        stats = {"record": "bad-format", "slpm": "abc", "str_acc": "xyz"}
        r = validate_stats_response(stats, "Test")
        self.assertTrue(any("quality" in w.lower() for w in r["warnings"]))
        self.assertLess(r["data_quality_score"], 0.5)

    # --- Partial stats ---

    def test_partial_stats_still_valid(self):
        stats = {"record": "10-2-0"}
        r = validate_stats_response(stats, "Test")
        self.assertTrue(r["valid"])
        self.assertGreater(len(r["warnings"]), 0)  # Missing fields warned

    # --- Edge: None values ---

    def test_none_stat_values(self):
        r = validate_stats_response(
            self._complete_stats(slpm=None, sapm=None), "Test"
        )
        self.assertTrue(r["valid"])
        self.assertTrue(any("slpm" in w for w in r["warnings"]))


if __name__ == "__main__":
    unittest.main()
