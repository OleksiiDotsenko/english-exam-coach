# Dogfood checklist — what the tests cannot prove

The test suite covers the scripts: the state contract, logging, the queue's
scheduling and corruption recovery, the drill selector, the test history and
error catalog, the item builders, the print renderer, and the audio helpers
against stand-in programs. All of that is mechanical.

**The other half is judgement and environment**, and no unit test can check
either. Whether the assistant tags an error consistently, whether a
regenerated item really tests the same point, whether a band range is
defensible — those need a human who knows the exams. Whether the skill
behaves in a chat sandbox the way it does in a terminal needs someone to
run it there. This is that checklist.

Until it has been worked through, treat scores and drill choices as
promising rather than proven. Nothing here blocks using the plugin; it
blocks *trusting* it.

`coach` below means
`python3 plugins/english-exam-coach/skills/english-exam-coach/scripts/coach.py`.

---

## 1. Tag consistency (the highest-risk item)

**Why it matters.** The queue and the catalog group by `category/subtype`
and by the wording of the point. A mis-tagged error drills the wrong point
for weeks; two wordings of one habit hide it from the catalog.

**How to check.** Over ~2 weeks of normal use, then `coach queue show` and
`coach catalog --points`:

- [ ] Read every point aloud. Would a fresh item testing that point actually
      re-test what went wrong?
- [ ] Any two entries that are the same weakness under different names?
      (That is label drift — `coach catalog --points` exists to prevent it.
      Was it consulted before new points were coined?)
- [ ] What share sits in catch-alls (`word-choice`, `technique`)? Over ~20%
      means the taxonomy is being used as a dustbin.
- [ ] Take 10 errors from `coach catalog --full --ids`, re-tag them yourself
      from `data/error-taxonomy.md`, and compare. Under ~8/10 agreement
      means the guidance needs sharpening, not the learner. Fix what is
      wrong with `coach log-error --amend`.
- [ ] Do the ten tags added in 3.0 (`comprehension/purpose`, `negation`,
      `lexis/non-word`, …) get used where they fit, or are those mistakes
      still landing in the older, broader tags?

## 2. Regenerated items really test the same point

**Why it matters.** This is the moat. If the "fresh item" drifts to a
different structure, the loop is a random drill generator with extra steps.

- [ ] Trigger a re-test (`/daily-drill` when points are due).
- [ ] For each: does the new item test the *same* grammar, lexis or
      comprehension point? Is it genuinely new wording, not a paraphrase of
      the original?
- [ ] Is it at the right level — not quietly easier to make the pass
      likelier?

## 3. Scoring credibility

- [ ] Submit the same essay twice in separate sessions. Do the criteria land
      within half a level of each other? Wide swings mean the two-pass
      protocol is not being followed.
- [ ] Submit a deliberately weak (A2-ish) response. Is it reported below B1,
      or force-fitted up to the anchor floor?
- [ ] Submit a strong C1 response. Are the criteria differentiated, or all
      flattened to the same level?
- [ ] Does the report's "lowest criterion" line match your own reading of
      your weaknesses?

## 4. The loop closes

- [ ] Complete a task → are 2–5 errors logged (not zero, not twenty)?
- [ ] Does `coach queue sync` run without being asked?
- [ ] Next session: does `/daily-drill` lead with due re-tests and **state
      the reason** before the task?
- [ ] After a re-test, is the result recorded with `coach queue review`?
- [ ] Miss a point deliberately — does it return the next day (box 1)?

## 5. Revise-and-resubmit

- [ ] After feedback, are you actually offered a second draft of the *same*
      task?
- [ ] Is the revision judged against the same criteria, with a per-criterion
      delta?
- [ ] When a criterion did not improve, is that said plainly — or is an
      unearned improvement reported to be encouraging?

## 6. Full-test review (new in 3.0)

**Why it matters.** A tutor will act on this. A review that invents a
mistake, or a score, is worse than no review.

- [ ] `/review-test` with a real score report and real answers. Are the
      scores logged **exactly as the test gave them**? Is a computed overall
      called computed?
- [ ] Is every mistake in the batch backed by something in the material —
      the learner's words, the option they chose? Did the assistant refuse
      to guess the reason for a wrong answer it could not see?
- [ ] Is the batch complete — every mistake, not the 2–5 of a single drill?
- [ ] Were existing labels reused (`coach catalog --points`), or does the
      catalog now show the same habit twice?
- [ ] With three tests logged: does the report decline to call a difference
      a trend?
- [ ] With six or more: do the habit states match your own reading? Is a
      point that stayed away for two tests called *fading*, not fixed? Is
      one that came back called *returned*?
- [ ] Is a first-language carry-over marked with `--transfer` only when it
      really is one?
- [ ] In tutor mode with two learners: does any command ever write to the
      wrong folder? (`coach state learners`, then read both.)

## 7. TOEFL item builders (new in 3.0)

- [ ] Ask for a Complete the Words drill. Was the item made with `coach
      ctest make` and shown **exactly as printed** — including single-letter
      stems such as `o_`, which are correct and must not be "repaired"?
- [ ] Count the blanks in three gaps by hand against the key.
- [ ] Is the paragraph 70–80 words with a real topic sentence, and is there
      whole text after the tenth gap?
- [ ] Ask for a Build a Sentence set. Ten items, each with a first sentence?
      Do the blanks in every frame match its tiles? Try to build a *second*
      correct sentence from each item's tiles — any you can build is a
      defect in the item.
- [ ] Compare one generated set, side by side, with the exam provider's own
      free practice material. Does it look like the same task?

## 8. Printable sheets (new in 3.0)

- [ ] `/worksheet` for a point from the catalog. Is there one target, not
      five? Are the learner's own sentences in it? Is every item original?
- [ ] Open the HTML and print-preview it. Does the key start on its own
      page? Does the learner's copy (`--no-key`) have no key at all?
- [ ] Do blanks and writing lines survive? Does a wide table fit with
      `--landscape`?
- [ ] Is anything described as "a PDF" that is actually an HTML file?

## 9. Timed speaking and sound

These only work on your own computer, with a speaker.

- [ ] `speak.py check`, then a listening drill. Are the speakers' voices
      different? Is the pace natural? Was the audio folder cleaned up
      afterwards?
- [ ] TOEFL Listen and Choose a Response: one prompt at a time, never
      replayed, options on screen only?
- [ ] `timed_speak.py --audio` for Listen and Repeat and for the interview:
      prompt, tone, clock, tone — audible without watching the screen?
- [ ] Is the logged time the task's own clock, not wall-clock including the
      prompts?
- [ ] `transcribe.py` on a real recording of yourself (not a synthetic
      voice). Is the transcript shown to you to confirm before accuracy is
      judged? Compare it with what you actually said: which slips did the
      recogniser silently repair?
- [ ] Is a typed-from-memory transcript logged as `--evidence-grade
      partial` and never as `full`?
- [ ] On a machine with no synthesiser (or in a cloud session): does the
      coach fall back to a read-once script and *say* that it is not pure
      listening?

## 10. Other surfaces (new in 3.0, untested by the author's tooling)

The skill was restructured so that it does not depend on anything outside
its own folder. That it then *works* outside Claude Code has not been
verified end to end.

- [ ] In a chat or Cowork session with the plugin enabled: does the skill
      load, and can it find and run `scripts/coach.py`?
- [ ] At the first write, does the coach say where progress is going, and —
      if the session's files will not persist — offer `coach state export`
      before the conversation ends?
- [ ] Does `coach state import` restore that file in a new session?
- [ ] Do the nine commands appear and route into the skill?

## 11. First run on a clean machine

- [ ] Delete (or move) `~/english-exam-coach/` and run `/start-prep`. Does
      it offer the storage choice *before* anything is written?
- [ ] Is the target profile captured once, and used later ("your target is
      4.5, you are averaging B2")?
- [ ] `coach state validate` on the resulting directory — clean?
- [ ] After a session, is there anything new inside the plugin's own
      folder? (There should be nothing — not even `__pycache__`.)

---

## Recording the outcome

Note the date, what you checked, and anything that failed. A failed item is
a bug report, not a reason to stop using the plugin — but section 1 failing
means the queue and the catalog are counting noise, and section 6 failing
means a tutor is being told things that are not in the evidence. Those two
are worth fixing before relying on it.
