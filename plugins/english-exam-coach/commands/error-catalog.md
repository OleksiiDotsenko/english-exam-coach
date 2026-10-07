---
description: Show the error catalog - what keeps going wrong across full tests, and which habits are closed
argument-hint: "[optional: learner name, for a tutor]"
---

Show the error catalog: $ARGUMENTS

**First load the coach.** This command is only a shortcut: the instructions
and the tools live in the skill `english-exam-coach:english-exam-coach`.
Invoke that skill now (it is a different thing from this command). If it
cannot be invoked here, read
`${CLAUDE_PLUGIN_ROOT}/skills/english-exam-coach/SKILL.md` instead and treat
the folder it is in as the skill folder. Do not search the disk for it, and
do not improvise the workflow from memory: if neither works, say so and
stop.

Then, with the skill's `references/test-review.md` (sections 4 and 5): run
`coach catalog` (with `--learner <name>` if a learner was named), present it
in the user's language with the numbers copied exactly, and explain the
habit states by the rule in force: a point is closed only after four clean
tests in a row. If fewer than two tests are logged, say what is missing
instead of guessing a trend.
