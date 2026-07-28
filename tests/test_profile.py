"""Tests for profile.py and convert_score.py (Phase 0 target intake)."""

import json
import tempfile
import unittest
from pathlib import Path

from helpers import CONVERT_SCORE, PROFILE, run_script


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def profile_json(self):
        return json.loads((self.base / "profile.json").read_text(encoding="utf-8"))

    def test_show_without_a_profile_explains_how_to_make_one(self):
        result = run_script(PROFILE, ["show", "--base", self.base])
        self.assertEqual(result.returncode, 0)
        self.assertIn("No profile set yet", result.stdout)
        self.assertFalse((self.base / "profile.json").exists())

    def test_set_stores_target_and_derives_cefr(self):
        result = run_script(PROFILE, [
            "set", "--exam", "toefl-ibt", "--target-score", "4.5",
            "--base", self.base])
        self.assertEqual(result.returncode, 0, result.stderr)
        stored = self.profile_json()
        self.assertEqual(stored["exam"], "toefl-ibt")
        self.assertEqual(stored["target_score"], "4.5")
        self.assertEqual(stored["target_scale"], "toefl")
        # TOEFL band 4.5 sits in the B2 row of the official alignment.
        self.assertEqual(stored["target_cefr"], "B2")

    def test_ielts_target_of_7_derives_c1(self):
        run_script(PROFILE, ["set", "--exam", "ielts-academic",
                             "--target-score", "7", "--base", self.base])
        self.assertEqual(self.profile_json()["target_cefr"], "C1")

    def test_set_merges_instead_of_replacing(self):
        run_script(PROFILE, ["set", "--exam", "toefl-ibt",
                             "--target-score", "4.5", "--base", self.base])
        run_script(PROFILE, ["set", "--current-level", "B1", "--base", self.base])
        stored = self.profile_json()
        self.assertEqual(stored["current_level"], "B1")
        # The earlier fields must survive a partial update.
        self.assertEqual(stored["exam"], "toefl-ibt")
        self.assertEqual(stored["target_score"], "4.5")

    def test_bad_exam_date_is_rejected_without_writing(self):
        result = run_script(PROFILE, ["set", "--exam-date", "12-09-2026",
                                      "--base", self.base])
        self.assertEqual(result.returncode, 2)
        self.assertIn("YYYY-MM-DD", result.stderr)
        self.assertFalse((self.base / "profile.json").exists())

    def test_bad_current_level_is_rejected(self):
        result = run_script(PROFILE, ["set", "--current-level", "D1",
                                      "--base", self.base])
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.base / "profile.json").exists())

    def test_target_score_without_exam_is_rejected(self):
        # Without the exam we do not know the scale, so the CEFR translation
        # would be a guess.
        result = run_script(PROFILE, ["set", "--target-score", "4.5",
                                      "--base", self.base])
        self.assertEqual(result.returncode, 2)
        self.assertIn("--exam", result.stderr)

    def test_corrupt_profile_is_treated_as_empty_not_fatal(self):
        (self.base / "profile.json").write_text("{not json", encoding="utf-8")
        result = run_script(PROFILE, ["show", "--base", self.base])
        self.assertEqual(result.returncode, 0)
        self.assertIn("No profile set yet", result.stdout)

    def test_days_until_exam_is_reported(self):
        from datetime import date, timedelta
        soon = (date.today() + timedelta(days=10)).isoformat()
        result = run_script(PROFILE, ["set", "--exam-date", soon,
                                      "--base", self.base])
        self.assertIn("10 days away", result.stdout)


class ConvertScoreTests(unittest.TestCase):
    def convert(self, *args):
        return run_script(CONVERT_SCORE, list(args))

    def test_toefl_band_to_cefr(self):
        result = self.convert("--from", "toefl", "--score", "5")
        self.assertEqual(result.returncode, 0)
        self.assertIn("C1", result.stdout)

    def test_ielts_band_to_cefr(self):
        self.assertIn("B2", self.convert("--from", "ielts", "--score", "6").stdout)

    def test_cambridge_scale_to_cefr(self):
        self.assertIn("C1", self.convert("--from", "cambridge",
                                         "--score", "185").stdout)

    def test_cefr_back_to_an_exam_scale(self):
        result = self.convert("--from", "cefr", "--level", "C1", "--to", "ielts")
        self.assertEqual(result.returncode, 0)
        self.assertIn("7.0-8.0", result.stdout)

    def test_toefl_band_to_legacy_uses_published_concordance(self):
        result = self.convert("--from", "toefl", "--score", "5",
                              "--to", "toefl-legacy")
        self.assertIn("95-106", result.stdout)

    def test_legacy_total_maps_back_to_cefr(self):
        self.assertIn("C1", self.convert("--from", "toefl-legacy",
                                         "--score", "100").stdout)

    def test_out_of_range_score_is_rejected(self):
        result = self.convert("--from", "ielts", "--score", "12")
        self.assertEqual(result.returncode, 2)
        self.assertIn("outside", result.stderr)

    def test_cross_scale_conversion_is_labelled_indicative(self):
        result = self.convert("--from", "toefl", "--score", "5", "--to", "ielts")
        self.assertEqual(result.returncode, 0)
        self.assertIn("indicative", result.stdout)

    def test_bad_cefr_level_is_rejected(self):
        result = self.convert("--from", "cefr", "--level", "D2", "--to", "ielts")
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
