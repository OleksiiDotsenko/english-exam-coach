---
name: speaking-coach
description: >
  Use when the user wants to practice English exam speaking (IELTS Parts 1-3,
  TOEFL iBT speaking tasks, B1-C2 interview/long turn/collaborative tasks),
  wants a speaking prompt or cue card, or wants feedback on a spoken answer
  provided as a transcript, self-recording description, or audio file.
  Generates original tasks in the exam's format with real timings and gives
  criteria-based feedback (fluency, coherence, lexis, grammar,
  pronunciation) with a range estimate and CEFR level. Logs every scored
  attempt.
---

# Speaking Coach

Terminal-friendly speaking practice: **record or perform → transcribe →
evaluate**. Paths are relative to `${CLAUDE_PLUGIN_ROOT}` (if unset, resolve
relative to the plugin root — the directory two levels above this file,
`.../plugins/english-exam-coach`).

## When to use

The user wants a speaking task, mock speaking interview, or feedback on an
answer they spoke (pasted as transcript or provided as an audio file).

## Steps

1. **Identify** exam + level + part. Load `data/exam-formats/<exam-id>.md`,
   `data/cefr/speaking-descriptors.md`, and
   `data/cefr/speaking-calibration-anchors.md` (leveled transcript samples).
   Seed shapes: `data/item-bank/seed/speaking-tasks.md` (imitate format,
   never reuse).

2. **Generate the task** with the exam's real prep/speaking times (e.g.
   IELTS Part 2: 1 min prep, 1–2 min talk; TOEFL interview answers: 45 s
   each with no preparation time). **Pitch the prompt's demand to the level**
   (B1 concrete/personal; B2 opinion on a familiar topic; C1 abstract, asks
   the speaker to weigh/hypothesise; C2 nuanced) — `speaking-calibration-
   anchors.md` shows an at-level answer to aim the prompt at. Visual-dependent
   tasks (Cambridge B1 Part 2 describe-a-photo; B2 First / C1 Advanced Part 2
   compare-photographs; C2 Part 2 picture discussion) can't be rendered here;
   say so and offer a non-visual part instead of faking it. IELTS Speaking uses
   no visual prompts — its Part 2 is a text cue card and IS fully renderable.
   Tell the user how to respond, in order of preference:
   - **record themselves** (any voice recorder) and paste an accurate
     transcript, noting hesitations/self-corrections honestly;
   - or speak first and then type from memory (say that this loses fluency
     information);
   - for a paired-format task (collaborative discussion), play the partner:
     alternate short turns with the user in chat.

   **TOEFL Listen and Repeat** (7 of the 11 TOEFL speaking items) works
   differently: deliver each sentence once via `say` when available (else
   read it once as a partner), have the user repeat it from memory and type
   what they said, and score each sentence on exactness — content words, word
   order, grammatical endings. Report the sentence length at which recall
   broke down; that breakdown point is itself the diagnostic. Log with
   `--task-type toefl-listen-and-repeat --score <n> --max 7`.

3. **Evaluate the transcript** against the five paraphrased CEFR aspects
   (range, accuracy, fluency, interaction, coherence) and the exam's
   criteria structure. Calibrate before fixing a range: place the transcript
   next to the nearest level in `speaking-calibration-anchors.md` per aspect
   (aspects may land on different levels — say so). The anchors start at B1: if
   the transcript sits clearly below the B1 anchor on most aspects, report it as
   below B1 (approx. A1/A2) rather than snapping up to B1, and log `--level` /
   `--cefr-estimate` as A1 or A2 accordingly. From text alone, fluency
   and pronunciation are only partly observable — judge fluency from
   fillers/self-corrections if the transcript preserves them, and say so;
   only comment on pronunciation the user asks about or reports ("I struggle
   with th-").

4. **Return:** (a) estimate as a range + CEFR level; (b) 3–5 prioritized
   fixes with *your phrase → stronger phrase* rewrites from the user's own
   answer; (c) one upgraded model answer fragment (2–3 sentences, next level
   up); (d) one follow-up question to re-drill the weakest point now.

5. **Log the attempt** (silently):
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/progress-tracker/scripts/log_attempt.py" \
     --exam <exam-id> --skill speaking-coach --task-type <slug> \
     --level <anchor> --band-estimate "<low>-<high>" --cefr-estimate <cefr> \
     --seconds <time-on-task>
   ```
   On Windows, if `python3` isn't found, use `python` or `py` instead.
   Use the exact `--task-type` slug from `data/task-types.md`.
   For TOEFL estimate the 1–6 band scale: `--score <band> --max 6`
   (half bands allowed; official CEFR alignment: 4 ≈ B2, 5 ≈ C1, 6 = C2).

## Boundaries

- Never claim to hear audio you cannot access; if an audio file is provided
  and cannot be transcribed in this environment, ask for a transcript
  instead of inventing one.
- Descriptors are paraphrased public CEFR only; no official rubrics.
- Estimates are indicative ranges, never official scores.
- Do not log attempts the user didn't make.
