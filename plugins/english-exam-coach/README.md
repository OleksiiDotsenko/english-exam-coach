# English Exam Coach

A coach for **IELTS** (Academic and General Training), **TOEFL iBT** (the
format in use from January 2026) and the Cambridge exams **B1 Preliminary,
B2 First, C1 Advanced and C2 Proficiency**.

It sets original practice in the real exam's format, gives feedback against
public CEFR descriptors with an honest score *range*, and — the part that
makes it coaching rather than grading — keeps a private record of what you
got wrong and brings each point back later on a **freshly written item**,
so you can never answer from memory of the question.

It also works for **tutors**: log a student's full test from any platform,
review it against their earlier tests, see which mistakes are habits and
which are slips, and print practice sheets with answer keys.

> **Indicative, not official.** Scores and level estimates are practice
> feedback, not official results, and do not predict them. This project is
> not affiliated with or endorsed by IELTS, ETS/TOEFL, Cambridge English or
> any exam board; exam names are used only to say what a task prepares for.

## What you can do

- **Writing** — paste an essay, email or report: a band range, a CEFR
  level, and fixes shown as rewrites of *your own sentences*; then a second
  draft, judged criterion by criterion.
- **Speaking** — exam-format tasks under the real clock; feedback on a
  transcript, or on a recording if a speech recogniser is installed.
- **Reading and Use of English** — cloze, key word transformations,
  matching, True/False/Not Given, TOEFL Complete the Words… scored
  objectively, every answer explained.
- **Listening** — original scripts with exam-style questions, spoken with
  your computer's own voice where there is one, read-once otherwise.
- **Vocabulary** — levelled sets with spaced review.
- **Level check, study plan, timed mocks, progress reports.**
- **Full-test review** — record the scores of a whole test, log every
  mistake, and get the history across tests and an **error catalog**: what
  went wrong, how often, in how many tests, and whether it is *chronic*,
  *returned*, *fading* or *closed* (closed means four clean tests in a row —
  not two).
- **Printable sheets** — practice aimed at a learner's known mistakes, with
  an answer key, as a page that prints cleanly or saves as PDF.

## How to use it

Just say what you want — *"help me prepare for TOEFL"*, *"here is my IELTS
Task 2 essay"*, *"review my student's mock test"* — or use a command:

| Command | Does |
|---|---|
| `/start-prep` | guided start: exam → level → section → first task |
| `/assess-level` | a 15-minute CEFR check |
| `/daily-drill` | 10–15 minutes on what your own log says is weakest |
| `/mock-exam` | a timed mock — one section or a whole test |
| `/session-report` · `/progress` | this session · all time |
| `/review-test` | log and review a full test taken elsewhere |
| `/error-catalog` | what keeps going wrong across tests |
| `/worksheet` | a printable practice sheet with a key |

## What it runs, reads and writes

Everything is local. **The plugin makes no network connection, sends no
telemetry, and has no MCP server, no hook and no background process.**

- **Instructions and reference data** — Markdown files the assistant reads:
  exam format facts, paraphrased public CEFR descriptors, and original
  sample items.
- **`scripts/coach.py`** — one command-line tool, Python 3 standard library
  only (Python 3.8 or newer). It records attempts and mistakes, schedules
  re-tests, builds reports, cuts two TOEFL item types to their exact shape,
  and turns Markdown into a printable HTML page. It starts no other program
  and opens no connection; the test suite checks that statically. It reads
  only working files (`.txt`, `.md`, `.json`, `.jsonl`) and replaces only
  pages and archives it wrote itself, so it stays harmless wherever it is
  pointed. Nothing is pre-approved: you decide what may run without asking.
- **Your progress directory** — plain files in a folder you choose
  (`~/english-exam-coach/` by default, or `$EXAM_COACH_HOME`, or `--base`):
  append-only logs of attempts, mistakes and full tests; the re-test queue;
  your target; reports and sheets. In tutor mode each learner has a
  sub-folder of their own. This is the only place the tooling writes,
  besides files you ask it to render. The logs are never rewritten; a
  correction is a new line.
- **Three optional helper scripts** that start programs **already on your
  computer**, used only when a task calls for them and only where there is
  a sound device:
  - `speak.py` — the system speech synthesiser (`say` on macOS;
    `espeak-ng` or `espeak` on Linux) and an audio player (`afplay`,
    `paplay`, `aplay` or `ffplay`), to speak a listening script. Audio goes
    to a temporary folder that is deleted after the drill.
  - `timed_speak.py` — the same voice and player, for the speaking clock.
  - `transcribe.py` — a speech recogniser you have installed
    (`whisper-cli`, `whisper-cpp` or `whisper`) with a model file already
    on disk, and `ffmpeg` or `afconvert` to convert the audio, to
    transcribe a recording **you** give it. It does not record, and nothing
    is uploaded.

  If none of these programs exist, the coach falls back to text.

Nothing is downloaded, installed or updated by the plugin.

**Environment variables.** The plugin reads two, both optional and both
plain settings, not credentials: `EXAM_COACH_HOME` (the folder to keep
progress in) and `EXAM_COACH_LEARNER` (which learner's sub-folder to use).
It reads no token, key, password or account detail from the environment or
from any file, and — having no network code at all — could not send one
anywhere.

## Your data

Practice data stays on your machine, in files you can read, move, back up
or delete. In a cloud session with no folder of yours attached, the coach
says so and offers a one-file export (`coach state export`) that you can
bring back next time. A tutor's records of a student — name, scores,
writing, mistakes — are kept in that student's folder and nowhere else.

## Content policy

No official exam content: no past papers, item banks or mark schemes. Every
practice item is original, written to match public *format facts*.
Assessment anchors are paraphrased from the public CEFR framework.

## More

Source, tests, change log and issue tracker:
<https://github.com/OleksiiDotsenko/english-exam-coach> · MIT licence.
