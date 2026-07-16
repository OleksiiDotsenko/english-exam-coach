---
description: Quick CEFR level diagnostic across reading/use of English and writing
argument-hint: "[optional: target exam, e.g. toefl-ibt]"
---

Assess my English level: $ARGUMENTS

Use the `exam-router` skill's level diagnostic (its step 4): a compact
~15-minute probe — 8 graded use-of-english items and a short writing sample
(the primary evidence) — anchored to the paraphrased CEFR descriptors and
calibration anchors in `${CLAUDE_PLUGIN_ROOT}/data/cefr/`.

Report a SINGLE blended CEFR range (e.g. "B2, approaching C1"), consistent
with the exam-router diagnostic's method (the writing sample is the primary
evidence, the items refine it), say clearly that it is an indicative
self-practice estimate and that listening and speaking were not measured, and
— if the user named a target exam — state the gap to that exam's typical pass
level and suggest the first drill. The diagnostic is logged exactly once by
exam-router step 4; do not log it again here.
