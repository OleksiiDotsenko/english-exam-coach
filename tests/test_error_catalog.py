"""Tests for the error catalog: counting across tests, and habit states.

The rule the catalog exists to enforce is the unwelcome one: an error that
stays away for two tests has not gone. It is closed only after four clean
tests in a row, and it is `returned` the moment it comes back.
"""

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import SCRIPTS, coach

sys.path.insert(0, str(SCRIPTS))
import error_catalog  # noqa: E402
import log_error  # noqa: E402
import log_test  # noqa: E402

classify = error_catalog.classify


def presence(pattern):
    """'x..x' -> [True, False, False, True], oldest test first."""
    return [ch == "x" for ch in pattern]


class HabitStateTests(unittest.TestCase):
    def check(self, pattern, expected, **kwargs):
        self.assertEqual(classify(presence(pattern), **kwargs), expected, pattern)

    def test_never_seen_has_no_state(self):
        self.check("......", None)

    def test_closed_needs_four_clean_tests_in_a_row(self):
        self.check("x....", "closed")
        self.check("xx....", "closed")
        self.check("x...", "one-off")       # three clean: not closed
        self.check("xx...", "fading")
        self.check("xxxxxx....", "closed")  # however chronic it used to be

    def test_two_clean_tests_is_not_closed(self):
        self.check("xxx..", "fading")
        self.check("x.x..", "fading")

    def test_new_is_a_first_appearance_in_the_latest_test(self):
        self.check(".....x", "new")
        self.check("x", "new")

    def test_returned_is_back_after_two_or_more_clean_tests(self):
        self.check("x..x", "returned")
        self.check("xx...x", "returned")
        self.check("x.....x", "returned")   # even after it had been closed
        self.check("x.x", "recurring")      # one clean test is not a return

    def test_chronic_is_most_tests_and_still_present(self):
        self.check("xxxxxx", "chronic")
        self.check("xxx.xx", "chronic")
        self.check("x.xxxx", "chronic")
        self.check("xxx", "recurring")      # too few tests to call it a habit
        self.check("x.x.x.", "fading")

    def test_one_clean_test_does_not_break_a_standing_habit(self):
        self.check("xxxxx.", "chronic")
        self.check("xxxx..", "fading")

    def test_recurring_is_present_now_but_not_in_most_tests(self):
        self.check("..x.xx", "recurring")
        self.check(".x.x.x", "recurring")

    def test_one_off_was_seen_once_and_not_in_the_latest_test(self):
        self.check("..x..", "one-off")
        self.check("....x.", "one-off")

    def test_the_closing_rule_can_be_changed(self):
        self.check("x..", "closed", closed_after=2)
        self.check("x..", "one-off", closed_after=3)

    def test_every_state_has_a_meaning_and_an_order(self):
        self.assertEqual(sorted(error_catalog.STATE_ORDER),
                         sorted(error_catalog.STATE_MEANING))


class Base(unittest.TestCase):
    TESTS = [("Alpha", "2026-07-01"), ("Bravo", "2026-07-08"),
             ("Charlie", "2026-07-15"), ("Delta", "2026-07-22"),
             ("Echo", "2026-07-29"), ("Foxtrot", "2026-08-05")]

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name) / "progress"
        self.batch_file = Path(self._tmp.name) / "batch.jsonl"

    def tearDown(self):
        self._tmp.cleanup()

    def quietly(self, main, args):
        """Fill the logs in-process: a subprocess per row would be slow."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(["--base", str(self.base)] + [str(a) for a in args])
        self.assertEqual(code, 0, err.getvalue())

    def log_tests(self, count=6):
        for name, date in self.TESTS[:count]:
            self.quietly(log_test.main, [
                "--name", name, "--date", date, "--exam", "toefl-ibt",
                "--reading", "4.0", "--listening", "4.0", "--writing", "4.0",
                "--speaking", "4.0"])

    def session(self, name):
        date = dict(self.TESTS)[name]
        return "test-%s-%s" % (name.lower(), date.replace("-", ""))

    def mistakes(self, test_name, rows):
        self.batch_file.write_text(
            "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
        args = ["--batch", self.batch_file]
        if test_name:
            args += ["--session", self.session(test_name)]
        self.quietly(log_error.main, args)

    def catalog(self, *args):
        result = coach(self.base, "catalog", *args)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def data(self, *args):
        return json.loads(self.catalog("--json", *args))


def row(subtype, point, evidence="", fix="", category="grammar", **extra):
    data = {"category": category, "subtype": subtype, "point": point}
    if evidence:
        data["evidence"] = evidence
    if fix:
        data["fix"] = fix
    data.update(extra)
    return data


ARTICLE = "missing article before a singular count noun"
SPELL = "truly spelled with a double l"


class CatalogTests(Base):
    def populate(self):
        self.log_tests()
        for name, _date in self.TESTS:                      # in every test
            self.mistakes(name, [row("article", ARTICLE, "it was good idea",
                                     "it was a good idea")])
        self.mistakes("Alpha", [
            row("article", ARTICLE.upper(), "I am student", "I am a student"),
            row("spelling", SPELL, "trully", "truly", category="lexis"),
            row("word-order", "indirect question word order",
                "know what time does it start", "know what time it starts")])
        self.mistakes("Bravo", [
            row("spelling", SPELL, "Trully ", "truly", category="lexis"),
            row("word-choice", "adapted, not adopted", "adopted to the climate",
                "adapted to the climate", category="lexis")])
        self.mistakes("Delta", [row("spelling", SPELL, "trully", "truly",
                                    category="lexis")])
        self.mistakes("Echo", [
            row("pronoun", "no reflexive after concentrate", "concentrate myself",
                "concentrate", transfer="the verb is reflexive in the first language")])
        self.mistakes("Foxtrot", [
            row("word-choice", "adapted, not adopted", "adopted to the world",
                "adapted to the world", category="lexis"),
            row("negation", "negative questions answered backwards",
                category="comprehension")])
        self.mistakes(None, [row("preposition", "depend on, not depend of",
                                 "depends of", "depends on")])

    def test_an_empty_ledger_is_said_plainly(self):
        out = self.catalog()
        self.assertIn("No mistakes are logged", out)
        self.assertFalse((self.base / "reports").exists())

    def test_counts_per_point_and_per_test(self):
        self.populate()
        data = self.data()
        self.assertEqual(data["mistakes"], 16)
        self.assertEqual([t["name"] for t in data["tests"]],
                         [name for name, _d in self.TESTS])
        points = {p["label"]: p for p in data["points"]}
        article = points[ARTICLE]
        # The same point written in capitals is the same point.
        self.assertEqual(article["mistakes"], 7)
        self.assertEqual(article["per_test"], [2, 1, 1, 1, 1, 1])
        self.assertEqual(article["tests_hit"], 6)
        self.assertEqual(points[SPELL]["per_test"], [1, 1, 0, 1, 0, 0])
        # Most frequent first.
        self.assertEqual(data["points"][0]["label"], ARTICLE)

    def test_habit_states_follow_the_rule_of_four(self):
        self.populate()
        states = {p["label"]: p["state"] for p in self.data()["points"]}
        self.assertEqual(states[ARTICLE], "chronic")
        self.assertEqual(states[SPELL], "fading")                       # 2 clean
        self.assertEqual(states["indirect question word order"], "closed")   # 5 clean
        self.assertEqual(states["adapted, not adopted"], "returned")
        self.assertEqual(states["negative questions answered backwards"], "new")
        self.assertEqual(states["no reflexive after concentrate"], "one-off")

    def test_practice_mistakes_count_in_totals_but_not_in_any_test(self):
        self.populate()
        points = {p["label"]: p for p in self.data()["points"]}
        practice = points["depend on, not depend of"]
        self.assertEqual(practice["practice"], 1)
        self.assertEqual(practice["tests_hit"], 0)
        self.assertIsNone(practice["state"])
        out = self.catalog("--no-write")
        self.assertIn("1 mistake from practice outside the logged tests is counted", out)

    def test_categories_and_types_are_ranked(self):
        self.populate()
        data = self.data()
        self.assertEqual([c["category"] for c in data["categories"]],
                         ["grammar", "lexis", "comprehension"])
        self.assertEqual(data["categories"][0]["mistakes"], 10)
        self.assertEqual(data["types"][0]["label"], "grammar/article")
        self.assertEqual(data["types"][0]["tests_hit"], 6)

    def test_word_for_word_repeats_ignore_case_and_spacing(self):
        self.populate()
        repeats = self.data()["repeats"]
        trully = [r for r in repeats if r["fix"] == "truly"][0]
        self.assertEqual(trully["count"], 3)
        self.assertEqual(trully["where"], ["Alpha", "Bravo", "Delta"])
        # "it was good idea" was logged in all six tests.
        self.assertEqual(repeats[0]["count"], 6)

    def test_first_language_cases_are_listed_with_their_cause(self):
        self.populate()
        cases = self.data()["transfer"]
        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0]["test"], "Echo")
        self.assertEqual(cases[0]["transfer"],
                         "the verb is reflexive in the first language")

    def test_the_report_has_every_section_and_the_rule_in_words(self):
        self.populate()
        out = self.catalog("--no-write")
        for heading in ("# Error catalog", "## By category", "## By error type",
                        "## Points, most frequent first", "## Point × test",
                        "## Habit states", "## Repeated word for word",
                        "## Carried over from the first language"):
            self.assertIn(heading, out)
        self.assertIn("**16 mistakes · 7 distinct points · 6 tests "
                      "(2026-07-01 → 2026-08-05)**", out)
        self.assertIn("closed only after it stays out of 4 tests in a row", out)
        self.assertIn("| %s | 2 | 1 | 1 | 1 | 1 | 1 | 7 |" % ARTICLE, out)
        self.assertIn("| %s | 1 | 1 | · | 1 | · | · | 3 |" % SPELL, out)
        self.assertIn("ALP = Alpha", out)
        self.assertIn("Not affiliated with any exam board", out)
        self.assertNotIn("## Full catalog", out)

    def test_the_full_catalog_quotes_every_mistake(self):
        self.populate()
        out = self.catalog("--full", "--no-write")
        self.assertIn("## Full catalog", out)
        self.assertIn("- *I am student* → I am a student — Alpha", out)
        self.assertIn("**%s** (7) — chronic" % ARTICLE, out)
        self.assertIn("- (no quotation logged) — Foxtrot", out)

    def test_the_summary_prints_and_the_full_report_is_written(self):
        self.populate()
        out = self.catalog()
        written = (self.base / "reports" / "error-catalog.md").read_text(encoding="utf-8")
        self.assertNotIn("## Full catalog", out)
        self.assertIn("## Full catalog", written)

    def test_points_listing_shows_the_labels_already_in_use(self):
        self.populate()
        out = self.catalog("--points")
        self.assertRegex(out, r"grammar/article\s+7\s+%s" % ARTICLE)
        self.assertRegex(out, r"lexis/spelling\s+3\s+%s" % SPELL)
        self.assertEqual(len(out.strip().splitlines()), 7)

    def test_top_limits_the_tables_and_says_what_was_left_out(self):
        self.populate()
        out = self.catalog("--top", "2", "--no-write")
        self.assertIn("…and 5 more in the full report.", out)

    def test_the_closing_rule_is_adjustable_from_the_command_line(self):
        self.populate()
        states = {p["label"]: p["state"]
                  for p in self.data("--closed-after", "2")["points"]}
        self.assertEqual(states[SPELL], "closed")
        self.assertEqual(coach(self.base, "catalog", "--closed-after", "0").returncode, 2)

    def test_table_cells_survive_pipes_and_newlines_in_what_was_logged(self):
        self.log_tests(2)
        self.mistakes("Alpha", [row("article", "a | an before\na vowel sound",
                                    "a hour | an hour", "an hour")])
        out = self.catalog("--full", "--no-write")
        for line in out.splitlines():
            if line.startswith("| 1 | a "):
                self.assertEqual(line.count(" | "), line.replace("\\|", "").count(" | "))
        self.assertIn("a \\| an before a vowel sound", out)


class ThinDataTests(Base):
    def test_without_tests_nothing_per_test_is_shown_or_guessed(self):
        self.mistakes(None, [row("article", ARTICLE, "I am student", "I am a student"),
                             row("article", ARTICLE, "it is good idea", "it is a good idea")])
        out = self.catalog("--no-write")
        self.assertIn("**2 mistakes · 1 distinct point**", out)
        self.assertNotIn("Habit states", out)
        self.assertNotIn("Point × test", out)
        self.assertNotIn(" of 0", out)
        self.assertIn("need at least two logged tests", out)
        self.assertIsNone(self.data()["points"][0]["state"])

    def test_one_test_is_not_enough_for_a_habit_state(self):
        self.log_tests(1)
        self.mistakes("Alpha", [row("article", ARTICLE, "I am student", "I am a student")])
        out = self.catalog("--no-write")
        self.assertNotIn("Habit states", out)
        self.assertIn("1 of 1", out)
        self.assertIsNone(self.data()["points"][0]["state"])

    def test_two_tests_give_states_but_never_chronic(self):
        self.log_tests(2)
        for name in ("Alpha", "Bravo"):
            self.mistakes(name, [row("article", ARTICLE, "x", "y")])
        self.assertEqual(self.data()["points"][0]["state"], "recurring")

    def test_a_mistake_tied_to_an_unknown_session_is_practice(self):
        self.log_tests(2)
        self.mistakes(None, [row("article", ARTICLE, "x", "y", session="2026-07-03-am")])
        point = self.data()["points"][0]
        self.assertEqual((point["practice"], point["tests_hit"]), (1, 0))

    def test_an_amended_test_keeps_its_mistakes(self):
        self.log_tests(2)
        self.mistakes("Alpha", [row("article", ARTICLE, "x", "y")])
        result = coach(self.base, "log-test", "--name", "Alpha", "--date",
                       "2026-07-01", "--exam", "toefl-ibt", "--reading", "5.0", "--amend")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = self.data()
        self.assertEqual(len(data["tests"]), 2)
        self.assertEqual(data["points"][0]["per_test"], [1, 0])

    def test_short_column_names_stay_unique(self):
        names = error_catalog.short_names([{"name": "Mock 1"}, {"name": "Mock 2"},
                                           {"name": "Mock 3"}, {"name": "!!!"}])
        self.assertEqual(len(set(names)), 4)
        self.assertEqual(names[0], "MOC")


if __name__ == "__main__":
    unittest.main()
