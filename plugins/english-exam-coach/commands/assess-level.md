---
description: A 15-minute check of your CEFR level from use-of-English items and a writing sample
argument-hint: "[optional: target exam, e.g. toefl-ibt]"
---

Assess my English level: $ARGUMENTS

**First load the coach.** This command is only a shortcut: the instructions
and the tools live in this plugin's skill named `english-exam-coach` (listed
as `english-exam-coach:english-exam-coach` where skills carry their plugin's
name). Load that skill now — it is a different thing from this command. If
it cannot be loaded here, read
`${CLAUDE_PLUGIN_ROOT}/skills/english-exam-coach/SKILL.md` instead and treat
the folder it is in as the skill folder. Do not search the disk for it, and
do not improvise the workflow from memory: if neither works, say so and
stop.

Then follow the skill's `references/level-check.md`. Report one blended
CEFR range, say that it is an indicative estimate and that listening and
speaking were not measured, and — if a target exam was named — state the gap
to that exam's usual pass level and suggest the first drill. Log the check
exactly once.
