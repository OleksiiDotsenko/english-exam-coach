---
description: Run a timed mock - one section or a whole test - then score and log it
argument-hint: "[exam-id] [section or 'full']  e.g. toefl-ibt reading"
---

Run a timed mock: $ARGUMENTS

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

Then follow the **Mock** workflow in the skill's `references/workflows.md`.
Read the exam's format file first, announce the real rules and time limit,
give no hints and no key until the section is finished, and log one row per
task type under a single mock session id.
