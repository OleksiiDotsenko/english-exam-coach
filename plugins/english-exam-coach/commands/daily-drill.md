---
description: A short daily drill targeting your weakest task type from the progress log
argument-hint: "[optional: skill or task-type to force, e.g. writing]"
---

Run today's drill: $ARGUMENTS

1. Find the weakest task type: run
   `python3 "${CLAUDE_PLUGIN_ROOT}/skills/progress-tracker/scripts/build_report.py" --scope all --no-write`
   and read the "Weakest" line. If the user passed an argument, drill that
   instead. If the log is empty, run a quick level diagnostic via the
   `exam-router` skill and drill whatever it finds shakiest.
2. Keep it to 10–15 minutes: one focused set (e.g. 6–10 use-of-english
   items, one speaking long turn, or one writing paragraph task) generated
   by the matching skill at the user's level.
3. Score it, give tight feedback (the top fix only, not an essay), and log
   the attempt via the `progress-tracker` skill.
4. Close with one line: today's result vs. the task type's average, and
   whether the streak continues.
