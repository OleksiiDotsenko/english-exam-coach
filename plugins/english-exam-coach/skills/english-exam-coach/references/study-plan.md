# Study plan

Read this when the user names a target exam and a date (or a preparation
window), asks for a study schedule, wants an existing plan adjusted, or
asks "am I on track?". `coach <command>` is defined in `SKILL.md`.

The plan is a file in the learner's progress directory — `<base>/plan.md`.
`coach state show` prints where `<base>` is.

## Steps

1. **Gather the inputs:** target exam id, exam date, hours a week
   available, current level. For the current level prefer evidence: `coach
   profile show`, the CEFR estimates in `coach report --scope all
   --no-write`, and — if full tests are logged — `coach tests --no-write`.
   If nothing is logged, run the level check (`references/level-check.md`)
   first. Load `data/exam-formats/<exam-id>.md` for the sections to cover.
   Save what the user tells you once, so every later session can be
   specific about the gap:
   ```bash
   coach profile set --exam <exam-id> --target-score <score> \
     --exam-date <YYYY-MM-DD> --current-level <CEFR>
   ```
   Omit any flag they cannot answer; `coach convert` translates a target
   score to CEFR and back.

2. **Build the plan**, working back from the exam date:
   - **First check the window is real.** If the exam date is in the past,
     is today, or leaves under about a week, say so plainly and offer a
     compressed triage plan (a timed mock section plus review of the
     weakest skills, no new material) instead of a week-by-week schedule.
   - Every section of the exam appears every week; the weakest two skills
     (from logged evidence) get double weight.
   - What is already known to go wrong goes in first: the points due in
     `coach queue due`, and — when tests are logged — the chronic and
     returned habits in `coach catalog`.
   - Each week is made of concrete, loggable drills ("2 × key-word
     transformation sets", "1 timed Task 2 essay with evaluation"), not
     vague goals ("improve grammar").
   - Include one weekly review of the vocabulary box, and one full timed
     mock section every 2–3 weeks, the last no later than a week before
     the exam.
   - Final week: a lighter load, timing practice, no new material.

3. **Write the plan** to `<base>/plan.md` with YAML front matter
   (`type: study-plan`, `exam`, `exam_date`, `hours_per_week`, `created`).
   Overwriting an old plan is allowed — confirm first, and summarise what
   changed.

4. **"Am I on track?"** — compare the current week's planned drills with
   the log (`coach report --scope all`): what was done, what was skipped,
   whether the CEFR trend per skill is moving toward the target. Adjust the
   coming weeks rather than piling missed work forward; say plainly if the
   target looks out of reach at the current pace, and what pace would be
   enough.

## Boundaries

- Plans are built from drills this skill can run and log, so progress is
  measurable. Do not prescribe third-party or official materials as
  required steps; mentioning them as optional extras is fine.
- Never fabricate "on track" — it must come from the log.
- Timeline estimates ("B2 to C1 in N weeks") are honest guesses with stated
  uncertainty, not promises.
