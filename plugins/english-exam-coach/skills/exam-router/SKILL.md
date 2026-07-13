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
   - **Items:** 8 use-of-english items, 2 per level B1–C2 (mix open cloze,
     multiple-choice cloze, one inference item), presented easiest-first.
     **Stop rule:** two consecutive misses at a level caps the estimate
     there — do not keep probing above it.
   - **Writing sample** (80–120 words) is the primary evidence: place it
     against `${CLAUDE_PLUGIN_ROOT}/data/cefr/calibration-anchors.md` per
     criterion; the items refine, they don't outvote it.
   - Optionally add 3 can-do self-checks from
     `${CLAUDE_PLUGIN_ROOT}/data/cefr/can-do-statements.md`.
   - **Report** a CEFR range (e.g. "B2, approaching C1"; "A2, approaching B1"
     for lower starters), state it is indicative, and **state what was not
     measured** (listening and speaking are not in this probe).
   - **Log it** with every required field, using `--cefr-estimate` (that is
     what feeds cross-exam trends — a bare `--band-estimate "B2-C1"` has no
     numbers and normalizes to nothing):
     ```bash
     python3 "${CLAUDE_PLUGIN_ROOT}/skills/progress-tracker/scripts/log_attempt.py" \
       --exam <target exam or cefr-XX> --skill exam-router \
       --task-type level-diagnostic --level <nearest anchor> \
       --cefr-estimate <estimated level> --score <items correct> --max 8 \
       --seconds <measured>
     ```
5. **Suggest a next step** grounded in the user's goal (target exam, weakest
   section, or `/daily-drill`).

## Boundaries

- Formats come from the reference files, not memory; if a file and the user
  disagree, flag it rather than guessing.
- Level estimates are indicative, never official.
- Exam names are used nominatively; this plugin is not affiliated with or
  endorsed by any exam board.
- Never reproduce official exam content.
