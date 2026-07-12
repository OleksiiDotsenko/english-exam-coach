# Changelog

## 0.1.3 — 2026-07-09

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
