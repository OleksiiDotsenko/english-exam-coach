# Reading & Use of English

Read this when the user asks to drill any reading or use-of-English task
type, or asks why a reading answer is what it is. Objective drills run
**generate → answer → score → explain → log**. `coach <command>` is defined
in `SKILL.md`.

## Steps

1. **Identify** exam + level + task type (ask once if unclear; a daily drill
   takes the weakest type from the log instead). Load
   `data/exam-formats/<exam-id>.md` for the exact shape (items per task,
   options per question), and `data/cefr/reading-descriptors.md` +
   `data/cefr/reading-calibration-anchors.md` to calibrate text difficulty.
   Seed shapes: `data/item-bank/seed/reading-use-of-english-items.md`.
   **Check the requested task type is actually in the chosen exam** (per its
   format file): key word transformation and word formation exist only in
   B2–C2, cross-text matching only in C1, and so on. If the user asks for a
   task their exam does not contain, say so plainly and offer the nearest
   valid task or name the exam(s) that do include it — never generate an
   off-format item.
   **True/False/Not Given vs Yes/No/Not Given:** T/F/NG statements are about
   FACTUAL information in the text; Y/N/NG statements are about the WRITER'S
   views and claims (so the passage must carry opinions). Use the correct
   labels for each.

2. **Generate an ORIGINAL passage and items** matching the format exactly:
   the right number of items, the right option count, plausible distractors,
   one defensibly correct answer each. Calibrate lexis and syntax to the
   CEFR level. Give a realistic time budget (about 1.3 min per
   use-of-English item; a proportional share of the section time for
   reading sets).

   **Match the passage to authentic length** — this is as important as the
   item count. Aim for the **upper end** of the target range and count your
   words before presenting: left to instinct these passages come out 30–40%
   too short. Use the exam's figure from `data/exam-formats/<exam-id>.md`;
   as a fallback:
   - Gapped text: **B2 ~500–600, C1 ~550–780, C2 ~700–800 words** of base
     text.
   - Long-text multiple choice / multiple matching: **B2 ~500–700,
     C1 ~700–800, C2 ~700–800 words** of base text. IELTS Academic passages
     ~700–900 words **each**; IELTS General Training sections vary — see
     `ielts-general.md`. A too-short passage is the most common failure — a
     C2 Part 6 gapped text must be ~750 words, not ~450.
   - Cloze / word formation: ~150–220 words.
   - **Gapped text always has ONE more option than gaps** (B2/C1/C2) or
     three more (B1 Part 4) — the surplus fits no gap and is a deliberate
     distractor. Removed paragraphs run ~50–80 words each.
   - TOEFL: see the next section.

   **Verify the length mechanically, do not estimate it.** Write the passage
   to a temporary file and count it (`wc -w <file>`) before presenting;
   self-estimated word counts are exactly the failure this guards against.
   If the count is below the target range, extend the passage and re-count.
   Never present a passage you have not counted.

3. **Withhold the key.** Present only the passage, the items and the time
   budget. Ask the user to answer all items ("1 B, 2 A, …") and to note how
   long they took.

4. **Score objectively** — one mark per item, no partial credit unless the
   exam gives it (key word transformations are marked out of 2 in the B2–C2
   exams: award 1 for a half-correct split).
   **For open-ended item types** (open cloze, sentence and summary
   completion, short answer, word formation), credit ANY answer that is
   valid and correctly spelled — one that fits the context and, for a
   cloze, the word limit; the printed key is one acceptable answer, not the
   only one.
   **If the user answered only some items:** if they ran out of time or
   stopped early, log against the number actually attempted (`--max
   <attempted>`), not the full set; if they genuinely gave up, count blanks
   as wrong; if nothing was attempted, log nothing. Never fabricate answers
   for unattempted items.
   Then explain EVERY item, right or wrong: why the key is correct, why
   each tempting distractor fails, and for Not Given items, exactly what
   the passage does not say.

5. **Log the attempt** (silently):
   ```bash
   coach log-attempt \
     --exam <exam-id> --skill reading-use-of-english --task-type <slug> \
     --level <anchor> --score <n> --max <total> --seconds <time>
   ```
   Then, for each item the user missed, log **why** it was missed — a
   `comprehension` tag from `data/error-taxonomy.md` (detail, inference,
   paraphrase, distractor, purpose, main-idea, negation, structure,
   vocabulary, location, instruction) with a `--point` a fresh item could
   re-test, such as "not recognising a paraphrase of 'decline'" — and run
   `coach queue sync`. The item number is not re-testable; the reason is.
   Full protocol: `references/the-loop.md`.

   For out-of-2 task types (key word transformation), `--max` is **2 ×** the
   number of items scored and `--score` is the sum of the 0/1/2 marks — a
   6-item set is `--max 12`, a 4-item partial attempt is `--max 8`.
   `coach log-attempt` rejects a `--score` above `--max` and writes nothing,
   so an under-sized `--max` silently drops the attempt.

   Then offer one of: re-drill the same type, step up a level, or switch to
   the weakest type from the log.

## TOEFL iBT reading (2026 format)

Three task types. In the official practice test one module is 20 questions:
one Complete-the-Words paragraph (10), two Daily Life texts (2 + 3) and one
academic passage (5). A full reading section is a router module followed by
a second module; build a mock module in that 10 + 5 + 5 shape.

**Complete the Words — always built with `coach ctest`.** Write one plain
paragraph of about 70–80 words on an everyday or general-academic topic: a
real topic sentence first (it is the only context the learner gets), and a
full sentence or two after the tenth gap. Then:

```bash
coach ctest make --file paragraph.txt           # or --text "…"
```

Show the learner exactly the part printed under "SHOW THE LEARNER". The
script applies the real rule — first sentence whole, then the second half
of every second word removed until ten are gapped, one blank per missing
letter — so a gap can leave a single visible letter (`o_` for *of*). That is
correct; do not "repair" it into a longer stem. If the script prints a
note (too short, nothing after the last gap), fix the paragraph and run it
again. Pass an unrecoverable technical term with `--keep <word>`.
Mark with `coach ctest check --file paragraph.txt --answers "…"` (missing
letters or whole words, in order) or `--filled "<the whole paragraph as the
learner typed it>"`. Exact spelling, no partial credit, no penalty for a
wrong answer — tell the learner to fill every gap. For each miss the script
prints the gap as it was shown, its blank count, and whether the answer was
the right length. **Explain from those lines and never recount blanks
yourself:** an answer of the right length (*which* in `wh_ _ _`, where the
key is *while*) is wrong for its meaning or its grammar, not for its
length, and a reason built on a miscounted gap teaches the learner
something false. Log `--task-type toefl-complete-the-words --score <n>
--max 10`, and log each miss by its cause: `lexis/spelling`,
`grammar/agreement`, `comprehension/vocabulary`…

**Read in Daily Life.** A short everyday text — a notice, a sign, a menu,
an email, a social-media post, a schedule — of about 15–150 words, with
**2 or 3** four-option questions: what kind of text or business it is, its
purpose, a detail, an inference about the writer or reader. Give the text a
realistic form (sender and subject for an email, a heading for a notice).

**Read an Academic Passage.** A titled passage of about 150–200 words in
three or so short paragraphs, with **5** four-option questions drawn from:
main idea, detail, vocabulary in context ("the word … is closest in meaning
to"), inference, why the author mentions something, and NOT/EXCEPT.

All TOEFL reading questions have four options and one key. Vary the
position of the correct option.

## Boundaries

- Passages and items must be original — never reproduced or lightly
  paraphrased from published tests or copyrighted texts.
- Every item must have exactly one defensible key; if the user argues an
  item is ambiguous, re-examine honestly and concede when they are right
  (do not retro-fit justifications) — and still log the score as taken.
- Scores are indicative practice results, not predictions of official
  marks.
