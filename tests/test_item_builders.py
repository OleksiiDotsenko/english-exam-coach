"""Tests for the two TOEFL item builders: ctest.py and build_sentence.py.

Both tasks have a mechanical shape. A blank too many in a gapped word, or a
frame whose blanks do not match its tiles, makes an item impossible to answer
— so the shape is produced and marked by rule, and these tests pin the rule.
Every sentence used here is our own; nothing is taken from an exam.
"""

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import SCRIPTS, coach

sys.path.insert(0, str(SCRIPTS))
import build_sentence  # noqa: E402
import ctest  # noqa: E402

def gaps(text):
    """Write a gap the way ctest prints it: its blanks joined by non-breaking
    spaces, so that it cannot be split across two lines."""
    return re.sub(r"(?<=_) (?=_)", ctest.NBSP, text)


BEES = ("Honeybees tell each other where food is by dancing inside the dark "
        "hive. A returning worker walks in a short straight line while shaking "
        "her body from side to side. The angle of this line shows the direction "
        "of the flowers, and the time she spends shaking shows how far away "
        "they are. Other bees follow her closely and then fly out to the same "
        "place. In this way a single bee can guide hundreds of others to a "
        "good source of nectar.")


class GapRuleTests(unittest.TestCase):
    def test_a_word_keeps_its_first_half_rounded_down(self):
        cases = {"of": ("o", "f"), "use": ("u", "se"), "grow": ("gr", "ow"),
                 "fruit": ("fr", "uit"), "worker": ("wor", "ker"),
                 "flowers": ("flo", "wers"), "straight": ("stra", "ight"),
                 "gardeners": ("gard", "eners")}
        for word, (shown, missing) in cases.items():
            got_shown, got_missing, _printed = ctest.gap_word(word, "spaced")
            self.assertEqual((got_shown, got_missing), (shown, missing), word)

    def test_one_blank_is_printed_for_each_missing_letter(self):
        for word in ("of", "use", "grow", "fruit", "worker", "flowers", "gardeners"):
            for style, blank in (("spaced", "_"), ("dash", "-")):
                shown, missing, printed = ctest.gap_word(word, style)
                self.assertEqual(printed.count(blank), len(missing), (word, style))
                self.assertEqual(len(shown) + printed.count(blank), len(word))
        self.assertEqual(ctest.gap_word("fruit", "spaced")[2], gaps("fr_ _ _"))
        self.assertEqual(ctest.gap_word("flowers", "dash")[2], "flo----")
        self.assertEqual(ctest.gap_word("of", "spaced")[2], "o_")

    def test_a_gap_cannot_be_split_across_two_lines(self):
        printed = ctest.gap_word("gardeners", "spaced")[2]
        self.assertNotIn(" ", printed)
        self.assertEqual(len(printed.split()), 5)      # still five separate blanks


class CtestBuildTests(unittest.TestCase):
    def setUp(self):
        self.item = ctest.make_item(BEES)

    def test_the_first_sentence_is_left_whole(self):
        first = "Honeybees tell each other where food is by dancing inside the dark hive."
        self.assertEqual(self.item["first_sentence"], first)
        self.assertTrue(self.item["item"].startswith(first + gaps(" A returning wor_ _ _ ")))

    def test_every_second_word_from_the_second_word_of_sentence_two(self):
        # "A" is one letter and is not counted: returning, WORKER, walks, IN, …
        self.assertEqual([g["word"] for g in self.item["gaps"]],
                         ["worker", "in", "straight", "while", "her", "from",
                          "to", "The", "of", "line"])

    def test_exactly_ten_gaps_then_the_rest_is_whole(self):
        self.assertEqual(len(self.item["gaps"]), 10)
        tail = self.item["item"].split(gaps("li_ _"), 1)[1]
        self.assertNotIn("_", tail)
        self.assertTrue(tail.strip().startswith("shows the direction"))
        self.assertTrue(self.item["item"].endswith("a good source of nectar."))

    def test_blanks_in_the_text_equal_the_letters_in_the_key(self):
        total = sum(g["blanks"] for g in self.item["gaps"])
        self.assertEqual(self.item["item"].count("_"), total)
        for gap in self.item["gaps"]:
            self.assertEqual(gap["blanks"], len(gap["missing"]))
            self.assertEqual(gap["shown"] + gap["missing"], gap["word"])

    def test_filling_the_blanks_restores_the_paragraph(self):
        restored = self.item["item"]
        for gap in self.item["gaps"]:
            printed = ctest.gap_word(gap["word"], "spaced")[2]
            self.assertIn(printed, restored)
            restored = restored.replace(printed, gap["word"], 1)
        self.assertEqual(restored, BEES)

    def test_punctuation_stays_attached_to_a_gapped_word(self):
        item = ctest.make_item("Rivers shape the land around them over time. "
                               "However, water alone cannot explain every valley "
                               "we see today in the mountains.", gaps=3)
        self.assertIn(gaps("However, wa_ _ _ alone can_ _ _ explain ev_ _ _ valley"),
                      item["item"])

    def test_the_dash_style(self):
        item = ctest.make_item(BEES, style="dash")
        self.assertIn("A returning wor--- walks i- a short stra---- line", item["item"])
        self.assertNotIn("_", item["item"])

    def test_uncountable_words_are_left_whole_and_not_counted(self):
        text = ("Deserts are not always hot places with endless sand. "
                "In 1911 Dr. Amara Lee crossed a well-known desert in Asia and "
                "didn't find DNA samples that she wanted for the long study.")
        item = ctest.make_item(text, gaps=6)
        for whole in ("1911", "Dr.", "Amara", "Lee", " a ", "well-known", "Asia",
                      "didn't", "DNA"):
            self.assertIn(whole, item["item"])
        # counted: In, crossed, desert, in, and, find, samples, that, she, wanted…
        self.assertEqual([g["word"] for g in item["gaps"]],
                         ["crossed", "in", "find", "that", "wanted", "the"])

    def test_keep_leaves_a_term_whole_and_shifts_the_count(self):
        item = ctest.make_item(BEES, keep=["Worker"])
        self.assertIn(gaps("A returning worker wa_ _ _ in a sh_ _ _ straight"), item["item"])
        self.assertEqual(len(item["gaps"]), 10)

    def test_an_explicit_split_mark_wins(self):
        item = ctest.make_item("Vitamin C. is a strange start || Plants make "
                               "their own food from light and water each day.", gaps=3)
        self.assertEqual(item["first_sentence"], "Vitamin C. is a strange start")
        self.assertNotIn("||", item["item"])

    def test_an_abbreviation_does_not_end_the_first_sentence(self):
        item = ctest.make_item("Dr. Okafor studies how birds find their way home. "
                               "Her team follows small groups across the sea for "
                               "many weeks.", gaps=3)
        self.assertEqual(item["first_sentence"],
                         "Dr. Okafor studies how birds find their way home.")

    def test_a_paragraph_that_is_too_short_is_refused_with_advice(self):
        with self.assertRaises(ValueError) as caught:
            ctest.make_item("A first sentence is here. Then only four more words.")
        self.assertIn("only carries 2 gaps", str(caught.exception))
        with self.assertRaises(ValueError):
            ctest.make_item("Just one sentence without anything after it.")
        with self.assertRaises(ValueError):
            ctest.make_item("   ")

    def test_notes_flag_an_item_that_is_off_shape(self):
        self.assertEqual(self.item["notes"], [])
        short = ctest.make_item("Short start. Then " + "word " * 20 + "end.", gaps=10)
        joined = " ".join(short["notes"])
        self.assertIn("official paragraphs run about 70-80", joined)
        self.assertIn("first sentence is only 2 words", joined)
        self.assertIn("after the last gap", joined)

    def test_new_lines_in_the_source_do_not_matter(self):
        wrapped = BEES.replace(". ", ".\n")
        self.assertEqual(ctest.make_item(wrapped)["item"], self.item["item"])


class CtestMarkTests(unittest.TestCase):
    def setUp(self):
        self.item = ctest.make_item(BEES)
        self.key = [g["missing"] for g in self.item["gaps"]]

    def test_missing_letters_or_whole_words_are_both_right(self):
        _results, score = ctest.mark_answers(self.item, self.key)
        self.assertEqual(score, 10)
        _results, score = ctest.mark_answers(
            self.item, [g["word"].upper() for g in self.item["gaps"]])
        self.assertEqual(score, 10)

    def test_a_near_miss_is_wrong(self):
        answers = list(self.key)
        answers[3] = "wile"        # "while" misspelt
        answers[4] = "r"           # one letter short
        results, score = ctest.mark_answers(self.item, answers)
        self.assertEqual(score, 8)
        self.assertEqual([r["n"] for r in results if not r["correct"]], [4, 5])

    def test_blank_and_missing_answers_are_wrong_not_errors(self):
        results, score = ctest.mark_answers(self.item, self.key[:3] + [""])
        self.assertEqual(score, 3)
        self.assertEqual(len(results), 10)

    def test_a_filled_in_paragraph_can_be_marked(self):
        filled = BEES.replace("worker", "worked").replace("straight", "strange")
        answers = ctest.answers_from_filled(self.item, filled)
        _results, score = ctest.mark_answers(self.item, answers)
        self.assertEqual(score, 8)
        with self.assertRaises(ValueError):
            ctest.answers_from_filled(self.item, BEES + " extra words")

    def test_answer_lists_split_on_commas_and_spaces(self):
        self.assertEqual(ctest.split_answers("ker, n  ight;ile / - ?"),
                         ["ker", "n", "ight", "ile", "", ""])


class CtestCommandTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.file = Path(self._tmp.name) / "paragraph.txt"
        self.file.write_text(BEES, encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_make_shows_the_item_apart_from_its_key(self):
        result = coach(self._tmp.name, "ctest", "make", "--file", self.file)
        self.assertEqual(result.returncode, 0, result.stderr)
        shown, kept = result.stdout.split("KEEP BACK")
        self.assertIn(ctest.INSTRUCTION, shown)
        self.assertIn(gaps("wor_ _ _"), shown)
        self.assertNotIn("worker", shown)
        self.assertRegex(kept, r"1\s+ker\s+worker")

    def test_json_and_check_agree_with_each_other(self):
        made = json.loads(coach(self._tmp.name, "ctest", "make", "--file",
                                self.file, "--json").stdout)
        answers = " ".join(g["missing"] for g in made["gaps"])
        result = coach(self._tmp.name, "ctest", "check", "--file", self.file,
                       "--answers", answers, "--json")
        self.assertEqual(json.loads(result.stdout)["score"], 10)

    def test_check_reports_each_gap(self):
        result = coach(self._tmp.name, "ctest", "check", "--file", self.file,
                       "--answers", "ker n ight wile")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith("3 / 10"))
        self.assertIn("wrong   while  (missing letters: ile; answered: wile)", result.stdout)

    def test_input_errors_are_reported_not_raised(self):
        for args in (["make", "--text", "One sentence only."],
                     ["make", "--file", Path(self._tmp.name) / "missing.txt"],
                     ["check", "--file", self.file],
                     ["check", "--file", self.file, "--answers", "a " * 11],
                     ["make", "--file", self.file, "--gaps", "0"]):
            result = coach(self._tmp.name, "ctest", *args)
            self.assertEqual(result.returncode, 2, args)
            self.assertNotIn("Traceback", result.stderr)


LAB = dict(context="The lab is closed on Friday.",
           answer="do | you | know | if | [we can] | hand in | the report | on Monday ?",
           distractor="does")


class SentenceBuildTests(unittest.TestCase):
    def test_the_frame_has_one_blank_per_tile_and_shows_the_end_mark(self):
        item = build_sentence.make_item(**LAB)
        self.assertEqual(item["frame"], "_____ _____ _____ _____ we can _____ _____ _____ ?")
        self.assertEqual(item["blanks"], 7)
        self.assertEqual(item["frame"].count("_____"), item["blanks"])
        self.assertEqual(len(item["tiles"]), item["blanks"] + 1)   # one extra
        self.assertEqual(item["answer"], "Do you know if we can hand in the report on Monday?")
        self.assertEqual(item["unused"], "does")

    def test_tiles_are_scrambled_the_same_way_every_time(self):
        first = build_sentence.make_item(**LAB)
        again = build_sentence.make_item(**LAB)
        self.assertEqual(first["tiles"], again["tiles"])
        self.assertNotEqual(first["tiles"][:7], first["in_order"])
        self.assertEqual(sorted(first["tiles"]), sorted(first["in_order"] + ["does"]))

    def test_no_item_is_ever_printed_already_in_order(self):
        words = ["alpha", "bravo", "charlie", "delta", "echo", "golf", "hotel"]
        for size in (5, 6, 7):
            for shift in range(40):
                tiles = [w + str(shift) for w in words[:size]]
                item = build_sentence.make_item("Context here.", " | ".join(tiles) + " .")
                self.assertNotEqual(item["tiles"], item["in_order"])
                self.assertEqual(sorted(item["tiles"]), sorted(item["in_order"]))

    def test_the_first_tile_loses_its_capital_unless_it_must_keep_it(self):
        item = build_sentence.make_item("It starts at six.",
                                        "What | time | does | it | finish ?")
        self.assertIn("what", item["tiles"])
        self.assertEqual(item["answer"], "What time does it finish?")
        kept = build_sentence.make_item("How was it?",
                                        "I | have | never | seen | anything | better .")
        self.assertIn("I", kept["tiles"])
        name = build_sentence.make_item("Who called?", "Dana | rang | twice | this | morning .",
                                        keep_case=True)
        self.assertIn("Dana", name["tiles"])

    def test_pre_printed_words_stay_in_the_frame_and_out_of_the_tiles(self):
        item = build_sentence.make_item(
            "How was the lecture?",
            "[the] professor | who | gave it | explained | everything | clearly .")
        self.assertEqual(item["frame"], "The _____ _____ _____ _____ _____ _____ .")
        self.assertNotIn("the", [t.lower() for t in item["tiles"]])
        self.assertEqual(item["answer"],
                         "The professor who gave it explained everything clearly.")
        middle = build_sentence.make_item(
            "I can't find my notes.",
            "Could | you | tell me [where you] | last | saw | them ?")
        self.assertEqual(middle["frame"], "_____ _____ _____ where you _____ _____ _____ ?")

    def test_the_official_shape_is_enforced(self):
        for answer, message in (
                ("one | two | three | four .", "5 to 7"),
                ("a | b | c | d | e | f | g | h .", "5 to 7"),
                ("one | two | three | four | five", "must end"),
                ("[all] [printed] .", "no tiles"),
                ("one | two [three | four | five .", "unbalanced"),
                ("", "empty")):
            with self.assertRaises(ValueError) as caught:
                build_sentence.make_item("Context.", answer)
            self.assertIn(message, str(caught.exception), answer)
        with self.assertRaises(ValueError) as caught:
            build_sentence.make_item("", "one | two | three | four | five .")
        self.assertIn("two sentences", str(caught.exception))
        with self.assertRaises(ValueError):
            build_sentence.make_item("Context.", "one | two | three | four | five .",
                                     distractor="THREE")

    def test_the_tile_limits_can_be_loosened_for_other_drills(self):
        item = build_sentence.make_item("Context.", "one | two | three .", min_blanks=3)
        self.assertEqual(item["blanks"], 3)


class SentenceMarkTests(unittest.TestCase):
    def setUp(self):
        self.item = build_sentence.make_item(also=["Do you know if on Monday we "
                                                   "can hand in the report?"], **LAB)

    def test_marking_is_all_or_nothing(self):
        right = ("Do you know if we can hand in the report on Monday?",
                 "do you know if we can hand in the report on monday",
                 "  Do you know   if we can hand in the report on Monday ?  ",
                 "do you know if hand in the report on Monday",      # tiles only
                 "Do you know if on Monday we can hand in the report?")
        for response in right:
            self.assertTrue(build_sentence.mark(self.item, response), response)
        wrong = ("Does you know if we can hand in the report on Monday?",
                 "Do you know if we can hand in on Monday the report?",
                 "Do you know if we can hand in the report?", "", "   ")
        for response in wrong:
            self.assertFalse(build_sentence.mark(self.item, response), response)


class SentenceCommandTests(unittest.TestCase):
    ITEMS = [
        LAB,
        {"context": "How was the lecture?",
         "answer": "[The] professor | who | gave it | explained | everything | clearly ."},
        {"context": "It starts at six.", "answer": "What | time | does | it | finish ?"},
    ]

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.batch = self.dir / "set.json"
        self.batch.write_text(json.dumps(self.ITEMS), encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def run_cmd(self, *args):
        return coach(self.dir, "sentence", *args)

    def test_a_set_is_numbered_and_its_key_is_kept_apart(self):
        result = self.run_cmd("make", "--batch", self.batch)
        self.assertEqual(result.returncode, 0, result.stderr)
        shown, kept = result.stdout.split("KEEP BACK")
        self.assertIn(build_sentence.INSTRUCTION, shown)
        self.assertIn("1. The lab is closed on Friday.", shown)
        self.assertIn("   The _____ _____ _____ _____ _____ _____ .", shown)
        self.assertEqual(len(re.findall(r"^\d\. ", shown, flags=re.MULTILINE)), 3)
        self.assertNotIn("Do you know if we can", shown)
        self.assertIn("1. Do you know if we can hand in the report on Monday?   "
                      "(not used: does)", kept)

    def test_every_frame_matches_its_tiles_in_json(self):
        items = json.loads(self.run_cmd("make", "--batch", self.batch, "--json").stdout)
        for item in items:
            extra = 1 if item["unused"] else 0
            self.assertEqual(item["frame"].count("_____"), len(item["tiles"]) - extra)

    def test_a_set_is_marked_from_a_file_of_answers(self):
        answers = self.dir / "answers.txt"
        answers.write_text("1. Do you know if we can hand in the report on Monday?\n"
                           "2. The professor who explained it gave everything clearly.\n"
                           "3. What time does it finish?\n", encoding="utf-8")
        result = self.run_cmd("check", "--batch", self.batch, "--responses", answers)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith("2 / 3"))
        self.assertIn("2  wrong   The professor who gave it explained everything clearly.",
                      result.stdout)

    def test_numbered_answers_survive_a_skipped_item(self):
        answers = self.dir / "answers.txt"
        answers.write_text("1) Do you know if we can hand in the report on Monday?\n"
                           "3) What time does it finish?\n", encoding="utf-8")
        result = self.run_cmd("check", "--batch", self.batch, "--responses", answers,
                              "--json")
        data = json.loads(result.stdout)
        self.assertEqual([r["correct"] for r in data["results"]], [True, False, True])

    def test_one_bad_item_stops_the_whole_set_and_names_it(self):
        broken = self.ITEMS + [{"context": "Fine.", "answer": "too | short ."}]
        self.batch.write_text(json.dumps(broken), encoding="utf-8")
        result = self.run_cmd("make", "--batch", self.batch)
        self.assertEqual(result.returncode, 2)
        self.assertIn("item 4:", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_input_errors_are_reported_not_raised(self):
        self.batch.write_text("{not json", encoding="utf-8")
        for args in (["make", "--batch", self.batch],
                     ["make"],
                     ["make", "--batch", self.dir / "missing.json"],
                     ["check", "--context", "c", "--answer", "a | b | c | d | e ."],
                     ["check", "--context", "c", "--answer", "a | b | c | d | e .",
                      "--response", "x", "--response", "y"]):
            result = self.run_cmd(*args)
            self.assertEqual(result.returncode, 2, args)
            self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
