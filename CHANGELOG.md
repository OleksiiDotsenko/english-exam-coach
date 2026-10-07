# Changelog

## 3.0.1 — 2026-10-07

Two wording fixes for the surfaces where a plugin's commands load as skills
(chat), found by reading the directory's current documentation after 3.0.0.

- **Commands name the skill the way every surface lists it.** The hand-over
  paragraph said only `english-exam-coach:english-exam-coach`, which is how
  Claude Code and Cowork name a plugin's skill. It now says "the skill named
  `english-exam-coach`" first and gives the prefixed form as the variant.
- **`SKILL.md` says where the tool is when the path variable is not filled
  in.** A chat sandbox copies the skill's folder in whole and leaves
  `${CLAUDE_SKILL_DIR}` as written; the file is `scripts/coach.py` beside
  `SKILL.md`. It also says that every command and script is listed on that
  page — a test session spent three calls listing the folder to find them.

No change to scripts, data or progress files.

## 3.0.0 — 2026-10-07

**One skill, a tutor's workflow, and task shapes taken from the source.**

Three things drove this release. The plugin as packaged could only work in
Claude Code, because its eight skills reached outside their own folders. Its
author turned out to use it as a *tutor* — reviewing a student's full tests
by hand, because the plugin had no path for that. And two earlier "fixes" to
the TOEFL task shapes, taken from prep-site summaries, were themselves wrong.

### Breaking: eight skills became one

- The plugin now ships **one self-contained skill**, `english-exam-coach`: a
  short router (`SKILL.md`), one reference file per area, the reference
  data, and the scripts, all in one folder. Nothing reaches outside it, so
  it works wherever only a skill's own folder is available.
- The eight old skill names (`exam-router`, `writing-evaluator`, …) no
  longer exist as skills. The six commands are unchanged, and three are new.
  **Progress data needs no migration** — the logs are additive-only.
- All bookkeeping goes through **one tool**, `coach.py` (`coach log-attempt`,
  `coach report`, …). It and everything it can import use the standard
  library only, start no other program and open no connection — and a test
  now walks the import graph to keep it that way.
- `queue.py` and `profile.py` shadowed Python's own modules of those names
  and are now `review_queue.py` and `learner_profile.py`.
- **Each command now loads the skill by its full name, with a path to read
  if it cannot.** A command is not the skill: told only to "use the
  skill", a test session re-invoked the command itself, never found the
  skill's folder, and improvised its own files. Every command now names
  `english-exam-coach:english-exam-coach`, gives the fallback path, and
  forbids both searching the disk and improvising.

### Harmless wherever it is pointed

`coach.py` is a command a user allows once and stops reading, and a
learner's essay is untrusted text. So the tool itself is fenced in:

- It **reads only working files** — `.txt`, `.md`, `.json`, `.jsonl`, after
  following links — and will not print a key file or a shell profile back,
  whatever it is called on the command line.
- It **writes a page only to `.html` and an archive only to `.zip`**, and
  replaces an existing file only if it wrote it.
- `coach state export` and `import` move **the files of the progress layout
  and nothing else** — not the rest of the folder a progress directory may
  sit in, and not whatever an archive from elsewhere happens to contain.
- **Nothing is pre-approved.** The skill grants itself no tools.
- The helpers are fenced too: `speak.py` will not render into a folder it
  did not make, and `transcribe.py` hands a converter only audio files and
  confines it to local files.

### New: full tests, and what keeps going wrong across them

- **`coach log-test`** records a whole test — a mock platform, an official
  practice test, the real exam — with its section scores exactly as given,
  the overall, and per-task detail. A computed overall is labelled as
  computed. Corrections are new lines (`--amend`, `--void`).
- **`coach tests`** reports the history: records, the best score in each
  section added up, first half against second half (only from four tests —
  with fewer it says a difference is not a trend), per-task detail; and
  `--test NAME` reviews one test against the ones before it — which mistakes
  are new, which were seen before and in how many tests, which stayed away.
- **`coach catalog`** is the error catalog: categories, error types and
  specific points ranked with "in N of M tests", a point-by-test matrix,
  mistakes repeated word for word, mistakes carried over from the first
  language, and a **habit state** for every point — chronic, returned,
  recurring, new, fading, closed, one-off. One rule throughout: a point is
  closed only after **four clean tests in a row**.
- **`coach log-error --batch`** imports a reviewed test's mistakes in one
  go, all-or-nothing. `--transfer` records what in the learner's first
  language produces an error.
- **The taxonomy grew from 42 to 52 tags**, each added because a catalog of
  several hundred real mistakes had a recurring group with no honest home:
  `comprehension/purpose`, `main-idea`, `negation`, `structure`,
  `vocabulary`; `lexis/non-word`, `redundancy`; `grammar/pronoun`,
  `omission`; `delivery/repetition`. It now has a reference file
  (`data/error-taxonomy.md`) that a test keeps identical to the code.
- **Corrections for an append-only ledger.** Every mistake has an id;
  `coach log-error --void` withdraws one and `--amend` replaces it, as new
  lines. The queue and the catalog follow.

### New: tutor mode

- **`--learner <name>`** (or `$EXAM_COACH_LEARNER`) keeps each student in a
  folder of their own under `learners/`, with exactly the solo layout.
  `coach state learners` lists them.
- **`coach state export` / `import`** packs a progress directory into one
  zip and restores it — how progress survives a session whose files do not
  persist, and how it moves between machines.

### New: paper

- **`coach render`** turns any report or a Markdown worksheet into one
  self-contained HTML page laid out for print: A4 or Letter, portrait or
  landscape, page numbers, an answer key that starts on its own page or is
  left out for the learner's copy (`--no-key`). The page loads nothing and
  runs nothing; all source HTML is escaped. No PDF library — the browser's
  print dialog saves the PDF.
- A new reference, `practice-sheets.md`, and a `/worksheet` command: sheets
  aimed at a learner's known mistakes, built around their own sentences.

### Fixed: TOEFL task shapes, re-derived from the exam provider's own material

Verified against the published 2026 test specifications and the official
full-length practice test. The previous two releases were wrong here.

- **Complete the Words is a C-test.** The first sentence is whole; then the
  second half of *every second word* is removed until ten are gapped; a word
  of *n* letters keeps `n // 2` of them, so a stem can be a single letter;
  one blank per missing letter. v0.1.7 said "not every other word" and
  v2.0.1 said "the first 3–5 letters" — both wrong. Items are now **built by
  `coach ctest make`** from a plain paragraph and marked by `coach ctest
  check`, never laid out by hand.
- **Build a Sentence** shows the reply as a frame of 5–7 blanks, sometimes
  with a word or two pre-printed, with lower-case tiles and — in a few items
  — one extra tile that is not used. Most replies are questions. Items are
  **built by `coach sentence make`** and marked all-or-nothing by `coach
  sentence check`.
- **Listen and Repeat** sentences grow loosely from 5–7 to 11–14 words and
  do not reach "the upper teens" (v2.0.1). The scenario line gives a role
  and a speaker; there is no preparation time.
- **Take an Interview**: after the first, every question is led into by one
  to three sentences — interviewer turns of 35–60 words, not one-liners —
  and the four climb from a fact, to a reaction, to agree/disagree, to a
  policy opinion.
- **Section facts** now come from the published blueprint: Reading 50 items
  (30 of them Complete-the-Words gaps), Listening 47, raw points per
  section, router and second-module timings, two questions per conversation
  and announcement, four per talk, no going back in Listening. Build a
  Sentence's "6 min 50 s" was a prep-site figure; none is published.
- Email and discussion seeds now have the real layout (situation, three
  bullets, To/Subject filled in; a professor's post and two students on
  different sides, at least 100 words). Instructions are in our own words.

### New: sound, where there is any

Three optional helper scripts, kept out of `coach.py` because they start
other programs:

- **`speak.py`** speaks a script with the system voices — `say` on macOS,
  `espeak` on Linux — a different voice per speaker, rendered first and
  played afterwards so synthesis never leaks thinking time. Replaces the
  ad-hoc shell the listening instructions used to improvise.
- **`timed_speak.py --audio`** plays each prompt and then runs the answer
  clock, so Listen and Repeat and the interview run hands-free.
- **`transcribe.py`** transcribes a recording the learner provides with a
  recogniser already installed (`whisper-cli` or `whisper`), locally, and
  measures pace, start delay and long pauses. It never records.
- **`coach repeat`** compares a repeated sentence with the one heard, word
  for word, and names the first sentence that broke down.

### Fixed

- **Points written in a non-Latin alphabet collapsed into one.** The
  grouping key kept only `a–z0–9`, so every point named in, say, Ukrainian
  became the same empty key. Grouping is now Unicode-aware; Latin points
  group exactly as before, and the queue re-keys itself on the next sync.
- `state.py export` left derived reports out only at the top level.
- Tests could be steered into real data by a developer's own
  `EXAM_COACH_LEARNER`.
- The tools no longer write Python bytecode into the skill's own folder.

**Tests:** 135 → 473, on Python 3.9 and 3.14. Two end-to-end runs were made
in a real session before release — a drill, and a tutor's test review
through `/review-test`; the first attempt at the second is what found the
command hand-over problem described above.

## 2.0.1 — 2026-07-28

Four TOEFL 2026 task-shape fixes, all found by dogfooding generated practice
and all verified against the published task descriptions. Each was a case of
the plugin generating something *plausible* that the real task does not look
like — so each is now pinned by a test as well as fixed in the seeds.

- **Complete the Words** now states the two rules that make the item
  answerable: the visible stem is the word's **first 3–5 letters**, and the
  number of underscores **equals the missing letters, exactly**. The seed had
  two-letter stems (`gr__`) and 9 gaps; it now has ten gaps and a correct
  count on every one. Generation counts the letters instead of eyeballing.
- **Build a Sentence** always shows **two sentences** — a question or
  statement to read, then the chunks you arrange into a reply. Three of the
  five seed items had no first sentence, which is a different task. Chunk
  count (5–7) and all-or-nothing scoring are now stated too.
- **Listen and Repeat** is **one scenario** across all seven sentences, with a
  short spoken introduction, and the sentences lengthen from ~5–6 words to the
  upper teens. The seed was seven unrelated campus sentences.
- **Take an Interview** opens with a **brief scenario** and asks four
  questions on that single everyday topic (habits, travel, study, work), not
  four unrelated academic ones. Answer volume for a 45-second turn is stated:
  roughly 90–130 words. The format file's "academic/campus topics" was wrong
  and is corrected.

**Tests:** 121 → 135, including a checker that re-derives every C-test gap
from its answer key.

## 2.0.0 — 2026-07-28

**Close the loop, honestly.** Until now the plugin scored well and forgot
everything: it graded a task, explained it, wrote one number to the log, and
threw the diagnosis away. v2.0 is one product — a closed learning loop:

```
attempt → per-criterion judgement → error ledger → spaced re-testing with a
FRESHLY GENERATED item → one explainable drill choice → honest trends
```

The point that comes back is the *point*, never the item: a regenerated
question cannot be answered from memory of the answer.

**The loop:**
- **Error ledger** (`log_error.py` → `errors.jsonl`). Each mistake is recorded
  against a closed two-level taxonomy (8 categories, 42 subtypes) plus a
  required free-text point naming what a fresh item must test. The enum is
  closed on purpose: free-form tags drift until nothing groups, and a
  mis-tagged error drills the wrong thing for weeks.
- **Spaced re-testing** (`queue.py` → `queue.json`), reusing the vocabulary
  Leitner intervals. A point that reappears is pulled back to box 1, because
  repetition means the explanation did not stick. The script owns every write
  and rebuilds from the ledger if the file is ever corrupted.
- **One drill selector** (`drill_context.py`). Every "what should I practise?"
  surface asks the same question and gets the same answer, with a reason:
  due re-tests, then a recurring error type, then the weakest task type, and
  an honest cold start when there is no evidence yet.
- **Revise and resubmit** for writing and speaking: a second draft of the same
  task, judged against the same criteria, reported as a per-criterion delta —
  and honest when a criterion did not move.

**Honest scoring:**
- Per-criterion levels are now persisted (`--criteria`) and reported, so a
  band comes with *which criterion is holding it there*, stated as an
  observation rather than a diagnosis.
- Two-pass judging: gather evidence with no level attached, then judge and
  argue the opposite case before fixing a range.
- `--timing-source` and `--evidence-grade` mean a script-timed performance and
  a typed-from-memory transcript are never averaged together silently. The
  report says what the estimates rest on.
- `timed_speak.py` runs the real prep/answer clocks with audible cues and logs
  the task's own elapsed time.

**Foundations:**
- `state.py` is the state-directory contract: append-only logs, additive-only
  fields, atomic JSON writes, tolerant reads, quarantine of corrupt state, and
  preservation of unknown keys. Every script writes through it. A v0.1.1-era
  log still reads, and there are tests that keep it that way.
- Skill instructions stay within a line budget; the loop protocol lives in
  `references/the-loop.md` and `references/tagging-examples.md`.

**Tests:** 71 → 121, including an end-to-end simulation of the whole loop.
`DOGFOOD.md` covers what tests cannot: whether the tagging, the regenerated
items, and the band ranges are actually sound.

**Deliberately not in 2.0:** no new exams. PTE, Duolingo, TOEIC and Linguaskill
all scored well on reach, but seven format files is already an annual
re-verification burden, and depth in the loop beats breadth in the catalogue.

## 0.1.8 — 2026-07-28

Phase 0 of the v2.0 roadmap ("Close the loop, honestly"). This is the
depth-and-hygiene release that lands ahead of the learning loop; nothing here
changes the log schema.

**Target profile (new):**
- `profile.py` stores your target exam, target score and exam date in
  `<base>/profile.json`, written atomically and never required. `/start-prep`
  now asks once and saves it, so later sessions can talk about the actual gap
  instead of generic advice.
- `convert_score.py` translates in both directions between an exam's own
  scale and CEFR (TOEFL 1–6, the legacy 0–120 concordance, IELTS bands, the
  Cambridge Scale), so conversions stop being done from memory. Cross-scale
  hops are labelled indicative.

**TOEFL iBT 2026 depth:**
- Seed exemplars for the two redesigned task types that had none: **Build a
  Sentence** (with the design rules that keep the arrangement unique) and
  **Listen and Choose a Response** (with per-distractor rationales).
- Listen-and-Choose now has a per-item playback protocol: every ~5-second
  prompt is pre-rendered before the drill so synthesis pauses cannot leak
  thinking time into a task whose difficulty is that it goes by once.

**Generation honesty:**
- Reading passages and listening scripts are now counted mechanically with
  `wc -w` before being presented, instead of estimated — the failure mode
  earlier audits measured at 30–71% too short.

**Accuracy:**
- The router no longer lists B1 Business Preliminary as an unsupported
  alternative (Cambridge discontinued it in 2023–24); PTE Core, TOEIC and
  Linguaskill are named instead.
- Every exam-format file now carries a `last-verified` stamp, so the annual
  re-verification pass has something to check against.

**Tests:** 71 → 89.

## 0.1.7 — 2026-07-16

Fixes from a fourth audit (block-wise: per-file review, live factual
verification of every exam-format claim, cross-cutting invariants,
completeness critics — every finding adversarially verified). ~43 distinct
issues fixed; no critical findings survived the previous rounds.

**Exam-fact corrections (all web-verified):**
- IELTS Speaking Part 2 was mislabelled visual-dependent in the speaking
  coach; it is a text cue card and is now offered normally, while the
  genuinely visual Cambridge B1–C2 Part 2 photo tasks are the ones guarded.
- C2 Proficiency Writing no longer mentions the set-text option (removed by
  Cambridge in January 2024). B1 Preliminary Speaking Part 3 corrected to
  ~4 min. TOEFL "Complete the Words" gap density described accurately
  (~10 targeted words, opening sentence intact). IELTS Academic passage
  word ranges now sum to the stated total.

**Logging correctness:**
- `/mock-exam` no longer double-logs: the delegated skill's single silent
  auto-log now writes under the mock session with split time.
- The level diagnostic is logged exactly once and is excluded from the
  "weakest task type" ranking (no more "drill 10 more level diagnostics").
- TOEFL Build-a-Sentence and Listen-and-Repeat are always percentage-scored
  (new `OBJECTIVE_TASK_TYPES`), so an item count can never be misread as a
  1–6 band, even under the holistic writing/speaking skills.
- A timezone-aware `--ts` derives its session id from local time (matching
  how reports read it); a date-only `--ts` is rejected.

**Report clarity:**
- Per-skill trends sort chronologically (back-dated logs no longer invert
  the direction) and the improving/slipping arrow is derived from the same
  half-level values that are displayed — `B2 → B2 (improving)` is gone.
- A lone task type is no longer listed as both strongest and weakest.
- Legacy TOEFL cut table: unreachable reading/listening rows removed;
  docstring now describes the actual five-bucket objective mapping.

**Skills & guidance:** correct `${CLAUDE_PLUGIN_ROOT}`-unset fallback in
four skills; sub-B1 floor for writing/speaking (no more force-fitting A1/A2
up to B1); reading fallback passage lengths aligned with the format files;
`--max` = 2× items for out-of-2 tasks; TTS scripts stripped of markup before
`say`; credit any valid answer on open-ended items; guards for unsupported
exams and past exam dates; vocabulary review logging rule for mixed-level
rounds; Leitner/interaction-anchor notes.

**Docs & first-run:** honest security wording (optional macOS TTS writes a
short-lived temp file); Windows `python`/`py` fallback noted at every
`python3` call site; macOS "preinstalled Python" claim corrected; progress
storage (default vs `EXAM_COACH_HOME`/Obsidian) offered in `/start-prep`
before the first log; canonical listening slugs written out explicitly;
marketplace metadata version synced.

**Tests:** 61 → 71, covering every behavioural fix above.

## 0.1.6 — 2026-07-15

Fixes from Audit 3 — a comprehensive, per-file + full-matrix pass (one
reviewer per file and per exam×task, adversarially verified). The sizing
work from 0.1.5 held up: 116 of 121 generation probes now pass.

**Correctness:**
- `log_attempt.py` now accepts UTC timestamps ending in `Z` on Python < 3.11
  (the macOS system default), and guards against concatenating a record onto
  a previous partial line.
- `build_report.py` skips log rows missing core fields instead of rendering
  `| None |`.
- Writing-evaluator `--level` is now unambiguously the task's target level
  (performance goes only in `--cefr-estimate`), so the report's attainment
  and weakest-task signal is no longer overwritten.

**Content accuracy:**
- Fixed a broken C-test seed stem (`flo___` → `flow___` for "flowers"),
  reconciled the vocabulary Leitner schedule between skill and seed, corrected
  the C1 speaking Range descriptor (was defined with C2-only features), made
  IELTS General reading section lengths sum to the stated total, and fixed
  task-type slug scoping (no B1 essay, no C1 article).
- Listening question-preview timing is now exam-conditional (TOEFL hides
  questions until after the audio); mock-exam splits elapsed time across task
  types; assess-level reports a single blended estimate.

**Generation leveling:** the writing, speaking, and vocabulary generate steps
now pitch *prompt/item* difficulty to the target level (not just format),
referencing the calibration anchors — closing a cluster of mis-leveling gaps.

**Tests:** 58 → 61.

## 0.1.5 — 2026-07-14

Fixes from a second, generation-based audit (22 adversarially verified
findings) that *exercises* the plugin rather than only reading it.

**Scoring correctness:**
- **Critical:** raw item counts of 6, 9, or 30 were misread as TOEFL/IELTS
  proficiency *bands*, inflating a realistic drill by 1–3 CEFR levels. Band
  scales now apply only to the holistic skills (writing/speaking); objective
  drills are always percentage-scored.
- Sub-60% scores get finer resolution, so a total failure is distinguishable
  from a near-miss and aspirational above-level practice isn't over-credited.
- At the A1 floor a near-total failure no longer reads as "at target level".

**Task sizing (generated content now matches authentic length):**
- Added authentic passage/script word-count targets — and gapped-text
  distractor-option counts — to every Cambridge/IELTS reading section and a
  length directive to the reading and listening skills. A C2 Part 6 gapped
  text was generating ~450w (−71%); it now targets ~700–800w.

**Coverage & format authenticity:**
- New slugs for reading-comprehension multiple choice, C1 cross-text
  matching, and IELTS reading question types; the reading skill now advertises
  them. T/F/Not Given vs Yes/No/Not Given distinction stated, with a new
  worked seed. IELTS Task 1 process/map anatomy added. Visual-dependent
  listening tasks are now honestly scoped as undeliverable in a terminal.

**Robustness & difficulty:**
- Guards for off-format task requests, partial answer sets, un-transcribable
  audio, non-English submissions, and sub-B1 estimates.
- New `data/cefr/reading-calibration-anchors.md` so generated passages sit at
  the claimed CEFR level.

**Tests:** 54 → 58.

## 0.1.4 — 2026-07-13

Fixes from an exhaustive multi-agent quality audit (48 adversarially
verified findings across scripts, skills, data, docs, and UX).

**Progress-tracker scripts (correctness):**
- `build_report.py` no longer crashes on a log that mixes timezone-aware and
  naive timestamps, on a non-numeric `seconds` field, or on wrong-shape JSON
  rows — the append-only log can never be permanently broken by one bad line.
- `log_attempt.py` rejects NaN/Infinity, whitespace-only `--band-estimate`,
  and whitespace-only `--session`; writes strict JSON (`allow_nan=False`).
- A bare IELTS score logged without `--max` is no longer misread as a band 9
  (was inflating the CEFR estimate to C2); low scores stay on the CEFR scale
  instead of rendering as `~?`.
- "Weakest task type" now ranks every task on one CEFR-relative attainment
  axis, so band-scored writing/speaking are no longer systematically ranked
  below easier objective drills; reports no longer print bands as `%`.
- Streak shown as "last streak" once a run has lapsed; report counts are
  pluralized; sub-minute times round correctly.
- A back-dated `--ts` now derives its session id from that timestamp.

**Skills & data:**
- New `data/task-types.md` canonical slug registry; every scoring skill logs
  with the exact slug so progress aggregates across sessions.
- Vocabulary Leitner schedule made consistent between the skill and its seed.
- Listening trainer now plays recordings twice for the CEFR B1–C2 exams
  (once for IELTS/TOEFL), matching the format files.
- Writing evaluator now asks for the original task prompt before judging task
  achievement; TOEFL Build-a-Sentence and Listen-and-Repeat are covered.
- Level diagnostic hardened (8 items, stop rule, "not measured" note); added
  `--level A1/A2` support and a Windows `python`/`py` note.
- New A1/A2 can-do rows and speaking calibration anchors; corrected seed item
  keys, word counts, and CEFR terminology; reworded near-verbatim boilerplate.

**Tests:** 26 → 54, covering every fix above.

## 0.1.3 — 2026-07-12

- Scoring consistency: new `data/cefr/calibration-anchors.md` — four
  original leveled answers (B1/B2/C1/C2) to one shared prompt, each with
  the reasoning that places it at its level. The writing evaluator now
  calibrates against the nearest anchor per criterion before fixing a band
  range, instead of judging from descriptors alone.
- README: clearer install flow (enter Claude Code first, run commands one
  at a time), desktop-app path, and FAQ entries for the two real first-run
  errors ("/plugin isn't available", "SSH authentication failed").

## 0.1.2 — 2026-07-09

- README: example session walkthrough, security & privacy section, CI badge.
- plugin.json: `homepage` and `repository` metadata.
- No functional changes to skills, commands, or scripts.

## 0.1.1 — 2026-07-09 (initial public release)

- 8 skills organized by macro-skill (exam differences live in reference
  data, not code): exam-router, writing-evaluator, speaking-coach,
  reading-use-of-english, listening-trainer, vocabulary-builder,
  study-planner, progress-tracker.
- 6 commands: /start-prep (guided entry), /mock-exam, /daily-drill,
  /assess-level, /session-report, /progress.
- Exam format data verified against official sources as of July 2026:
  TOEFL iBT 2026 redesign (1–6 band scale, adaptive Reading/Listening,
  new task types), IELTS computer-delivered, CEFR B1–C2 (Cambridge)
  specifications.
- Append-only progress log (attempts.jsonl) + derived Markdown reports
  with CEFR-normalized cross-exam trends; Python stdlib only; 26 tests.
- CI: unittest suite + strict manifest validation on push/PR.
