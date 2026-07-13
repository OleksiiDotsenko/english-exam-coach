---
name: reading-use-of-english
description: >
  Use when the user wants to practice English exam reading or use-of-english
  tasks: IELTS (matching headings, True/False/Not Given, Yes/No/Not Given),
  TOEFL iBT reading (complete-the-words cloze, daily-life texts, short
  academic passages), or
  B1-C2 tasks (open cloze, multiple-choice cloze, gapped text, multiple
  matching; plus key word transformation and word formation in the B2-C2
  exams only). Generates an original
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
   options per question) and `data/cefr/reading-descriptors.md` to calibrate
   text difficulty. Seed shapes: `data/item-bank/seed/reading-use-of-english-items.md`.

2. **Generate an ORIGINAL passage and items** matching the format exactly:
   right number of items, right option count, plausible distractors, one
   defensibly correct answer each. Calibrate lexis and syntax to the CEFR
   level. Give a realistic time budget (e.g. ~1.3 min per use-of-english
   item; proportional share of the section time for reading sets).

3. **Withhold the key.** Present only the passage, the items, and the time
   budget. Ask the user to answer all items (e.g. "1 B, 2 A, …") and note
   how long they took.

4. **Score objectively** — one mark per item, no partial credit unless the
   exam gives it (key word transformations are marked out of 2 in the B2–C2
   exams: award 1 for a half-correct split). Then explain EVERY item, right
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
