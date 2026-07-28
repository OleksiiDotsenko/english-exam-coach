"""Tests for the state-directory contract (state.py).

These lock the promises every other script depends on: append-only logs,
additive-only fields, atomic JSON writes, tolerant reads, and quarantine of
corrupt state. A regression here can silently damage a user's whole history,
so the coverage is deliberately blunt.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import SCRIPTS, log_attempt, run_script

STATE = SCRIPTS / "state.py"

sys.path.insert(0, str(SCRIPTS))
import state  # noqa: E402


class AppendOnlyTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.log = self.base / "attempts.jsonl"

    def tearDown(self):
        self._tmp.cleanup()

    def test_append_never_truncates_existing_records(self):
        for i in range(3):
            state.append_jsonl(self.log, {"n": i})
        rows, skipped = state.read_jsonl(self.log)
        self.assertEqual([r["n"] for r in rows], [0, 1, 2])
        self.assertEqual(skipped, 0)

    def test_append_repairs_a_missing_trailing_newline(self):
        self.log.write_text('{"n": 0}', encoding="utf-8")  # no newline
        state.append_jsonl(self.log, {"n": 1})
        raw = self.log.read_bytes()
        self.assertNotIn(b"}{", raw)
        self.assertNotIn(b"\n\n", raw)
        rows, skipped = state.read_jsonl(self.log)
        self.assertEqual(len(rows), 2)
        self.assertEqual(skipped, 0)

    def test_append_writes_exactly_one_line_per_record(self):
        for i in range(5):
            state.append_jsonl(self.log, {"n": i})
        raw = self.log.read_bytes()
        self.assertEqual(raw.count(b"\n"), 5)
        self.assertTrue(raw.endswith(b"\n"))
        self.assertNotIn(b"\n\n", raw)

    def test_nan_is_refused_rather_than_written(self):
        with self.assertRaises(ValueError):
            state.append_jsonl(self.log, {"score": float("nan")})

    def test_unicode_round_trips_unescaped(self):
        state.append_jsonl(self.log, {"note": "café — naïve"})
        self.assertIn("café — naïve", self.log.read_text(encoding="utf-8"))


class TolerantReadTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_one_corrupt_line_does_not_hide_the_rest(self):
        log = self.base / "errors.jsonl"
        log.write_text('{"a": 1}\n{oops\n{"a": 2}\n', encoding="utf-8")
        rows, skipped = state.read_jsonl(log)
        self.assertEqual(len(rows), 2)
        self.assertEqual(skipped, 1)

    def test_rows_missing_required_keys_are_skipped(self):
        log = self.base / "errors.jsonl"
        log.write_text('{"ts": 1, "kind": "x"}\n{"ts": 2}\n', encoding="utf-8")
        rows, skipped = state.read_jsonl(log, required_keys=("ts", "kind"))
        self.assertEqual(len(rows), 1)
        self.assertEqual(skipped, 1)

    def test_missing_file_reads_as_empty_not_an_error(self):
        rows, skipped = state.read_jsonl(self.base / "nope.jsonl")
        self.assertEqual(rows, [])
        self.assertEqual(skipped, 0)


class JsonStateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_write_json_leaves_no_temp_file_behind(self):
        state.write_json(self.base / "queue.json", {"items": []})
        names = {p.name for p in self.base.iterdir()}
        self.assertEqual(names, {"queue.json"})

    def test_corrupt_state_is_quarantined_and_replaced(self):
        path = self.base / "queue.json"
        path.write_text("{not json", encoding="utf-8")
        data, note = state.read_json(path, default={"items": []},
                                     quarantine_on_error=True)
        self.assertEqual(data, {"items": []})
        self.assertIsNotNone(note, "the user must be told state was quarantined")
        self.assertFalse(path.exists())
        moved = list(self.base.glob("queue.json.corrupt-*"))
        self.assertEqual(len(moved), 1)
        # The damaged bytes are preserved, not deleted.
        self.assertIn("{not json", moved[0].read_text(encoding="utf-8"))

    def test_unknown_keys_survive_a_read_write_cycle(self):
        # Rule 5: an older script must not strip a newer script's fields.
        path = self.base / "queue.json"
        state.write_json(path, {"version": 2, "future_field": {"deep": [1, 2]}})
        data, note = state.read_json(path)
        self.assertIsNone(note)
        state.write_json(path, data)
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["future_field"],
                         {"deep": [1, 2]})

    def test_a_json_array_is_treated_as_corrupt(self):
        path = self.base / "queue.json"
        path.write_text("[1, 2, 3]", encoding="utf-8")
        data, note = state.read_json(path, default={})
        self.assertEqual(data, {})
        self.assertIsNotNone(note)


class LegacyCompatibilityTests(unittest.TestCase):
    """Logs written by earlier versions must keep working forever (rule 2)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_a_v0_1_1_era_log_still_reads_and_reports(self):
        # Exactly the fields the first release wrote — no criteria, no
        # timing_source, no evidence_grade.
        legacy = {"ts": "2026-07-08T09:15:00", "exam": "cefr-c1",
                  "skill": "reading-use-of-english",
                  "task_type": "key-word-transformation", "level": "C1",
                  "score": 7, "max": 10, "seconds": 540,
                  "session": "2026-07-08-am"}
        (self.base / "attempts.jsonl").write_text(
            json.dumps(legacy) + "\n", encoding="utf-8")
        rows, skipped = state.read_jsonl(self.base / "attempts.jsonl")
        self.assertEqual(skipped, 0)
        self.assertEqual(len(rows), 1)
        result = run_script(SCRIPTS / "build_report.py",
                            ["--scope", "all", "--base", self.base, "--no-write"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Key word transformation", result.stdout)

    def test_appending_to_a_legacy_log_keeps_the_old_line_intact(self):
        legacy_line = ('{"ts": "2026-07-08T09:15:00", "exam": "cefr-c1", '
                       '"skill": "reading-use-of-english", "task_type": '
                       '"open-cloze", "level": "C1", "score": 6, "max": 8, '
                       '"seconds": 300, "session": "2026-07-08-am"}')
        (self.base / "attempts.jsonl").write_text(legacy_line + "\n",
                                                  encoding="utf-8")
        result = log_attempt(self.base, **{"task-type": "word-formation",
                                           "score": 7, "max": 8})
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = [l for l in (self.base / "attempts.jsonl")
                 .read_text(encoding="utf-8").splitlines() if l.strip()]
        self.assertEqual(len(lines), 2)
        self.assertEqual(json.loads(lines[0]), json.loads(legacy_line))

    def test_legacy_vocab_box_is_readable_and_not_rewritten(self):
        # vocab-box.json predates the contract and is written by the assistant,
        # not by a script; the contract must tolerate it as-is.
        box = {"boxes": {"1": ["ubiquitous"], "3": ["mitigate"]},
               "last_review": "2026-07-01"}
        path = self.base / "vocab-box.json"
        path.write_text(json.dumps(box), encoding="utf-8")
        before = path.read_bytes()
        data, note = state.read_json(path)
        self.assertIsNone(note)
        self.assertEqual(data["boxes"]["3"], ["mitigate"])
        self.assertEqual(path.read_bytes(), before, "reading must not rewrite")

    def test_describe_lists_legacy_files_without_choking(self):
        (self.base / "plan.md").write_text("# Plan\n- week 1\n", encoding="utf-8")
        (self.base / "vocab-box.json").write_text("{}", encoding="utf-8")
        text = state.describe(self.base)
        self.assertIn("plan.md", text)
        self.assertIn("legacy", text)


class StateCliTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_validate_is_quiet_and_zero_on_a_healthy_directory(self):
        log_attempt(self.base)
        result = run_script(STATE, ["validate", "--base", self.base])
        self.assertEqual(result.returncode, 0)
        self.assertIn("state ok", result.stdout)

    def test_validate_reports_damage_and_exits_one(self):
        log_attempt(self.base)
        with open(self.base / "attempts.jsonl", "a", encoding="utf-8") as handle:
            handle.write("{damaged\n")
        result = run_script(STATE, ["validate", "--base", self.base])
        self.assertEqual(result.returncode, 1)
        self.assertIn("unreadable", result.stderr)

    def test_show_on_a_missing_directory_is_not_an_error(self):
        result = run_script(STATE, ["show", "--base", self.base / "nothing"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("does not exist yet", result.stdout)


if __name__ == "__main__":
    unittest.main()
