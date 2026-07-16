---
name: writing-evaluator
description: >
  Use when the user wants feedback on English exam writing (IELTS Task 1/2,
  TOEFL email, academic-discussion, and build-a-sentence tasks, B1–C2 essays,
  emails, letters, articles, reports, reviews, proposals) or wants an original
  writing prompt in a specific exam format. Evaluates against paraphrased
  public CEFR descriptors and the exam's criteria structure; returns a
  band/score estimate as a range, a CEFR level, and prioritized rewrites
  drawn from the user's own text. Logs every scored attempt.
---

# Writing Evaluator

Generates original writing prompts and evaluates responses. Paths are
relative to `${CLAUDE_PLUGIN_ROOT}` (if unset, resolve relative to the plugin
root — the directory two levels up from this file, i.e. the folder containing
`data/` and `skills/`).

## When to use

The user pasted a piece of writing for assessment, OR asked for a practice
writing task in a named exam format, OR asked how to improve exam writing.

## Steps

1. **Identify** exam + level + task type. If unclear, ask once.
   **When EVALUATING pasted writing, also obtain the exact task prompt as it
   was set** — the IELTS question, the two given points for a B2 essay, the
   TOEFL email's three content points, the letter's bullets — plus whether it
   was written timed and in how long. Task fulfilment (were the required
   points covered, right genre, word count) is the first-ranked criterion and
   caps the band; without the prompt, say so and mark Task Achievement
   provisionally rather than guessing. Load:
   - `data/exam-formats/<exam-id>.md` (format, word count, timing, criteria names)
   - `data/cefr/writing-descriptors.md` (assessment anchors)
   - `data/cefr/calibration-anchors.md` (leveled reference samples)
   - `skills/writing-evaluator/references/task-anatomy.md` (structure and
     register expectations per task type)

2. **If GENERATING a prompt:** produce an ORIGINAL prompt matching the
   format's structure, word count and timing (seed examples:
   `data/item-bank/seed/writing-prompts.md` — imitate shape, never reuse
   content). **Pitch the prompt's cognitive/topic demand to the level**, not
   just its length: B1 concrete/personal; B2 a familiar issue to take a stance
   on; C1 abstract, requiring evaluation/weighing; C2 nuanced or
   counter-intuitive. (`calibration-anchors.md` shows what an at-level *answer*
   looks like — aim the prompt so a level-appropriate answer lands there.)
   State the time limit and word target. Offer to time the attempt: note the
   start time, and compute elapsed seconds when the answer arrives.

3. **If EVALUATING:** assess against that exam's criteria structure (e.g.
   Task Achievement/Response, Coherence & Cohesion, Lexical Resource,
   Grammatical Range & Accuracy for IELTS; content, communicative
   achievement, organisation, language for the B1–C2 exams; development,
   organisation, language use for TOEFL), anchored in the paraphrased CEFR
   descriptors. Check task-specific requirements first: word count, all
   content points covered, register, format conventions (greeting/sign-off,
   headings for reports/proposals). Then CALIBRATE before fixing the range:
   compare the text with the leveled samples in
   `data/cefr/calibration-anchors.md` and pick the nearest anchor per
   criterion — criteria may land on different levels (say so if they do).
   Never show anchor texts to the user as model answers.

4. **Return, in this order:**
   - (a) estimate as a RANGE (e.g. "IELTS ~6.5–7.0", "on track for a C1
     pass") plus the normalized CEFR level;
   - (b) 3–5 prioritized fixes, each shown as *your sentence → improved
     sentence* using the user's own text;
   - (c) one model upgrade: a single paragraph rewritten at the next level up,
     with a one-line explanation of what changed. If the writing is already at
     C2 (the ceiling), instead sharpen a paragraph WITHIN C2 — tightening
     precision, idiom and economy toward the top of the band — and note there
     is no higher CEFR level.

5. **Log the attempt** (silently, right after scoring):
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/progress-tracker/scripts/log_attempt.py" \
     --exam <exam-id> --skill writing-evaluator --task-type <slug> \
     --level <target-level> --band-estimate "<low>-<high>" --cefr-estimate <cefr> \
     --seconds <time-on-task>
   ```
   (On Windows, if `python3` isn't found, run the same command with `python`
   or `py`.)
   **`--level` is the task's TARGET level from step 1** (e.g. C1 for a cefr-c1
   essay; the exam's anchor for IELTS/TOEFL) — NOT the level the writing landed
   at. The calibrated performance goes ONLY in `--cefr-estimate`. Confusing the
   two collapses the report's attainment and weakest-task signal.
   Use the exact `--task-type` slug from `data/task-types.md`.
   Use `--band-estimate` (a range) for holistic band/CEFR judgements — IELTS,
   TOEFL and the Cambridge B1–C2 essays — where a single number would be false
   precision. Use `--score`/`--max` only for objective item counts (e.g. the
   TOEFL Build a Sentence task, `--max 10`).
   If time on task is unknown, ask the user — never substitute the task's
   nominal time limit, which would corrupt the "min on task" totals.

**TOEFL Build a Sentence** is objective, not band-scored: present the 10
scrambled items, mark each correct/incorrect, and log with
`--task-type toefl-build-a-sentence --score <n> --max 10`.

## Boundaries

- **If the response is not in English** (or mixes in substantial non-English
  text), do not score it as an English attempt: flag the language, explain
  that off-language content earns nothing on the real exam, and ask for an
  English version before evaluating or logging.
- **If the writing is clearly below B1** (the descriptors and calibration
  anchors floor at B1): say so explicitly rather than snapping it up to the B1
  anchor, give concrete B1 targets to aim for instead of a false in-range
  band, and log `--cefr-estimate A2` (or `A1`) while keeping the task's target
  `--level` unchanged.
- Do NOT reproduce official rubrics, past papers, or answer keys; criteria
  names may be used, official descriptor text may not.
- Descriptors are paraphrased from the public CEFR framework only.
- Estimates are ranges and indicative, never official assessment.
- Never log an attempt the user didn't actually make.
