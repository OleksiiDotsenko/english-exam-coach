---
description: Run a timed mock - one section or a whole test - then score and log it
argument-hint: "[exam-id] [section or 'full']  e.g. toefl-ibt reading"
---

Run a timed mock: $ARGUMENTS

**First load the coach.** This command is only a shortcut: the instructions
and the tools live in the skill `english-exam-coach:english-exam-coach`.
Invoke that skill now (it is a different thing from this command). If it
cannot be invoked here, read
`${CLAUDE_PLUGIN_ROOT}/skills/english-exam-coach/SKILL.md` instead and treat
the folder it is in as the skill folder. Do not search the disk for it, and
do not improvise the workflow from memory: if neither works, say so and
stop.

Then follow the **Mock** workflow in the skill's `references/workflows.md`.
Read the exam's format file first, announce the real rules and time limit,
give no hints and no key until the section is finished, and log one row per
task type under a single mock session id.
