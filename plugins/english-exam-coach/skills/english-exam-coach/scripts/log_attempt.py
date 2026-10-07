#!/usr/bin/env python3
"""Append one exam-practice attempt to the append-only progress log.

Writes exactly one JSON line to <base>/attempts.jsonl. The file is opened in
append mode only and is never truncated or rewritten. If validation fails,
the script exits non-zero without touching the log.

Base directory resolution (first match wins):
  1. --base CLI flag
  2. EXAM_COACH_HOME environment variable
  3. ~/english-exam-coach/

Example:
  log_attempt.py --exam cefr-c1 --skill reading-use-of-english \\
      --task-type key-word-transformation --level C1 \\
      --score 7 --max 10 --seconds 540 --session 2026-07-08-am
"""

import argparse
import math
import sys
from datetime import datetime

import state

LOG_NAME = "attempts.jsonl"
CEFR_LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")

# How the logged time was obtained. An estimate and a script-run clock must
# never look alike in the data, or pacing analysis is built on sand.
TIMING_SOURCES = ("script", "wall-clock", "self-reported", "estimated")

# How much of the performance was actually observable. A speaking estimate
# from a typed-from-memory transcript is weaker evidence than one from a
# recording, and the log has to say so rather than average them together.
EVIDENCE_GRADES = ("full", "partial", "self-reported")


def default_session(now):
    return "{:%Y-%m-%d}-{}".format(now, "am" if now.hour < 12 else "pm")


def normalize_ts(ts):
    """Accept a trailing 'Z' UTC suffix on Python < 3.11 too (fromisoformat
    only learned to parse 'Z' in 3.11; the macOS system python is often older).
    Returns an ISO string fromisoformat can parse on any supported version."""
    if ts and ts.endswith("Z"):
        return ts[:-1] + "+00:00"
    return ts


def build_parser():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--exam", required=True,
                        help="exam id, e.g. cefr-c1, ielts-academic, toefl-ibt")
    parser.add_argument("--skill", required=True,
                        help="source skill, e.g. writing-evaluator")
    parser.add_argument("--task-type", required=True, dest="task_type",
                        help="canonical slug from data/task-types.md, "
                             "e.g. key-word-transformation, ielts-task2-essay")
    parser.add_argument("--level", required=True,
                        help="CEFR anchor of the task: A1, A2, B1, B2, C1 or C2")
    parser.add_argument("--score", type=float, default=None,
                        help="raw numeric score, when applicable")
    parser.add_argument("--max", type=float, default=None, dest="max_score",
                        help="maximum possible value for --score")
    parser.add_argument("--band-estimate", default=None, dest="band_estimate",
                        help='range string when a single number would be false '
                             'precision, e.g. "6.5-7.0"')
    parser.add_argument("--cefr-estimate", default=None, dest="cefr_estimate",
                        help="normalized CEFR level for cross-exam trends, e.g. B2")
    parser.add_argument("--seconds", type=float, required=True,
                        help="time on task, in seconds")
    parser.add_argument("--session", default=None,
                        help="session id, e.g. 2026-07-08-am "
                             "(default: derived from the current time)")
    parser.add_argument("--ts", default=None,
                        help="ISO 8601 timestamp (default: now)")
    state.add_location_arguments(parser)
    parser.add_argument("--criteria", default=None,
                        help="per-criterion CEFR levels, the judgement the "
                             "evaluator already made: "
                             '"task_response=B2,coherence=C1,lexis=B2"')
    parser.add_argument("--timing-source", default=None, dest="timing_source",
                        choices=TIMING_SOURCES,
                        help="how --seconds was obtained (default: unstated)")
    parser.add_argument("--evidence-grade", default=None, dest="evidence_grade",
                        choices=EVIDENCE_GRADES,
                        help="how much of the performance was actually "
                             "observable (default: unstated)")
    parser.add_argument("--draft", type=int, default=None,
                        help="draft number for a revise-and-resubmit cycle "
                             "(1 = first attempt)")
    return parser


def parse_criteria(raw):
    """'task_response=B2,coherence=C1' -> {'task_response': 'B2', ...}.

    Raises ValueError with a human-readable message on anything malformed:
    a half-parsed criteria map is worse than none, because it would silently
    under-report which criterion is holding the learner back.
    """
    criteria = {}
    for chunk in str(raw).split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "=" not in chunk:
            raise ValueError("expected name=LEVEL pairs, got %r" % chunk)
        name, _, level = chunk.partition("=")
        name = name.strip().lower().replace(" ", "_").replace("-", "_")
        level = level.strip().upper()
        if not name:
            raise ValueError("missing criterion name in %r" % chunk)
        if level not in CEFR_LEVELS:
            raise ValueError("criterion %r must be one of %s (got %r)"
                             % (name, "/".join(CEFR_LEVELS), level))
        criteria[name] = level
    if not criteria:
        raise ValueError("no criteria found")
    return criteria


def validate(args):
    """Return a list of human-readable validation errors (empty = valid)."""
    errors = []

    for field in ("exam", "skill", "task_type"):
        value = getattr(args, field)
        if not value or not value.strip():
            errors.append("--%s must be a non-empty string" % field.replace("_", "-"))

    level = (args.level or "").strip().upper()
    if level not in CEFR_LEVELS:
        errors.append("--level must be one of %s (got %r)"
                      % ("/".join(CEFR_LEVELS), args.level))

    # Reject NaN/Infinity up front: they slip past every ordered comparison
    # below and would be written to the append-only log as invalid JSON.
    for flag, value in (("--score", args.score), ("--max", args.max_score),
                        ("--seconds", args.seconds)):
        if isinstance(value, float) and not math.isfinite(value):
            errors.append("%s must be a finite number (got %r)" % (flag, value))

    band = (args.band_estimate or "").strip()
    if args.score is None and not band:
        errors.append("at least one of --score or --band-estimate is required")

    if args.score is not None and args.score < 0:
        errors.append("--score must be >= 0")

    if args.max_score is not None:
        if args.score is None:
            errors.append("--max is only meaningful together with --score")
        elif args.max_score <= 0:
            errors.append("--max must be > 0")
        elif args.score is not None and args.score > args.max_score:
            errors.append("--score (%g) cannot exceed --max (%g)"
                          % (args.score, args.max_score))

    if args.cefr_estimate is not None:
        if args.cefr_estimate.strip().upper() not in CEFR_LEVELS:
            errors.append("--cefr-estimate must be one of %s (got %r)"
                          % ("/".join(CEFR_LEVELS), args.cefr_estimate))

    if args.seconds < 0:
        errors.append("--seconds must be >= 0")

    if args.session is not None and not args.session.strip():
        errors.append("--session must not be blank (omit it to auto-derive one)")

    if args.criteria is not None:
        try:
            parse_criteria(args.criteria)
        except ValueError as exc:
            errors.append("--criteria: %s" % exc)

    if args.draft is not None and args.draft < 1:
        errors.append("--draft must be 1 or more (1 = the first attempt)")

    if args.ts is not None:
        try:
            datetime.fromisoformat(normalize_ts(args.ts))
        except ValueError:
            errors.append("--ts must be an ISO 8601 timestamp (got %r)" % args.ts)
        else:
            # --ts is documented as a full timestamp. A bare date parses (as
            # midnight) but would be stored verbatim and silently forced to an
            # 'am' session regardless of when the attempt happened, so reject
            # a value with no time component.
            if "T" not in args.ts and ":" not in args.ts:
                errors.append("--ts must include a time, e.g. "
                              "2026-07-10T14:30:00 (got %r)" % args.ts)

    return errors


def as_number(value):
    """Store integral floats as ints so the log stays clean (7, not 7.0)."""
    if value is None:
        return None
    return int(value) if float(value).is_integer() else float(value)


def build_record(args, now):
    record = {
        "ts": normalize_ts(args.ts) or now.isoformat(timespec="seconds"),
        "exam": args.exam.strip(),
        "skill": args.skill.strip(),
        "task_type": args.task_type.strip(),
        "level": args.level.strip().upper(),
    }
    if args.score is not None:
        record["score"] = as_number(args.score)
    if args.max_score is not None:
        record["max"] = as_number(args.max_score)
    if args.band_estimate and args.band_estimate.strip():
        record["band_estimate"] = args.band_estimate.strip()
    if args.cefr_estimate:
        record["cefr_estimate"] = args.cefr_estimate.strip().upper()
    if args.criteria:
        record["criteria"] = parse_criteria(args.criteria)
    if args.draft is not None:
        record["draft"] = args.draft
    record["seconds"] = as_number(args.seconds)
    if args.timing_source:
        record["timing_source"] = args.timing_source
    if args.evidence_grade:
        record["evidence_grade"] = args.evidence_grade
    if args.session and args.session.strip():
        record["session"] = args.session.strip()
    else:
        # Derive the session from the attempt's own timestamp (not wall-clock
        # now) so a back-dated --ts and its session id never disagree.
        if args.ts:
            stamp = datetime.fromisoformat(normalize_ts(args.ts))
            # Mirror build_report.parse_ts: normalize a tz-aware --ts to naive
            # local time before reading its day/hour, so the session id agrees
            # with how the reader interprets the same ts.
            if stamp.tzinfo is not None:
                stamp = stamp.astimezone().replace(tzinfo=None)
        else:
            stamp = now
        record["session"] = default_session(stamp)
    return record


def main(argv=None):
    args = build_parser().parse_args(argv)

    errors = validate(args)
    if errors:
        for error in errors:
            print("error: %s" % error, file=sys.stderr)
        return 2

    base = state.base_from_args(args)
    log_path = base / LOG_NAME

    now = datetime.now()
    record = build_record(args, now)

    try:
        # state.append_jsonl owns the append-only invariant for every log:
        # append mode only, strict JSON (no NaN), and a repair for a previous
        # write that left no trailing newline.
        state.append_jsonl(log_path, record)
    except OSError as exc:
        print("error: could not write %s: %s" % (log_path, exc), file=sys.stderr)
        return 1

    print("logged: %s %s %s -> %s"
          % (record["exam"], record["task_type"],
             record.get("band_estimate")
             or ("%s/%s" % (record.get("score"), record.get("max"))
                 if record.get("max") is not None else record.get("score")),
             log_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
