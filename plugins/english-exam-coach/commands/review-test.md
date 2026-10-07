---
description: Log and review a full test taken elsewhere - scores, every mistake, and how it compares with earlier tests
argument-hint: "[optional: learner name and test name, e.g. Dana 'Mock 4']"
---

Review a full test: $ARGUMENTS

**First load the coach.** This command is only a shortcut: the instructions
and the tools live in this plugin's skill named `english-exam-coach` (listed
as `english-exam-coach:english-exam-coach` where skills carry their plugin's
name). Load that skill now — it is a different thing from this command. If
it cannot be loaded here, read
`${CLAUDE_PLUGIN_ROOT}/skills/english-exam-coach/SKILL.md` instead and treat
the folder it is in as the skill folder. Do not search the disk for it, and
do not improvise the workflow from memory: if neither works, say so and
stop.

Then follow the skill's `references/test-review.md` from the top: find out
what material there is, log the scores as the test gave them with `coach
log-test`, collect every mistake into a batch with tags from the closed
list, import it with `coach log-error --batch`, and build the review with
`coach tests --test`. If this is someone else's test, work in tutor mode
(`--learner <name>`). Never fill a gap in the evidence with a guess, and
never keep the records in files of your own making — the `coach` commands
are the record.
