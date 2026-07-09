---
name: study-planner
description: >
  Use when the user wants a preparation plan for an English exam ("I take
  TOEFL on September 12, make me a plan", "how should I prepare for C1
  Advanced in 8 weeks?"), wants to adjust an existing plan, or asks whether
  they are on track. Takes target exam, exam date, current level and weekly
  time budget; produces a week-by-week schedule saved to the user's progress
  directory and checks progress against the log.
---

# Study Planner

Turns a target exam + date into a week-by-week plan, then keeps it honest
against the progress log. Paths are relative to `${CLAUDE_PLUGIN_ROOT}` (if
unset, resolve relative to this file). The plan lives in the user's progress
directory (`$EXAM_COACH_HOME` or `~/english-exam-coach/plan.md`), NOT in the
plugin.

## When to use

The user names a target exam and a date (or a preparation window), asks for
a study schedule, or asks "am I on track?".

## Steps

1. **Gather inputs:** target exam id, exam date, hours/week available,
   current level. For current level, prefer evidence: recent CEFR estimates
   from the progress log (ask `progress-tracker` or read
   `<base>/attempts.jsonl`); if the log is empty, run the `exam-router`
   level diagnostic first. Load `data/exam-formats/<exam-id>.md` for the
   sections to cover.

2. **Build the plan** working back from the exam date:
   - Every section of the exam appears every week; the weakest two skills
     (from log evidence) get double weight.
   - Each week = concrete, loggable drills ("2× key-word-transformation set",
     "1 timed Task 2 essay with evaluation"), not vague goals ("improve
     grammar").
   - Include one weekly review of the vocabulary box, and one full timed
     mock section (`/mock-exam`) every 2–3 weeks, the last one ≤1 week
     before the exam.
   - Final week: lighter load, timing practice, no new material.

3. **Write the plan** to `<base>/plan.md` with YAML frontmatter
   (`type: study-plan`, `exam`, `exam_date`, `hours_per_week`,
   `created`). Overwriting an old plan is allowed — confirm first, and
   summarize what changed.

4. **"Am I on track?"** — compare the current week's planned drills against
   the log (`build_report.py --scope all` or read the log): what was done,
   what was skipped, whether CEFR trend per skill is moving toward the
   target. Adjust the coming weeks rather than piling missed work forward;
   say plainly if the target looks out of reach at the current pace and
   what pace would suffice.

## Boundaries

- Plans allocate real logged drills from this plugin's skills, so progress
  is measurable; do not prescribe third-party or official materials as
  required steps (mentioning them as optional extras is fine, nominatively).
- Never fabricate "on track" status — it must come from the log.
- Timeline estimates ("B2 → C1 in N weeks") are honest guesses with stated
  uncertainty, not promises.
