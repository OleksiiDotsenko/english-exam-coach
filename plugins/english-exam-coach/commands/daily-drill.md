---
description: A short daily drill targeting your weakest task type from the progress log
argument-hint: "[optional: skill or task-type to force, e.g. writing]"
---

Run today's drill: $ARGUMENTS

1. Ask what to drill — do not decide it yourself:
   `python3 "${CLAUDE_PLUGIN_ROOT}/skills/progress-tracker/scripts/drill_context.py"`
   (on Windows, if `python3` isn't found, use `python` or `py`).
   It returns one recommendation and the reason for it, choosing between
   points due for re-testing, a recurring error type, and the weakest task
   type. If the user passed an argument, drill that instead.
2. **Show the reason before the task.** "You have missed this three times and
   it is due today" is why the drill is worth doing; a bare instruction is not.
3. If the recommendation is `re-test`, generate a **fresh item for each due
   point** — same target, new wording and context, never the original item —
   and record each outcome:
   `python3 ".../scripts/queue.py" review --id <id> --result pass|fail`.
   Otherwise run one focused set from the matching skill at the user's level.
4. Keep it to 10–15 minutes: one set (6–10 use-of-english items, one speaking
   long turn, one writing paragraph). Score it, give the top fix only, log the
   attempt, and log any new mistakes with `log_error.py` + `queue.py sync` —
   see `skills/progress-tracker/references/the-loop.md`.
5. Close with one line: today's result against the task type's average, what
   comes back next, and whether the streak continues.
