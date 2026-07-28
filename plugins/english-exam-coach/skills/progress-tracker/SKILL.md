---
name: progress-tracker
description: >
  Use to log a completed exam-practice attempt or to generate a progress
  report. Call it right after any writing/speaking/reading/listening/
  vocabulary task is scored to append the result, and when the user asks to
  see results or trends ("show my progress", "session report", "how am I
  doing on writing", "what's my weakest task?"). Reads and appends to the
  user's progress directory ($EXAM_COACH_HOME or ~/english-exam-coach/);
  the log is append-only.
---

# Progress Tracker

Two-layer model: `attempts.jsonl` is the append-only source of truth;
Markdown reports in `reports/` are derived and regenerable. Scripts live at
`${CLAUDE_PLUGIN_ROOT}/skills/progress-tracker/scripts/` (if the variable is
unset, resolve relative to this SKILL.md).

The base directory is resolved by the scripts themselves:
`--base` flag → `$EXAM_COACH_HOME` → `~/english-exam-coach/`. Because
attempts are usually logged inline by another skill — which silently creates
`~/english-exam-coach/` on first write — the default-vs-custom choice must be
surfaced at the first real entry point (`/start-prep`, or exam-router before
its diagnostic) **before any attempt is logged**: ask once whether the user
wants the default (`~/english-exam-coach/`) or a custom path such as an
Obsidian vault folder, then suggest exporting `EXAM_COACH_HOME` in their
shell profile to persist the choice. If this skill is nonetheless the first
to log and no base exists yet, ask that same question before the first write.

## When to use

- After ANY task is scored by another skill → log the attempt, silently.
- When the user asks for results, trends, streaks, or weakest areas → build
  and show a report.
- When advice needs the learner's target ("am I on track?", "is B2 enough?")
  → read the profile; when they state a target or an exam date → save it.

## The learning loop

Scores alone are amnesia: every session grades, explains, and forgets. The
loop turns each mistake into a scheduled re-test on a freshly generated item.
The full protocol — two-pass judging, the error taxonomy, the queue, and the
revise-and-resubmit cycle — is in
[`references/the-loop.md`](references/the-loop.md). Read it when scoring
anything or when asked what to practise next.

```bash
python3 ".../scripts/log_error.py" --category <cat> --subtype <sub> \
  --point "<the specific, re-testable target>"   # one line per mistake
python3 ".../scripts/queue.py" sync              # fold new points in
python3 ".../scripts/queue.py" due               # what is due today
python3 ".../scripts/drill_context.py"           # ONE explainable next step
python3 ".../scripts/state.py" validate          # check the directory is sound
```

`log_error.py --list-taxonomy` prints the closed enum. Never invent a tag —
the queue groups by it.

## Target profile and score scales

`profile.py` stores the target exam, score and exam date in
`<base>/profile.json`; everything works without it. `convert_score.py`
translates between an exam's own scale and CEFR in either direction — use it
instead of converting from memory.

```bash
python3 ".../scripts/profile.py" show
python3 ".../scripts/profile.py" set --exam toefl-ibt --target-score 4.5 \
  --exam-date 2026-09-12
python3 ".../scripts/convert_score.py" --from toefl --score 4.5   # ≈ CEFR B2
python3 ".../scripts/convert_score.py" --from cefr --level C1 --to ielts
```

## Logging an attempt

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/progress-tracker/scripts/log_attempt.py" \
  --exam <exam-id> --skill <source-skill> --task-type <task-type> \
  --level <A1|A2|B1|B2|C1|C2> \
  [--score <n> --max <m> | --band-estimate "<low>-<high>"] \
  [--cefr-estimate <level>] --seconds <time-on-task> [--session <id>]
```

- If `python3` is not found (common on Windows), run the same command with
  `python` or `py` — the scripts are stdlib-only and version-agnostic.
- Use the **exact `--task-type` slug** from
  `data/task-types.md` for the exam, so results aggregate correctly across
  sessions (the "weakest task type" stat groups by this string).
- `--level` is the task's CEFR anchor, `A1`–`C2` (TOEFL tasks can reach A1).
- At least one of `--score` / `--band-estimate` is required; the script
  validates and exits non-zero without writing if the record is malformed.
- `--session` defaults to `<date>-am/pm`. For one continuous sitting, pick a
  single session id at the first log and pass the same `--session` on every
  attempt in that sitting — otherwise a session that crosses noon would
  split into `-am`/`-pm` halves and the session report would show only one.
- `--seconds` is real time on task — measure it (note the start time when a
  task is issued); ask the user rather than inventing a number.
- The script only ever appends. Never edit `attempts.jsonl` by hand or with
  other tools.

## Building a report

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/progress-tracker/scripts/build_report.py" \
  --scope session [--session <id>]   # current/named session
python3 "${CLAUDE_PLUGIN_ROOT}/skills/progress-tracker/scripts/build_report.py" \
  --scope all                        # full history
```

The script prints the Markdown and writes it under `<base>/reports/`
(`session-<id>.md` / `progress-overview.md`). Show the user the report body
(or a faithful summary of it plus the file path) — don't re-derive numbers
yourself; the script's aggregation is authoritative.

## What the reports contain

- **Session:** tasks, time on task, a per-attempt results table (one row per
  logged attempt), estimated CEFR level this session, weakest task type, one
  prioritized next step.
- **Overview (all):** CEFR trend per skill, attempts per exam, best/worst
  task types, days practised and current streak, one recommendation.
- Cross-exam comparison uses CEFR normalization only (explicit
  `--cefr-estimate` wins; else public IELTS/TOEFL alignments; else a
  documented percentage heuristic at the task's anchor level). Raw scores
  from different exams are never merged into one number.

## Boundaries

- Append-only: never rewrite, truncate, sort, or "clean up" the log.
  "Clearing progress" must be an explicit user action performed by the user
  themselves (tell them which file to delete); never do it as a side effect.
- Never fabricate or backfill attempts for tasks that weren't actually done.
- Every report states that scores are indicative self-practice estimates,
  not official results (the script includes this footer — keep it when
  summarizing).
