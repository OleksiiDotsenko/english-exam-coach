---
name: writing-evaluator
description: >
  Use when the user wants feedback on English exam writing (IELTS Task 1/2,
  TOEFL email and academic-discussion tasks, B1–C2 essays, emails,
  letters, articles, reports, reviews, proposals) or wants an original
  writing prompt in a specific exam format. Evaluates against paraphrased
  public CEFR descriptors and the exam's criteria structure; returns a
  band/score estimate as a range, a CEFR level, and prioritized rewrites
  drawn from the user's own text. Logs every scored attempt.
---

# Writing Evaluator

Generates original writing prompts and evaluates responses. Paths are
relative to `${CLAUDE_PLUGIN_ROOT}` (if unset, resolve relative to this file).

## When to use

The user pasted a piece of writing for assessment, OR asked for a practice
writing task in a named exam format, OR asked how to improve exam writing.

## Steps

1. **Identify** exam + level + task type. If unclear, ask once. Load:
   - `data/exam-formats/<exam-id>.md` (format, word count, timing, criteria names)
   - `data/cefr/writing-descriptors.md` (assessment anchors)
   - `data/cefr/calibration-anchors.md` (leveled reference samples)
   - `skills/writing-evaluator/references/task-anatomy.md` (structure and
     register expectations per task type)

2. **If GENERATING a prompt:** produce an ORIGINAL prompt matching the
   format's structure, word count and timing (seed examples:
   `data/item-bank/seed/writing-prompts.md` — imitate shape, never reuse
   content). State the time limit and word target. Offer to time the attempt:
   note the start time, and compute elapsed seconds when the answer arrives.

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
     with a one-line explanation of what changed.

5. **Log the attempt** (silently, right after scoring):
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/progress-tracker/scripts/log_attempt.py" \
     --exam <exam-id> --skill writing-evaluator --task-type <task-type> \
     --level <anchor> --band-estimate "<low>-<high>" --cefr-estimate <cefr> \
     --seconds <time-on-task>
   ```
   Use `--score`/`--max` instead of `--band-estimate` only when the exam
   truly uses a numeric scale for the task (e.g. TOEFL: `--score 4.5
   --max 6` on the 1–6 band scale).
   If time on task is unknown, ask or use the task's standard timing.

## Boundaries

- Do NOT reproduce official rubrics, past papers, or answer keys; criteria
  names may be used, official descriptor text may not.
- Descriptors are paraphrased from the public CEFR framework only.
- Estimates are ranges and indicative, never official assessment.
- Never log an attempt the user didn't actually make.
