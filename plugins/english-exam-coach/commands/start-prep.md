---
description: Guided entry point - pick your exam, level and section, then start practicing
argument-hint: "[optional: exam and/or section to skip questions, e.g. toefl-ibt writing]"
---

Start a guided exam-prep session: $ARGUMENTS

Walk the user from zero to a running practice task. Ask ONE question at a
time, keep each question short, and skip any question already answered by
the arguments or the conversation.

1. **Returning learner check.** Run
   `python3 "${CLAUDE_PLUGIN_ROOT}/skills/progress-tracker/scripts/build_report.py" --scope all --no-write`
   (ignore errors if the log does not exist yet; on Windows, if `python3`
   isn't found, use `python` or `py`). If there is history, open
   with a one-line status — last session date, current weakest task type —
   and offer "pick up where you left off" (drill the weakest task type) as
   the first option before asking anything else.

2. **Progress storage (first-time setup).** If step 1 found no history,
   this is a fresh learner: mention that progress is saved to
   `~/english-exam-coach/` by default, and offer a custom location — set the
   `EXAM_COACH_HOME` environment variable to any folder (e.g. an Obsidian
   vault) to keep the log there instead. Settle this before the first
   attempt is logged. Skip silently for returning learners.

3. **Exam.** Ask which exam they are preparing for:
   IELTS Academic (`ielts-academic`), IELTS General Training
   (`ielts-general`), TOEFL iBT (`toefl-ibt`), or a CEFR-level exam:
   B1 (`cefr-b1`), B2 (`cefr-b2`), C1 (`cefr-c1`), C2 (`cefr-c2`).
   If they are unsure which exam they need, ask what it is for (university,
   migration, work, general proof of level) and recommend one, using the
   `exam-router` skill's knowledge.

4. **Level and target.** For `cefr-*` exams the level is implied — skip the
   level question. For IELTS/TOEFL ask for their current working level
   (B1/B2/C1/C2); if they do not know, offer the 15-minute diagnostic
   (`/assess-level`) and use its result. Also ask what score they need and
   when they sit the exam, then save it once so every later session can be
   specific about the gap:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/progress-tracker/scripts/profile.py" set \
     --exam <exam-id> --target-score <score> --exam-date <YYYY-MM-DD> \
     --current-level <CEFR>
   ```
   Omit any flag they cannot answer — a partial profile is fine, and the
   command prints the target translated into CEFR. If they do not have a
   target or a date, skip this and do not ask twice.

5. **Section.** Ask what to work on: Writing, Speaking,
   Reading / Use of English, Listening, or Vocabulary — or a full timed
   section (point to `/mock-exam <exam-id> <section>`) or a week-by-week
   plan toward an exam date (hand off to the `study-planner` skill).

6. **Mode.** Ask whether they want to (a) practice a new task, (b) get
   feedback on something they already wrote or recorded, or (c) first see
   how the section works — for (c), explain the format from
   `${CLAUDE_PLUGIN_ROOT}/data/exam-formats/<exam-id>.md`, then offer (a).

7. **Hand off.** Route to the matching skill via the `exam-router` skill
   (writing-evaluator, speaking-coach, reading-use-of-english,
   listening-trainer, or vocabulary-builder) with the chosen exam, level,
   and task type. The skill generates or evaluates, scores, and logs the
   attempt as usual; scores are indicative self-practice estimates.
