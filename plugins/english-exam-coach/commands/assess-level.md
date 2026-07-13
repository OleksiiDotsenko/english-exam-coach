---
description: Quick CEFR level diagnostic across reading/use of English and writing
argument-hint: "[optional: target exam, e.g. toefl-ibt]"
---

Assess my English level: $ARGUMENTS

Use the `exam-router` skill's level diagnostic (its step 4): a compact
~15-minute probe — 8 graded use-of-english items and a short writing sample
(the primary evidence) — anchored to the paraphrased CEFR descriptors and
calibration anchors in `${CLAUDE_PLUGIN_ROOT}/data/cefr/`.

Report the estimate as a CEFR range (e.g. "reading ~C1, writing ~B2+"), say
clearly that it is an indicative self-practice estimate and that listening
and speaking were not measured, log the diagnostic via the `progress-tracker`
skill, and — if the user named a target exam — state the gap to that exam's
typical pass level and suggest the first drill.
