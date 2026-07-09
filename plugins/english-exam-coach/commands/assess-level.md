---
description: Quick CEFR level diagnostic across reading, writing and vocabulary
argument-hint: "[optional: target exam, e.g. toefl-ibt]"
---

Assess my English level: $ARGUMENTS

Use the `exam-router` skill's level diagnostic (its step 4): a compact
15-minute probe — graded use-of-english items, a short writing sample, and a
few can-do self-checks — anchored to the paraphrased CEFR descriptors in
`${CLAUDE_PLUGIN_ROOT}/data/cefr/`.

Report the estimate as a CEFR range per skill (e.g. "reading ~C1, writing
~B2+"), say clearly that it is an indicative self-practice estimate, log the
diagnostic via the `progress-tracker` skill, and — if the user named a
target exam — state the gap to that exam's typical pass level and suggest
the first drill.
