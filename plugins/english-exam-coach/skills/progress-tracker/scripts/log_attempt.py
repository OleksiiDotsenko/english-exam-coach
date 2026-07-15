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
import json
import math
import os
import sys
from datetime import datetime
from pathlib import Path

LOG_NAME = "attempts.jsonl"
CEFR_LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")


def default_base():
    env = os.environ.get("EXAM_COACH_HOME", "").strip()
    if env:
        return Path(env).expanduser()
    return Path.home() / "english-exam-coach"


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
    parser.add_argument("--base", default=None,
                        help="progress directory (default: $EXAM_COACH_HOME "
                             "or ~/english-exam-coach)")
    return parser


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

    if args.ts is not None:
        try:
            datetime.fromisoformat(normalize_ts(args.ts))
        except ValueError:
            errors.append("--ts must be an ISO 8601 timestamp (got %r)" % args.ts)

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
    record["seconds"] = as_number(args.seconds)
    if args.session and args.session.strip():
        record["session"] = args.session.strip()
    else:
        # Derive the session from the attempt's own timestamp (not wall-clock
        # now) so a back-dated --ts and its session id never disagree.
        stamp = datetime.fromisoformat(normalize_ts(args.ts)) if args.ts else now
        record["session"] = default_session(stamp)
    return record


def main(argv=None):
    args = build_parser().parse_args(argv)

    errors = validate(args)
    if errors:
        for error in errors:
            print("error: %s" % error, file=sys.stderr)
        return 2

    base = Path(args.base).expanduser() if args.base else default_base()
    log_path = base / LOG_NAME

    now = datetime.now()
    record = build_record(args, now)
    # allow_nan=False is a last-line defense: strict JSON only, so the
    # append-only log can never hold NaN/Infinity that a reader would choke on.
    line = json.dumps(record, ensure_ascii=False, allow_nan=False)

    try:
        base.mkdir(parents=True, exist_ok=True)
        # If a prior write left the file without a trailing newline, our append
        # would concatenate onto that partial line and corrupt both records.
        prefix = ""
        if log_path.exists() and log_path.stat().st_size > 0:
            with open(log_path, "rb") as fh:
                fh.seek(-1, 2)
                if fh.read(1) != b"\n":
                    prefix = "\n"
        # Append mode only — the log must never be truncated or rewritten.
        with open(log_path, "a", encoding="utf-8") as log:
            log.write(prefix + line + "\n")
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
