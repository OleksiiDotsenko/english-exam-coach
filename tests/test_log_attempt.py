"""Tests for log_attempt.py: append integrity, validation, append-only guarantee."""

import json
import re
import tempfile
import unittest
from pathlib import Path

from helpers import LOG_ATTEMPT, log_attempt, parsed_log, read_log_lines, run_script


class LogAttemptTests(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name) / "coach"
        self.addCleanup(self._tmp.cleanup)

    def test_appends_exactly_one_valid_json_line(self):
        result = log_attempt(self.base, score=7, max=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = parsed_log(self.base)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["exam"], "cefr-c1")
        self.assertEqual(row["skill"], "reading-use-of-english")
        self.assertEqual(row["task_type"], "key-word-transformation")
        self.assertEqual(row["level"], "C1")
        self.assertEqual(row["score"], 7)
        self.assertEqual(row["max"], 10)
        self.assertEqual(row["seconds"], 540)
        self.assertEqual(row["session"], "2026-07-08-am")
        self.assertRegex(row["ts"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

    def test_second_append_preserves_first_line(self):
        log_attempt(self.base, score=7, max=10)
        first = read_log_lines(self.base)[0]
        result = log_attempt(self.base, **{"task-type": "open-cloze",
                                           "score": 5, "max": 8})
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = read_log_lines(self.base)
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], first, "append must never rewrite history")

    def test_integral_numbers_stored_as_ints(self):
        log_attempt(self.base, score=7.0, max=10.0, seconds=540.0)
        line = read_log_lines(self.base)[0]
        self.assertIn('"score": 7,', line + ",")
        self.assertNotIn("7.0", line)

    def test_band_estimate_without_score_is_valid(self):
        result = log_attempt(self.base, **{"exam": "ielts-academic",
                                           "skill": "writing-evaluator",
                                           "task-type": "task-2-essay",
                                           "band-estimate": "6.5-7.0"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(parsed_log(self.base)[0]["band_estimate"], "6.5-7.0")

    def test_missing_score_and_band_rejected_without_touching_log(self):
        result = log_attempt(self.base)  # neither score nor band-estimate
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--score or --band-estimate", result.stderr)
        self.assertEqual(read_log_lines(self.base), [])
        self.assertFalse((self.base / "attempts.jsonl").exists())

    def test_invalid_level_rejected(self):
        result = log_attempt(self.base, level="D1", score=7, max=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--level", result.stderr)
        self.assertEqual(read_log_lines(self.base), [])

    def test_score_above_max_rejected(self):
        result = log_attempt(self.base, score=11, max=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(read_log_lines(self.base), [])

    def test_negative_seconds_rejected(self):
        result = log_attempt(self.base, score=7, max=10, seconds=-5)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(read_log_lines(self.base), [])

    def test_invalid_ts_rejected(self):
        result = log_attempt(self.base, score=7, max=10, ts="yesterday")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(read_log_lines(self.base), [])

    def test_failed_validation_never_truncates_existing_log(self):
        log_attempt(self.base, score=7, max=10)
        before = read_log_lines(self.base)
        log_attempt(self.base, level="ZZ", score=7, max=10)
        self.assertEqual(read_log_lines(self.base), before)

    def test_env_var_sets_base_path(self):
        env_base = Path(self._tmp.name) / "via-env"
        result = run_script(
            LOG_ATTEMPT,
            ["--exam", "cefr-b2", "--skill", "reading-use-of-english",
             "--task-type", "open-cloze", "--level", "B2",
             "--score", "6", "--max", "8", "--seconds", "300",
             "--session", "2026-07-08-am"],
            env_overrides={"EXAM_COACH_HOME": str(env_base)},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((env_base / "attempts.jsonl").exists())

    def test_session_defaults_to_date_am_pm(self):
        result = log_attempt(self.base, score=7, max=10, session=None)
        self.assertEqual(result.returncode, 0, result.stderr)
        session = parsed_log(self.base)[0]["session"]
        self.assertRegex(session, r"^\d{4}-\d{2}-\d{2}-(am|pm)$")

    def test_level_and_cefr_estimate_uppercased(self):
        log_attempt(self.base, level="c1", score=7, max=10,
                    **{"cefr-estimate": "b2"})
        row = parsed_log(self.base)[0]
        self.assertEqual(row["level"], "C1")
        self.assertEqual(row["cefr_estimate"], "B2")

    def test_nan_score_rejected_without_touching_log(self):
        result = log_attempt(self.base, score="nan", max=10)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("finite", result.stderr)
        self.assertEqual(read_log_lines(self.base), [])

    def test_infinite_seconds_rejected(self):
        result = log_attempt(self.base, score=7, max=10, seconds="inf")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("finite", result.stderr)
        self.assertEqual(read_log_lines(self.base), [])

    def test_blank_session_rejected(self):
        result = log_attempt(self.base, score=7, max=10, session="   ")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--session", result.stderr)
        self.assertEqual(read_log_lines(self.base), [])

    def test_whitespace_band_estimate_is_not_a_result(self):
        result = log_attempt(self.base, **{"band-estimate": "   ", "score": None})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--score or --band-estimate", result.stderr)
        self.assertEqual(read_log_lines(self.base), [])

    def test_max_without_score_rejected(self):
        result = log_attempt(self.base, max=10,
                             **{"band-estimate": "4-5", "score": None})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--max is only meaningful together with --score",
                      result.stderr)
        self.assertEqual(read_log_lines(self.base), [])

    def test_invalid_cefr_estimate_rejected(self):
        result = log_attempt(self.base, score=7, max=10,
                             **{"cefr-estimate": "Z9"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--cefr-estimate", result.stderr)
        self.assertEqual(read_log_lines(self.base), [])

    def test_a2_level_is_accepted(self):
        result = log_attempt(self.base, level="A2", score=5, max=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(parsed_log(self.base)[0]["level"], "A2")

    def test_unicode_fields_round_trip_unescaped(self):
        result = log_attempt(self.base, score=7, max=8,
                             **{"task-type": "résumé-übung", "session": "séance-1"})
        self.assertEqual(result.returncode, 0, result.stderr)
        line = read_log_lines(self.base)[0]
        self.assertIn("résumé-übung", line)  # ensure_ascii=False keeps UTF-8
        self.assertEqual(parsed_log(self.base)[0]["session"], "séance-1")

    def test_ts_without_session_derives_session_from_ts_not_now(self):
        # A back-dated attempt must land in the session of its own timestamp.
        result = log_attempt(self.base, score=7, max=10, session=None,
                             ts="2025-03-04T15:00:00")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(parsed_log(self.base)[0]["session"], "2025-03-04-pm")


if __name__ == "__main__":
    unittest.main()
