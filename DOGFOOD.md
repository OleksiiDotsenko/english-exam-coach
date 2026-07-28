# Dogfood checklist — what the tests cannot prove

The test suite covers the scripts: state contract, logging, the queue's
scheduling and corruption recovery, the drill selector's states, and an
end-to-end simulation of the whole loop. All of that is mechanical.

**The other half of v2.0 is judgement**, and no unit test can check it. Whether
the assistant tags an error consistently, whether a regenerated item really
tests the same point, whether a band range is defensible — those need a human
who knows the exams. This is that checklist.

Until it has been worked through, treat v2.0's scores and drill choices as
promising rather than proven. Nothing here blocks using the plugin; it blocks
*trusting* it.

---

## 1. Tag consistency (the highest-risk item)

**Why it matters.** The queue groups by `category/subtype`. A mis-tagged error
drills the wrong point for weeks, silently, and the learner just feels stuck.

**How to check.** Over ~2 weeks of normal use, then:

```bash
python3 plugins/english-exam-coach/skills/progress-tracker/scripts/queue.py show
```

- [ ] Read every point aloud. Would a fresh item testing that point actually
      re-test what you got wrong?
- [ ] Any two entries that are the same weakness under different names? (That
      is tag drift — the thing the closed enum exists to prevent.)
- [ ] What share sits in `other`-ish catch-alls (`word-choice`, `technique`)?
      Over ~20% means the taxonomy is being used as a dustbin.
- [ ] Take 10 errors from `errors.jsonl`, re-tag them yourself from
      `references/tagging-examples.md`, and compare. Under ~8/10 agreement
      means the guidance needs sharpening, not the learner.

## 2. Regenerated items really test the same point

**Why it matters.** This is the moat. If the "fresh item" drifts to a
different structure, the loop is just a random drill generator with extra
steps.

- [ ] Trigger a re-test (`/daily-drill` when points are due).
- [ ] For each: does the new item test the *same* grammar/lexis/comprehension
      point? Is it genuinely new wording, not a paraphrase of the original?
- [ ] Is it at the right level — not quietly easier to make the pass likelier?

## 3. Scoring credibility

- [ ] Submit the same essay twice in separate sessions. Do the criteria land
      within half a level of each other? Wide swings mean the two-pass
      protocol is not being followed.
- [ ] Submit a deliberately weak (A2-ish) response. Is it reported below B1,
      or force-fitted up to the anchor floor?
- [ ] Submit a strong C1 response. Are the criteria differentiated, or all
      flattened to the same level?
- [ ] Does the report's "lowest criterion" line match your own reading of your
      weaknesses?

## 4. The loop closes

- [ ] Complete a task → are 2–5 errors logged (not zero, not twenty)?
- [ ] Does `queue.py sync` run without being asked?
- [ ] Next session: does `/daily-drill` lead with due re-tests and **state the
      reason** before the task?
- [ ] After a re-test, is the result recorded with `queue.py review`?
- [ ] Miss a point deliberately — does it return the next day (box 1)?

## 5. Revise-and-resubmit

- [ ] After feedback, are you actually offered a second draft of the *same*
      task?
- [ ] Is the revision judged against the same criteria, with a per-criterion
      delta?
- [ ] When a criterion did not improve, is that said plainly — or is an
      unearned improvement reported to be encouraging?

## 6. Timed speaking

- [ ] `timed_speak.py` under a real task: are the cues audible without
      watching the screen?
- [ ] Is the logged time the task's own clock, not wall-clock including the
      tool's announcements?
- [ ] Is a typed-from-memory transcript logged as `--evidence-grade partial`
      and never as `full`?

## 7. First run on a clean machine

- [ ] Delete (or move) `~/english-exam-coach/` and run `/start-prep`. Does it
      offer the storage choice *before* anything is written?
- [ ] Is the target profile captured once, and used later ("your target is
      4.5, you are averaging B2")?
- [ ] `state.py validate` on the resulting directory — clean?

---

## Recording the outcome

Note the date, what you checked, and anything that failed. A failed item is a
bug report, not a reason to stop using the plugin — but section 1 failing
means the queue is scheduling noise, and that is worth fixing before relying
on it for exam preparation.
