# Changelog

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
