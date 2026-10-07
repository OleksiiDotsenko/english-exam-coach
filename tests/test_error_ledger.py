"""Tests for log_error.py: the closed taxonomy, single and batch logging.

A reviewed full test yields dozens of mistakes at once, so the batch path is
the one a tutor actually uses — and in an append-only log a half-imported
batch can only be untangled by hand. The all-or-nothing rule is the point.
"""

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import DATA, SCRIPTS, coach, run_script

sys.path.insert(0, str(SCRIPTS))
import log_error  # noqa: E402

LOG_ERROR = SCRIPTS / "log_error.py"


def rows_of(base):
    path = Path(base) / "errors.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


class TaxonomyTests(unittest.TestCase):
    def test_every_subtype_has_a_definition(self):
        for category, subtypes in log_error.TAXONOMY.items():
            self.assertTrue(subtypes, category)
            for subtype, meaning in subtypes.items():
                self.assertRegex(subtype, r"^[a-z][a-z-]*$")
                self.assertGreater(len(meaning), 10, "%s/%s" % (category, subtype))

    def test_the_tags_real_reviews_needed_are_present(self):
        # Added in v3.0 from a catalog of several hundred real mistakes: each
        # of these was a recurring group that had no honest tag before.
        for category, subtype in (("comprehension", "purpose"),
                                  ("comprehension", "negation"),
                                  ("comprehension", "main-idea"),
                                  ("comprehension", "structure"),
                                  ("comprehension", "vocabulary"),
                                  ("lexis", "non-word"), ("lexis", "redundancy"),
                                  ("grammar", "pronoun"), ("grammar", "omission"),
                                  ("delivery", "repetition")):
            self.assertIn(subtype, log_error.TAXONOMY[category])

    def test_no_tag_was_removed_or_renamed(self):
        # Fields are additive-only: an old log must keep validating.
        for category, subtype in (("grammar", "verb-form"), ("grammar", "article"),
                                  ("lexis", "collocation"), ("discourse", "cohesion"),
                                  ("task", "task-response"), ("comprehension", "distractor"),
                                  ("delivery", "fluency"), ("vocabulary", "recall"),
                                  ("strategy", "timing")):
            self.assertIn(subtype, log_error.TAXONOMY[category])

    def test_the_printed_taxonomy_lists_every_tag(self):
        result = run_script(LOG_ERROR, ["--list-taxonomy"])
        self.assertEqual(result.returncode, 0)
        for category, subtypes in log_error.TAXONOMY.items():
            self.assertIn(category, result.stdout)
            for subtype in subtypes:
                self.assertIn(subtype, result.stdout)

    def test_the_reference_table_matches_the_code(self):
        # The assistant tags from the reference file; the script validates
        # against the code. They must never disagree, in either direction.
        text = (DATA / "error-taxonomy.md").read_text(encoding="utf-8")
        documented = dict(re.findall(r"^\| `([a-z-]+/[a-z-]+)` \| (.+?) \|$", text,
                                     flags=re.MULTILINE))
        in_code = {"%s/%s" % (category, subtype): meaning
                   for category, subtypes in log_error.TAXONOMY.items()
                   for subtype, meaning in subtypes.items()}
        self.assertEqual(documented, in_code)


class SingleErrorTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def log(self, *args):
        return coach(self.base, "log-error", *args)

    def test_a_valid_error_is_written_with_normalised_fields(self):
        result = self.log("--category", "Grammar", "--subtype", "ARTICLE",
                          "--point", "  a before a job  ", "--level", "b2",
                          "--evidence", "she is doctor", "--fix", "she is a doctor",
                          "--transfer", "no articles in the first language",
                          "--task-type", "toefl-write-email", "--item", "3")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("noted: grammar/article — a before a job", result.stdout)
        row = rows_of(self.base)[0]
        self.assertEqual((row["category"], row["subtype"], row["point"]),
                         ("grammar", "article", "a before a job"))
        self.assertEqual(row["level"], "B2")
        self.assertEqual(row["item"], 3)
        self.assertEqual(row["transfer"], "no articles in the first language")
        self.assertRegex(row["session"], r"^\d{4}-\d{2}-\d{2}-(am|pm)$")

    def test_unknown_category_and_subtype_are_refused(self):
        for args in (["--category", "syntax", "--subtype", "article"],
                     ["--category", "grammar", "--subtype", "articles"]):
            result = self.log(*args, "--point", "something specific")
            self.assertEqual(result.returncode, 2)
            self.assertIn("must be one of", result.stderr)
        self.assertEqual(rows_of(self.base), [])

    def test_a_point_is_required_and_must_be_specific(self):
        for point in ("", "ab"):
            result = self.log("--category", "grammar", "--subtype", "article",
                              "--point", point)
            self.assertEqual(result.returncode, 2)
        result = self.log("--category", "grammar", "--subtype", "article")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(rows_of(self.base), [])

    def test_bad_level_and_timestamp_are_refused(self):
        result = self.log("--category", "grammar", "--subtype", "article",
                          "--point", "a before a job", "--level", "B3")
        self.assertEqual(result.returncode, 2)
        result = self.log("--category", "grammar", "--subtype", "article",
                          "--point", "a before a job", "--ts", "yesterday")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(rows_of(self.base), [])

    def test_an_explicit_timestamp_sets_the_default_session(self):
        self.log("--category", "lexis", "--subtype", "spelling",
                 "--point", "truly, one l", "--ts", "2026-03-04T15:30:00")
        row = rows_of(self.base)[0]
        self.assertEqual(row["ts"], "2026-03-04T15:30:00")
        self.assertEqual(row["session"], "2026-03-04-pm")


class BatchTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name) / "progress"
        self.file = Path(self._tmp.name) / "batch.jsonl"

    def tearDown(self):
        self._tmp.cleanup()

    GOOD = [
        {"category": "grammar", "subtype": "article",
         "point": "a before a singular count noun",
         "evidence": "I am student", "fix": "I am a student"},
        {"category": "lexis", "subtype": "spelling", "point": "truly, one l",
         "evidence": "trully", "fix": "truly"},
        {"category": "grammar", "subtype": "pronoun",
         "point": "no reflexive after concentrate",
         "evidence": "concentrate myself", "fix": "concentrate",
         "transfer": "the verb is reflexive in the first language"},
    ]

    def write(self, rows, as_array=False):
        if as_array:
            self.file.write_text(json.dumps(rows), encoding="utf-8")
        else:
            self.file.write_text("\n".join(json.dumps(r) for r in rows) + "\n",
                                 encoding="utf-8")

    def batch(self, *args):
        return coach(self.base, "log-error", "--batch", self.file, *args)

    def test_json_lines_batch_with_command_line_defaults(self):
        self.write(self.GOOD)
        result = self.batch("--session", "test-alpha-20260701", "--exam",
                            "toefl-ibt", "--level", "B2")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("noted 3 mistakes (2 grammar, 1 lexis)", result.stdout)
        rows = rows_of(self.base)
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(r["session"] == "test-alpha-20260701" for r in rows))
        self.assertTrue(all(r["exam"] == "toefl-ibt" and r["level"] == "B2"
                            for r in rows))
        self.assertEqual(rows[2]["transfer"],
                         "the verb is reflexive in the first language")

    def test_json_array_batch(self):
        self.write(self.GOOD, as_array=True)
        self.assertEqual(self.batch().returncode, 0)
        self.assertEqual(len(rows_of(self.base)), 3)

    def test_a_row_value_beats_the_command_line_default(self):
        rows = [dict(self.GOOD[0], session="test-bravo-20260708"), self.GOOD[1]]
        self.write(rows)
        self.batch("--session", "test-alpha-20260701")
        written = rows_of(self.base)
        self.assertEqual(written[0]["session"], "test-bravo-20260708")
        self.assertEqual(written[1]["session"], "test-alpha-20260701")

    def test_one_bad_row_means_nothing_is_written(self):
        rows = list(self.GOOD) + [{"category": "grammar", "subtype": "nonsense",
                                   "point": "whatever this is"}]
        self.write(rows)
        result = self.batch()
        self.assertEqual(result.returncode, 2)
        self.assertIn("row 4", result.stderr)
        self.assertIn("Nothing was written", result.stderr)
        self.assertEqual(rows_of(self.base), [])

    def test_every_bad_row_is_reported_at_once(self):
        self.write([{"category": "x", "subtype": "y", "point": "long enough"},
                    {"category": "grammar", "subtype": "article"}])
        result = self.batch()
        self.assertIn("row 1", result.stderr)
        self.assertIn("row 2", result.stderr)

    def test_malformed_and_empty_batches_are_errors_not_crashes(self):
        self.file.write_text('{"category": "grammar"\n', encoding="utf-8")
        result = self.batch()
        self.assertEqual(result.returncode, 2)
        self.assertIn("line 1", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

        self.file.write_text("\n\n", encoding="utf-8")
        result = self.batch()
        self.assertEqual(result.returncode, 2)
        self.assertIn("empty", result.stderr)

        self.file.write_text('["just a string"]', encoding="utf-8")
        self.assertEqual(self.batch().returncode, 2)

        result = coach(self.base, "log-error", "--batch", self.file.with_name("missing.jsonl"))
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(rows_of(self.base), [])

    def test_blank_lines_in_a_batch_are_ignored(self):
        self.file.write_text("\n" + json.dumps(self.GOOD[0]) + "\n\n"
                             + json.dumps(self.GOOD[1]) + "\n", encoding="utf-8")
        self.assertEqual(self.batch().returncode, 0)
        self.assertEqual(len(rows_of(self.base)), 2)

    def test_unknown_keys_in_a_row_do_not_break_the_import(self):
        self.write([dict(self.GOOD[0], colour="blue")])
        self.assertEqual(self.batch().returncode, 0)
        self.assertNotIn("colour", rows_of(self.base)[0])

    def test_batch_appends_and_never_rewrites(self):
        self.write(self.GOOD[:1])
        self.batch()
        before = (self.base / "errors.jsonl").read_bytes()
        self.write(self.GOOD[1:])
        self.batch()
        after = (self.base / "errors.jsonl").read_bytes()
        self.assertTrue(after.startswith(before))
        self.assertEqual(len(rows_of(self.base)), 3)


if __name__ == "__main__":
    unittest.main()


class CorrectionTests(unittest.TestCase):
    """The log is append-only, so a wrong entry is corrected by a newer line."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name) / "progress"
        for point, evidence in (("a before a job", "she is doctor"),
                                ("a before a job", "he is engineer"),
                                ("truly, one l", "trully")):
            subtype = "spelling" if "truly" in point else "article"
            category = "lexis" if "truly" in point else "grammar"
            result = coach(self.base, "log-error", "--category", category,
                           "--subtype", subtype, "--point", point,
                           "--evidence", evidence, "--session", "test-alpha-20260701")
            self.assertEqual(result.returncode, 0, result.stderr)

    def tearDown(self):
        self._tmp.cleanup()

    def active(self):
        sys.path.insert(0, str(SCRIPTS))
        import state
        return state.read_errors(self.base)[0]

    def ident(self, evidence):
        return [r["id"] for r in self.active() if r.get("evidence") == evidence][0]

    def test_every_mistake_gets_an_id_and_says_so(self):
        result = coach(self.base, "log-error", "--category", "grammar", "--subtype",
                       "pronoun", "--point", "no reflexive after concentrate")
        self.assertRegex(result.stdout, r"\(id e-[0-9a-f]{8}\)")
        ids = [r["id"] for r in self.active()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_void_withdraws_a_mistake_without_rewriting_the_log(self):
        before = (self.base / "errors.jsonl").read_bytes()
        result = coach(self.base, "log-error", "--void", self.ident("he is engineer"),
                       "--reason", "this one was a typo, not a habit")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("withdrawn 1 mistake", result.stdout)
        after = (self.base / "errors.jsonl").read_bytes()
        self.assertTrue(after.startswith(before))          # appended, not edited
        self.assertEqual(sorted(r["evidence"] for r in self.active()),
                         ["she is doctor", "trully"])
        marker = rows_of(self.base)[-1]
        self.assertEqual(marker["reason"], "this one was a typo, not a habit")

    def test_an_unknown_id_writes_nothing(self):
        before = (self.base / "errors.jsonl").read_bytes()
        result = coach(self.base, "log-error", "--void", "e-00000000", "--void",
                       self.ident("trully"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("e-00000000", result.stderr)
        self.assertEqual((self.base / "errors.jsonl").read_bytes(), before)

    def test_amend_replaces_only_the_fields_given(self):
        old = self.ident("she is doctor")
        result = coach(self.base, "log-error", "--amend", old, "--point",
                       "a/an before a profession")
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = self.active()
        self.assertEqual(len(rows), 3)
        new = [r for r in rows if r.get("amends") == old][0]
        self.assertEqual(new["point"], "a/an before a profession")
        self.assertEqual(new["evidence"], "she is doctor")           # kept
        self.assertEqual(new["session"], "test-alpha-20260701")      # kept
        self.assertEqual(new["subtype"], "article")                  # kept
        self.assertNotIn(old, [r["id"] for r in rows])

    def test_an_invalid_amendment_changes_nothing(self):
        before = (self.base / "errors.jsonl").read_bytes()
        result = coach(self.base, "log-error", "--amend", self.ident("trully"),
                       "--subtype", "no-such-subtype")
        self.assertEqual(result.returncode, 2)
        self.assertEqual((self.base / "errors.jsonl").read_bytes(), before)

    def test_corrections_and_batches_do_not_mix(self):
        result = coach(self.base, "log-error", "--void", self.ident("trully"),
                       "--batch", "whatever.jsonl")
        self.assertEqual(result.returncode, 2)

    def test_a_row_written_before_ids_existed_can_still_be_corrected(self):
        with open(self.base / "errors.jsonl", "a", encoding="utf-8") as handle:
            handle.write(json.dumps({"ts": "2026-05-01T10:00:00", "category": "lexis",
                                     "subtype": "collocation", "point": "make vs do",
                                     "evidence": "did a mistake"}) + "\n")
        old = self.ident("did a mistake")
        self.assertRegex(old, r"^e-[0-9a-f]{8}$")
        self.assertEqual(old, self.ident("did a mistake"))         # stable
        self.assertEqual(coach(self.base, "log-error", "--void", old).returncode, 0)
        self.assertNotIn("did a mistake", [r.get("evidence") for r in self.active()])

    def test_the_queue_follows_a_correction(self):
        self.assertEqual(coach(self.base, "queue", "sync").returncode, 0)
        queue = json.loads((self.base / "queue.json").read_text(encoding="utf-8"))
        article = [i for i in queue["items"] if i["subtype"] == "article"][0]
        self.assertEqual(article["occurrences"], 2)
        coach(self.base, "log-error", "--void", self.ident("he is engineer"))
        coach(self.base, "log-error", "--void", self.ident("trully"))
        result = coach(self.base, "queue", "sync")
        self.assertEqual(result.returncode, 0, result.stderr)
        queue = json.loads((self.base / "queue.json").read_text(encoding="utf-8"))
        self.assertEqual([(i["subtype"], i["occurrences"]) for i in queue["items"]],
                         [("article", 1)])          # the spelling point is gone

    def test_the_catalog_counts_only_what_stands_and_can_show_ids(self):
        coach(self.base, "log-error", "--void", self.ident("he is engineer"))
        result = coach(self.base, "catalog", "--full", "--ids", "--no-write")
        self.assertIn("**2 mistakes · 2 distinct points**", result.stdout)
        self.assertNotIn("he is engineer", result.stdout)
        self.assertRegex(result.stdout, r"- she is doctor `e-[0-9a-f]{8}`")
        plain = coach(self.base, "catalog", "--full", "--no-write")
        self.assertNotIn("`e-", plain.stdout)

    def test_the_directory_still_validates_after_corrections(self):
        coach(self.base, "log-error", "--void", self.ident("trully"))
        result = coach(self.base, "state", "validate")
        self.assertEqual(result.returncode, 0, result.stderr)
        shown = coach(self.base, "state", "show")
        self.assertIn("4 records, 1 of them correction", shown.stdout)


class NonLatinPointTests(unittest.TestCase):
    """A tutor may name points in their own language. They must still group
    as separate points — an ASCII-only key once merged them all into one."""

    def test_points_in_another_alphabet_stay_apart(self):
        sys.path.insert(0, str(SCRIPTS))
        import review_queue
        first = review_queue.normalize_point("Артикль перед злічуваним іменником!")
        second = review_queue.normalize_point("артикль  перед злічуваним іменником")
        other = review_queue.normalize_point("узгодження підмета і присудка")
        self.assertEqual(first, second)
        self.assertNotEqual(first, other)
        self.assertNotEqual(review_queue.item_id("grammar", "article", first),
                            review_queue.item_id("grammar", "article", other))
        self.assertTrue(first)

    def test_latin_points_group_exactly_as_before(self):
        sys.path.insert(0, str(SCRIPTS))
        import review_queue
        self.assertEqual(review_queue.normalize_point('Past perfect after "by the time".'),
                         "past perfect after by the time")
        self.assertEqual(review_queue.normalize_point("make_vs_do"), "make vs do")

    def test_the_catalog_keeps_them_apart(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for point in ("артикль перед іменником", "узгодження підмета і присудка",
                          "Артикль перед іменником"):
                coach(base, "log-error", "--category", "grammar", "--subtype",
                      "article", "--point", point)
            result = coach(base, "catalog", "--no-write")
            self.assertIn("**3 mistakes · 2 distinct points**", result.stdout)
            self.assertEqual(coach(base, "queue", "sync").returncode, 0)
            queue = json.loads((base / "queue.json").read_text(encoding="utf-8"))
            self.assertEqual(sorted(i["occurrences"] for i in queue["items"]), [1, 2])
