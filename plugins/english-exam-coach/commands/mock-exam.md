---
description: Run a timed mock section of an English exam, score it, and log the result
argument-hint: "[exam-id] [section]  e.g. cefr-c1 reading"
---

Run a timed mock exam section: $ARGUMENTS

1. Parse the arguments as exam id and section. If either is missing, use the
   `exam-router` skill to resolve them from the user's goals (or ask once).
   Valid exam ids: ielts-academic, ielts-general, toefl-ibt, cefr-b1,
   cefr-b2, cefr-c1, cefr-c2.
2. Load the exact section format from
   `${CLAUDE_PLUGIN_ROOT}/data/exam-formats/<exam-id>.md` and announce the
   rules: parts, item counts, and the real time limit. Note the start time.
3. Run the section at full length using the matching skill
   (reading-use-of-english, writing-evaluator, speaking-coach, or
   listening-trainer) with ORIGINAL items only. No hints, no feedback, and
   no answer key until the section is finished. Each of those skills already
   ends with a single silent auto-log — for a mock, tell the skill to make
   that its ONE log, writing under `--session mock-<exam-id>-<date>` with the
   split `--seconds` from step 4. Do not add a second log; one row per task
   type, in the mock session, with split time.
4. When the user submits (or declares time up), score the whole section and
   give per-part feedback and explanations. The single per-task log is the
   delegated skill's own silent auto-log from step 3 (under `--session
   mock-<exam-id>-<date>`, using the canonical `--task-type` slugs from
   `data/task-types.md`) — do not log a separate attempt here. A section runs
   under ONE clock, so **split the real elapsed time across the task types**
   (e.g. proportional to item count) and pass each task's share as the
   `--seconds` for that log — do not log the full section time on every row,
   or the report's "min on task" will be inflated N-fold.
   - **If the user quits mid-section:** offer to score only the fully
     completed parts and log those task types with the real elapsed time
     and the same session id. Never fabricate answers for unattempted items.
     If nothing was completed, log nothing and say so.
5. Finish with the session report:
   `python3 "${CLAUDE_PLUGIN_ROOT}/skills/progress-tracker/scripts/build_report.py" --scope session --session mock-<exam-id>-<date>`.
   (On Windows, if `python3` isn't found, use `python` or `py` instead.)
