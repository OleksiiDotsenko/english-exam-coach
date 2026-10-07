---
description: Make a printable practice sheet with an answer key, aimed at a learner's known mistakes
argument-hint: "[optional: learner name and/or topic, e.g. Dana articles]"
---

Make a printable practice sheet: $ARGUMENTS

**First load the coach.** This command is only a shortcut: the instructions
and the tools live in this plugin's skill named `english-exam-coach` (listed
as `english-exam-coach:english-exam-coach` where skills carry their plugin's
name). Load that skill now — it is a different thing from this command. If
it cannot be loaded here, read
`${CLAUDE_PLUGIN_ROOT}/skills/english-exam-coach/SKILL.md` instead and treat
the folder it is in as the skill folder. Do not search the disk for it, and
do not improvise the workflow from memory: if neither works, say so and
stop.

Then follow the skill's `references/practice-sheets.md`: choose one target
from the error catalog or the queue (or the topic given), write an original
sheet in Markdown with the learner's own sentences to correct and a key
after `<!-- key -->`, then `coach render` it — once with the key and once
with `--no-key` for the learner. Give the user the HTML files and say how to
print them or save them as PDF.
