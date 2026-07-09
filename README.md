# English Exam Coach

A Claude Code plugin — a bundle of Agent Skills — for preparing for
standardized English exams: **IELTS (Academic & General)**, **TOEFL iBT**,
and the **CEFR-level exams B1–C2** (B1 Preliminary, B2 First, C1 Advanced,
C2 Proficiency).

Practice any section of any supported exam from inside Claude Code:
generate original tasks in the correct format, get feedback mapped to public
CEFR descriptors with an indicative band/score range, and track every
attempt on disk so you can see trends, weak task types, and what to drill
next.

> **Indicative, not official.** All scores and level estimates produced by
> this plugin are self-practice estimates. They are not official results and
> do not predict them. This project is not affiliated with, endorsed by, or
> connected to IELTS, ETS/TOEFL, Cambridge English, or any exam board; exam
> names are used nominatively to describe compatibility.

## Install

```
/plugin marketplace add OleksiiDotsenko/english-exam-coach
/plugin install english-exam-coach@english-exam-coach
```

Requires Python 3 on PATH for progress tracking (standard library only — no
third-party packages).

## Quickstart

| Say / run | What happens |
|---|---|
| `/start-prep` | Guided start: pick exam → level → section → practice |
| `/assess-level toefl-ibt` | 15-minute CEFR diagnostic, logged as your baseline |
| "Give me a C1 Advanced key word transformation drill" | Original items, objective scoring, explanations, logged |
| "Here's my IELTS Task 2 essay: …" | Criteria-based feedback, band range + CEFR level, prioritized rewrites, logged |
| `/mock-exam cefr-c1 reading` | Full timed section, no hints, scored and logged |
| `/daily-drill` | 10–15 min drill on your weakest task type from the log |
| `/session-report` · `/progress` | Markdown reports for the session / all time |

A typical loop: task is generated → you answer → the skill scores it →
the attempt is appended to your log → reports show trends and the next
recommended drill.

## Supported exams

| exam id | Exam | CEFR anchor | Scale |
|---|---|---|---|
| `ielts-academic` | IELTS Academic | B1–C2 | Bands 0–9 |
| `ielts-general` | IELTS General Training | B1–C2 | Bands 0–9 |
| `toefl-ibt` | TOEFL iBT (2026 format) | A1–C2 | Bands 1–6, half steps |
| `cefr-b1` | B1 Preliminary | B1 | Cambridge English Scale |
| `cefr-b2` | B2 First | B2 | Cambridge English Scale |
| `cefr-c1` | C1 Advanced | C1 | Cambridge English Scale |
| `cefr-c2` | C2 Proficiency | C2 | Cambridge English Scale |

Format facts live in [data/exam-formats/](plugins/english-exam-coach/data/exam-formats/)
— task types, item counts, timings, word counts, scales. Formats change
occasionally; confirm details with the exam provider before test day.

## How progress tracking works

Two layers, both plain files in your own workspace (never inside the plugin):

- `attempts.jsonl` — append-only log, one JSON line per scored attempt.
  **Source of truth.** The tooling only ever appends; "clearing progress" is
  a deliberate manual action (delete the file yourself), never a side effect.
- `reports/*.md` — session reports and an all-time overview, derived from
  the log and regenerable at any time, with YAML frontmatter.

Cross-exam trends are normalized to CEFR — an IELTS band and a TOEFL score
are never merged into one number.

**Where the files live** (first match wins):

1. `--base` flag on the scripts
2. `EXAM_COACH_HOME` environment variable
3. `~/english-exam-coach/` (created on first use)

### Obsidian / Dataview (optional)

Point `EXAM_COACH_HOME` at a folder inside your vault and the generated
reports' frontmatter (`type`, `date`, `session`, `tasks`, `minutes`,
`exams`) makes cross-session Dataview tables and trend views work with no
extra code.

## What's inside

- **Skills** (organized by macro-skill, not by exam — exam differences are
  data, not code): `exam-router`, `writing-evaluator`, `speaking-coach`,
  `reading-use-of-english`, `listening-trainer`, `vocabulary-builder`,
  `study-planner`, `progress-tracker`.
- **Commands:** `/start-prep`, `/mock-exam`, `/daily-drill`,
  `/assess-level`, `/session-report`, `/progress`.
- **Data:** exam format facts, paraphrased public CEFR descriptors, and a
  small bank of original seed items used as format references.
- **Scripts:** `log_attempt.py` and `build_report.py` — Python 3 standard
  library only.

Listening drills are text-first in v0.1: on macOS the built-in `say` command
is used for audio when available; otherwise drills degrade gracefully to
script-based practice. No third-party TTS dependency.

## Content and IP policy

- **No official exam content.** No past papers, official item banks, or
  official mark schemes anywhere in this repository. All practice items are
  original, generated to match public *format facts* (task types, counts,
  timings, scales — facts are not copyrightable).
- **Public descriptors only.** Evaluation anchors are paraphrased from the
  public CEFR framework (Council of Europe); criterion *names* are used
  nominatively.
- **Brand-neutral naming.** Files and identifiers are named by CEFR level
  where possible; trademarks appear only nominatively, with no claim of
  affiliation or endorsement.

If you believe any content in this repository crosses these lines, please
open an issue — it will be treated as a bug.

## Development

```bash
python3 -m unittest discover -s tests   # from the repo root
claude plugin validate ./plugins/english-exam-coach
```

Design notes: skills are procedures, exam differences are reference data
loaded on demand; the progress log is append-only and reports are derived.
Defaults chosen for v0.1: separate IELTS Academic/General format files,
text-first listening, MIT license, log location `~/english-exam-coach/`
(configurable via `EXAM_COACH_HOME`).

## License

[MIT](LICENSE) © 2026 Oleksii Dotsenko
