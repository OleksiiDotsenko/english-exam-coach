# The learning loop — how a scored attempt becomes tomorrow's drill

Read this when scoring any task, or when deciding what to practise next. It
is the protocol every other reference file relies on; they carry only the
one or two commands they need.

```
attempt → per-criterion judgement → error ledger → spaced queue →
   drill selector → a FRESH item on the same point → attempt …
```

The value is in the last step: the learner is re-tested on the *point*,
never on the item. A regenerated question cannot be answered from memory of
the answer.

`coach <command>` is defined in `SKILL.md`. In tutor mode every command
below carries `--learner <name>`.

---

## 1. Judge in two passes, not one

A single pass invents a score and then rationalises it. Two passes cost one
extra moment and produce a defensible judgement:

**Pass 1 — evidence first, no score.** Collect what is actually in the
response: quote 3–6 concrete features (a tense error, a well-handled
concession, a missing content point, a range of linkers). Do not name a
level yet — naming it first makes everything after it confirmation.

**Pass 2 — judge, then attack the judgement.** Place the evidence against
the calibration anchors per criterion. Then argue the opposite case once:
*what would make this a level lower? a level higher?* If the counter-case is
as strong as the case, widen the range rather than picking a midpoint.
Report a range; never a false-precision point score.

## 2. Persist the per-criterion judgement

The criteria you just weighed are the diagnosis — log them, or the next
session starts blind:

```bash
coach log-attempt \
  --exam <exam-id> --skill <area> --task-type <slug> --level <target-CEFR> \
  --band-estimate "<low>-<high>" --cefr-estimate <CEFR> --seconds <n> \
  --criteria "task_response=B2,coherence=C1,lexis=B2,grammar=B1" \
  --timing-source <script|wall-clock|self-reported|estimated> \
  --evidence-grade <full|partial|self-reported>
```

- `--skill` is the practice area, one of the fixed labels in
  `data/task-types.md` (`writing-evaluator`, `speaking-coach`,
  `reading-use-of-english`, `listening-trainer`, `vocabulary-builder`,
  `exam-router`). The reports group by it, so use the label exactly.
- `--task-type` is the exact slug from `data/task-types.md`.
- `--level` is the task's TARGET level; what the learner achieved goes in
  `--cefr-estimate`. Confusing the two collapses the report's attainment
  figures.
- `--criteria` takes CEFR levels, one per criterion the exam actually uses.
  Use the exam's own criterion names, lowercased with underscores.
- `--timing-source`: `script` only when `timed_speak.py` produced the
  number. A number the learner told you is `self-reported`; your own guess
  is `estimated`. These must never be indistinguishable in the log.
- `--evidence-grade`: `full` for written work or a transcript made from
  audio; `partial` for a speaking transcript typed from memory (content
  survived, delivery did not); `self-reported` when the learner only
  described their performance.
- Objective tasks log `--score <n> --max <m>` instead of a band estimate.
- One continuous sitting uses one `--session` id on every attempt; the
  default (`<date>-am` / `-pm`) would split a session that crosses noon.
- If the time on task is unknown, ask. Never substitute the task's nominal
  time limit.

## 3. Record each mistake as a re-testable point

For every distinct error worth returning to, write one ledger line:

```bash
coach log-error \
  --category grammar --subtype article \
  --point "zero article with uncountable nouns" \
  --evidence "the information were useful" \
  --fix "the information was useful" \
  --exam <exam-id> --skill <area> --task-type <slug> --level <CEFR>
```

**How many.** After a single drill, 2–5: twenty is noise, and the learner
will act on none of them. When reviewing a full test for the error catalog
(`references/test-review.md`), all of them — there the count is the point.

`--category` and `--subtype` come from a **closed list**:
`data/error-taxonomy.md`. Never invent a tag: everything downstream groups
by it, and a drifting tag means one weakness is scheduled three times under
three names. `references/tagging-examples.md` settles the hard cases.

`--point` is the load-bearing field. It must name something a *new item can
test*:

| Good `--point` | Why | Bad `--point` |
|---|---|---|
| `past perfect after "by the time"` | a new sentence can test it | `verb tenses` |
| `make vs do collocations` | generates fresh pairs | `word choice` |
| `not recognising a paraphrase of "decline"` | new passage, same trap | `reading` |

**Reuse the label.** Points are grouped by their wording, so "missing
article before a count noun" and "no article with singular nouns" become two
habits instead of one. Before coining a point, list the labels already in
use with `coach catalog --points` and reuse one when it is the same thing.

Objective drills: log the *reason* the item was missed (a `comprehension`
subtype), not the item number.

When the cause is the learner's first language — a structure translated
word for word — add `--transfer "<what the first language does>"`. Those
errors respond to contrast pairs, not to another explanation of the rule,
and the catalog lists them separately.

Many at once: write one JSON object per line to a file, with the same field
names, and pass `--batch <file>`. Flags on the command line fill in whatever
a row leaves out, and nothing is written unless every row is valid.

## 4. Fold new points into the queue

After logging errors, always:

```bash
coach queue sync
```

A point that reappears is bumped back to box 1 — repetition means the
explanation did not stick, and it should come back sooner, not later.

## 5. Re-test, and record the result

When `coach next` returns due points, generate a **fresh item per point** —
same target, new wording, new context — and then:

```bash
coach queue review --id <id> --result pass     # or: --result fail
```

Boxes: 1 = next session · 2 = 1 day · 3 = 3 days · 4 = 7 days · 5 = 30 days.
A pass promotes, a miss resets to box 1. Say which points you are re-testing
and why, so the learner sees the system working rather than a random drill.

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
coach log-attempt … --draft 2 \
  --criteria "task_response=B2,coherence=C1,lexis=B2,grammar=B2"
```

Be honest when a criterion did not move — an unearned improvement is worse
than none, because it teaches the learner that revision is cosmetic. If a
fix was applied mechanically without understanding, say so and log the point
again so the queue keeps it alive.

## 7. Choosing what to practise

Never guess. Ask the selector, which reads queue, ledger, log and profile:

```bash
coach next            # add --json to read it as data
```

It returns exactly one recommendation with its reason. Show the learner the
reason — "you missed this three times and it is due today" is motivating in
a way that "let's practise articles" is not.

## 8. Keep the directory sound

```bash
coach state show        # what is in the progress directory
coach state validate    # exit 1 if a log or state file is damaged
```

The scripts append to the logs and rewrite only their own state files. Do
not open the logs with an editor or another tool; if `validate` reports a
problem, tell the user what it said.
