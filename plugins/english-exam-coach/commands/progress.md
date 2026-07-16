---
description: Show all-time progress - CEFR trends, streak, strongest and weakest task types
---

Build the all-time progress overview.

Run:
`python3 "${CLAUDE_PLUGIN_ROOT}/skills/progress-tracker/scripts/build_report.py" --scope all`
(If `python3` is not found — common on Windows — run the same command with `python` or `py`.)

Show the report body (CEFR trend per skill, exams practised, best/worst task
types, streak, recommendation) and mention where it was written
(`<base>/reports/progress-overview.md`). Keep the indicative-scores footer.
If the log is empty, say so and offer `/assess-level` to establish a
baseline.
