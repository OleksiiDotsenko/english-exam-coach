---
name: exam-router
description: >
  Use when the user asks to prepare for, practice, or learn about an English
  exam (IELTS, TOEFL iBT, B1 Preliminary, B2 First, C1 Advanced, C2
  Proficiency) without naming a specific task — e.g. "help me prepare for
  TOEFL", "what's in the C1 Advanced reading paper?", "test my English level".
  Resolves exam + CEFR level + section, explains formats from reference data,
  runs a quick level diagnostic, and hands off to the matching macro-skill
  (writing-evaluator, speaking-coach, reading-use-of-english,
  listening-trainer, vocabulary-builder, study-planner).
---

# Exam Router

Entry point and orchestrator. Resolves *which exam, which level, which
section*, then delegates. Does not evaluate work itself.

All plugin file paths below are relative to `${CLAUDE_PLUGIN_ROOT}` (the
plugin's install directory; if the variable is unset, resolve paths relative
to this SKILL.md file, two directories up).

## Supported exams

| exam id | Exam (nominative) | CEFR anchor |
|---|---|---|
| `ielts-academic` | IELTS Academic | B1–C2 (band 0–9) |
| `ielts-general` | IELTS General Training | B1–C2 (band 0–9) |
| `toefl-ibt` | TOEFL iBT (2026 format) | A1–C2 (bands 1–6) |
| `cefr-b1` | B1 Preliminary | B1 |
| `cefr-b2` | B2 First | B2 |
| `cefr-c1` | C1 Advanced | C1 |
| `cefr-c2` | C2 Proficiency | C2 |

## Steps

1. **Resolve the request** to exam id + CEFR level + section. Infer where
   possible ("FCE writing" → `cefr-b2`, B2, writing). If the exam is
   ambiguous AND matters for the task, ask one short question; otherwise
   default sensibly and say what you assumed.
2. **Load** `${CLAUDE_PLUGIN_ROOT}/data/exam-formats/<exam-id>.md`. Answer
   format questions directly from it — never from memory.
3. **Hand off** by section: writing → `writing-evaluator`, speaking →
   `speaking-coach`, reading/use of english → `reading-use-of-english`,
   listening → `listening-trainer`, vocabulary → `vocabulary-builder`,
   study plan / exam date → `study-planner`, results → `progress-tracker`.
4. **Level diagnostic** (when asked "what's my level" or via /assess-level):
   run a compact probe — 5 reading/use-of-english items of graded difficulty,
   one short writing sample (80–120 words), optionally 3 can-do
   self-assessments from `${CLAUDE_PLUGIN_ROOT}/data/cefr/can-do-statements.md`.
   Estimate a CEFR level as a range (e.g. "B2, approaching C1"), state that
   it is indicative, and log the diagnostic via `progress-tracker` with
   `--skill exam-router --task-type level-diagnostic`.
5. **Suggest a next step** grounded in the user's goal (target exam, weakest
   section, or `/daily-drill`).

## Boundaries

- Formats come from the reference files, not memory; if a file and the user
  disagree, flag it rather than guessing.
- Level estimates are indicative, never official.
- Exam names are used nominatively; this plugin is not affiliated with or
  endorsed by any exam board.
- Never reproduce official exam content.
