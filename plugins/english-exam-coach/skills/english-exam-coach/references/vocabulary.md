# Vocabulary

Read this when the user asks for new vocabulary at a level or on a topic,
asks to review or be quizzed on vocabulary they have studied, or meets
unknown words in another drill and wants them kept. `coach <command>` is
defined in `SKILL.md`.

The review state is a file in the learner's progress directory —
`<base>/vocab-box.json`. `coach state show` prints where `<base>` is (with
`--learner <name>` in tutor mode).

## Steps

1. **New set:** identify the level (B1–C2) and the theme (a topic, or an
   exam register such as "hedging for C1 writing"). Follow the structure in
   `data/item-bank/seed/vocabulary-sets.md`: 5–8 items per set, each with
   collocations and one original example sentence. **Level the words, not
   just the theme:** pick items whose frequency and register fit the level —
   B1 high-frequency everyday; B2 common academic (roughly the middle bands
   of the Academic Word List); C1 lower-frequency and abstract; C2 idiomatic
   and precise — and write the example sentence at that level too, so the
   set carries level-appropriate language beyond the headword. Hedging and
   precision-verb sets sit at C1/C2, not B1–B2. Open lists such as the
   Academic Word List may be named.

2. **Keep it for review:** append new items to `<base>/vocab-box.json`
   (create it if missing). The file is a JSON array; each element is
   `{"item": ..., "level": ..., "box": 1, "added": "YYYY-MM-DD", "due": "YYYY-MM-DD"}`
   with ISO dates. New items enter **box 1** with `due` = today, so they
   surface in the next review round.
   **Leitner intervals (they must match `vocabulary-sets.md`):**
   box 1 = next session · box 2 = 1 day · box 3 = 3 days · box 4 = 7 days ·
   box 5 = 30 days (mature). This file is working state and MAY be
   rewritten — unlike the logs, which are only ever appended to through
   `coach`.

3. **Review ("quiz me"):** read `vocab-box.json` and select items with
   `due <= today` (oldest first, about 12 per round at most). Quiz actively
   — ask for the word from a definition or a gapped sentence, or for a
   collocation to be completed; a plain "do you remember this?" is not a
   test. Correct → box +1 (5 at most), `due` = today + the new box's
   interval; wrong → back to box 1, `due` = today. Rewrite the file once at
   the end of the round.

4. **Score the round** (n correct of n asked) and show which items fell
   back to box 1.

5. **Log the round** (silently):
   ```bash
   coach log-attempt \
     --exam <target exam, or the cefr-<level> id> \
     --skill vocabulary-builder --task-type spaced-review \
     --level <level> --score <n> --max <asked> --seconds <time>
   ```
   When an item is missed for a reason worth re-testing beyond the word
   itself — a wrong form, a collocation, a register slip — log it with
   `coach log-error` under `vocabulary` and run `coach queue sync`: the word
   stays in the Leitner box, the *pattern* enters the queue. See
   `references/the-loop.md`.
   A round often mixes levels, but the log takes one `--level` and one
   `--exam`: use the most common level among the items quizzed, and the
   user's target exam (or the `cefr-<level>` id for that level).
   A study session with no quiz is not logged — only tested recall counts
   as an attempt.

## Boundaries

- Word lists and example sentences are original, or from open sources that
  are named; never from a proprietary coursebook or an exam board's
  vocabulary bank.
- `vocab-box.json` is the only file you rewrite directly. Never touch the
  logs except through `coach`.
- Do not log rounds that did not happen; unanswered items count as wrong
  only if the user gave up, not if the session was cut short.
