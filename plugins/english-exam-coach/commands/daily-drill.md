---
description: A short daily drill aimed at what your own log says is weakest
argument-hint: "[optional: a skill or task type to force, e.g. writing]"
---

Run today's drill: $ARGUMENTS

**First load the coach.** This command is only a shortcut: the instructions
and the tools live in this plugin's skill named `english-exam-coach` (listed
as `english-exam-coach:english-exam-coach` where skills carry their plugin's
name). Load that skill now — it is a different thing from this command. If
it cannot be loaded here, read
`${CLAUDE_PLUGIN_ROOT}/skills/english-exam-coach/SKILL.md` instead and treat
the folder it is in as the skill folder. Do not search the disk for it, and
do not improvise the workflow from memory: if neither works, say so and
stop.

Then follow the **Daily drill** workflow in the skill's
`references/workflows.md`. Ask the selector what to drill (`coach next`)
rather than deciding yourself, and show the learner the reason before the
task. If an argument was given, drill that instead.
