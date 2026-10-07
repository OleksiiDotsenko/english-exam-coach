---
description: Show all-time progress - CEFR trends, streak, strongest and weakest task types
argument-hint: "[optional: learner name, for a tutor]"
---

Show the all-time progress overview: $ARGUMENTS

**First load the coach.** This command is only a shortcut: the instructions
and the tools live in this plugin's skill named `english-exam-coach` (listed
as `english-exam-coach:english-exam-coach` where skills carry their plugin's
name). Load that skill now — it is a different thing from this command. If
it cannot be loaded here, read
`${CLAUDE_PLUGIN_ROOT}/skills/english-exam-coach/SKILL.md` instead and treat
the folder it is in as the skill folder. Do not search the disk for it, and
do not improvise the workflow from memory: if neither works, say so and
stop.

Then, with the skill's `references/progress.md`: run `coach report --scope
all` (with `--learner <name>` if a learner was named), show the report and
say where it was written. Keep the indicative-scores footer. If full tests
are logged, mention that `coach tests` has their history. If the log is
empty, say so and offer the level check to set a baseline.
