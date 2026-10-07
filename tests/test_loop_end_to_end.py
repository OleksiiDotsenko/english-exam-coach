"""End-to-end simulation of the v2.0 learning loop.

Unit tests cover each script; this covers the thing they add up to. It drives a
realistic multi-session history through the real scripts — attempt, criteria,
errors, queue sync, due, re-test, promotion — and asserts the loop closes.

The LLM half of the loop (judging, tagging, generating a fresh item) cannot be
unit-tested; DOGFOOD.md covers that with a human checklist.
"""

import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from helpers import SCRIPTS, run_script

LOG_ATTEMPT = SCRIPTS / "log_attempt.py"
LOG_ERROR = SCRIPTS / "log_error.py"
QUEUE = SCRIPTS / "review_queue.py"
DRILL_CONTEXT = SCRIPTS / "drill_context.py"
BUILD_REPORT = SCRIPTS / "build_report.py"
PROFILE = SCRIPTS / "learner_profile.py"


class LoopEndToEndTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    # -- helpers ---------------------------------------------------------

    def attempt(self, **fields):
        args = ["--base", str(self.base)]
        for key, value in fields.items():
            args += ["--" + key.replace("_", "-"), str(value)]
        result = run_script(LOG_ATTEMPT, args)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def error(self, category, subtype, point, **fields):
        args = ["--base", str(self.base), "--category", category,
                "--subtype", subtype, "--point", point]
        for key, value in fields.items():
            args += ["--" + key.replace("_", "-"), str(value)]
        result = run_script(LOG_ERROR, args)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def queue_cmd(self, *args):
        result = run_script(QUEUE, list(args) + ["--base", str(self.base)])
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def context(self):
        result = run_script(DRILL_CONTEXT, ["--base", str(self.base), "--json"])
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def queue_items(self):
        return json.loads((self.base / "queue.json").read_text(encoding="utf-8"))["items"]

    # -- the loop --------------------------------------------------------

    def test_full_cycle_from_first_attempt_to_promoted_point(self):
        # 1. Cold start: nothing logged, so nothing is invented.
        self.assertEqual(self.context()["action"], "cold-start")

        # 2. A scored writing attempt with the per-criterion judgement.
        self.attempt(exam="ielts-academic", skill="writing-evaluator",
                     task_type="ielts-task2-essay", level="C1",
                     band_estimate="6.0-6.5", cefr_estimate="B2", seconds=2400,
                     criteria="task_response=B2,coherence=B2,lexis=B2,grammar=B1",
                     timing_source="wall-clock", evidence_grade="full", draft=1)

        # 3. Two mistakes worth re-testing.
        self.error("grammar", "article", "zero article with uncountable nouns",
                   skill="writing-evaluator", exam="ielts-academic",
                   task_type="ielts-task2-essay", level="C1")
        self.error("lexis", "collocation", "make vs do collocations",
                   skill="writing-evaluator", exam="ielts-academic")

        # 4. Sync: both points enter the queue, due immediately (box 1).
        self.queue_cmd("sync")
        items = self.queue_items()
        self.assertEqual(len(items), 2)
        self.assertTrue(all(i["box"] == 1 for i in items))

        # 5. The selector now prioritises re-testing over anything else.
        choice = self.context()
        self.assertEqual(choice["action"], "re-test")
        self.assertEqual(len(choice["points"]), 2)
        self.assertIn("re-test", choice["headline"].lower())
        # It must explain itself — a bare instruction is not the product.
        self.assertTrue(choice["reason"].strip())
        self.assertIn("FRESH", choice["instruction"])

        # 6. Re-test one point successfully: it is promoted and scheduled out.
        target = choice["points"][0]["id"]
        self.queue_cmd("review", "--id", target, "--result", "pass")
        promoted = next(i for i in self.queue_items() if i["id"] == target)
        self.assertEqual(promoted["box"], 2)
        self.assertEqual(promoted["due"],
                         (date.today() + timedelta(days=1)).isoformat())
        self.assertEqual(promoted["reviews"], 1)

        # 7. Miss the other point: it resets to box 1 and is due again today.
        other = choice["points"][1]["id"]
        self.queue_cmd("review", "--id", other, "--result", "fail")
        lapsed = next(i for i in self.queue_items() if i["id"] == other)
        self.assertEqual(lapsed["box"], 1)
        self.assertEqual(lapsed["lapses"], 1)
        self.assertEqual(lapsed["due"], date.today().isoformat())

    def test_a_repeated_mistake_is_pulled_back_to_the_front(self):
        self.error("grammar", "verb-form", "past perfect after 'by the time'")
        self.queue_cmd("sync")
        ident = self.queue_items()[0]["id"]
        self.queue_cmd("review", "--id", ident, "--result", "pass")
        self.queue_cmd("review", "--id", ident, "--result", "pass")
        self.assertEqual(self.queue_items()[0]["box"], 3)

        # The same point again, phrased differently: it must not create a
        # second item, and it must come back sooner rather than stay in box 3.
        self.error("grammar", "verb-form", "Past perfect after \"by the time\".")
        self.queue_cmd("sync")
        items = self.queue_items()
        self.assertEqual(len(items), 1, "the same point must not be duplicated")
        self.assertEqual(items[0]["box"], 1)
        self.assertEqual(items[0]["occurrences"], 2)

    def test_criteria_reach_the_report_and_name_the_lowest(self):
        for day in range(1, 5):
            self.attempt(exam="ielts-academic", skill="writing-evaluator",
                         task_type="ielts-task2-essay", level="C1",
                         band_estimate="6.0-6.5", cefr_estimate="B2",
                         seconds=2400, evidence_grade="full",
                         timing_source="wall-clock",
                         criteria="task_response=C1,coherence=B2,lexis=B2,grammar=B1",
                         ts="2026-07-0%dT10:00:00" % day)
        result = run_script(BUILD_REPORT, ["--scope", "all", "--base", self.base,
                                           "--no-write"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("## Criterion detail", result.stdout)
        self.assertIn("Task response", result.stdout)
        self.assertIn("Lowest criterion", result.stdout)
        self.assertIn("grammar", result.stdout)
        # The wording must stay an observation, not a diagnosis.
        self.assertIn("not a diagnosis", result.stdout)
        self.assertIn("**Evidence:**", result.stdout)

    def test_selector_falls_back_through_its_states_in_order(self):
        # Weakest-task state: attempts but no errors.
        self.attempt(exam="cefr-c1", skill="reading-use-of-english",
                     task_type="open-cloze", level="C1", score=3, max=8,
                     seconds=300)
        self.assertEqual(self.context()["action"], "weakest-task")

        # Error-pattern state: a repeated tag, nothing synced to the queue yet.
        self.error("grammar", "preposition", "depend on vs depend of")
        self.error("grammar", "preposition", "interested in vs interested on")
        choice = self.context()
        self.assertEqual(choice["action"], "target-error-type")
        self.assertIn("preposition", choice["headline"])

        # Re-test state wins once the points are queued.
        self.queue_cmd("sync")
        self.assertEqual(self.context()["action"], "re-test")

    def test_the_profile_target_is_quoted_in_the_reason(self):
        run_script(PROFILE, ["set", "--exam", "toefl-ibt", "--target-score",
                             "4.5", "--base", str(self.base)])
        self.attempt(exam="toefl-ibt", skill="reading-use-of-english",
                     task_type="toefl-read-academic", level="B2", score=3,
                     max=10, seconds=300)
        self.assertIn("4.5", self.context()["reason"])

    def test_a_corrupt_queue_never_loses_the_underlying_points(self):
        self.error("discourse", "cohesion", "overusing 'moreover' as a linker")
        self.queue_cmd("sync")
        (self.base / "queue.json").write_text("{ truncated", encoding="utf-8")
        # sync rebuilds from errors.jsonl, which is the durable source.
        result = run_script(QUEUE, ["sync", "--base", str(self.base)])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("unreadable", result.stderr)
        self.assertEqual(len(self.queue_items()), 1)
        self.assertEqual(len(list(self.base.glob("queue.json.corrupt-*"))), 1)

    def test_errors_log_is_append_only_across_many_writes(self):
        for i in range(6):
            self.error("lexis", "spelling", "double consonant before -ing %d" % i)
        raw = (self.base / "errors.jsonl").read_bytes()
        self.assertEqual(raw.count(b"\n"), 6)
        self.assertNotIn(b"\n\n", raw)


if __name__ == "__main__":
    unittest.main()
