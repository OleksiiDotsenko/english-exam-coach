# Listening

Read this when the user asks to drill listening, or brings their own audio
or transcript and wants exam-style questions on it. `coach <command>` and
the helper `speak.py` are defined in `SKILL.md`; the helper is run as
`python3 ${CLAUDE_SKILL_DIR}/scripts/speak.py` and written here by name.

## Steps

1. **Identify** exam + level + part. Load `data/exam-formats/<exam-id>.md`
   for the part's shape (speakers, question count, question types). Seed
   shapes: `data/item-bank/seed/listening-scripts.md`.

2. **Generate an ORIGINAL script** (a dialogue or a monologue, as the part
   requires) and its questions.
   **Whether the learner sees the questions first depends on the exam:**
   IELTS and the B1–C2 exams give time to read the questions before the
   recording, so show them first. **TOEFL iBT does not** — the questions
   come after the recording — so for TOEFL keep them hidden until playback
   ends. Keep the script hidden until the drill is scored.
   **Match the script to the recording's real length**: speech runs at
   about 130–160 words a minute, so a 4-minute monologue or interview is
   ~550–650 words and a short 30–40 second exchange ~80–110. A script that
   is too short makes the drill easier than the real test. **Count the
   script mechanically before delivering it** — write it to a temporary
   file and run `wc -w`; a self-estimated count is the failure this guards
   against.

3. **Set the number of plays from the exam.** IELTS and TOEFL iBT play each
   recording **once**; the B1–C2 exams play each recording **twice** (their
   format files say so). Honour that in every mode below.

4. **Deliver the audio, best available mode.**

   **A. The computer's own voice** — when `speak.py check` succeeds (a
   session on the user's own Mac or Linux machine with a speaker):
   ```bash
   speak.py render --file script.txt     # prints the audio folder
   speak.py play <folder> --plays <1|2>  # the whole script, in order
   speak.py clean <folder>               # when the drill is over
   ```
   Write the script as plain lines, `Woman: …` / `Man: …` /
   `Professor: …`; each speaker gets a voice of their own, and a script
   pasted with its Markdown quote marks and bold labels is read correctly.
   A line with no label continues the turn above it. Render first, play
   afterwards: synthesis takes a moment, and that moment must not become
   thinking time. `--rate 140` slows it for B1; the default is a natural
   160 words a minute. Playing blocks until the recording ends, so give the
   command a time limit longer than the audio.

   **Separate short prompts** (TOEFL Listen and Choose a Response): put one
   prompt per line, render once, then play **one item at a time** with
   `speak.py play <folder> --item <n>`, collecting the answer after each
   and never replaying. The four options are shown on screen, not spoken.

   **B. The learner's own audio.** They have a text-to-speech tool or a
   study partner: give them the script to be read aloud, for the exam's
   number of plays, without looking at it themselves.

   **C. Read-once fallback** (always works): reveal the script, ask the
   learner to read it through — once for IELTS and TOEFL, twice for the
   B1–C2 exams — at a natural pace without going back, then hide it and
   answer. Say plainly that this trains a reading-listening hybrid, not
   pure listening.

   `speak.py` exits with status 3 where there is no synthesiser or no sound
   device (a cloud session, Windows): go straight to B or C.

5. **Score and explain:** one mark per item; quote the exact script line
   that decides each answer; point out the trap where there is one
   (paraphrase against echo, corrected information, the speaker's
   attitude).

6. **User-provided audio or transcript:** build exam-format questions on
   their material (get the transcript from them or from their own tool),
   then score as above. Set `--task-type` to the matching exam question
   type.

7. **Log the attempt** (silently):
   ```bash
   coach log-attempt \
     --exam <exam-id> --skill listening-trainer --task-type <slug> \
     --level <anchor> --score <n> --max <total> --seconds <time>
   ```
   For each missed item, also log why with `coach log-error` — a
   `comprehension` tag from `data/error-taxonomy.md` and a re-testable
   `--point`, such as "misses numbers said as 'fifteen' against 'fifty'" —
   then run `coach queue sync`. See `references/the-loop.md`.

## TOEFL iBT listening (2026 format)

Every recording plays once, each question has its own clock, and the learner
**cannot go back** to an earlier question — present and collect one question
at a time, and do not let an answer be changed afterwards.

| Task | Script | Questions |
|---|---|---|
| Listen and Choose a Response | one short utterance — a question or a remark, a few seconds long | pick the best reply from 4 printed options |
| Listen to a Conversation | two speakers, about 35–100 words; everyday, workplace or campus | 2 |
| Listen to an Announcement | one speaker, classroom or campus, about 35–100 words | 2 |
| Listen to an Academic Talk | one speaker, a short lecture or a podcast-style talk, up to 250 words | 4 |

In the official practice test a module opens with 8 Choose-a-Response
items, then one or two conversations, an announcement and a talk — 16 to 18
questions. Build a mock module in that shape.

**Choose a Response** tests the function of what was said, not its words.
Each wrong option should fail in a different way: one echoes words from the
prompt but ignores what it was for; one answers a question that was not
asked; one is on the topic but beside the point; one contradicts what the
prompt implied. Typical traps worth building in: a negative question
("Didn't you…?"), "Would you mind…?", an indirect request, a remark that
needs a response rather than an answer. Shuffle the options — the key must
not sit in the same place every time.

Conversation and talk questions ask for the gist or purpose, a detail, what
a speaker implies or means by a phrase, why they mention something, and
what will happen next. All have four options.

## Boundaries

- Scripts and questions must be original; for user-provided material, quote
  only what the user supplied, and only for their private practice.
- Audio is optional — every drill must work with no sound at all; when
  falling back to read-once mode, state the limitation instead of
  pretending it measures listening.
- **Never invent a transcript or claim to have heard audio you cannot
  access.** If a user-supplied audio file cannot be transcribed here, ask
  for a transcript.
- **Formats that depend on a picture cannot be delivered here.** IELTS map,
  plan and diagram labelling and B1 Preliminary Listening Part 1
  picture-choice need images — say so and offer a non-visual part of the
  same exam instead of faking one.
- Partial answers: score against what was actually attempted; if the user
  stopped early, do not count unseen items as wrong. Never fabricate
  answers.
- Scores are indicative practice results, not official marks.
