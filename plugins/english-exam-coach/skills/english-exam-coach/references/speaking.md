# Speaking — tasks, timing and feedback

Read this when the user wants a speaking task, a mock speaking interview, or
feedback on an answer they spoke. The cycle is **perform under the clock →
get the words down → evaluate**. `coach <command>` and the three helper
scripts (`speak.py`, `timed_speak.py`, `transcribe.py`) are defined in
`SKILL.md`; the helpers are run as
`python3 ${CLAUDE_SKILL_DIR}/scripts/<name>.py` and written here by name.

## Steps

1. **Identify** exam + level + part. Load `data/exam-formats/<exam-id>.md`,
   `data/cefr/speaking-descriptors.md` and
   `data/cefr/speaking-calibration-anchors.md` (levelled transcript
   samples). Seed shapes: `data/item-bank/seed/speaking-tasks.md` (imitate
   the format, never reuse).

2. **Generate the task** with the exam's real preparation and speaking times
   (IELTS Part 2: 1 min to prepare, 1–2 min to talk; TOEFL: no preparation
   time at all). **Pitch the prompt's demand to the level** (B1 concrete and
   personal; B2 an opinion on a familiar topic; C1 abstract, asks the
   speaker to weigh or hypothesise; C2 nuanced) —
   `speaking-calibration-anchors.md` shows an at-level answer to aim at.
   Tasks that depend on a picture (B1 Part 2 describe-a-photo; B2 First and
   C1 Advanced Part 2 compare-photographs; C2 Part 2 picture discussion)
   cannot be rendered here: say so and offer a non-visual part instead of
   faking one. IELTS Speaking uses no pictures — its Part 2 is a text cue
   card and IS fully renderable.

3. **Decide how the answer will reach you**, best evidence first, and tell
   the learner before they start:
   - **A recording.** They record themselves with any recorder (a phone, a
     voice-memo app) and give you the file. If `transcribe.py check`
     succeeds, run `transcribe.py <file>`: you get the transcript plus what
     a typed transcript loses — pace, the delay before starting, long
     pauses. Show the learner the transcript and let them correct it before
     you judge accuracy: a recogniser drops many fillers and quietly repairs
     small slips. Log `--evidence-grade full`.
   - **Their own transcript of a recording**, with hesitations and
     self-corrections left in honestly. Also `full`.
   - **Typed from memory** after speaking. Say that this keeps the content
     and loses the delivery; log `--evidence-grade partial`.
   - **A paired task** (collaborative discussion): play the partner,
     alternating short turns in the chat.

   Never claim to have heard audio. If a file cannot be transcribed here
   (`transcribe.py` exits with status 3), ask for a transcript — do not
   invent one.

4. **Run the real clock.** Answering "when ready" removes the constraint the
   task is built around. On the user's own computer:
   ```bash
   timed_speak.py --exam <exam-id> --task <slug>
   ```
   It signals each transition and prints the seconds to log with
   `--timing-source script`. It blocks for the whole task, so give the
   command a time limit longer than the task. Where the learner cannot hear
   the machine (a cloud session), ask them to use a timer of their own and
   log what they report as `--timing-source self-reported`.

5. **Evaluate the transcript** against the five paraphrased CEFR aspects
   (range, accuracy, fluency, interaction, coherence) and the exam's
   criteria. Calibrate before fixing a range: place the transcript next to
   the nearest level in `speaking-calibration-anchors.md` per aspect
   (aspects may land on different levels — say so). The anchors start at
   B1: if the transcript sits clearly below the B1 anchor on most aspects,
   report it as below B1 (about A1/A2) rather than snapping it up, and log
   `--cefr-estimate A1` or `A2`. From text alone, fluency and pronunciation
   are only partly observable — judge fluency from the timing figures, or
   from fillers and self-corrections if the transcript preserves them, and
   say which. Comment on pronunciation only when the user asks or reports a
   difficulty ("I struggle with th-"); never score it.

6. **Return:** (a) the estimate as a range + CEFR level; (b) 3–5 prioritised
   fixes with *your phrase → stronger phrase* rewrites from the user's own
   answer; (c) one upgraded model fragment (2–3 sentences, next level up);
   (d) one follow-up question to re-drill the weakest point now.

7. **Log the attempt** (silently):
   ```bash
   coach log-attempt \
     --exam <exam-id> --skill speaking-coach --task-type <slug> \
     --level <anchor> --band-estimate "<low>-<high>" --cefr-estimate <cefr> \
     --seconds <time-on-task> --criteria "fluency=B2,lexis=B2,grammar=B1,..." \
     --evidence-grade <full|partial> --timing-source <script|self-reported>
   ```
   For a TOEFL interview the band estimate is on the 1–6 scale (half bands
   allowed; 4 ≈ B2, 5 ≈ C1, 6 = C2). Then log 2–5 mistakes with `coach
   log-error`, run `coach queue sync`, and offer a second attempt at the
   same task, reporting the change per aspect. Full protocol:
   `references/the-loop.md`.

## TOEFL Listen and Repeat

Seven sentences, **one scenario, one speaker**, each heard once and repeated
at once. The scenario line gives the learner a role and says who is
speaking; it is read first and not repeated. Lengths grow loosely from a
short clause of 5–7 words to sentences of 11–14 words — never into the high
teens. Worked example: `data/item-bank/seed/speaking-tasks.md`.

**With sound** (`speak.py check` succeeds):

1. Write the seven sentences to a file, one per line, and render them:
   `speak.py render --file sentences.txt --one-voice` — it prints the audio
   folder.
2. Show the scenario line. Then either
   - run the whole task hands-free:
     `timed_speak.py --task toefl-listen-and-repeat --audio <folder>` plays
     each sentence once and gives a short window after each. The learner
     records the run on their own device, or
   - go one at a time: `speak.py play <folder> --item <n>`, the learner
     repeats aloud and types what they said, then the next item. Never
     replay an item.
3. Get what was said: a recording (`transcribe.py`), or the typed lines —
   one line per sentence, `-` for one they could not repeat.
4. Mark it: `coach repeat --audio <folder> --said said.txt`. It reports, per
   sentence, the words dropped, changed and added, how many were repeated
   exactly, and the first sentence that broke down — that length is the
   diagnosis.
5. `speak.py clean <folder>`.

**Without sound:** the task cannot be done honestly from text the learner
can see. Give the sentences to a study partner or any text-to-speech tool
of their own to read out once each, collect what they repeated, and mark it
with `coach repeat --targets sentences.txt --said said.txt`. Say plainly
that reading a sentence and typing it back is not this task.

Log with `--task-type toefl-listen-and-repeat --score <sentences repeated
exactly> --max 7`, and log the pattern behind the misses as points — for
example `delivery/repetition`: "drops articles when a sentence passes ten
words". The exam itself scores each sentence 0–5 and also weighs how
intelligible it was; a word count cannot see that, so do not present it as
the exam score.

## TOEFL Take an Interview

One interviewer, **ONE everyday topic, opened by a short scenario**, four
questions, no preparation time. After the first, **every question comes with
a lead-in of one to three sentences**, so each interviewer turn runs about
35–60 words; a list of four one-line questions is the wrong shape. The turns
climb: a factual question about the learner → their own reaction and why →
agree or disagree with a view the interviewer states → their opinion on a
policy or proposal. Worked example: `data/item-bank/seed/speaking-tasks.md`.

**The learner must not see the next question before answering this one** —
in the exam each is heard once, then answered straight away.

**With sound:** write the four interviewer turns to a file, one per line,
render them with `speak.py render --file turns.txt --one-voice`, show the
scenario, then run `timed_speak.py --task toefl-take-an-interview --audio
<folder>`: it plays each turn, signals, and gives about 45 seconds to
answer. The learner records the whole run and you transcribe it; or go turn
by turn with `speak.py play <folder> --item <n>` followed by `timed_speak.py
--answer 45 --items 1`, collecting each answer before the next turn.

**Without sound:** show ONE turn at a time, have the learner answer aloud
against their own 45-second timer and then type or paste what they said,
and only then show the next turn.

About 45 seconds is roughly 90–130 words at a natural pace — five to eight
sentences. Far less reads as underdeveloped; running past the clock gets cut
off, which costs more than stopping early. Evaluate each answer, then the
four together; log one attempt with `--task-type toefl-take-an-interview`
and a band estimate on the 1–6 scale.

## Boundaries

- Never claim to hear audio you cannot access, and never invent a
  transcript.
- No pronunciation scoring.
- Descriptors are paraphrased public CEFR only; no official rubrics.
- Estimates are indicative ranges, never official scores.
- Do not log attempts the user did not make.
