---
description: Build and show the practice report for the current session
argument-hint: "[optional: session id, e.g. 2026-07-08-am]"
---

Build the session report: $ARGUMENTS

Run:
`python3 "${CLAUDE_PLUGIN_ROOT}/skills/progress-tracker/scripts/build_report.py" --scope session`
(append `--session $ARGUMENTS` if a session id was given; otherwise it uses
the most recent session in the log).

Show the report body to the user and mention where it was written
(`<base>/reports/session-<id>.md`). If the script reports no attempts yet,
offer `/daily-drill` instead of improvising numbers.

If no session id was given and the most recent session in the log is **not
from today**, say so explicitly ("no attempts logged today — this is your
last session, from <date>") before showing it, and offer `/daily-drill`, so
a stale session is never presented as if it were today's.
