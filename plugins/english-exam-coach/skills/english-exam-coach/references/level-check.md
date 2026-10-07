# Level check — a 15-minute CEFR probe

Read this when the user asks what their level is, or needs a starting point
before a plan or a first drill. `coach <command>` is defined in `SKILL.md`.

## The probe

- **Items:** 8 use-of-English items, 2 per level B1–C2 (a mix of open
  cloze, multiple-choice cloze and one inference item), presented easiest
  first. **Stop rule:** two misses in a row at a level cap the estimate
  there — do not keep probing above it.
- **Writing sample** (80–120 words) is the primary evidence: place it
  against `data/cefr/calibration-anchors.md` per criterion; the items
  refine the estimate, they do not outvote it.
- Optionally add 3 can-do self-checks from
  `data/cefr/can-do-statements.md`.
- If the user has already logged work, read it first (`coach report --scope
  all --no-write`): recent evidence may make the probe unnecessary.

## The result

- **Report one blended CEFR range** ("B2, approaching C1"; "A2, approaching
  B1" for a lower starter). Say that it is indicative, and **say what was
  not measured**: listening and speaking are not in this probe.
- If the user named a target exam, state the gap to that exam's usual pass
  level (`coach convert` for the scale) and suggest the first drill.
- **Below B1:** say the estimate plainly, explain that guided practice here
  starts at B1, and make B1 the working target.

## Logging — exactly once

```bash
coach log-attempt \
  --exam <target exam, or cefr-<level>> --skill exam-router \
  --task-type level-diagnostic --level <nearest anchor> \
  --cefr-estimate <estimated level> --score <items correct> --max 8 \
  --seconds <measured>
```

Use `--cefr-estimate`: it is what feeds the trends across exams (a bare
`--band-estimate "B2-C1"` has no numbers in it and normalises to nothing).
Log the probe once, however it was reached. The `level-diagnostic` row is
reference only — a probe, not a drillable task — so never offer it as the
"weakest task type" to practise.

Then save the level so later sessions can use it: `coach profile set
--current-level <CEFR>` (add `--exam` and `--target-score` if the user
gave them), and suggest a next step grounded in their goal.

## Boundaries

- Level estimates are indicative, never official.
- Formats and descriptors come from the files in `data/`, not from memory.
- Never reproduce official exam content in the probe items.
