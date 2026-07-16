# Changelog

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
