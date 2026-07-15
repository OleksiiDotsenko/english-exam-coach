---
name: listening-trainer
description: >
  Use when the user wants to practice English exam listening (IELTS parts
  1-4, TOEFL iBT conversations, announcements, academic talks and
  listen-and-choose-a-response items, B1-C2 listening parts).
  Generates an original script with exam-format questions, delivers it as
  audio when a local TTS is available (macOS `say`) or as a
  read-once/partner-read script otherwise, scores answers, explains them
  with script evidence, and logs the attempt. Also builds questions for
  user-provided audio or transcripts (podcasts, lectures).
---

# Listening Trainer

Text-first listening practice with optional zero-dependency TTS. Paths are
relative to `${CLAUDE_PLUGIN_ROOT}` (if unset, resolve relative to this file).

## When to use

The user asks to drill listening, or brings their own audio/transcript and
wants exam-style questions on it.

## Steps

1. **Identify** exam + level + part. Load `data/exam-formats/<exam-id>.md`
   for the part's shape (speakers, question count, question types). Seed
   shapes: `data/item-bank/seed/listening-scripts.md`.

2. **Generate an ORIGINAL script** (dialogue or monologue per the part) and
   its questions. **Preview timing is exam-conditional:** IELTS and the CEFR
   B1–C2 (Cambridge) exams give time to read the questions before the audio,
   so show the questions first; **TOEFL iBT does not** — the questions come
   after the recording (listen/take notes → then answer), so for TOEFL keep
   the questions hidden until playback ends. Keep the script hidden until the
   drill is scored. **Match the script to the recording's real
   duration**: a spoken passage runs ~130–160 words per minute, so a ~4-min
   monologue/interview is ~550–650 words and a short 30–40 s exchange is
   ~80–110 words. A script that is too short makes the drill easier than the
   real test.

3. **Deliver the audio, best available mode.** First, set the **number of
   plays from the exam**: IELTS and TOEFL iBT play each recording **once**;
   the CEFR B1–C2 (Cambridge) exams play each recording **twice** (their
   format files say so). Honor that count in every mode below — "once"
   means once for IELTS/TOEFL and twice for `cefr-b1`…`cefr-c2`.
   - **TTS (optional, macOS):** if the `say` command exists
     (`command -v say`), write the script to a temp file and play it at
     natural speed for the exam's number of plays, e.g.
     `say -f script.txt` (or `say -o audio.aiff -f script.txt && afplay audio.aiff`).
     Vary voices per speaker with `-v` when available.
   - **User-side audio:** the user has any TTS or a practice partner → give
     them the script to synthesize/have read aloud, for the exam's number of
     plays.
   - **Fallback (always works):** timed read-through — reveal the script,
     instruct the user to read it (once for IELTS/TOEFL, twice for the CEFR
     exams) at natural pace without scrolling back, then hide-and-answer.
     Say plainly this trains reading-listening hybrid comprehension, not
     pure listening.

4. **Score and explain:** one mark per item; quote the exact script line
   that decides each answer; point out the distractor trap where relevant
   (paraphrase vs. echo, corrected information, speaker attitude).

5. **User-provided audio/transcript mode:** build exam-format questions on
   their material (get the transcript from them or from their tool), then
   score as above. Set `--task-type` to the matching exam question type.

6. **Log the attempt** (silently):
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/progress-tracker/scripts/log_attempt.py" \
     --exam <exam-id> --skill listening-trainer --task-type <slug> \
     --level <anchor> --score <n> --max <total> --seconds <time>
   ```
   Use the exact `--task-type` slug from `data/task-types.md`.

## Boundaries

- Scripts and questions must be original; for user-provided material, quote
  only what the user supplied, and only for their private practice.
- TTS is strictly optional — every drill must work with no audio stack; when
  falling back to read-once mode, state the limitation instead of
  pretending it measures listening.
- **Never invent a transcript or claim to have heard audio you cannot
  access:** if a user-supplied audio file cannot be transcribed in this
  environment, ask for a transcript instead of fabricating one.
- **Visual-dependent formats can't be delivered here.** IELTS Part 2
  map/plan/diagram labelling and B1 Preliminary Listening Part 1
  picture-choice need images the terminal can't render — say so and offer a
  non-visual part of the same exam instead of faking it.
- Partial answers: score against what was actually attempted; if the user
  stopped early, don't count unseen items as wrong (mirror the reading
  trainer's rule). Never fabricate answers.
- Scores are indicative practice results, not official marks.
