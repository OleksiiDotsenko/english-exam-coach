# Workflows — starting out, the daily drill, a timed mock

Three guided paths that string the other references together. `coach
<command>` is defined in `SKILL.md`; in tutor mode every command carries
`--learner <name>`.

## Start

Walk the user from zero to a running practice task. Ask ONE question at a
time, keep each question short, and skip anything the conversation has
already answered.

1. **Returning learner?** Run `coach report --scope all --no-write` (an
   empty log is not an error). If there is history, open with one line —
   the last session's date, the current weakest task type, anything due in
   `coach queue due` — and offer "pick up where you left off" before asking
   anything else.

2. **Where progress is saved (first time only).** If there is no history,
   say where progress will be kept and offer another folder, as `SKILL.md`
   describes — including what happens when this session's files do not
   persist. Settle it before the first attempt is logged. Skip silently for
   a returning learner.

3. **Whose preparation is this?** If the user is preparing someone else — a
   student, a child — switch to tutor mode: agree a short name and use
   `--learner <name>` from here on. If they bring the results of a full
   test, go to `references/test-review.md`.

4. **Exam.** IELTS Academic (`ielts-academic`), IELTS General Training
   (`ielts-general`), TOEFL iBT (`toefl-ibt`), or B1 Preliminary
   (`cefr-b1`), B2 First (`cefr-b2`), C1 Advanced (`cefr-c1`), C2
   Proficiency (`cefr-c2`). If they are unsure which exam they need, ask
   what it is for (university, migration, work, proof of level) and
   recommend one.

5. **Level and target.** For the `cefr-*` exams the level is implied. For
   IELTS and TOEFL ask for their current working level; if they do not
   know, offer the 15-minute check (`references/level-check.md`). Ask what
   score they need and when they sit the exam, and save it once:
   ```bash
   coach profile set --exam <exam-id> --target-score <score> \
     --exam-date <YYYY-MM-DD> --current-level <CEFR>
   ```
   Omit any flag they cannot answer — a partial profile is fine, and the
   command prints the target translated into CEFR. Do not ask twice.

6. **Section.** Writing, Speaking, Reading / Use of English, Listening or
   Vocabulary — or a timed mock (below), or a week-by-week plan
   (`references/study-plan.md`).

7. **Mode.** (a) practise a new task, (b) get feedback on something already
   written or recorded, or (c) first see how the section works — for (c),
   explain the format from `data/exam-formats/<exam-id>.md`, then offer
   (a).

8. **Go.** Open the matching reference and run the task. It generates or
   evaluates, scores and logs as usual.

## Daily drill

Ten to fifteen minutes, aimed at what the log says is weakest.

1. **Ask what to drill — do not decide it yourself:** `coach next`. It
   returns one recommendation and the reason, choosing between points due
   for re-testing, an error type that keeps recurring, and the weakest task
   type. If the user asked for something specific, drill that instead.
2. **Show the reason before the task.** "You have missed this three times
   and it is due today" is why the drill is worth doing; a bare instruction
   is not.
3. If the recommendation is a re-test, generate a **fresh item for each due
   point** — the same target, new wording and context, never the original
   item — and record each outcome: `coach queue review --id <id> --result
   pass` (or `fail`). Otherwise run one focused set from the matching
   reference at the user's level.
4. Keep it short: one set (6–10 use-of-English items, one speaking long
   turn, one paragraph of writing). Score it, give the top fix only, log
   the attempt, and log any new mistakes with `coach log-error` + `coach
   queue sync` (`references/the-loop.md`).
5. Close with one line: today's result against the task type's average,
   what comes back next, and whether the streak continues.

## Mock

A timed mock of one section, or of a whole test, under the exam's own
rules.

1. **Settle the exam and the scope.** One section, or the whole test.
   Valid exam ids are the seven in `SKILL.md`.
2. **Load the format** from `data/exam-formats/<exam-id>.md` and announce
   the rules: the parts, the item counts and the real time limit. Note the
   start time.
3. **Run it at full length** with ORIGINAL items only, using the matching
   reference for each part. No hints, no feedback and no answer key until
   the section is finished. Keep to the exam's own rules of movement — in
   TOEFL listening, for example, a question once answered cannot be
   revisited.
4. **One session id for the whole mock:** `mock-<exam-id>-<date>`. Each
   part's reference ends with a silent log; pass that session id every
   time, and log **one row per task type**, not one per section and not a
   second copy afterwards.
5. **Split the time.** A section runs on ONE clock, so divide the real
   elapsed time across its task types (in proportion to their items) and
   pass each share as that row's `--seconds`. Logging the whole section's
   time on every row would inflate the time-on-task totals several times
   over.
6. **Score when the user submits** or calls time: the whole section, with
   feedback and explanations per part. Log the mistakes as points (`coach
   log-error`, with `--session mock-<exam-id>-<date>`) and run `coach queue
   sync`.
   - **If the user stops part-way,** offer to score only the completed
     parts and log those, with the real elapsed time and the same session
     id. Never invent answers for items that were not attempted. If nothing
     was completed, log nothing and say so.
7. **Finish with the report:** `coach report --scope session --session
   mock-<exam-id>-<date>`.

### A whole TOEFL iBT mock (2026 format)

Sections in the fixed order, no breaks. The real test is adaptive and this
is not: say so, and build each module at the learner's working level.

| Section | Build | Clock |
|---|---|---|
| Reading | two modules, each one Complete-the-Words paragraph (10 gaps), two Daily Life texts (2 + 3 questions) and one academic passage (5) — 40 questions | about 30 min; moving back is allowed inside a module, not to the first module once the second begins |
| Listening | two modules, each 8 Choose-a-Response items, then one or two conversations (2 questions each), an announcement (2) and a talk (4) — 32 to 36 questions | about 29 min; everything is heard once and no question can be revisited |
| Writing | Build a Sentence (10 items), Write an Email (7 min), Write for an Academic Discussion (10 min) | 23 min in all, about 6 of them for the ten sentences |
| Speaking | Listen and Repeat (7 sentences, one scenario), Take an Interview (4 questions, one topic) | about 8 min; no preparation time |

The item counts above follow the official practice test; the real test
carries a few more items in Reading and Listening, some of them unscored.
Reading and Listening give raw scores here (so many right out of so many).
The real conversion to a 1–6 band is adaptive and unpublished, so report
the raw score with an indicative CEFR range rather than a band; give
Writing and Speaking band estimates as ranges.

### Should a mock go on the test history?

`coach log-test` is for tests that come with a score of their own — a mock
platform, an official practice test, the real exam
(`references/test-review.md`). A mock run here is logged as attempts, which
already feed every report. If the learner wants it on the same history line
as their other tests, log it as a test **only** when all four sections were
completed in one sitting, and mark it for what it is:

```bash
coach log-test --name "<name>" --exam <exam-id> --date <YYYY-MM-DD> \
  --source "self-run mock (indicative)" \
  --reading <band> --listening <band> --writing <band> --speaking <band>
```

Use the lower end of each range — for Reading and Listening, the lower end
of what `coach convert --from cefr --level <level> --to toefl` gives for
the indicative level. The history then names the source beside every test,
so an estimate is never mistaken for a platform's score.
