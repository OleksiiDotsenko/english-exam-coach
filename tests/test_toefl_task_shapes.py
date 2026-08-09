"""The TOEFL 2026 task seeds must obey the real tasks' structural rules.

These four rules were all broken in generated practice at some point, and each
one is mechanically checkable, so they are pinned here rather than left to
review. The seeds are what the assistant imitates: a seed that breaks a rule
teaches every generated item to break it too.
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SEEDS = REPO_ROOT / "plugins" / "english-exam-coach" / "data" / "item-bank" / "seed"
FORMATS = REPO_ROOT / "plugins" / "english-exam-coach" / "data" / "exam-formats"


class CompleteTheWordsTests(unittest.TestCase):
    """Stem 3-5 letters; underscores exactly equal the missing letters."""

    def setUp(self):
        text = (SEEDS / "reading-use-of-english-items.md").read_text(encoding="utf-8")
        section = text.split("## Complete the Words")[1]
        passage, rest = section.split("**Key:**", 1)
        self.gaps = re.findall(r"([A-Za-z]+)((?:\\_)+)", passage)
        key_line = rest.split("*(Ten gaps")[0]
        self.keys = [k.strip() for k in key_line.replace("\n", " ").split("·")
                     if k.strip()]

    def test_the_seed_has_exactly_ten_gaps(self):
        # The real task always has 10 blanks.
        self.assertEqual(len(self.gaps), 10)
        self.assertEqual(len(self.keys), 10)

    def test_every_underscore_run_matches_the_missing_letter_count(self):
        for (stem, underscores), key in zip(self.gaps, self.keys):
            with self.subTest(gap=stem, key=key):
                shown = underscores.count("_")
                missing = len(key) - len(stem)
                self.assertEqual(
                    shown, missing,
                    "%s + %d underscores does not spell %r (needs %d)"
                    % (stem, shown, key, missing))

    def test_every_visible_stem_is_three_to_five_letters(self):
        for stem, _underscores in self.gaps:
            with self.subTest(stem=stem):
                self.assertGreaterEqual(len(stem), 3)
                self.assertLessEqual(len(stem), 5)

    def test_every_stem_actually_starts_its_key(self):
        for (stem, _u), key in zip(self.gaps, self.keys):
            with self.subTest(stem=stem):
                self.assertTrue(key.lower().startswith(stem.lower()),
                                "%r is not the start of %r" % (stem, key))


class BuildASentenceTests(unittest.TestCase):
    """Every item shows a context sentence plus 5-7 chunks."""

    def setUp(self):
        text = (SEEDS / "writing-prompts.md").read_text(encoding="utf-8")
        self.section = text.split("Build a Sentence")[1]
        self.items = re.findall(r"> \d+\. \*You read:\*(.+?)\*\(key:",
                                self.section, re.S)

    def test_all_five_items_carry_a_context_sentence(self):
        # A bare chunk list is a different task; the first sentence is what
        # makes one word order the natural one.
        self.assertEqual(len(self.items), 5,
                         "every item must open with *You read:* context")

    def test_each_item_offers_between_five_and_seven_chunks(self):
        for item in self.items:
            chunks = re.findall(r"`[^`]+`", item)
            with self.subTest(item=item.strip()[:40]):
                self.assertGreaterEqual(len(chunks), 5)
                self.assertLessEqual(len(chunks), 7)

    def test_the_all_or_nothing_rule_is_stated(self):
        self.assertIn("all or nothing", self.section.lower())


class SpeakingScenarioTests(unittest.TestCase):
    """Both TOEFL speaking tasks are single-scenario, with an opener."""

    def setUp(self):
        self.text = (SEEDS / "speaking-tasks.md").read_text(encoding="utf-8")

    def test_listen_and_repeat_has_one_scenario_and_an_introduction(self):
        section = self.text.split("Listen and Repeat")[1].split("\n## ")[0]
        self.assertIn("ONE scenario", section)
        self.assertIn("Introduction (read first", section)

    def test_listen_and_repeat_sentences_grow_in_length(self):
        section = self.text.split("Listen and Repeat")[1].split("\n## ")[0]
        counts = [int(n) for n in re.findall(r"\*\((\d+)(?: words)?\)\*", section)]
        self.assertEqual(len(counts), 7, "expected 7 annotated sentences")
        self.assertLessEqual(counts[0], 6, "the first sentence should be short")
        self.assertGreaterEqual(counts[-1], 15, "the last should reach the teens")
        self.assertEqual(counts, sorted(counts), "lengths must not decrease")

    def test_take_an_interview_opens_with_a_scenario(self):
        section = self.text.split("Take an Interview")[1].split("\n## ")[0]
        self.assertIn("Scenario (read first", section)
        self.assertIn("ONE everyday topic", section)

    def test_take_an_interview_has_exactly_four_questions(self):
        section = self.text.split("Take an Interview")[1].split("\n## ")[0]
        questions = re.findall(r"^> \d+\. ", section, re.M)
        self.assertEqual(len(questions), 4)


class FormatFileAgreementTests(unittest.TestCase):
    """The format file must state the same rules the seeds demonstrate."""

    def setUp(self):
        self.text = (FORMATS / "toefl-ibt.md").read_text(encoding="utf-8")

    def test_format_file_states_the_stem_and_gap_count(self):
        self.assertIn("first 3–5 letters", self.text)
        self.assertIn("exactly 10", self.text)

    def test_format_file_states_build_a_sentence_shows_two_sentences(self):
        self.assertIn("Every item shows two sentences", self.text)

    def test_format_file_states_the_speaking_scenarios(self):
        self.assertIn("belong to ONE scenario", self.text)
        self.assertIn("opened by a brief scenario", self.text)


if __name__ == "__main__":
    unittest.main()
