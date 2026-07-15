#!/usr/bin/env python3
"""Build a Markdown progress report from the attempts.jsonl log.

Reads <base>/attempts.jsonl (append-only source of truth), derives a report,
writes it under <base>/reports/ and prints it to stdout. Reports are derived
artifacts: rebuilding them is always safe, the log is never modified.

Scopes:
  --scope session   one session only (default: the most recent session id)
  --scope all       full history: trends, streak, best/worst task types

CEFR normalization is intentionally coarse and clearly indicative:
  1. an explicit cefr_estimate on the log line always wins;
  2. IELTS band midpoints map via the public IELTS/CEFR alignment;
  3. TOEFL iBT bands (1-6 scale, tests from Jan 2026) map via the official
     ETS CEFR alignment; legacy 0-30 section scores (pre-2026 logs and the
     TOEFL iBT Australia carve-out) map via the published legacy cut scores;
  4. otherwise an objective score/max at a task's anchor level maps by
     percentage: >=80%% at level, 60-79%% borderline, <60%% below level.
Raw values are never merged across exams; only CEFR is compared.

Base directory resolution (first match wins):
  1. --base CLI flag
  2. EXAM_COACH_HOME environment variable
  3. ~/english-exam-coach/
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

LOG_NAME = "attempts.jsonl"
DISCLAIMER = ("*Indicative self-practice estimates, not official scores. "
              "Not affiliated with any exam board.*")

# CEFR levels on a numeric axis (halves = borderline between two levels).
CEFR_NUM = {"A1": 1.0, "A2": 2.0, "B1": 3.0, "B2": 4.0, "C1": 5.0, "C2": 6.0}
NUM_CEFR = {v: k for k, v in CEFR_NUM.items()}

# Public IELTS band -> CEFR alignment (band >= threshold).
IELTS_BAND_TO_CEFR = ((8.5, "C2"), (7.0, "C1"), (5.5, "B2"), (4.0, "B1"), (0.0, "A2"))

# Official ETS CEFR alignment for the TOEFL iBT 1-6 band scale (Jan 2026+),
# identical for overall and per-section bands.
TOEFL_BAND_TO_CEFR = ((6.0, "C2"), (5.0, "C1"), (4.0, "B2"),
                      (3.0, "B1"), (2.0, "A2"), (0.0, "A1"))

# Published ETS section score -> CEFR minimums for the legacy 0-30 scale
# (logs from before Jan 2026 and the TOEFL iBT Australia carve-out).
TOEFL_LEGACY_CUTS = {
    "reading":   ((29, "C2"), (24, "C1"), (18, "B2"), (4, "B1")),
    "listening": ((28, "C2"), (22, "C1"), (17, "B2"), (9, "B1")),
    "speaking":  ((28, "C2"), (25, "C1"), (20, "B2"), (16, "B1")),
    "writing":   ((29, "C2"), (24, "C1"), (17, "B2"), (13, "B1")),
}

SKILL_MACRO = {
    "writing-evaluator": "writing",
    "speaking-coach": "speaking",
    "reading-use-of-english": "reading",
    "listening-trainer": "listening",
    "vocabulary-builder": "vocabulary",
}

# Holistically scored skills log band/CEFR estimates; the band and legacy-0-30
# scales apply ONLY to these. Objective skills log raw item counts via
# --score/--max, so a count of 6, 9 or 30 must never be read as a band.
HOLISTIC_SKILLS = ("writing-evaluator", "speaking-coach")

SKILL_DISPLAY = {
    "writing-evaluator": "Writing",
    "speaking-coach": "Speaking",
    "reading-use-of-english": "Reading/UoE",
    "listening-trainer": "Listening",
    "vocabulary-builder": "Vocabulary",
    "study-planner": "Planning",
    "exam-router": "Diagnostic",
}

EXAM_DISPLAY = {
    "ielts-academic": "IELTS Academic",
    "ielts-general": "IELTS General",
    "toefl-ibt": "TOEFL iBT",
    "cefr-b1": "CEFR B1",
    "cefr-b2": "CEFR B2",
    "cefr-c1": "CEFR C1",
    "cefr-c2": "CEFR C2",
    # Legacy ids from logs written before the brand-neutral rename.
    "b1-preliminary": "CEFR B1",
    "b2-first": "CEFR B2",
    "c1-advanced": "CEFR C1",
    "c2-proficiency": "CEFR C2",
}


def default_base():
    env = os.environ.get("EXAM_COACH_HOME", "").strip()
    if env:
        return Path(env).expanduser()
    return Path.home() / "english-exam-coach"


def read_log(log_path):
    """Return (attempts, skipped_count). Malformed lines are skipped, never fatal."""
    attempts, skipped = [], 0
    with open(log_path, encoding="utf-8") as log:
        for raw in log:
            raw = raw.strip()
            if not raw:
                continue
            try:
                row = json.loads(raw)
            except ValueError:
                skipped += 1
                continue
            if not isinstance(row, dict) or "ts" not in row or "session" not in row \
                    or not all(row.get(k) for k in ("exam", "skill", "task_type")):
                # Missing core fields → cannot render meaningfully; skip, never crash.
                skipped += 1
                continue
            attempts.append(row)
    return attempts, skipped


def parse_ts(row):
    try:
        parsed = datetime.fromisoformat(str(row.get("ts")))
    except ValueError:
        return None
    if parsed.tzinfo is not None:
        # Normalize timezone-aware timestamps to naive local time so a log
        # mixing both forms never breaks date comparisons in the reports.
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed


def band_midpoint(band_estimate):
    """'6.5-7.0' -> 6.75; '7' -> 7.0; None on parse failure."""
    if not band_estimate:
        return None
    parts = re.split(r"[-–]", str(band_estimate))
    values = []
    for part in parts:
        part = part.strip()
        try:
            values.append(float(part))
        except ValueError:
            continue
    if not values:
        return None
    return sum(values) / len(values)


def from_cuts(value, cuts):
    for threshold, level in cuts:
        if value >= threshold:
            return CEFR_NUM[level]
    return None


def cefr_value(row):
    """Best-effort normalized CEFR as a number (halves = borderline), or None."""
    explicit = str(row.get("cefr_estimate") or "").strip().upper()
    if explicit in CEFR_NUM:
        return CEFR_NUM[explicit]

    exam = str(row.get("exam") or "")
    skill = str(row.get("skill") or "")
    score, max_score = row.get("score"), row.get("max")
    # Band / legacy-section scales apply only to holistic skills; a raw item
    # count from an objective drill must never be reinterpreted as a band.
    holistic = skill in HOLISTIC_SKILLS

    if exam.startswith("ielts"):
        band = band_midpoint(row.get("band_estimate"))
        if band is None and holistic and isinstance(score, (int, float)) \
                and max_score in (None, 9) and 0 <= float(score) <= 9:
            band = float(score)
        if band is not None:
            return from_cuts(band, IELTS_BAND_TO_CEFR)

    if exam == "toefl-ibt":
        band = band_midpoint(row.get("band_estimate"))
        if band is None and holistic and isinstance(score, (int, float)):
            # New 1-6 band scale: explicit max of 6, or a band-sized bare score.
            if max_score == 6 or (max_score is None and 0 < float(score) <= 6):
                band = float(score)
        if band is not None:
            return from_cuts(band, TOEFL_BAND_TO_CEFR)
        macro = SKILL_MACRO.get(skill)
        if holistic and macro in TOEFL_LEGACY_CUTS \
                and isinstance(score, (int, float)) and max_score in (None, 30):
            return from_cuts(float(score), TOEFL_LEGACY_CUTS[macro])

    anchor = CEFR_NUM.get(str(row.get("level") or "").strip().upper())
    if anchor and isinstance(score, (int, float)) \
            and isinstance(max_score, (int, float)) and max_score > 0:
        pct = float(score) / float(max_score)
        floor = CEFR_NUM["A1"]
        # Finer than three buckets so a total failure is distinguishable from a
        # near-miss, and aspirational above-level practice is not over-credited.
        if pct >= 0.8:
            return anchor
        if pct >= 0.6:
            return max(floor, anchor - 0.5)
        if pct >= 0.4:
            return max(floor, anchor - 1.0)
        if pct >= 0.2:
            return max(floor, anchor - 1.5)
        return max(floor, anchor - 2.0)
    return None


def cefr_label(value):
    if value is None:
        return "?"
    if value < CEFR_NUM["A1"]:
        return "<A1"
    if value in NUM_CEFR:
        return NUM_CEFR[value]
    lower, upper = NUM_CEFR.get(value - 0.5), NUM_CEFR.get(value + 0.5)
    if lower and upper:
        return "%s/%s" % (lower, upper)
    return NUM_CEFR.get(round(value), "?")


def quality(row):
    """Level-relative attainment in 0..1 for ranking task types, or None.

    1.0 = performing at or above the task's target (anchor) level; each
    half-level below subtracts 0.25. Putting band-scored and objective
    tasks on one CEFR-relative axis keeps the 'weakest task type' ranking
    from being biased by which scoring scale a task happens to use.
    """
    anchor = CEFR_NUM.get(str(row.get("level") or "").strip().upper())
    achieved = cefr_value(row)
    score, max_score = row.get("score"), row.get("max")
    is_objective = isinstance(score, (int, float)) \
        and isinstance(max_score, (int, float)) and max_score > 0
    if anchor is not None and achieved is not None:
        att = max(0.0, min(1.0, 1.0 + (achieved - anchor) / 2.0))
        if is_objective:
            # At the A1 floor the CEFR value can't fall further, so also cap by
            # the raw percentage (80% = at level) — a near-total failure must
            # not read as "at level" just because A1 is the bottom of the scale.
            att = max(0.0, min(att, float(score) / float(max_score) / 0.8))
        return att
    # No anchor/CEFR available: fall back to a raw objective percentage.
    if is_objective:
        return max(0.0, min(1.0, float(score) / float(max_score)))
    return None


def attainment_phrase(avg):
    """Describe an average attainment (0..1) relative to the target level."""
    if avg >= 0.9:
        return "at or above your target level"
    if avg >= 0.7:
        return "about half a level below target"
    if avg >= 0.4:
        return "about a level below target"
    return "well below your target level"


def fmt_num(value):
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def fmt_result(row):
    if row.get("band_estimate"):
        return str(row["band_estimate"]).replace("-", "–")
    if row.get("score") is not None and row.get("max") is not None:
        return "%s/%s" % (fmt_num(row["score"]), fmt_num(row["max"]))
    if row.get("score") is not None:
        return fmt_num(row["score"])
    return "—"


def fmt_time(seconds):
    try:
        seconds = float(seconds)
    except (TypeError, ValueError):
        return "?"
    if round(seconds) < 60:
        return "%ds" % round(seconds)
    minutes = seconds / 60.0
    return "%gm" % round(minutes, 1) if minutes < 10 else "%dm" % round(minutes)


def display_skill(skill):
    return SKILL_DISPLAY.get(skill, str(skill).replace("-", " ").title())


def display_exam(exam):
    return EXAM_DISPLAY.get(exam, str(exam).replace("-", " ").title())


def display_task(task_type):
    return str(task_type).replace("-", " ").capitalize()


def mean(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def group_by(rows, key):
    grouped = {}
    for row in rows:
        grouped.setdefault(str(row.get(key)), []).append(row)
    return grouped


def plural(count, singular, suffix="s"):
    return "%d %s%s" % (count, singular, "" if count == 1 else suffix)


def rank_task_types(rows):
    """[(task_type, avg_quality, attempts)] sorted weakest first.

    Ties break on task_type name so the ranking (and every report and test
    that depends on it) is deterministic.
    """
    ranked = []
    for task_type, task_rows in group_by(rows, "task_type").items():
        avg = mean([quality(r) for r in task_rows])
        if avg is not None:
            ranked.append((task_type, avg, len(task_rows)))
    ranked.sort(key=lambda item: (item[1], item[0]))
    return ranked


def streak_days(rows):
    """Consecutive days practised, ending on the most recent practice day."""
    days = sorted({ts.date() for ts in (parse_ts(r) for r in rows) if ts})
    if not days:
        return 0
    streak, cursor = 1, days[-1]
    for day in reversed(days[:-1]):
        if cursor - day == timedelta(days=1):
            streak += 1
            cursor = day
        else:
            break
    return streak


def level_summary(rows):
    """'~C1 (writing), ~B2 (speaking)' from per-macro-skill CEFR averages."""
    parts = []
    for skill, skill_rows in sorted(group_by(rows, "skill").items()):
        avg = mean([cefr_value(r) for r in skill_rows])
        if avg is None:
            continue
        macro = SKILL_MACRO.get(skill, display_skill(skill).lower())
        parts.append("~%s (%s)" % (cefr_label(round(avg * 2) / 2), macro))
    return ", ".join(parts)


def recommendation(rows):
    ranked = rank_task_types(rows)
    if not ranked:
        return "Log a few scored attempts, then rebuild this report."
    task_type, avg, _count = ranked[0]
    sample = next(r for r in rows if str(r.get("task_type")) == task_type)
    where = "%s at %s" % (display_task(task_type), sample.get("level", "?"))
    if avg < 0.9:
        return ("%s is your weakest area (%s) — drill 10 more, "
                "then re-test." % (where, attainment_phrase(avg)))
    return ("All task types are at their target level — keep the balance and "
            "try a full timed mock next (weakest: %s)." % where)


def attempts_table(rows):
    lines = ["| Skill | Task | Exam | Result | Time |", "|---|---|---|---|---|"]
    for row in rows:
        lines.append("| %s | %s | %s | %s | %s |" % (
            display_skill(row.get("skill")),
            display_task(row.get("task_type")),
            display_exam(row.get("exam")),
            fmt_result(row),
            fmt_time(row.get("seconds")),
        ))
    return "\n".join(lines)


def frontmatter(kind, date, tasks, minutes, exams, session=None):
    lines = ["---", "type: %s" % kind, "date: %s" % date.isoformat()]
    if session:
        lines.append("session: %s" % session)
    lines += ["tasks: %d" % tasks,
              "minutes: %d" % minutes,
              "exams: [%s]" % ", ".join(sorted(exams)),
              "---"]
    return "\n".join(lines)


def report_date(rows):
    stamps = [ts for ts in (parse_ts(r) for r in rows) if ts]
    return max(stamps).date() if stamps else datetime.now().date()


def total_minutes(rows):
    seconds = 0.0
    for row in rows:
        try:
            seconds += float(row.get("seconds") or 0)
        except (TypeError, ValueError):
            # A malformed seconds value must not abort the whole report.
            continue
    return int(round(seconds / 60.0))


def human_date(date):
    return "%d %s %d" % (date.day, date.strftime("%b"), date.year)


def session_title(session, date):
    suffix = ""
    match = re.search(r"-(am|pm)$", session)
    if match:
        suffix = " (%s)" % match.group(1).upper()
    return "# Session Report — %s%s" % (human_date(date), suffix)


def build_session_report(rows, session):
    date = report_date(rows)
    minutes = total_minutes(rows)
    exams = {str(r.get("exam")) for r in rows}

    parts = [
        frontmatter("exam-session", date, len(rows), minutes, exams, session),
        "",
        session_title(session, date),
        "",
        "**%d task%s · %d min on task**" % (
            len(rows), "" if len(rows) == 1 else "s", minutes),
        "",
        attempts_table(rows),
        "",
    ]
    levels = level_summary(rows)
    if levels:
        parts.append("**Estimated level this session:** %s" % levels)
    ranked = rank_task_types(rows)
    if ranked:
        weakest, avg, _ = ranked[0]
        parts.append("**Weakest:** %s — %s." % (
            display_task(weakest), attainment_phrase(avg)))
    parts += ["**Next:** %s" % recommendation(rows), "", DISCLAIMER, ""]
    return "\n".join(parts)


def trend_arrow(first, last):
    if first is None or last is None:
        return None
    if last > first:
        return "improving"
    if last < first:
        return "slipping"
    return "steady"


def skill_trends(rows):
    lines = []
    for skill, skill_rows in sorted(group_by(rows, "skill").items()):
        values = [cefr_value(r) for r in skill_rows]
        values = [v for v in values if v is not None]
        if len(values) < 2:
            continue
        half = max(1, len(values) // 2)
        first, last = mean(values[:half]), mean(values[half:])
        arrow = trend_arrow(round(first, 2), round(last, 2))
        lines.append("- **%s:** %s → %s (%s, %d attempts)" % (
            display_skill(skill),
            cefr_label(round(first * 2) / 2),
            cefr_label(round(last * 2) / 2),
            arrow, len(skill_rows)))
    return lines


def exam_lines(rows):
    lines = []
    for exam, exam_rows in sorted(group_by(rows, "exam").items()):
        avg = mean([quality(r) for r in exam_rows])
        detail = " · %s" % attainment_phrase(avg) if avg is not None else ""
        lines.append("- **%s:** %s%s" % (
            display_exam(exam), plural(len(exam_rows), "attempt"), detail))
    return lines


def build_overview_report(rows):
    date = report_date(rows)
    minutes = total_minutes(rows)
    exams = {str(r.get("exam")) for r in rows}
    sessions = {str(r.get("session")) for r in rows}
    days = {ts.date() for ts in (parse_ts(r) for r in rows) if ts}

    streak = streak_days(rows)
    recent = max(days) if days else None
    # "current" only if practice reaches into today or yesterday; otherwise the
    # run has lapsed and calling it current would be misleading.
    streak_label = "current streak"
    if recent is not None and recent < datetime.now().date() - timedelta(days=1):
        streak_label = "last streak"

    parts = [
        frontmatter("progress-overview", date, len(rows), minutes, exams),
        "",
        "# Progress Overview — through %s" % human_date(date),
        "",
        "**%s · %s · %s practised · %d min on task · %s: %s**" % (
            plural(len(rows), "attempt"), plural(len(sessions), "session"),
            plural(len(days), "day"), minutes,
            streak_label, plural(streak, "day")),
        "",
    ]

    trends = skill_trends(rows)
    if trends:
        parts += ["## CEFR trend per skill", ""] + trends + [""]

    parts += ["## Exams practised", ""] + exam_lines(rows) + [""]

    ranked = rank_task_types(rows)
    if ranked:
        parts += ["## Task types", ""]
        best = ranked[-1]
        worst = ranked[0]
        parts.append("- **Strongest:** %s — %s over %s" % (
            display_task(best[0]), attainment_phrase(best[1]),
            plural(best[2], "attempt")))
        parts.append("- **Weakest:** %s — %s over %s" % (
            display_task(worst[0]), attainment_phrase(worst[1]),
            plural(worst[2], "attempt")))
        parts.append("")

    levels = level_summary(rows)
    if levels:
        parts += ["**Estimated current level:** %s" % levels, ""]
    parts += ["**Next:** %s" % recommendation(rows), "", DISCLAIMER, ""]
    return "\n".join(parts)


def safe_filename(name):
    return re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-") or "report"


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--scope", choices=("session", "all"), default="session")
    parser.add_argument("--session", default=None,
                        help="session id to report on (default: most recent in log)")
    parser.add_argument("--base", default=None,
                        help="progress directory (default: $EXAM_COACH_HOME "
                             "or ~/english-exam-coach)")
    parser.add_argument("--no-write", action="store_true",
                        help="print the report without writing a file")
    args = parser.parse_args(argv)

    base = Path(args.base).expanduser() if args.base else default_base()
    log_path = base / LOG_NAME
    if not log_path.exists():
        print("No log found at %s — nothing to report yet." % log_path)
        return 0

    attempts, skipped = read_log(log_path)
    if skipped:
        print("warning: skipped %d malformed line(s) in %s"
              % (skipped, log_path), file=sys.stderr)
    if not attempts:
        print("The log at %s has no valid attempts yet." % log_path)
        return 0

    if args.scope == "session":
        session = args.session or str(attempts[-1].get("session"))
        rows = [r for r in attempts if str(r.get("session")) == session]
        if not rows:
            print("No attempts found for session %r." % session)
            return 0
        report = build_session_report(rows, session)
        filename = "session-%s.md" % safe_filename(session)
    else:
        report = build_overview_report(attempts)
        filename = "progress-overview.md"

    print(report)

    if not args.no_write:
        reports_dir = base / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        out_path = reports_dir / filename
        out_path.write_text(report, encoding="utf-8")
        print("written: %s" % out_path, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
