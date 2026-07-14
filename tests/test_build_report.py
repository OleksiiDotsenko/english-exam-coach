"""Tests for build_report.py: session isolation, CEFR normalization, log safety."""

import tempfile
import unittest
from pathlib import Path

from helpers import BUILD_REPORT, log_attempt, run_script


def seed_two_sessions(base):
    """Three attempts in the morning session, one in the evening session."""
    log_attempt(base, score=7, max=10, seconds=540,
                ts="2026-07-08T09:10:00", session="2026-07-08-am")
    log_attempt(base, **{"exam": "ielts-academic", "skill": "writing-evaluator",
                         "task-type": "task-2-essay", "band-estimate": "6.5-7.0",
                         "seconds": 1980, "ts": "2026-07-08T09:45:00",
                         "session": "2026-07-08-am"})
    log_attempt(base, **{"exam": "toefl-ibt", "skill": "reading-use-of-english",
                         "task-type": "inference", "level": "B2",
                         "score": 24, "max": 30, "seconds": 600,
                         "ts": "2026-07-08T10:20:00", "session": "2026-07-08-am"})
    log_attempt(base, **{"task-type": "open-cloze", "score": 4, "max": 8,
                         "seconds": 300, "ts": "2026-07-08T19:00:00",
                         "session": "2026-07-08-pm"})


class BuildReportTests(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name) / "coach"
        self.addCleanup(self._tmp.cleanup)

    def build(self, *args):
        result = run_script(BUILD_REPORT, ["--base", str(self.base)] + list(args))
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def test_session_scope_defaults_to_most_recent_session(self):
        seed_two_sessions(self.base)
        result = self.build("--scope", "session")
        self.assertIn("session: 2026-07-08-pm", result.stdout)
        self.assertIn("**1 task ·", result.stdout)

    def test_explicit_session_is_isolated(self):
        seed_two_sessions(self.base)
        result = self.build("--scope", "session", "--session", "2026-07-08-am")
        self.assertIn("session: 2026-07-08-am", result.stdout)
        self.assertIn("**3 tasks ·", result.stdout)
        self.assertNotIn("Open cloze", result.stdout)

    def test_report_file_written_with_frontmatter_and_disclaimer(self):
        seed_two_sessions(self.base)
        self.build("--scope", "session", "--session", "2026-07-08-am")
        report = self.base / "reports" / "session-2026-07-08-am.md"
        self.assertTrue(report.exists())
        text = report.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        for key in ("type: exam-session", "date: 2026-07-08",
                    "session: 2026-07-08-am", "tasks: 3", "minutes:", "exams:"):
            self.assertIn(key, text)
        self.assertIn("Indicative self-practice estimates", text)

    def test_minutes_and_table_contents(self):
        seed_two_sessions(self.base)
        result = self.build("--scope", "session", "--session", "2026-07-08-am")
        self.assertIn("**3 tasks · 52 min on task**", result.stdout)  # 3120 s
        self.assertIn("| Writing | Task 2 essay | IELTS Academic | 6.5–7.0 | 33m |",
                      result.stdout)
        self.assertIn("| Reading/UoE | Key word transformation | CEFR C1 "
                      "| 7/10 | 9m |", result.stdout)

    def test_cefr_normalization_ielts_band_and_objective_reading(self):
        seed_two_sessions(self.base)
        result = self.build("--scope", "session", "--session", "2026-07-08-am")
        # writing: IELTS band 6.75 -> B2. reading: KWT 70% at C1 -> B2/C1 (4.5)
        # averaged with the TOEFL reading drill 24/30 at B2, now correctly
        # scored as an objective 80% -> B2 (4.0), not misread as a legacy band;
        # mean 4.25 -> B2.
        self.assertIn("~B2 (writing)", result.stdout)
        self.assertIn("~B2 (reading)", result.stdout)

    def test_cefr_normalization_toefl_2026_band_scale(self):
        log_attempt(self.base, **{"exam": "toefl-ibt", "skill": "speaking-coach",
                                  "task-type": "take-an-interview", "level": "B2",
                                  "score": 4.5, "max": 6, "seconds": 480,
                                  "ts": "2026-07-10T09:00:00",
                                  "session": "2026-07-10-am"})
        log_attempt(self.base, **{"exam": "toefl-ibt", "skill": "writing-evaluator",
                                  "task-type": "write-an-email", "level": "C1",
                                  "band-estimate": "5.0-5.5", "seconds": 420,
                                  "ts": "2026-07-10T09:15:00",
                                  "session": "2026-07-10-am"})
        result = self.build("--scope", "session", "--session", "2026-07-10-am")
        # band 4.5 -> B2; band midpoint 5.25 -> C1 (official ETS alignment)
        self.assertIn("~B2 (speaking)", result.stdout)
        self.assertIn("~C1 (writing)", result.stdout)

    def test_overview_covers_all_sessions_with_streak_and_extremes(self):
        seed_two_sessions(self.base)
        result = self.build("--scope", "all")
        self.assertIn("type: progress-overview", result.stdout)
        self.assertIn("4 attempts · 2 sessions · 1 day practised", result.stdout)
        # Seed dates are in the past, so the run has lapsed: "last", not "current".
        self.assertIn("last streak: 1 day", result.stdout)
        self.assertIn("**Weakest:** Open cloze — about a level below target",
                      result.stdout)
        self.assertTrue((self.base / "reports" / "progress-overview.md").exists())

    def test_weakest_task_type_drives_recommendation(self):
        seed_two_sessions(self.base)
        result = self.build("--scope", "all")
        self.assertIn("Open cloze at C1 is your weakest area "
                      "(about a level below target)", result.stdout)

    def test_malformed_lines_skipped_without_crash(self):
        seed_two_sessions(self.base)
        with open(self.base / "attempts.jsonl", "a", encoding="utf-8") as log:
            log.write("{this is not json}\n")
        result = self.build("--scope", "all")
        self.assertIn("skipped 1 malformed line", result.stderr)
        self.assertIn("4 attempts", result.stdout)

    def test_building_reports_never_modifies_the_log(self):
        seed_two_sessions(self.base)
        log_path = self.base / "attempts.jsonl"
        before = log_path.read_bytes()
        self.build("--scope", "session")
        self.build("--scope", "all")
        self.assertEqual(log_path.read_bytes(), before)

    def test_missing_log_is_a_friendly_no_op(self):
        result = self.build("--scope", "all")
        self.assertIn("nothing to report yet", result.stdout)
        self.assertFalse((self.base / "reports").exists())

    def test_unknown_session_is_a_friendly_no_op(self):
        seed_two_sessions(self.base)
        result = self.build("--scope", "session", "--session", "1999-01-01-am")
        self.assertIn("No attempts found for session", result.stdout)

    def test_no_write_flag_skips_report_file(self):
        seed_two_sessions(self.base)
        self.build("--scope", "all", "--no-write")
        self.assertFalse((self.base / "reports").exists())


if __name__ == "__main__":
    unittest.main()
