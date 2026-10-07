# Writing — prompts and feedback

Read this when the user pastes a piece of writing for assessment, asks for a
practice writing task in a named exam format, or asks how to improve their
exam writing. `coach <command>` is defined in `SKILL.md`.

## Steps

1. **Identify** exam + level + task type. If unclear, ask once.
   **When EVALUATING pasted writing, also get the exact task prompt as it
   was set** — the IELTS question, the two given points for a B2 essay, the
   TOEFL email's three bullets, the letter's bullets — plus whether it was
   written timed and in how long. Task fulfilment (were the required points
   covered, right genre, word count) is the first-ranked criterion and caps
   the band; without the prompt, say so and mark task achievement
   provisionally rather than guessing. Load:
   - `data/exam-formats/<exam-id>.md` (format, word count, timing, criteria)
   - `data/cefr/writing-descriptors.md` (assessment anchors)
   - `data/cefr/calibration-anchors.md` (levelled reference samples)
   - `references/task-anatomy.md` (structure and register per task type)

2. **If GENERATING a prompt:** produce an ORIGINAL prompt matching the
   format's structure, word count and timing (seed examples:
   `data/item-bank/seed/writing-prompts.md` — imitate the shape, never reuse
   the content). **Pitch the prompt's cognitive and topic demand to the
   level**, not just its length: B1 concrete and personal; B2 a familiar
   issue to take a stance on; C1 abstract, requiring evaluation and
   weighing; C2 nuanced or counter-intuitive. (`calibration-anchors.md`
   shows what an at-level *answer* looks like — aim the prompt so a
   level-appropriate answer lands there.) State the time limit and word
   target. Offer to time the attempt: note the start time, and compute the
   elapsed seconds when the answer arrives.

   The two TOEFL written tasks have a fixed layout — follow the seed:
   - **Write an Email** (7 min): a situation in two or three sentences, who
     to write to, **three bullets** that each ask for a different thing, and
     the To and Subject lines already filled in. No word count is set.
   - **Write for an Academic Discussion** (10 min): a professor's post of
     about 60–80 words ending in a question, and two students' posts of
     about 40–50 words taking **different sides**. A good answer has at
     least 100 words.

3. **If EVALUATING:** assess against that exam's criteria structure (Task
   Achievement/Response, Coherence & Cohesion, Lexical Resource, Grammatical
   Range & Accuracy for IELTS; content, communicative achievement,
   organisation, language for the B1–C2 exams; development, organisation,
   language use for TOEFL), anchored in the paraphrased CEFR descriptors.
   Check task-specific requirements first: word count, all content points
   covered, register, format conventions (greeting and sign-off, headings
   for reports and proposals). Then CALIBRATE before fixing the range:
   compare the text with the levelled samples in
   `data/cefr/calibration-anchors.md` and pick the nearest anchor per
   criterion — criteria may land on different levels (say so if they do).
   Never show anchor texts to the user as model answers.
   **Judge in two passes** (`references/the-loop.md` §1): first quote 3–6
   concrete features of the response with no level attached, then place them
   against the anchors and argue the opposite case once before fixing the
   range. Naming a level first turns everything after it into confirmation.

4. **Return, in this order:**
   - (a) the estimate as a RANGE ("IELTS ~6.5–7.0", "on track for a C1
     pass") plus the CEFR level;
   - (b) 3–5 prioritised fixes, each shown as *your sentence → improved
     sentence* using the user's own text;
   - (c) one model upgrade: a single paragraph rewritten at the next level
     up, with a one-line explanation of what changed. If the writing is
     already at C2 (the ceiling), sharpen a paragraph WITHIN C2 instead —
     tighter precision, idiom and economy — and note there is no higher
     CEFR level.

5. **Log the attempt** (silently, right after scoring):
   ```bash
   coach log-attempt \
     --exam <exam-id> --skill writing-evaluator --task-type <slug> \
     --level <target-level> --band-estimate "<low>-<high>" --cefr-estimate <cefr> \
     --seconds <time-on-task> \
     --criteria "<criterion>=<CEFR>,..." --evidence-grade full \
     --timing-source <wall-clock|self-reported>
   ```
   `--criteria` carries the per-criterion levels you just judged, using the
   exam's own criterion names — it is what lets the report say *which*
   criterion is holding the band down.
   **`--level` is the task's TARGET level from step 1** (C1 for a `cefr-c1`
   essay; the exam's anchor for IELTS and TOEFL) — NOT the level the writing
   landed at. The calibrated performance goes ONLY in `--cefr-estimate`.
   Use `--band-estimate` (a range) for holistic judgements — IELTS, TOEFL
   and the B1–C2 written tasks — where a single number would be false
   precision. Use `--score`/`--max` only for objective counts (TOEFL Build a
   Sentence, `--max 10`). If the time on task is unknown, ask the user;
   never substitute the task's nominal time limit.

6. **Record the mistakes, then offer a second draft.** Log 2–5 specific
   errors with `coach log-error` (tags from `data/error-taxonomy.md`;
   `--point` must name something a fresh item can re-test), run `coach queue
   sync`, then offer a revision of the *same* task. Judge the revision
   against the same criteria, report the delta per criterion, and log it
   with `--draft 2`. Say plainly when a criterion did not move. Full
   protocol: `references/the-loop.md`.

## TOEFL Build a Sentence

Objective, not band-scored, and **built by script, never by hand**.

**Every item is two sentences:** the learner reads one complete sentence — a
question, a piece of news, a plan — and builds the reply to it from tiles.
An item with no first sentence is the wrong task.

1. Write ten pairs: the first sentence and the reply. Mark the reply's tiles
   with `|`, anything already printed in the frame with `[ ]`, and end it
   with its full stop or question mark:
   `"do | you | know | if | [we can] | hand in | the report | on Monday ?"`
2. Keep to the real shape (the script enforces the first of these): **5 to 7
   tiles**; most replies are questions, often indirect ones; two or three
   items in ten carry **one** extra tile that is not used (`--distractor`),
   typically the wrong form of a word that is used.
3. Make the key unique: try to build a different correct sentence from the
   same tiles. A movable time or place phrase is the usual culprit — print
   it in the frame with `[ ]`. If two orders really are both right, pass the
   second with `also`.
4. Save the pairs as a JSON list and run `coach sentence make --batch
   set.json`. Show the learner the part under "SHOW THE LEARNER", exactly as
   printed; keep the key back.
5. Mark with `coach sentence check --batch set.json --responses
   answers.txt` (one sentence per line). It is all-or-nothing per item, as
   in the exam: one tile out of place scores zero.
6. Log with `--task-type toefl-build-a-sentence --score <n> --max 10`, and
   log the *reason* for each miss as a re-testable point (for example
   `grammar/word-order` — "statement word order in an indirect question").

The worked set, with its input and output side by side:
`data/item-bank/seed/writing-prompts.md`.

## Boundaries

- **If the response is not in English** (or mixes in substantial non-English
  text), do not score it as an English attempt: flag the language, explain
  that off-language content earns nothing in the real exam, and ask for an
  English version before evaluating or logging.
- **If the writing is clearly below B1** (the descriptors and calibration
  anchors start at B1): say so explicitly rather than snapping it up to the
  B1 anchor, give concrete B1 targets to aim for instead of a false in-range
  band, and log `--cefr-estimate A2` (or `A1`) while keeping the task's
  target `--level` unchanged.
- Do NOT reproduce official rubrics, past papers or answer keys; criteria
  names may be used, official descriptor text may not.
- Descriptors are paraphrased from the public CEFR framework only.
- Estimates are ranges and indicative, never official assessment.
- Never log an attempt the user did not actually make.
