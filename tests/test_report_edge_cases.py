"""Edge-case and regression tests for build_report.py.

Covers the crashes and mis-rankings found in the July 2026 quality audit
plus the report branches that previously had no coverage.
"""

import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from helpers import BUILD_REPORT, log_attempt, run_script


class ReportEdgeCaseTests(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name) / "coach"
        self.addCleanup(self._tmp.cleanup)

    def build(self, *args):
        result = run_script(BUILD_REPORT, ["--base", str(self.base)] + list(args))
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def append_raw(self, line):
        path = self.base / "attempts.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as log:
            log.write(line + "\n")

    # --- crash regressions -------------------------------------------------

    def test_mixed_tz_aware_and_naive_timestamps_do_not_crash(self):
        log_attempt(self.base, score=5, max=6, seconds=300,
                    ts="2026-07-10T10:00:00Z", session="2026-07-10-am")
        log_attempt(self.base, score=4, max=6, seconds=300,
                    ts="2026-07-10T11:00:00", session="2026-07-10-am")
        result = self.build("--scope", "all")
        self.assertIn("2 attempts", result.stdout)

    def test_non_numeric_seconds_in_valid_json_does_not_crash(self):
        log_attempt(self.base, score=7, max=10, seconds=300,
                    ts="2026-07-09T09:00:00", session="s1")
        self.append_raw('{"ts":"2026-07-09T09:30:00","exam":"cefr-c1",'
                        '"skill":"reading-use-of-english","task_type":"open-cloze",'
                        '"level":"C1","score":7,"max":10,'
                        '"seconds":"about 5 minutes","session":"s1"}')
        result = self.build("--scope", "all")
        self.assertIn("2 attempts", result.stdout)

    def test_wrong_shape_json_lines_are_skipped(self):
        log_attempt(self.base, score=7, max=10, seconds=300,
                    ts="2026-07-09T09:00:00", session="s1")
        for junk in ('[1, 2, 3]', '"just a string"', '42', '{"exam": "x"}'):
            self.append_raw(junk)
        result = self.build("--scope", "all")
        self.assertIn("skipped 4 malformed line", result.stderr)
        self.assertIn("1 attempt ", result.stdout)

    def test_rows_missing_core_fields_are_skipped_not_rendered_as_none(self):
        log_attempt(self.base, score=7, max=10, seconds=300,
                    ts="2026-07-09T09:00:00", session="s1")
        # valid JSON, has ts+session, but no exam/skill/task_type
        self.append_raw('{"ts":"2026-07-09T10:00:00","session":"s1","score":5}')
        result = self.build("--scope", "all")
        self.assertIn("skipped 1 malformed line", result.stderr)
        self.assertNotIn("| None |", result.stdout)

    # --- CEFR normalization correctness -----------------------------------

    def test_ielts_raw_count_without_max_is_not_read_as_band(self):
        # 25 logged with no --max must not be treated as a band and inflate to C2.
        log_attempt(self.base, **{"exam": "ielts-academic",
                                  "skill": "listening-trainer",
                                  "task-type": "ielts-listening-part1",
                                  "level": "B2", "score": 25, "seconds": 600,
                                  "ts": "2026-07-08T09:00:00", "session": "s1"})
        result = self.build("--scope", "session", "--session", "s1")
        self.assertNotIn("C2", result.stdout)

    def test_ielts_raw_score_out_of_9_is_treated_as_band(self):
        log_attempt(self.base, **{"exam": "ielts-academic", "skill": "speaking-coach",
                                  "task-type": "ielts-part2-long-turn", "level": "B2",
                                  "score": 6.5, "max": 9, "seconds": 120,
                                  "ts": "2026-07-08T09:00:00", "session": "s1"})
        result = self.build("--scope", "session", "--session", "s1")
        self.assertIn("~B2 (speaking)", result.stdout)

    def test_toefl_band_and_legacy_scales_apply_only_to_holistic_skills(self):
        # A holistic (speaking) TOEFL band 6 -> new 1-6 scale -> C2.
        log_attempt(self.base, **{"exam": "toefl-ibt", "skill": "speaking-coach",
                                  "task-type": "toefl-take-an-interview", "level": "C1",
                                  "score": 6, "max": 6, "seconds": 300,
                                  "ts": "2026-07-08T09:00:00", "session": "band"})
        band = self.build("--scope", "session", "--session", "band")
        self.assertIn("~C2 (speaking)", band.stdout)
        # A holistic (speaking) legacy 24/30 section score -> legacy cut -> B2.
        log_attempt(self.base, **{"exam": "toefl-ibt", "skill": "speaking-coach",
                                  "task-type": "toefl-take-an-interview", "level": "C1",
                                  "score": 24, "seconds": 300,
                                  "ts": "2026-07-08T10:00:00", "session": "legacy"})
        legacy = self.build("--scope", "session", "--session", "legacy")
        self.assertIn("~B2 (speaking)", legacy.stdout)

    def test_objective_item_count_of_6_is_not_misread_as_a_toefl_band(self):
        # THE CRITICAL FIX: a 6-item reading drill scored 5 must read as 83%
        # at its B2 anchor (-> B2), NOT as TOEFL band 5 (-> C1).
        log_attempt(self.base, **{"exam": "toefl-ibt", "skill": "reading-use-of-english",
                                  "task-type": "toefl-read-academic", "level": "B2",
                                  "score": 5, "max": 6, "seconds": 300,
                                  "ts": "2026-07-08T09:00:00", "session": "s1"})
        result = self.build("--scope", "session", "--session", "s1")
        self.assertIn("~B2 (reading)", result.stdout)
        self.assertNotIn("C1", result.stdout)

    def test_objective_item_count_of_9_is_not_misread_as_an_ielts_band(self):
        # A 9-item IELTS reading drill scored 8 -> 89% at C1 -> C1, not band 8.
        log_attempt(self.base, **{"exam": "ielts-academic", "skill": "reading-use-of-english",
                                  "task-type": "ielts-tf-not-given", "level": "C1",
                                  "score": 8, "max": 9, "seconds": 300,
                                  "ts": "2026-07-08T09:00:00", "session": "s1"})
        result = self.build("--scope", "session", "--session", "s1")
        self.assertIn("~C1 (reading)", result.stdout)

    def test_total_failure_is_distinguished_from_a_near_miss(self):
        log_attempt(self.base, **{"exam": "cefr-c1", "skill": "reading-use-of-english",
                                  "task-type": "open-cloze", "level": "C1",
                                  "score": 0, "max": 10, "seconds": 300,
                                  "ts": "2026-07-08T09:00:00", "session": "zero"})
        zero = self.build("--scope", "session", "--session", "zero")
        log_attempt(self.base, **{"exam": "cefr-c1", "skill": "reading-use-of-english",
                                  "task-type": "open-cloze", "level": "C1",
                                  "score": 5, "max": 10, "seconds": 300,
                                  "ts": "2026-07-08T10:00:00", "session": "half"})
        half = self.build("--scope", "session", "--session", "half")
        # 0/10 lands below B2; 5/10 lands at ~B2 — they must not be identical.
        self.assertNotEqual(
            [l for l in zero.stdout.splitlines() if "Estimated level" in l],
            [l for l in half.stdout.splitlines() if "Estimated level" in l])

    def test_a1_near_total_failure_is_not_reported_at_level(self):
        # At the A1 floor the CEFR value can't drop, but a 1/10 must not read
        # as "at or above your target level" — quality is capped by the raw %.
        log_attempt(self.base, **{"exam": "toefl-ibt", "skill": "reading-use-of-english",
                                  "task-type": "toefl-read-daily-life", "level": "A1",
                                  "score": 1, "max": 10, "seconds": 200,
                                  "ts": "2026-07-08T09:00:00", "session": "s1"})
        result = self.build("--scope", "all")
        self.assertNotIn("at or above your target level", result.stdout)

    def test_low_score_stays_on_the_cefr_scale(self):
        # An A2-anchored task scored poorly must not render as "~?".
        log_attempt(self.base, **{"exam": "toefl-ibt", "skill": "reading-use-of-english",
                                  "task-type": "toefl-read-daily-life", "level": "A2",
                                  "score": 1, "max": 10, "seconds": 200,
                                  "ts": "2026-07-08T09:00:00", "session": "s1"})
        result = self.build("--scope", "session", "--session", "s1")
        self.assertNotIn("~? (reading)", result.stdout)

    def test_en_dash_band_estimate_still_normalizes(self):
        log_attempt(self.base, **{"exam": "ielts-academic", "skill": "writing-evaluator",
                                  "task-type": "ielts-task2-essay", "level": "C1",
                                  "band-estimate": "6.5–7.0", "seconds": 1800,
                                  "ts": "2026-07-08T09:00:00", "session": "s1"})
        result = self.build("--scope", "session", "--session", "s1")
        self.assertIn("(writing)", result.stdout)
        self.assertNotIn("~? (writing)", result.stdout)

    # --- ranking on one axis (finding 9) ----------------------------------

    def test_band_scored_task_at_level_is_not_flagged_weak(self):
        # An IELTS essay at band 7.0 logged at its C1 target is AT level, and
        # an 80% B1 cloze is at its B1 target: both count as at-level, so the
        # report must not single the essay out as the weak area (old bug:
        # band/9 = 0.78 < 0.8 made every band-7 task look weak).
        log_attempt(self.base, **{"exam": "ielts-academic", "skill": "writing-evaluator",
                                  "task-type": "ielts-task2-essay", "level": "C1",
                                  "band-estimate": "7.0-7.0", "seconds": 1800,
                                  "ts": "2026-07-08T09:00:00", "session": "s1"})
        log_attempt(self.base, **{"exam": "cefr-b1", "skill": "reading-use-of-english",
                                  "task-type": "open-cloze", "level": "B1",
                                  "score": 8, "max": 10, "seconds": 300,
                                  "ts": "2026-07-08T09:30:00", "session": "s1"})
        result = self.build("--scope", "all")
        self.assertIn("at their target level", result.stdout)

    # --- streak (findings 12 & 18) ----------------------------------------

    def _log_day(self, day, session_suffix="am"):
        log_attempt(self.base, score=7, max=8, seconds=300,
                    ts="%sT09:00:00" % day, session="%s-%s" % (day, session_suffix))

    def test_stale_run_is_labelled_last_not_current(self):
        self._log_day("2025-03-01")
        self._log_day("2025-03-02")
        result = self.build("--scope", "all")
        self.assertIn("last streak: 2 days", result.stdout)
        self.assertNotIn("current streak", result.stdout)

    def test_active_consecutive_days_extend_current_streak(self):
        today = date.today()
        for delta in (2, 1, 0):
            self._log_day((today - timedelta(days=delta)).isoformat())
        result = self.build("--scope", "all")
        self.assertIn("current streak: 3 days", result.stdout)

    def test_streak_breaks_on_a_gap(self):
        today = date.today()
        for delta in (5, 1, 0):  # a gap between day-5 and day-1
            self._log_day((today - timedelta(days=delta)).isoformat())
        result = self.build("--scope", "all")
        self.assertIn("current streak: 2 days", result.stdout)

    # --- display polish (findings 14 & 16) --------------------------------

    def test_singular_counts_read_naturally(self):
        log_attempt(self.base, score=7, max=8, seconds=300,
                    ts="2026-07-08T09:00:00", session="2026-07-08-am")
        result = self.build("--scope", "all")
        self.assertIn("1 attempt · 1 session · 1 day practised", result.stdout)

    def test_fmt_time_rounds_before_choosing_unit(self):
        log_attempt(self.base, score=7, max=8, seconds=59.6,
                    ts="2026-07-08T09:00:00", session="s1")
        result = self.build("--scope", "session", "--session", "s1")
        self.assertIn("| 1m |", result.stdout)
        self.assertNotIn("| 60s |", result.stdout)

    # --- previously-uncovered report branches -----------------------------

    def test_legacy_exam_ids_render_as_cefr_names(self):
        log_attempt(self.base, **{"exam": "c1-advanced", "score": 7, "max": 8,
                                  "seconds": 300, "ts": "2026-07-08T09:00:00",
                                  "session": "s1"})
        result = self.build("--scope", "session", "--session", "s1")
        self.assertIn("| CEFR C1 |", result.stdout)

    def test_frontmatter_exams_are_sorted_raw_ids(self):
        log_attempt(self.base, **{"exam": "toefl-ibt", "score": 5, "max": 6,
                                  "seconds": 300, "ts": "2026-07-08T09:00:00",
                                  "session": "s1"})
        log_attempt(self.base, **{"exam": "cefr-b2", "score": 5, "max": 6,
                                  "seconds": 300, "ts": "2026-07-08T09:10:00",
                                  "session": "s1"})
        result = self.build("--scope", "session", "--session", "s1")
        self.assertIn("exams: [cefr-b2, toefl-ibt]", result.stdout)

    def test_all_strong_recommendation_branch(self):
        log_attempt(self.base, **{"exam": "cefr-c1", "task-type": "open-cloze",
                                  "level": "C1", "score": 10, "max": 10,
                                  "seconds": 300, "ts": "2026-07-08T09:00:00",
                                  "session": "s1"})
        result = self.build("--scope", "all")
        self.assertIn("All task types are at their target level", result.stdout)

    def test_empty_ranking_recommendation_branch(self):
        # A band-only, non-IELTS/TOEFL attempt with no CEFR estimate yields no
        # computable quality, so ranking is empty and the report says so.
        log_attempt(self.base, **{"exam": "cefr-c1", "skill": "writing-evaluator",
                                  "task-type": "essay", "level": "C1",
                                  "band-estimate": "pass", "score": None,
                                  "seconds": 300, "ts": "2026-07-08T09:00:00",
                                  "session": "s1"})
        result = self.build("--scope", "all")
        self.assertIn("Log a few scored attempts", result.stdout)

    # --- audit-fix regressions: objective task types under holistic skills --

    def test_build_a_sentence_is_objective_even_under_a_holistic_skill(self):
        # A 5/6 build-a-sentence at a B1 anchor is an item count: 83% at
        # level -> ~B1. It must NOT be read as TOEFL band 5 -> C1 just
        # because writing-evaluator is a holistic skill.
        log_attempt(self.base, **{"exam": "toefl-ibt", "skill": "writing-evaluator",
                                  "task-type": "toefl-build-a-sentence", "level": "B1",
                                  "score": 5, "max": 6, "seconds": 300,
                                  "ts": "2026-07-08T09:00:00", "session": "s1"})
        result = self.build("--scope", "session", "--session", "s1")
        self.assertIn("~B1 (writing)", result.stdout)
        self.assertNotIn("C1", result.stdout)

    # --- audit-fix regressions: skill trend ordering and rounding ----------

    def test_identical_rounded_trend_labels_read_steady(self):
        # First-half mean 4.83, second-half mean 5.0: both display as C1, so
        # the arrow must come from the same rounded values and read 'steady'.
        # 'C1 -> C1 (improving)' would be a self-contradictory line.
        scores = (8, 8, 7, 8, 8, 8)  # at C1: 5.0 5.0 4.5 | 5.0 5.0 5.0
        for hour, score in enumerate(scores):
            log_attempt(self.base, **{"exam": "cefr-c1",
                                      "skill": "reading-use-of-english",
                                      "task-type": "open-cloze", "level": "C1",
                                      "score": score, "max": 10, "seconds": 300,
                                      "ts": "2026-07-08T%02d:00:00" % (9 + hour),
                                      "session": "s1"})
        result = self.build("--scope", "all")
        self.assertIn("C1 → C1 (steady", result.stdout)
        self.assertNotIn("improving", result.stdout)
        self.assertNotIn("slipping", result.stdout)

    def test_rows_appended_out_of_order_trend_uses_chronology(self):
        # The later attempt (9/10 -> B2) is appended FIRST, the back-dated
        # earlier one (4/10 -> B1) second. Chronologically the skill improved;
        # append order must not flip the direction to 'slipping'.
        log_attempt(self.base, **{"exam": "cefr-b2", "skill": "writing-evaluator",
                                  "task-type": "essay", "level": "B2",
                                  "score": 9, "max": 10, "seconds": 300,
                                  "ts": "2026-07-08T09:00:00", "session": "s2"})
        log_attempt(self.base, **{"exam": "cefr-b2", "skill": "writing-evaluator",
                                  "task-type": "essay", "level": "B2",
                                  "score": 4, "max": 10, "seconds": 300,
                                  "ts": "2026-07-06T09:00:00", "session": "s1"})
        result = self.build("--scope", "all")
        self.assertIn("B1 → B2 (improving", result.stdout)
        self.assertNotIn("slipping", result.stdout)

    # --- audit-fix regressions: overview extremes and diagnostics ----------

    def test_single_task_type_is_not_both_strongest_and_weakest(self):
        log_attempt(self.base, score=7, max=10, seconds=300,
                    ts="2026-07-08T09:00:00", session="s1")
        result = self.build("--scope", "all")
        self.assertNotIn("**Strongest:**", result.stdout)
        self.assertNotIn("**Weakest:**", result.stdout)
        self.assertIn("- **Key word transformation:**", result.stdout)

    def test_level_diagnostic_rows_are_never_ranked_or_recommended(self):
        # Two weak diagnostic probes plus one mid normal task: the diagnostic
        # would rank weakest if included, but it is a level-establishing probe,
        # not a drillable task, so only the normal task may be ranked.
        for hour in (9, 10):
            log_attempt(self.base, **{"exam": "toefl-ibt", "skill": "exam-router",
                                      "task-type": "level-diagnostic", "level": "B2",
                                      "score": 2, "max": 10, "seconds": 300,
                                      "ts": "2026-07-08T%02d:00:00" % hour,
                                      "session": "s1"})
        log_attempt(self.base, **{"exam": "cefr-c1",
                                  "skill": "reading-use-of-english",
                                  "task-type": "open-cloze", "level": "C1",
                                  "score": 6, "max": 10, "seconds": 300,
                                  "ts": "2026-07-08T11:00:00", "session": "s1"})
        result = self.build("--scope", "all")
        self.assertIn("Open cloze at C1 is your weakest area", result.stdout)
        self.assertIn("- **Open cloze:**", result.stdout)
        self.assertNotIn("Level diagnostic", result.stdout)

    def test_skill_trend_reports_improving_direction(self):
        # Two writing attempts at a B2 target: below-level then at-level.
        log_attempt(self.base, **{"exam": "cefr-b2", "skill": "writing-evaluator",
                                  "task-type": "essay", "level": "B2",
                                  "score": 4, "max": 10, "seconds": 300,
                                  "ts": "2026-07-06T09:00:00", "session": "s1"})
        log_attempt(self.base, **{"exam": "cefr-b2", "skill": "writing-evaluator",
                                  "task-type": "essay", "level": "B2",
                                  "score": 9, "max": 10, "seconds": 300,
                                  "ts": "2026-07-08T09:00:00", "session": "s2"})
        result = self.build("--scope", "all")
        self.assertIn("improving", result.stdout)


if __name__ == "__main__":
    unittest.main()
