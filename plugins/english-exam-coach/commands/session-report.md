---
description: Build and show the practice report for the current session
argument-hint: "[optional: session id, e.g. 2026-07-08-am]"
---

Build the session report: $ARGUMENTS

(A bare placeholder at the end of the line above means nothing filled it
in: the request is what the user typed after the command.)

**First load the coach.** This command is only a shortcut: the instructions
and the tools live in this plugin's skill named `english-exam-coach` (listed
as `english-exam-coach:english-exam-coach` where skills carry their plugin's
name). Load that skill now — it is a different thing from this command. If
it cannot be loaded here, read
`${CLAUDE_PLUGIN_ROOT}/skills/english-exam-coach/SKILL.md` instead and treat
the folder it is in as the skill folder. Do not search the disk for the
skill, and do not improvise the workflow from memory: if neither works, say
so and stop. (Once loaded, the skill says how to find its own scripts.)

Then, with the skill's `references/progress.md`: run `coach report --scope
session` (add `--session <id>` if one was given; otherwise it reports the
most recent session). Show the report and say where it was written. If the
most recent session is not from today, say so before showing it. If nothing
is logged yet, offer a drill instead of improvising numbers.
