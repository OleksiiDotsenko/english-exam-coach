---
name: vocabulary-builder
description: >
  Use when the user wants to learn, review, or be quizzed on English
  vocabulary for exams: leveled word sets (B1-C2), collocations, academic
  vocabulary, phrasal verbs, or spaced-repetition review of previously
  studied items ("quiz me on my words", "new C1 vocabulary", "review my
  vocab"). Maintains a Leitner-box review state on disk and logs quiz
  results to the progress log.
---

# Vocabulary Builder

Leveled vocabulary with collocations and a file-based Leitner system. Paths
are relative to `${CLAUDE_PLUGIN_ROOT}` (if unset, resolve relative to this
file). The review state lives in the user's progress directory
(`$EXAM_COACH_HOME` or `~/english-exam-coach/`), NOT in the plugin.

## When to use

The user asks for new vocabulary at a level or topic, asks to review/quiz
existing vocabulary, or meets unknown words in another drill and wants them
kept.

## Steps

1. **New set:** identify level (B1–C2) and theme (topic, exam register,
   e.g. "hedging for C1 writing"). Follow the structure in
   `data/item-bank/seed/vocabulary-sets.md`: 5–8 items per set, each with
   collocations and one original example sentence. **Level the words, not just
   the theme:** pick items whose frequency/register fits the level — B1
   high-frequency everyday; B2 common academic (roughly the AWL mid-bands);
   C1 lower-frequency and abstract; C2 idiomatic/precise nuance — and write the
   example sentence at that level too, so the set carries level-appropriate
   language beyond the headword. Note that hedging and precision-verb sets sit
   at C1/C2, not B1–B2. Open lists like the Academic Word List may be
   referenced nominatively.

2. **Persist for review:** append new items to `<base>/vocab-box.json`
   (create if missing). The file is a JSON array; each element is
   `{"item": ..., "level": ..., "box": 1, "added": "YYYY-MM-DD", "due": "YYYY-MM-DD"}`
   with ISO dates. New items enter **box 1** with `due` = today, so they
   surface in the next review round.
   **Canonical Leitner intervals (must match `vocabulary-sets.md`):**
   box 1 = next session · box 2 = 1 day · box 3 = 3 days · box 4 = 7 days ·
   box 5 = 30 days (mature). This file is working state and MAY be
   rewritten — unlike `attempts.jsonl`, which this skill never touches
   directly.

3. **Review ("quiz me"):** read `vocab-box.json`, select items with
   `due <= today` (oldest first, max ~12 per round). Quiz actively — ask for
   the word from a definition/gap sentence, or a collocation completion; a
   plain "do you remember this?" is not a test. Correct → box +1 (max 5),
   set `due` = today + the new box's interval above; wrong → back to box 1,
   `due` = today (next session). Rewrite the file once at the end of the
   round.

4. **Score the round** (n correct / n asked) and show which items fell back
   to box 1.

5. **Log the round** (silently):
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/progress-tracker/scripts/log_attempt.py" \
     --exam <target-exam or cefr level file, e.g. cefr-c1> \
     --skill vocabulary-builder --task-type spaced-review \
     --level <level> --score <n> --max <asked> --seconds <time>
   ```
   (On Windows without `python3`, use `python` or `py` instead.)
   A due-based round often mixes levels, but the log takes one `--level` and
   one `--exam`: set `--level` to the modal (most common) level of the items
   quizzed and `--exam` to the user's target exam (or the `cefr-<level>` file
   matching that modal level) — for a mixed round the review level is only a
   rough anchor.
   For a new-set study session without a quiz, do not log — only tested
   recall counts as an attempt.

## Boundaries

- Word lists and example sentences are original or from open sources named
  nominatively; never proprietary coursebook or exam-board vocabulary banks.
- `vocab-box.json` is the only file this skill rewrites; never touch
  `attempts.jsonl` except through `log_attempt.py`.
- Do not log rounds that didn't happen; unanswered items count as wrong only
  if the user gave up, not if the session was cut short.
