# The learning loop — how a scored attempt becomes tomorrow's drill

Read this when scoring any task, or when deciding what to practise next. It is
the shared protocol behind every skill; the skills themselves only carry the
one or two commands they need.

```
attempt → per-criterion judgement → error ledger → spaced queue →
   drill selector → a FRESH item on the same point → attempt …
```

The value is in the last step: the learner is re-tested on the *point*, never
on the item. A regenerated question cannot be answered from memory of the
answer.

All commands below live in
`${CLAUDE_PLUGIN_ROOT}/skills/progress-tracker/scripts/`. On Windows without
`python3`, use `python` or `py`.

---

## 1. Judge in two passes, not one

A single pass invents a score and then rationalises it. Two passes cost one
extra moment and produce a defensible judgement:

**Pass 1 — evidence first, no score.** Collect what is actually in the
response: quote 3–6 concrete features (a tense error, a well-handled
concession, a missing content point, a range of linkers). Do not name a level
yet — naming it first makes everything after it confirmation.

**Pass 2 — judge, then attack the judgement.** Place the evidence against the
calibration anchors per criterion. Then argue the opposite case once: *what
would make this a level lower? a level higher?* If the counter-case is as
strong as the case, widen the range rather than picking a midpoint. Report a
range; never a false-precision point score.

## 2. Persist the per-criterion judgement

The criteria you just weighed are the diagnosis — log them, or the next
session starts blind:

```bash
python3 ".../scripts/log_attempt.py" \
  --exam <exam-id> --skill <skill> --task-type <slug> --level <target-CEFR> \
  --band-estimate "<low>-<high>" --cefr-estimate <CEFR> --seconds <n> \
  --criteria "task_response=B2,coherence=C1,lexis=B2,grammar=B1" \
  --timing-source <script|wall-clock|self-reported|estimated> \
  --evidence-grade <full|partial|self-reported>
```

- `--criteria` takes CEFR levels, one per criterion the exam actually uses.
  Use the exam's own criterion names, lowercased with underscores.
- `--timing-source`: `script` only when `timed_speak.py` produced the number.
  A number the learner told you is `self-reported`; your own guess is
  `estimated`. These must never be indistinguishable in the log.
- `--evidence-grade`: `full` for written work or a transcript from audio;
  `partial` for a speaking transcript typed from memory (content survived,
  delivery did not); `self-reported` when the learner only described their
  performance.

## 3. Record each mistake as a re-testable point

For every distinct error worth returning to — 2–5 per task is right; twenty
is noise — write one ledger line:

```bash
python3 ".../scripts/log_error.py" \
  --category grammar --subtype article \
  --point "zero article with uncountable nouns" \
  --evidence "the information were useful" \
  --fix "the information was useful" \
  --exam <exam-id> --skill <skill> --task-type <slug> --level <CEFR>
```

`--category`/`--subtype` come from a **closed enum** (`log_error.py
--list-taxonomy`). Never invent a tag: the queue groups by it, and a drifting
tag means the same weakness is scheduled three times under three names.

`--point` is the load-bearing field. It must name something a *new item can
test*:

| Good `--point` | Why | Bad `--point` |
|---|---|---|
| `past perfect after "by the time"` | a new sentence can test it | `verb tenses` |
| `make vs do collocations` | generates fresh pairs | `word choice` |
| `not recognising a paraphrase of "decline"` | new passage, same trap | `reading` |

Objective drills: log the *reason* the item was missed (a `comprehension`
subtype), not the item number.

## 4. Fold new points into the queue

After logging errors, always:

```bash
python3 ".../scripts/queue.py" sync
```

A point that reappears is bumped back to box 1 — repetition means the
explanation did not stick, and it should come back sooner, not later.

## 5. Re-test, and record the result

When `drill_context.py` returns due points, generate a **fresh item per
point** — same target, new wording, new context — and then:

```bash
python3 ".../scripts/queue.py" review --id <id> --result pass|fail
```

Boxes: 1 = next session · 2 = 1 day · 3 = 3 days · 4 = 7 days · 5 = 30 days.
Pass promotes, miss resets to box 1. Say which points you are re-testing and
why, so the learner sees the system working rather than a random drill.

## 6. Revise and resubmit (writing and speaking)

Grading once and stopping wastes the most teachable moment there is. After
feedback, offer a second draft — this is where the level actually moves:

1. Give the learner **three specific, prioritised fixes**, each shown as a
   rewrite of their own sentence, plus what to keep.
2. Ask for a revised version of the same task (not a new prompt).
3. Judge the revision **against the same criteria** and report the delta per
   criterion: *task response B2 → B2, coherence B2 → C1, grammar B1 → B2*.
4. Log it as a further draft of the same task:

```bash
python3 ".../scripts/log_attempt.py" ... --draft 2 \
  --criteria "task_response=B2,coherence=C1,lexis=B2,grammar=B2"
```

Be honest when a criterion did not move — an unearned improvement is worse
than none, because it teaches the learner that revision is cosmetic. If a fix
was applied mechanically without understanding, say so and log the point again
so the queue keeps it alive.

## 7. Choosing what to practise

Never guess. Ask the selector, which reads queue, ledger, log and profile:

```bash
python3 ".../scripts/drill_context.py"        # add --json to consume it
```

It returns exactly one recommendation with its reason. Show the learner the
reason — "you missed this three times, it is due today" is motivating in a way
that "let's practise articles" is not.
