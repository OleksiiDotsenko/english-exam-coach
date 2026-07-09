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
   its questions. Show the questions FIRST — real tests give preview time —
   and keep the script hidden.

3. **Deliver the audio, best available mode:**
   - **TTS (optional, macOS):** if the `say` command exists
     (`command -v say`), write the script to a temp file and play it once at
     natural speed, e.g.
     `say -f script.txt` (or `say -o audio.aiff -f script.txt && afplay audio.aiff`).
     Vary voices per speaker with `-v` when available.
   - **User-side audio:** the user has any TTS or a practice partner → give
     them the script to synthesize/have read aloud, listening only once.
   - **Fallback (always works):** timed read-once — reveal the script,
     instruct the user to read it once at natural pace without scrolling
     back, then hide-and-answer. Say plainly this trains reading-listening
     hybrid comprehension, not pure listening.

4. **Score and explain:** one mark per item; quote the exact script line
   that decides each answer; point out the distractor trap where relevant
   (paraphrase vs. echo, corrected information, speaker attitude).

5. **User-provided audio/transcript mode:** build exam-format questions on
   their material (get the transcript from them or from their tool), then
   score as above. Set `--task-type` to the matching exam question type.

6. **Log the attempt** (silently):
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/progress-tracker/scripts/log_attempt.py" \
     --exam <exam-id> --skill listening-trainer --task-type <task-type> \
     --level <anchor> --score <n> --max <total> --seconds <time>
   ```

## Boundaries

- Scripts and questions must be original; for user-provided material, quote
  only what the user supplied, and only for their private practice.
- TTS is strictly optional — every drill must work with no audio stack; when
  falling back to read-once mode, state the limitation instead of
  pretending it measures listening.
- Scores are indicative practice results, not official marks.
