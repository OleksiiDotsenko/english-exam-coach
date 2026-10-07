# Progress — logging, reports, targets

Read this when the user asks for results, trends, a streak or their weakest
areas ("show my progress", "session report", "how am I doing on writing?"),
when you need the learner's target to make advice specific, or when you are
unsure how to log something. `coach <command>` is defined in `SKILL.md`.

Two layers: the logs are the source of truth and are only ever appended to;
the Markdown reports under `<base>/reports/` are derived from them and can
be rebuilt at any time. Where the progress directory is, how tutor mode
works, and what to do when a session's files do not persist are covered in
`SKILL.md` — settle the location **before the first write**.

## The learning loop

Scores alone are amnesia: every session grades, explains and forgets. The
loop turns each mistake into a scheduled re-test on a freshly generated
item. The protocol — two-pass judging, the error tags, the queue, revise
and resubmit — is in `references/the-loop.md`. Read it when scoring
anything or when asked what to practise next.

```bash
coach log-error --category <cat> --subtype <sub> \
  --point "<the specific, re-testable target>"    # one per mistake
coach queue sync                                  # fold new points in
coach queue due                                   # what is due today
coach next                                        # ONE explainable next step
coach state validate                              # is the directory sound?
```

The tags are a closed list — `data/error-taxonomy.md`, or `coach log-error
--list-taxonomy`. Never invent one.

## Target and score scales

`coach profile` stores the target exam, score and exam date; everything
works without it. `coach convert` translates between an exam's own scale
and CEFR in either direction — use it instead of converting from memory.

```bash
coach profile show
coach profile set --exam toefl-ibt --target-score 4.5 --exam-date 2026-09-12
coach convert --from toefl --score 4.5            # about CEFR B2
coach convert --from cefr --level C1 --to ielts
```

## Logging an attempt

```bash
coach log-attempt \
  --exam <exam-id> --skill <area> --task-type <task-type> \
  --level <A1|A2|B1|B2|C1|C2> \
  [--score <n> --max <m> | --band-estimate "<low>-<high>"] \
  [--cefr-estimate <level>] --seconds <time-on-task> [--session <id>]
```

- `--skill` is the practice area and `--task-type` the task's slug; both
  come from `data/task-types.md` and must be used exactly, because the
  "weakest task type" figure groups by them.
- `--level` is the task's CEFR anchor (TOEFL tasks can reach A1).
- At least one of `--score` / `--band-estimate` is required; the command
  validates and exits non-zero without writing if the record is malformed.
- `--session` defaults to `<date>-am` or `-pm`. For one continuous sitting,
  choose a single session id at the first log and pass it on every attempt
  — otherwise a sitting that crosses noon splits in two and the session
  report shows half of it.
- `--seconds` is real time on task: measure it (note the start time when a
  task is issued) or ask. Never invent it.

## Reports

```bash
coach report --scope session [--session <id>]     # this or a named session
coach report --scope all                          # the whole history
```

Each prints its Markdown and writes it under `<base>/reports/`
(`session-<id>.md`, `progress-overview.md`); add `--no-write` to print only.
Show the user the report (or a faithful summary plus where the file is) —
do not re-derive the numbers yourself; the script's arithmetic is the
authority.

- **Session:** tasks, time on task, one row per logged attempt, the
  estimated CEFR level this session, the weakest task type, one next step.
- **All time:** CEFR trend per skill, criterion-level trends, attempts per
  exam, best and worst task types, days practised and the current streak,
  one recommendation.
- Exams are compared in CEFR only (an explicit `--cefr-estimate` wins; else
  the public IELTS and TOEFL alignments; else a stated percentage heuristic
  at the task's anchor level). Raw scores from different exams are never
  merged into one number.
- If no session id was given and the latest session in the log is **not
  from today**, say so before showing it ("nothing logged today — this is
  your last session, from <date>"), so a stale session is never presented
  as today's.
- If the log is empty, say so and offer the level check or a first drill
  instead of improvising numbers.

**Full tests** have reports of their own — the history across tests, a
review of one test, and the error catalog. See `references/test-review.md`.

**On paper:** `coach render <report>.md` turns any of these into a page
that prints cleanly (and saves as a PDF from the browser's print dialog).
See `references/practice-sheets.md`.

## Boundaries

- Append-only: never rewrite, truncate, sort or "clean up" a log.
  "Clearing progress" must be done by the user themselves (tell them which
  file to delete); never as a side effect.
- Never fabricate or backfill attempts for tasks that were not done.
- Every report says its scores are indicative self-practice estimates, not
  official results. The scripts print that footer — keep it when you
  summarise or translate.
