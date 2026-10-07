"""The TOEFL 2026 seeds and format file must describe the real task shapes.

Every rule here was broken in generated practice at some point, and twice a
"fix" taken from prep-site summaries was itself wrong (a three-to-five-letter
stem for Complete the Words; Listen-and-Repeat sentences in the high teens).
The shapes below were re-derived from the exam provider's own specifications
and practice test, and are pinned mechanically: the seeds are what the
assistant imitates, so a seed that breaks a rule teaches every generated item
to break it too.

The seed items themselves are ours. Nothing here is taken from an exam.
"""

import json
import re
import sys
import unittest

from helpers import DATA, PLUGIN_DIR, SCRIPTS

sys.path.insert(0, str(SCRIPTS))
import build_sentence  # noqa: E402
import ctest  # noqa: E402

SEEDS = DATA / "item-bank" / "seed"
FORMATS = DATA / "exam-formats"


def section(text, heading):
    """The body of the `## …heading…` section."""
    return text.split(heading, 1)[1].split("\n## ", 1)[0]


def unquote(block):
    """Markdown quote lines -> one line of plain text."""
    lines = [line.lstrip(">").strip() for line in block.splitlines()]
    return " ".join(" ".join(lines).split())


def fenced(text, language):
    return re.findall(r"```%s\n(.*?)\n```" % language, text, re.S)


class CompleteTheWordsTests(unittest.TestCase):
    """The printed item must be exactly what the builder makes of the source."""

    def setUp(self):
        text = (SEEDS / "reading-use-of-english-items.md").read_text(encoding="utf-8")
        self.section = section(text, "## Complete the Words")
        self.source, self.printed = fenced(self.section, "text")
        self.item = ctest.make_item(self.source)

    def test_the_seed_is_what_the_builder_prints(self):
        # Only the line wrapping may differ; the gaps' own (non-breaking)
        # spaces must survive, so plain spaces and new lines alone are folded.
        def fold(text):
            return re.sub(r"[ \n]+", " ", text)

        self.assertEqual(fold(self.printed), fold(ctest.render_item(self.item)))

    def test_ten_gaps_and_a_blank_for_every_missing_letter(self):
        self.assertEqual(len(self.item["gaps"]), 10)
        self.assertEqual(self.printed.count("_"),
                         sum(len(g["missing"]) for g in self.item["gaps"]))

    def test_the_first_sentence_is_whole_and_the_ending_is_whole(self):
        first = self.item["first_sentence"]
        self.assertNotIn("_", first)
        self.assertTrue(self.source.replace("\n", " ").startswith(first))
        after_last_gap = self.printed.rsplit("_", 1)[1]
        self.assertGreater(len(after_last_gap.split()), 15)

    def test_the_paragraph_is_the_official_length(self):
        self.assertTrue(65 <= self.item["words"] <= 85, self.item["words"])
        self.assertEqual(self.item["notes"], [])

    def test_the_key_lines_match_the_builder(self):
        letters = re.search(r"\*\*Key \(missing letters\):\*\* (.+)", self.section).group(1)
        words = re.search(r"\*\*Whole words:\*\* (.+)", self.section).group(1)
        self.assertEqual([k.strip() for k in letters.split("·")],
                         [g["missing"] for g in self.item["gaps"]])
        self.assertEqual([k.strip() for k in words.split("·")],
                         [g["word"] for g in self.item["gaps"]])

    def test_the_seed_tells_the_assistant_to_use_the_builder(self):
        self.assertIn("coach ctest make", self.section)
        self.assertIn("never by hand", self.section)


class BuildASentenceTests(unittest.TestCase):
    """The printed set must be exactly what the builder makes of the source."""

    def setUp(self):
        text = (SEEDS / "writing-prompts.md").read_text(encoding="utf-8")
        self.section = section(text, "— Build a Sentence")
        self.source = json.loads(fenced(self.section, "json")[0])
        self.shown, self.key = fenced(self.section, "text")
        self.items = [build_sentence.make_item(row["context"], row["answer"],
                                               row.get("distractor"), row.get("also") or [])
                      for row in self.source]

    def test_the_seed_is_what_the_builder_prints(self):
        self.assertEqual(self.shown, build_sentence.render_set(self.items))
        self.assertEqual(self.key, build_sentence.render_key(self.items))

    def test_a_full_set_is_ten_items_of_two_sentences_each(self):
        self.assertEqual(len(self.items), 10)
        for item in self.items:
            self.assertTrue(item["context"].endswith((".", "?", "!")), item["context"])

    def test_every_frame_has_five_to_seven_blanks_matching_its_tiles(self):
        for item in self.items:
            blanks = item["frame"].count("_____")
            self.assertTrue(5 <= blanks <= 7, item["frame"])
            self.assertEqual(len(item["tiles"]), blanks + (1 if item["unused"] else 0))
            self.assertTrue(item["frame"].endswith((".", "?")))

    def test_only_a_few_items_carry_an_extra_tile_and_never_more_than_one(self):
        with_extra = [item for item in self.items if item["unused"]]
        self.assertTrue(1 <= len(with_extra) <= 3, len(with_extra))

    def test_most_replies_are_questions(self):
        questions = [item for item in self.items if item["answer"].endswith("?")]
        self.assertGreaterEqual(len(questions), 6)
        self.assertLess(len(questions), 10)

    def test_some_frames_carry_pre_printed_words(self):
        printed = [item for item in self.items
                   if re.search(r"[A-Za-z]", item["frame"])]
        self.assertGreaterEqual(len(printed), 3)

    def test_the_rules_are_stated(self):
        lowered = self.section.lower()
        self.assertIn("all or nothing", lowered)
        self.assertIn("every item is two sentences", lowered)
        self.assertIn("coach sentence make", lowered)


class WritingPromptTests(unittest.TestCase):
    def setUp(self):
        self.text = (SEEDS / "writing-prompts.md").read_text(encoding="utf-8")

    def test_the_email_has_a_situation_three_bullets_and_a_filled_in_header(self):
        body = section(self.text, "— Write an Email")
        quoted = [line for line in body.splitlines() if line.startswith(">")]
        bullets = [line for line in quoted if line.startswith("> - ")]
        self.assertEqual(len(bullets), 3)
        self.assertIn("**To:**", body)
        self.assertIn("**Subject:**", body)
        self.assertIn("7 minutes", body)

    def test_the_discussion_has_a_professor_and_two_students_on_different_sides(self):
        body = section(self.text, "— Write for an Academic Discussion")
        posts = re.split(r">\s*\n", body.split("**Professor:**", 1)[1])
        professor, first, second = [unquote(post) for post in posts[:3]]
        self.assertTrue(55 <= len(professor.split()) <= 90, len(professor.split()))
        self.assertIn("?", professor)
        for post in (first, second):
            self.assertTrue(35 <= len(post.split()) <= 60, len(post.split()))
        self.assertIn("disagree", second.lower())
        self.assertIn("at least 100 words", body)
        self.assertIn("10 minutes", body)


class SpeakingScenarioTests(unittest.TestCase):
    def setUp(self):
        self.text = (SEEDS / "speaking-tasks.md").read_text(encoding="utf-8")

    def repeat_sentences(self):
        body = unquote(section(self.text, "— Listen and Repeat"))
        return re.findall(r"\d\. (.+?) \*\((\d+)(?: words)?\)\*", body)

    def test_listen_and_repeat_has_one_scenario_with_a_role_and_a_speaker(self):
        body = section(self.text, "— Listen and Repeat")
        self.assertIn("ONE scenario", body)
        scenario = unquote(body.split("**Scenario (read first, not repeated):**")[1]
                           .split(">\n")[0])
        self.assertIn("You are", scenario)
        self.assertRegex(scenario, r"Listen to your \w+ and repeat")

    def test_listen_and_repeat_has_seven_sentences_with_honest_word_counts(self):
        sentences = self.repeat_sentences()
        self.assertEqual(len(sentences), 7)
        for sentence, stated in sentences:
            self.assertEqual(len(re.findall(r"[A-Za-z']+", sentence)), int(stated),
                             sentence)

    def test_listen_and_repeat_grows_loosely_and_stays_out_of_the_high_teens(self):
        counts = [int(stated) for _sentence, stated in self.repeat_sentences()]
        self.assertTrue(5 <= counts[0] <= 7, counts)
        self.assertLessEqual(max(counts), 14, counts)
        self.assertGreaterEqual(min(counts[-2:]), 11, counts)
        # Longer at the end than at the start, without rising at every step.
        self.assertGreater(sum(counts[-3:]), sum(counts[:3]))

    def interview_turns(self):
        body = unquote(section(self.text, "— Take an Interview")
                       .split("**Scenario (read first):**")[1])
        return re.findall(r"\d\. \*\*Interviewer:\*\* (.+?) \*\((\d+) words\)\*", body)

    def test_the_interview_opens_with_a_scenario_on_one_topic(self):
        body = section(self.text, "— Take an Interview")
        self.assertIn("ONE everyday topic", body)
        self.assertIn("**Scenario (read first):**", body)

    def test_the_interview_has_four_turns_with_honest_word_counts(self):
        turns = self.interview_turns()
        self.assertEqual(len(turns), 4)
        for turn, stated in turns:
            self.assertEqual(len(turn.split()), int(stated), turn[:40])

    def test_every_interviewer_turn_has_a_lead_in_before_its_question(self):
        for turn, _stated in self.interview_turns():
            words = len(turn.split())
            self.assertTrue(35 <= words <= 60, "%d words: %s" % (words, turn[:40]))
            lead_in = turn.split("?")[0]
            self.assertGreaterEqual(len(re.findall(r"[.!]", lead_in)), 2,
                                    "no lead-in before the question: " + turn[:40])

    def test_the_interview_climbs_from_fact_to_policy(self):
        turns = [turn for turn, _stated in self.interview_turns()]
        self.assertRegex(turns[0], r"how often|do you|have you|where do you")
        self.assertIn("why", turns[1].lower())
        self.assertIn("Do you agree", turns[2])
        self.assertTrue(turns[2].endswith("Why or why not?"))
        self.assertIn("should", turns[3])
        self.assertTrue(turns[3].endswith("Why or why not?"))


class ListeningSeedTests(unittest.TestCase):
    def setUp(self):
        self.text = (SEEDS / "listening-scripts.md").read_text(encoding="utf-8")

    def script_words(self, heading):
        body = section(self.text, heading)
        script = body.split("**Script", 1)[1].split("**Questions:**")[0] \
            .split("**Key:**")[0]
        spoken = unquote("\n".join(line for line in script.splitlines()
                                   if line.startswith(">")))
        return len(re.sub(r"\*\*\w+:\*\*", "", spoken).split())

    def numbered_questions(self, heading):
        body = section(self.text, heading).split("**Questions:**")[1]
        body = body.split("**Script")[0].split("**Key:**")[0]
        return re.findall(r"^\d\. ", body, re.M)

    def test_a_conversation_is_short_and_has_two_questions(self):
        heading = "## Short conversation + 2 questions"
        self.assertTrue(35 <= self.script_words(heading) <= 100)
        self.assertEqual(len(self.numbered_questions(heading)), 2)

    def test_an_announcement_is_short_and_has_two_questions(self):
        heading = "## Announcement + 2 questions"
        self.assertTrue(35 <= self.script_words(heading) <= 100)
        self.assertEqual(len(self.numbered_questions(heading)), 2)

    def test_an_academic_talk_has_four_questions_and_at_most_250_words(self):
        heading = "## Mini-lecture + multiple choice"
        self.assertTrue(100 <= self.script_words(heading) <= 250)
        self.assertEqual(len(self.numbered_questions(heading)), 4)

    def test_every_multiple_choice_question_has_four_options_and_one_key(self):
        for heading in ("## Short conversation + 2 questions",
                        "## Announcement + 2 questions",
                        "## Mini-lecture + multiple choice"):
            body = section(self.text, heading).split("**Questions:**")[1]
            body = body.split("**Script")[0].split("**Key:**")[0]
            for question in re.split(r"^\d\. ", body, flags=re.M)[1:]:
                flat = " ".join(question.split())
                self.assertEqual(len(re.findall(r"\b[A-D]\. ", flat)), 4, flat[:50])
                self.assertEqual(flat.count("✅"), 1, flat[:50])

    def test_the_correct_option_is_not_always_in_the_same_place(self):
        keys = re.findall(r"\*\*Key:\*\* ((?:\d [A-D](?: · )?)+)", self.text)
        letters = re.findall(r"\d ([A-D])", " ".join(keys[:3]))
        self.assertGreaterEqual(len(set(letters)), 3, letters)


class FormatFileAgreementTests(unittest.TestCase):
    """The format file must state the rules the seeds demonstrate."""

    def setUp(self):
        self.text = (FORMATS / "toefl-ibt.md").read_text(encoding="utf-8")
        self.flat = " ".join(self.text.split())

    def test_complete_the_words_rule(self):
        self.assertIn("exactly 10 gaps", self.flat)
        self.assertIn("the second half of every second word is removed", self.flat)
        self.assertIn("One blank is shown for each missing letter", self.flat)
        self.assertIn("The first sentence is left whole", self.flat)

    def test_build_a_sentence_rule(self):
        self.assertIn("Every item shows two sentences", self.flat)
        self.assertIn("5 to 7 blanks", self.flat)
        self.assertIn("one extra tile that is not used", self.flat)

    def test_writing_tasks(self):
        self.assertIn("three bullet points", self.flat)
        self.assertIn("at least 100 words", self.flat)

    def test_speaking_scenarios(self):
        self.assertIn("belong to ONE scenario", self.flat)
        self.assertIn("opened by a brief scenario", self.flat)
        self.assertIn("each later question is led into by one to three sentences",
                      self.flat)
        self.assertIn("neither gives any preparation time", self.flat)

    def test_listening_rules(self):
        self.assertIn("Every recording plays once", self.flat)
        self.assertIn("you cannot go back to an earlier question", self.flat)

    def test_published_section_figures(self):
        for heading in ("## Reading — 30 min · 50 items",
                        "## Listening — 29 min · 47 items",
                        "## Writing — 23 min · 12 items",
                        "## Speaking — 8 min · 11 items"):
            self.assertIn(heading, self.text)

    def test_it_carries_a_verification_stamp(self):
        self.assertRegex(self.text, r"<!-- last-verified: \d{4}-\d{2}-\d{2} \|")


class RetiredClaimsTests(unittest.TestCase):
    """Claims that were shipped and were wrong must not come back anywhere."""

    WRONG = ("first 3–5 letters", "first 3-5 letters", "three to five letters",
             "upper teens", "not every other word", "6 min 50 s")

    def test_no_shipped_file_repeats_a_retired_claim(self):
        for path in sorted(PLUGIN_DIR.rglob("*.md")):
            text = " ".join(path.read_text(encoding="utf-8").split())
            for claim in self.WRONG:
                self.assertFalse(claim in text, "%s still says %r"
                                 % (path.relative_to(PLUGIN_DIR), claim))


if __name__ == "__main__":
    unittest.main()
