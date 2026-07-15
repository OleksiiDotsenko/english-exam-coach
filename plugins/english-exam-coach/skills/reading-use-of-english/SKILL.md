---
name: reading-use-of-english
description: >
  Use when the user wants to practice English exam reading or use-of-english
  tasks: IELTS (matching headings, True/False/Not Given, Yes/No/Not Given,
  matching information, sentence/summary completion, short answer),
  TOEFL iBT reading (complete-the-words cloze, daily-life texts, short
  academic passages), or
  B1-C2 tasks (reading-comprehension multiple choice, open cloze,
  multiple-choice cloze, gapped text, multiple matching; cross-text matching
  at C1; plus key word transformation and word formation in the B2-C2 exams
  only). Generates an original
  passage and items, scores answers objectively, explains every answer, and
  logs the attempt with score and time.
---

# Reading & Use of English

Objective drills: generate → answer → score → explain → log. Paths are
relative to `${CLAUDE_PLUGIN_ROOT}` (if unset, resolve relative to this file).

## When to use

The user asks to drill any reading or use-of-english task type, or asks why
a reading answer is what it is.

## Steps

1. **Identify** exam + level + task type (ask once if unclear; /daily-drill
   picks the weakest type from the progress log instead). Load
   `data/exam-formats/<exam-id>.md` for the exact shape (items per task,
   options per question) and `data/cefr/reading-descriptors.md` +
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
   views/claims (so the passage must carry opinions). Use the correct labels
   for each.

2. **Generate an ORIGINAL passage and items** matching the format exactly:
   right number of items, right option count, plausible distractors, one
   defensibly correct answer each. Calibrate lexis and syntax to the CEFR
   level. Give a realistic time budget (e.g. ~1.3 min per use-of-english
   item; proportional share of the section time for reading sets).

   **Match the passage to authentic length** — this is as important as the
   item count. Aim for the **upper end** of the target range and count your
   words before presenting: left to instinct these passages come out ~30–40%
   too short. Use the exam's figure from `data/exam-formats/<exam-id>.md`
   ("Passage lengths"); as a fallback:
   - Gapped text / long-text multiple choice / multiple matching: **B2
     ~500–600, C1 ~600–780, C2 ~700–800 words** of base text (IELTS Academic
     passages ~700–900 words **each**; IELTS General Training sections vary —
     see `ielts-general.md`). A too-short passage is the most common failure —
     a C2 Part 6 gapped text must be ~750 words, not ~450.
   - Cloze / word formation: ~150–220 words. TOEFL academic passage ~200;
     TOEFL daily-life texts 15–150.
   - **Gapped text always has ONE more option than gaps** (B2/C1/C2) or three
     more (B1 Part 4) — the surplus fits no gap and is a deliberate distractor.
     Removed paragraphs run ~50–80 words each.

3. **Withhold the key.** Present only the passage, the items, and the time
   budget. Ask the user to answer all items (e.g. "1 B, 2 A, …") and note
   how long they took.

4. **Score objectively** — one mark per item, no partial credit unless the
   exam gives it (key word transformations are marked out of 2 in the B2–C2
   exams: award 1 for a half-correct split). **If the user answered only
   some items:** if they ran out of time or stopped early, log against the
   number actually attempted (`--max <attempted>`), not the full set; if they
   genuinely gave up, count blanks as wrong; if nothing was attempted, log
   nothing. Never fabricate answers for unattempted items. Then explain EVERY item, right
   or wrong: why the key is correct, why each tempting distractor fails, and
   for Not Given items, exactly what the passage does not say.

5. **Log the attempt** (silently):
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/progress-tracker/scripts/log_attempt.py" \
     --exam <exam-id> --skill reading-use-of-english --task-type <slug> \
     --level <anchor> --score <n> --max <total> --seconds <time>
   ```
   Use the exact `--task-type` slug from `data/task-types.md` so attempts
   aggregate across sessions.
   Then offer one of: re-drill the same type, step up a level, or switch to
   the weakest type from the log.

## Boundaries

- Passages and items must be original — never reproduced or lightly
  paraphrased from published tests or copyrighted texts.
- Every item must have exactly one defensible key; if the user argues an
  item is ambiguous, re-examine honestly and concede when they are right
  (do not retro-fit justifications) — and still log the score as taken.
- Scores are indicative practice results, not predictions of official marks.
