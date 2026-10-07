# Reviewing a full test — scores, mistakes, trends, the error catalog

Read this when someone brings the results of a whole test taken somewhere
else — a mock on a practice platform, an official practice test, the real
exam — and wants it logged, reviewed, compared with earlier tests, or wants
to know what keeps going wrong. It is the path a tutor uses for a student,
and it works the same for a learner reviewing their own test.

`coach <command>` is defined in `SKILL.md`. For a tutor's student, **every
command below carries `--learner <name>`**; a learner working alone leaves
it out.

A single drill says how one task went. A run of full tests is the only
honest trend line, and laying every mistake across that run is what
separates a slip from a habit.

## 1. Find out what is on the table

Ask for, and read, whatever exists — do not review from a description:

- the score report: each section's score, the overall, and any per-task or
  per-item figures the test gives;
- the learner's own writing, with the prompts as they were set;
- the speaking answers — a recording, a transcript, or the platform's
  transcript — with the questions;
- the reading and listening items answered wrongly, with what the learner
  chose and what was right;
- anything the platform itself said about the mistakes.

Then settle: whose test (tutor mode), which exam, what the test is called
(use the name the user uses), the date it was taken, and where the scores
come from. If part of the test cannot be seen — only a section score, no
answers — say so, review what is there, and **do not invent the rest**.

Before logging, look at what is already there, so that nothing is logged
twice and names stay consistent:

```bash
coach tests --no-write          # tests already logged, with their dates
coach tests --json              # …and the task names used so far
coach catalog --points          # the point labels already in use
```

## 2. Log the scores

```bash
coach log-test --name "Saturn" --date 2026-08-25 --exam toefl-ibt \
  --source "mock platform" \
  --reading 4.0 --listening 5.0 --writing 3.5 --speaking 4.0 --overall 4.0 \
  --task build_a_sentence=7 --task email=3 --task discussion=4 \
  --task listen_and_repeat=5,5,5,5,4,4,2 --task interview=3,3,3,2.5
```

- **Scores are recorded as given** — whatever the test's own scoring
  produced. Do not rescale, round or "correct" them.
- `--overall` is the figure the test reported. If it reported none and all
  four sections are given, TOEFL and IELTS overalls are computed (the mean,
  rounded to a half band) and marked as computed.
- A section the test did not have a score for is simply left out. Other
  section names go in with `--section name=score` (`use_of_english=172`).
- `--task` holds detail inside the sections: one number, or a comma list of
  per-item scores. **Use the same name for the same thing in every test** —
  the history table lines them up by name. Names in use are in `coach tests
  --json`; for TOEFL, prefer `complete_the_words`, `build_a_sentence`,
  `email`, `discussion`, `listen_and_repeat`, `interview`.
- `--note` takes one line of context that bears on the score ("taken the
  day after another full test").
- The command prints the test's **session id** (`test-saturn-20260825`).
  Every mistake from this test is logged with that id.
- Logged wrongly? `coach log-test … --amend` records a corrected entry; the
  newer one wins. `coach log-test --void <name or session id>` withdraws a
  test that should not be there at all.

## 3. Collect the mistakes

Go through the material section by section and write **every** mistake to a
file, one JSON object per line. In a single drill 2–5 are enough; here
completeness is the point, because the catalog counts.

```json
{"category": "grammar", "subtype": "article", "point": "missing article before a singular count noun", "evidence": "I am student at this university", "fix": "I am a student at this university", "task_type": "toefl-write-email", "skill": "writing-evaluator"}
{"category": "comprehension", "subtype": "purpose", "point": "purpose questions answered with the topic", "evidence": "chose B: what the experiment was about", "fix": "C: it is evidence for the theory", "task_type": "toefl-listen-academic-talk", "skill": "listening-trainer"}
{"category": "grammar", "subtype": "pronoun", "point": "reflexive added where English uses none", "evidence": "I cannot concentrate myself", "fix": "I cannot concentrate", "transfer": "the verb is reflexive in the first language", "task_type": "toefl-take-an-interview", "skill": "speaking-coach"}
```

- **`category` / `subtype`**: from the closed list in
  `data/error-taxonomy.md`. Tag the cause, not the place it showed up.
  Hard cases: `references/tagging-examples.md`.
- **`point`**: the specific, re-testable thing. **Reuse a label from `coach
  catalog --points` whenever it is the same thing** — the catalog groups by
  the label's words, and two wordings of one habit hide it. Write the
  labels in one language throughout a learner's catalog.
- **`evidence`**: the learner's own words, exactly as written or said. For a
  wrong objective answer, what they chose.
- **`fix`**: the corrected form, or the right answer and what makes it
  right.
- **`transfer`**: only when the mistake is a word-for-word carry-over from
  the learner's first language, and you know what that language does.
- **`task_type`** and **`skill`**: the slug and the area label from
  `data/task-types.md`.

What to record, by section:

- **Writing**: every language error a rater would notice, each one its own
  line, and the task-level failures — a bullet not answered
  (`task/content-point`), too short (`task/length`), the wrong tone
  (`task/audience`).
- **Speaking**: errors in the transcript. Delivery only from evidence — the
  platform's own remarks, or timing figures. For repeat-after-me items,
  `delivery/repetition` with what was said as evidence and the target
  sentence as the fix.
- **Reading and listening**: the *reason* each wrong answer was wrong — a
  `comprehension` tag. If the material shows only that item 14 was wrong
  and not what it asked, there is no reason to record: say how many misses
  could not be explained, and leave them out.
- **Gapped words, sentence-building**: the cause — `lexis/spelling`,
  `grammar/agreement`, `grammar/word-order`, `comprehension/vocabulary`.

Do not log things that are not mistakes (a style preference, a correct
variant), and do not log a guess as a fact.

Then import the file. Nothing is written unless every row is valid:

```bash
coach log-error --batch mistakes.jsonl --session test-saturn-20260825 \
  --exam toefl-ibt --level B2
coach queue sync
```

Flags on the command line fill in whatever a row leaves out. `--level` is
the learner's target level.

## 4. Build the review

```bash
coach tests --test Saturn       # this test against the ones before it
coach tests                     # the history across all tests
coach catalog                   # the error catalog (full version on disk)
```

Each prints Markdown and writes it under `<base>/reports/`. Present the
review in the user's language, with the script's numbers copied exactly:

1. **The headline** — overall and each section: against the previous test,
   against the average of all earlier ones, and whether it is a record.
   One test is noise: with fewer than four tests, a difference between two
   of them is not a trend, and the report says so — do not overrule it.
2. **Inside the sections** — the per-task figures that moved.
3. **Mistakes seen before** — each with "in N of M tests". These are the
   habits; they come first.
4. **Mistakes new in this test.**
5. **What stayed away** — with how many clean tests it has had and how many
   are still needed (below).
6. **Three priorities for the coming week**, chosen by rule, not by taste:
   chronic and returned points first, then recurring ones; for each, one
   concrete drill. Offer a practice sheet for them
   (`references/practice-sheets.md`).

## 5. The rule of four, and what the states mean

A point is **closed only after it has stayed out of four tests in a row**.
Two clean tests is not closed — that is the moment habits come back. The
catalog gives every point seen in a test a state:

| State | Means | Say |
|---|---|---|
| chronic | in most tests, and still here | a standing habit: needs daily, short, targeted work |
| returned | back after two or more clean tests | it was not gone; restart the count |
| recurring | present now, not in most tests | keeps coming up; catch it before it becomes chronic |
| new | first seen in the latest test | watch whether it repeats before treating it as a habit |
| fading | absent from the last 1–3 tests | good sign, not closed: N clean, 4 − N to go |
| closed | absent from 4 tests running | done — and only now |
| one-off | seen once, not in the latest test | probably a slip |

States need at least two logged tests; with fewer the catalog leaves them
out rather than guess. A tutor who works to a different rule can pass
`--closed-after <n>`; say which rule is in force. Mistakes from practice
that are not tied to a logged test count in the totals, not in the states.

The catalog also lists **mistakes repeated word for word** (the same wrong
form, corrected the same way — the cheapest to fix: one card each) and
**mistakes carried over from the first language** (these respond to contrast
pairs — how we say it, how English says it — not to another explanation of
the rule).

`coach catalog --json` gives the same data for a layout of your own, and
`coach catalog --full` prints every mistake under its point.

## 6. Bringing in a backlog

Several past tests at once: log them **oldest first**, each with its own
`--date`, and import each test's mistakes with its own `--session` and with
`--ts <the test's date>T12:00:00`, so the ledger's dates are the tests'
dates and not today's. Run `coach queue sync` once at the end.

After a large import many points are due at once. `coach queue due --limit
5 --min-occurrences 2` shows the ones that matter first.

## 7. Corrections

The logs are append-only; a wrong entry is corrected by a newer line, never
by editing a file.

```bash
coach catalog --full --ids                         # every mistake with its id
coach log-error --void e-3f2a9c1d --reason "both forms are correct"
coach log-error --amend e-3f2a9c1d --subtype countability \
  --point "information as an uncountable noun"     # only what changes
coach queue sync
```

## 8. On paper

Any report can be turned into a page that prints cleanly, or saves as a PDF
from the browser's print dialog:

```bash
coach render <base>/reports/test-saturn-20260825.md
coach render <base>/reports/error-catalog.md --landscape
```

If you rewrite a report in the user's language, save your version as
Markdown beside it and render that. See `references/practice-sheets.md`
for what the renderer understands.

## Boundaries

- A learner's name, scores and writing are private. They stay in that
  learner's folder and in what you show the person you are working with.
- Scores from a test are reported as that test gave them. Estimates of your
  own are labelled as estimates. Nothing here is an official result.
- Never fill a gap in the evidence with a plausible guess — not a score, not
  a mistake, not a reason for a wrong answer.
- Reviewing someone's answers to a real or commercial test is fine;
  reproducing that test's questions is not. Quote the learner, describe the
  item, and do not copy the test.
