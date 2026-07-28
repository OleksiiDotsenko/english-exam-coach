#!/usr/bin/env python3
"""Read or update the learner profile: target exam, target score, exam date.

The profile is what makes advice specific ("you need 4.5, you are averaging
about B2") instead of generic. It lives at <base>/profile.json, is written
atomically, and is never required — every other script works without it.

Base directory resolution (first match wins):
  1. --base CLI flag
  2. EXAM_COACH_HOME environment variable
  3. ~/english-exam-coach/

Examples:
  profile.py show
  profile.py set --exam toefl-ibt --target-score 4.5 --exam-date 2026-09-12
  profile.py set --current-level B2
"""

import argparse
import json
import os
import sys
from datetime import datetime, date
from pathlib import Path

PROFILE_NAME = "profile.json"
PROFILE_VERSION = 1
CEFR_LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")
EXAM_SCALES = {
    "toefl-ibt": "toefl",
    "ielts-academic": "ielts",
    "ielts-general": "ielts",
    "cefr-b1": "cambridge",
    "cefr-b2": "cambridge",
    "cefr-c1": "cambridge",
    "cefr-c2": "cambridge",
}


def default_base():
    env = os.environ.get("EXAM_COACH_HOME", "").strip()
    if env:
        return Path(env).expanduser()
    return Path.home() / "english-exam-coach"


def resolve_base(base_arg):
    return Path(base_arg).expanduser() if base_arg else default_base()


def read_profile(base):
    """Return the stored profile, or an empty dict. Never raises on bad data."""
    path = base / PROFILE_NAME
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def write_profile(base, profile):
    """Atomically replace the profile file (write temp, then rename)."""
    base.mkdir(parents=True, exist_ok=True)
    path = base / PROFILE_NAME
    tmp = base / (PROFILE_NAME + ".tmp")
    tmp.write_text(json.dumps(profile, indent=2, ensure_ascii=False,
                              allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path


def parse_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date()


def days_until(exam_date, today=None):
    today = today or date.today()
    return (parse_date(exam_date) - today).days


def describe(profile, today=None):
    """Human-readable profile summary."""
    if not profile:
        return ("No profile set yet. Run: profile.py set --exam <exam-id> "
                "--target-score <score> [--exam-date YYYY-MM-DD]")
    lines = []
    exam = profile.get("exam")
    if exam:
        lines.append("Target exam: %s" % exam)
    if profile.get("target_score") is not None:
        scale = profile.get("target_scale") or ""
        lines.append("Target score: %s%s"
                     % (profile["target_score"], " (%s scale)" % scale if scale else ""))
    if profile.get("target_cefr"):
        lines.append("Target level: about CEFR %s" % profile["target_cefr"])
    if profile.get("current_level"):
        lines.append("Current level (self-reported): %s" % profile["current_level"])
    exam_date = profile.get("exam_date")
    if exam_date:
        try:
            days = days_until(exam_date, today)
        except ValueError:
            lines.append("Exam date: %s" % exam_date)
        else:
            if days > 1:
                lines.append("Exam date: %s (%d days away)" % (exam_date, days))
            elif days == 1:
                lines.append("Exam date: %s (tomorrow)" % exam_date)
            elif days == 0:
                lines.append("Exam date: %s (today)" % exam_date)
            else:
                lines.append("Exam date: %s (%d days ago — set a new one)"
                             % (exam_date, -days))
    return "\n".join(lines) if lines else "Profile is empty."


def validate(args):
    errors = []
    if args.exam is not None and not args.exam.strip():
        errors.append("--exam must not be blank")
    if args.current_level is not None:
        if args.current_level.strip().upper() not in CEFR_LEVELS:
            errors.append("--current-level must be one of %s"
                          % "/".join(CEFR_LEVELS))
    if args.exam_date is not None:
        try:
            parse_date(args.exam_date)
        except ValueError:
            errors.append("--exam-date must be YYYY-MM-DD (got %r)" % args.exam_date)
    if args.target_score is not None and args.exam is None:
        # The scale (and therefore the CEFR translation) comes from the exam.
        errors.append("--target-score needs --exam so the scale is known")
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    show = sub.add_parser("show", help="print the stored profile")
    show.add_argument("--base", default=None)
    show.add_argument("--json", action="store_true",
                      help="print raw JSON instead of a summary")

    setp = sub.add_parser("set", help="create or update profile fields")
    setp.add_argument("--exam", default=None, help="exam id, e.g. toefl-ibt")
    setp.add_argument("--target-score", default=None, dest="target_score",
                      help="target on the exam's own scale, e.g. 4.5")
    setp.add_argument("--exam-date", default=None, dest="exam_date",
                      help="exam date, YYYY-MM-DD")
    setp.add_argument("--current-level", default=None, dest="current_level",
                      help="current CEFR level, e.g. B2")
    setp.add_argument("--base", default=None)

    args = parser.parse_args(argv)
    base = resolve_base(args.base)

    if args.command == "show":
        profile = read_profile(base)
        if args.json:
            print(json.dumps(profile, indent=2, ensure_ascii=False))
        else:
            print(describe(profile))
        return 0

    errors = validate(args)
    if errors:
        for error in errors:
            print("error: %s" % error, file=sys.stderr)
        return 2

    profile = read_profile(base)
    profile["version"] = PROFILE_VERSION
    if args.exam is not None:
        profile["exam"] = args.exam.strip()
        scale = EXAM_SCALES.get(profile["exam"])
        if scale:
            profile["target_scale"] = scale
    if args.target_score is not None:
        profile["target_score"] = args.target_score.strip()
        scale = profile.get("target_scale")
        cefr = target_cefr(scale, profile["target_score"])
        if cefr:
            profile["target_cefr"] = cefr
    if args.exam_date is not None:
        profile["exam_date"] = args.exam_date.strip()
    if args.current_level is not None:
        profile["current_level"] = args.current_level.strip().upper()
    profile["updated"] = datetime.now().isoformat(timespec="seconds")

    try:
        path = write_profile(base, profile)
    except OSError as exc:
        print("error: could not write profile: %s" % exc, file=sys.stderr)
        return 1
    print("saved: %s" % path)
    print(describe(profile))
    return 0


def target_cefr(scale, score):
    """Translate a target score to CEFR using the same public alignments as
    convert_score.py. Returns None when the score is not numeric."""
    try:
        value = float(score)
    except (TypeError, ValueError):
        return None
    cuts = {
        "toefl": ((6.0, "C2"), (5.0, "C1"), (4.0, "B2"),
                  (3.0, "B1"), (2.0, "A2"), (0.0, "A1")),
        "ielts": ((8.5, "C2"), (7.0, "C1"), (5.5, "B2"), (4.0, "B1"), (0.0, "A2")),
        "cambridge": ((200, "C2"), (180, "C1"), (160, "B2"),
                      (140, "B1"), (120, "A2"), (80, "A1")),
    }.get(scale)
    if not cuts:
        return None
    for threshold, level in cuts:
        if value >= threshold:
            return level
    return None


if __name__ == "__main__":
    sys.exit(main())
