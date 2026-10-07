"""Tests for full-test results: log_test.py and the reports built on them.

A full test is the number the learner is working towards, so the scores are
recorded as given, a derived figure is labelled as derived, and a report never
calls a difference between two tests a trend.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import SCRIPTS, coach

sys.path.insert(0, str(SCRIPTS))
import full_tests  # noqa: E402
import log_test  # noqa: E402


def tests_of(base):
    path = Path(base) / "tests.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name) / "progress"

    def tearDown(self):
        self._tmp.cleanup()

    def log(self, name, date, *args, **kwargs):
        exam = kwargs.pop("exam", "toefl-ibt")
        return coach(self.base, "log-test", "--name", name, "--date", date,
                     "--exam", exam, *args)

    def toefl(self, name, date, reading, listening, writing, speaking, *extra):
        result = self.log(name, date, "--reading", reading, "--listening", listening,
                          "--writing", writing, "--speaking", speaking, *extra)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result


class PureFunctionTests(unittest.TestCase):
    def test_half_band_rounding_sends_ties_up(self):
        self.assertEqual(log_test.round_half_band(4.25), 4.5)
        self.assertEqual(log_test.round_half_band(4.75), 5.0)
        self.assertEqual(log_test.round_half_band(4.24), 4.0)
        self.assertEqual(log_test.round_half_band(4.125), 4.0)
        self.assertEqual(log_test.round_half_band(4.5), 4.5)

    def test_number_lists(self):
        self.assertEqual(log_test.parse_number_list("5,4, 5"), [5, 4, 5])
        self.assertEqual(log_test.parse_number_list("4.5"), 4.5)
        self.assertEqual(log_test.parse_number_list("3"), 3)
        for bad in ("", ",", "a,b", "nan", "inf"):
            with self.assertRaises(ValueError):
                log_test.parse_number_list(bad)

    def test_exam_family(self):
        self.assertEqual(log_test.exam_family("toefl-ibt"), "toefl")
        self.assertEqual(log_test.exam_family("IELTS-Academic"), "ielts")
        self.assertEqual(log_test.exam_family("cefr-c1"), "cefr")
        self.assertIsNone(log_test.exam_family("duolingo"))

    def test_scale_checks(self):
        self.assertIsNone(log_test.check_scale("toefl-ibt", "reading", 4.5))
        self.assertIn("outside", log_test.check_scale("toefl-ibt", "reading", 6.5))
        self.assertIn("outside", log_test.check_scale("toefl-ibt", "reading", 0.5))
        self.assertIn("steps", log_test.check_scale("toefl-ibt", "reading", 4.2))
        self.assertIsNone(log_test.check_scale("ielts-academic", "reading", 0))
        self.assertIsNone(log_test.check_scale("cefr-c1", "reading", 187))
        self.assertIsNone(log_test.check_scale("some-other-exam", "reading", 77))
        self.assertIn("negative", log_test.check_scale("some-other-exam", "reading", -1))

    def test_find_test_by_id_name_and_unique_prefix(self):
        tests = [{"name": "Saturn", "session": "test-saturn-20260801"},
                 {"name": "Sirius", "session": "test-sirius-20260808"},
                 {"name": "Mock 4", "session": "test-mock-4-20260815"}]
        self.assertEqual(full_tests.find_test(tests, "test-sirius-20260808")["name"], "Sirius")
        self.assertEqual(full_tests.find_test(tests, "saturn")["name"], "Saturn")
        self.assertEqual(full_tests.find_test(tests, "mo")["name"], "Mock 4")
        self.assertIsNone(full_tests.find_test(tests, "s"))      # ambiguous
        self.assertIsNone(full_tests.find_test(tests, "pluto"))


class LogTestTests(Base):
    def test_a_test_is_recorded_as_given(self):
        result = self.log("Saturn", "2026-08-25", "--source", "mock platform",
                          "--reading", "4.0", "--listening", "5.0", "--writing", "3.5",
                          "--speaking", "4.0", "--overall", "4.0",
                          "--task", "email=3", "--task", "Listen and Repeat=5,5,4,2",
                          "--note", "taken the day after another full test")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("session id: test-saturn-20260825", result.stdout)
        row = tests_of(self.base)[0]
        self.assertEqual(row["session"], "test-saturn-20260825")
        self.assertEqual(row["ts"], "2026-08-25T00:00:00")
        self.assertEqual(row["sections"], {"reading": 4, "listening": 5,
                                           "writing": 3.5, "speaking": 4})
        self.assertEqual(row["overall"], 4)
        self.assertNotIn("overall_computed", row)
        self.assertEqual(row["tasks"], {"email": 3, "listen_and_repeat": [5, 5, 4, 2]})
        self.assertEqual(row["source"], "mock platform")

    def test_a_computed_overall_is_labelled_as_computed(self):
        self.toefl("Alpha", "2026-07-01", "4.0", "5.0", "4.5", "3.5")   # mean 4.25
        row = tests_of(self.base)[0]
        self.assertEqual(row["overall"], 4.5)
        self.assertIs(row["overall_computed"], True)

    def test_no_overall_is_invented_from_a_partial_test(self):
        self.assertEqual(self.log("Half", "2026-07-01", "--reading", "4.0",
                                  "--listening", "5.0").returncode, 0)
        self.assertNotIn("overall", tests_of(self.base)[0])

    def test_no_overall_is_computed_for_an_exam_with_another_rule(self):
        self.assertEqual(self.log("C1 mock", "2026-07-01", "--reading", "180",
                                  "--listening", "175", "--writing", "170",
                                  "--speaking", "185", exam="cefr-c1").returncode, 0)
        self.assertNotIn("overall", tests_of(self.base)[0])

    def test_scores_off_the_scale_are_refused(self):
        for args in (["--reading", "7"], ["--reading", "4.3"],
                     ["--reading", "4", "--overall", "9"]):
            result = self.log("Bad", "2026-07-01", *args)
            self.assertEqual(result.returncode, 2, args)
        self.assertEqual(tests_of(self.base), [])

    def test_an_unknown_exam_is_accepted_without_a_range_check(self):
        result = self.log("Other", "2026-07-01", "--section", "literacy=135",
                          exam="some-other-exam")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(tests_of(self.base)[0]["sections"], {"literacy": 135})

    def test_other_sections_can_be_named(self):
        result = self.log("FCE", "2026-07-01", "--reading", "170",
                          "--section", "Use of English=165", exam="cefr-b2")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(tests_of(self.base)[0]["sections"],
                         {"reading": 170, "use_of_english": 165})

    def test_input_errors_write_nothing(self):
        for args in (["--date", "25/08/2026", "--reading", "4"],
                     ["--date", "2026-08-25"],                       # no score
                     ["--date", "2026-08-25", "--reading", "4", "--task", "email"],
                     ["--date", "2026-08-25", "--reading", "4", "--task", "email=x"],
                     ["--date", "2026-08-25", "--reading", "4", "--section", "a=1,2"]):
            result = coach(self.base, "log-test", "--name", "X", "--exam",
                           "toefl-ibt", *args)
            self.assertEqual(result.returncode, 2, args)
            self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(tests_of(self.base), [])

    def test_the_same_test_twice_needs_amend(self):
        self.toefl("Alpha", "2026-07-01", "4.0", "5.0", "4.5", "3.5")
        again = self.log("Alpha", "2026-07-01", "--reading", "4.5")
        self.assertEqual(again.returncode, 2)
        self.assertIn("--amend", again.stderr)
        self.assertEqual(len(tests_of(self.base)), 1)

    def test_amend_appends_and_the_newer_entry_wins(self):
        self.toefl("Alpha", "2026-07-01", "4.0", "5.0", "4.5", "3.5")
        self.toefl("Bravo", "2026-07-08", "4.0", "4.0", "4.0", "4.0")
        fixed = self.log("Alpha", "2026-07-01", "--reading", "4.5", "--listening",
                         "5.0", "--writing", "4.5", "--speaking", "3.5", "--amend")
        self.assertEqual(fixed.returncode, 0, fixed.stderr)
        self.assertIn("amended test", fixed.stdout)
        self.assertEqual(len(tests_of(self.base)), 3)      # nothing rewritten
        loaded = log_test.load_tests(self.base)
        self.assertEqual([t["name"] for t in loaded], ["Alpha", "Bravo"])
        self.assertEqual(loaded[0]["sections"]["reading"], 4.5)

    def test_tests_are_ordered_by_the_day_taken_not_the_day_logged(self):
        self.toefl("Later", "2026-07-08", "4.0", "4.0", "4.0", "4.0")
        self.toefl("Earlier", "2026-07-01", "4.0", "4.0", "4.0", "4.0")
        self.assertEqual([t["name"] for t in log_test.load_tests(self.base)],
                         ["Earlier", "Later"])

    def test_a_damaged_line_does_not_hide_the_other_tests(self):
        self.toefl("Alpha", "2026-07-01", "4.0", "5.0", "4.5", "3.5")
        with open(self.base / "tests.jsonl", "a", encoding="utf-8") as handle:
            handle.write("{broken\n")
            handle.write(json.dumps({"name": "x", "session": "s", "sections": "no"}) + "\n")
        self.toefl("Bravo", "2026-07-08", "4.0", "4.0", "4.0", "4.0")
        self.assertEqual([t["name"] for t in log_test.load_tests(self.base)],
                         ["Alpha", "Bravo"])

    def test_a_test_logged_by_mistake_can_be_withdrawn(self):
        self.toefl("Alpha", "2026-07-01", "4.0", "5.0", "4.5", "3.5")
        self.toefl("Bravo", "2026-07-08", "4.0", "4.0", "4.0", "4.0")
        before = (self.base / "tests.jsonl").read_bytes()
        result = coach(self.base, "log-test", "--void", "bravo")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("withdrawn: Bravo (test-bravo-20260708)", result.stdout)
        self.assertTrue((self.base / "tests.jsonl").read_bytes().startswith(before))
        self.assertEqual([t["name"] for t in log_test.load_tests(self.base)], ["Alpha"])
        # ...and logged again afterwards without --amend
        self.toefl("Bravo", "2026-07-08", "4.5", "4.0", "4.0", "4.0")
        self.assertEqual([t["name"] for t in log_test.load_tests(self.base)],
                         ["Alpha", "Bravo"])

    def test_withdrawing_an_unknown_or_ambiguous_test_is_an_error(self):
        self.toefl("Mock", "2026-07-01", "4.0", "5.0", "4.5", "3.5")
        self.toefl("Mock", "2026-07-08", "4.0", "4.0", "4.0", "4.0")
        for name in ("Pluto", "Mock"):
            result = coach(self.base, "log-test", "--void", name)
            self.assertEqual(result.returncode, 2, name)
        self.assertEqual(coach(self.base, "log-test", "--void",
                               "test-mock-20260708").returncode, 0)
        self.assertEqual(len(log_test.load_tests(self.base)), 1)

    def test_name_and_exam_are_still_required_to_log(self):
        result = coach(self.base, "log-test", "--reading", "4")
        self.assertEqual(result.returncode, 2)
        self.assertIn("--name and --exam are required", result.stderr)

    def test_tutor_mode_keeps_each_learners_tests_apart(self):
        coach(self.base, "log-test", "--name", "One", "--exam", "toefl-ibt",
              "--reading", "4", learner="anna")
        self.assertEqual(log_test.load_tests(self.base), [])
        self.assertEqual(len(log_test.load_tests(self.base / "learners" / "anna")), 1)


class HistoryReportTests(Base):
    def six(self):
        scores = [("Alpha", "2026-07-01", "4.0", "5.0", "4.5", "2.5"),
                  ("Bravo", "2026-07-08", "5.0", "4.0", "2.5", "3.5"),
                  ("Charlie", "2026-07-15", "4.5", "5.0", "4.0", "3.0"),
                  ("Delta", "2026-07-22", "4.0", "6.0", "4.0", "3.5"),
                  ("Echo", "2026-07-29", "5.0", "5.0", "4.0", "3.5"),
                  ("Foxtrot", "2026-08-05", "5.5", "5.5", "5.5", "4.0")]
        for row in scores:
            self.toefl(*row, "--task", "interview=3,3,2.5,3")

    def report(self, *args):
        result = coach(self.base, "tests", *args)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_nothing_logged_is_said_plainly(self):
        out = self.report()
        self.assertIn("No full tests are logged", out)
        self.assertFalse((self.base / "reports").exists())

    def test_history_marks_records_and_the_best_possible_sum(self):
        self.six()
        out = self.report()
        self.assertIn("| 4 | Delta | 2026-07-22 | 4.0 | **6.0** | 4.0 | 3.5 | 17.5 |", out)
        self.assertIn("| 6 | Foxtrot | 2026-08-05 | **5.5** | 5.5 | **5.5** | **4.0** |", out)
        # 5.5 + 6.0 + 5.5 + 4.0 = 21 -> 5.25 -> 5.5 on the half-band rule
        self.assertIn("added up: **21** → an overall of **5.5**", out)
        self.assertIn("they have not happened together", out)
        self.assertIn("overall computed from the four sections", out)
        self.assertIn("**Foxtrot** against Echo: Reading +0.5", out)
        self.assertIn("Not affiliated with any exam board", out)

    def test_halves_are_compared_only_from_four_tests(self):
        self.six()
        out = self.report()
        self.assertIn("## First half against second half", out)
        self.assertIn("| Tests 1–3 | 4.5 | 4.67 | 3.67 | 3 | 15.83 |", out)
        self.assertIn("| Change | +0.33 | +0.83 | +0.83 | +0.67 | +2.67 |", out)
        self.assertNotIn("not yet a trend", out)

    def test_three_tests_get_a_warning_instead_of_a_trend(self):
        self.toefl("Alpha", "2026-07-01", "4.0", "5.0", "4.5", "2.5")
        self.toefl("Bravo", "2026-07-08", "5.0", "4.0", "2.5", "3.5")
        self.toefl("Charlie", "2026-07-15", "4.5", "5.0", "4.0", "3.0")
        out = self.report()
        self.assertNotIn("First half against second half", out)
        self.assertIn("not yet a trend", out)

    def test_one_test_marks_no_records(self):
        self.toefl("Alpha", "2026-07-01", "4.0", "5.0", "4.5", "2.5")
        out = self.report()
        self.assertNotIn("**4.0**", out)
        self.assertNotIn("added up", out)

    def test_mixed_sources_are_named_and_a_single_source_is_not(self):
        self.six()
        self.assertNotIn("| Source |", self.report("--no-write"))
        self.toefl("Golf", "2026-08-12", "5.0", "5.0", "5.0", "4.0",
                   "--source", "self-run mock (indicative)")
        out = self.report("--no-write")
        self.assertIn("| Overall | Source |", out)
        self.assertIn("| self-run mock (indicative) |", out)
        self.assertIn("| not stated |", out)

    def test_per_item_scores_show_as_their_average(self):
        self.six()
        self.assertIn("| Interview | 2.88 | 2.88 |", self.report())

    def test_history_is_written_unless_asked_not_to(self):
        self.six()
        self.report("--no-write")
        self.assertFalse((self.base / "reports" / "tests-history.md").exists())
        self.report()
        self.assertTrue((self.base / "reports" / "tests-history.md").is_file())

    def test_json_output_is_the_logged_tests(self):
        self.six()
        data = json.loads(self.report("--json"))
        self.assertEqual([t["name"] for t in data["tests"]][-1], "Foxtrot")

    def test_a_partial_test_does_not_break_the_table(self):
        self.toefl("Alpha", "2026-07-01", "4.0", "5.0", "4.5", "2.5")
        self.log("Reading only", "2026-07-08", "--reading", "5.0")
        out = self.report()
        self.assertIn("| 2 | Reading only | 2026-07-08 | **5.0** | — | — | — | — | — |", out)


class ReviewReportTests(Base):
    def setUp(self):
        super().setUp()
        self.toefl("Alpha", "2026-07-01", "4.0", "5.0", "4.5", "2.5",
                   "--task", "interview=3,3,3,3.5")
        self.toefl("Bravo", "2026-07-08", "5.0", "4.0", "2.5", "3.5",
                   "--task", "interview=2.5,3,3,3")
        self.toefl("Charlie", "2026-07-15", "4.5", "5.0", "4.0", "3.0")

    def mistake(self, session, subtype, point, evidence, fix, category="grammar",
                **extra):
        args = ["log-error", "--category", category, "--subtype", subtype,
                "--point", point, "--evidence", evidence, "--fix", fix]
        if session:
            args += ["--session", session]
        for key, value in extra.items():
            args += ["--" + key.replace("_", "-"), value]
        result = coach(self.base, *args)
        self.assertEqual(result.returncode, 0, result.stderr)

    def review(self, name, *args):
        result = coach(self.base, "tests", "--test", name, *args)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_scores_are_set_against_the_previous_test_and_the_earlier_average(self):
        out = self.review("Charlie", "--no-write")
        self.assertIn("test 3 of 3 logged", out)
        # reading 4.5: previous 5.0 (−0.5), earlier average 4.5 (=)
        self.assertIn("| Reading | 4.5 | −0.5 | = |", out)
        # listening 5.0 ties the record set by Alpha
        self.assertIn("| Listening | 5.0 | +1 | +0.5 | ties the record |", out)
        self.assertIn("Overall computed from the four sections", out)

    def test_the_first_test_has_nothing_to_compare_with(self):
        out = self.review("Alpha", "--no-write")
        self.assertIn("| Reading | 4.0 |  |  |  |", out)
        self.assertNotIn("Stayed away", out)

    def test_a_review_only_looks_back_never_forward(self):
        self.mistake("test-charlie-20260715", "article", "a before a job",
                     "she is doctor", "she is a doctor")
        out = self.review("Bravo", "--no-write")
        self.assertIn("test 2 of 3 logged", out)
        self.assertNotIn("she is doctor", out)
        self.assertIn("No mistakes are logged for this test yet", out)
        self.assertIn("--session test-bravo-20260708", out)

    def test_mistakes_split_into_new_and_seen_before(self):
        self.mistake("test-alpha-20260701", "article", "a before a job",
                     "I am student", "I am a student")
        self.mistake("test-charlie-20260715", "article", "A before a job",
                     "she is doctor", "she is a doctor",
                     task_type="toefl-write-email")
        self.mistake("test-charlie-20260715", "pronoun",
                     "no reflexive after concentrate", "concentrate myself",
                     "concentrate", transfer="reflexive in the first language")
        self.mistake("test-bravo-20260708", "agreement", "third-person -s",
                     "she teach", "she teaches")
        out = self.review("Charlie", "--no-write")
        self.assertIn("**2 mistakes in 2 points — 1 new, 1 seen before**", out)
        self.assertIn("| a before a job | grammar/article | 1 | 2 of 3 | Alpha |", out)
        self.assertIn("| no reflexive after concentrate | grammar/pronoun | 1 |", out)
        self.assertIn("- *she is doctor* → she is a doctor — toefl-write-email", out)
        self.assertIn("from the first language: reflexive in the first language", out)
        self.assertNotIn("I am student", out)        # an earlier test's wording
        # third-person -s was in Bravo, not here: one clean test, three to go
        self.assertIn("| third-person -s | grammar/agreement | 1 of 3 | Bravo | "
                      "1 clean, 3 to go |", out)

    def test_task_detail_shows_per_item_scores(self):
        out = self.review("Bravo", "--no-write")
        self.assertIn("| Interview | 2.88 | 2.5 3 3 3 | 3.12 | 3.12 |", out)

    def test_an_unknown_or_ambiguous_test_is_an_error(self):
        self.toefl("Chaplin", "2026-07-22", "4.0", "4.0", "4.0", "4.0")
        for name in ("Pluto", "Cha"):
            result = coach(self.base, "tests", "--test", name)
            self.assertEqual(result.returncode, 2)
            self.assertIn("Logged: Alpha, Bravo, Charlie, Chaplin", result.stderr)

    def test_the_review_is_written_under_the_session_id(self):
        self.review("Charlie")
        self.assertTrue((self.base / "reports" / "test-charlie-20260715.md").is_file())


if __name__ == "__main__":
    unittest.main()
