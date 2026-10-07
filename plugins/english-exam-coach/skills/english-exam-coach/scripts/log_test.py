#!/usr/bin/env python3
"""Record the result of a full test: section scores, overall, per-task detail.

A full test — a mock on any platform, an official practice test, the real
exam — is a different kind of evidence from a single drill: it is the number
the learner is actually working towards, and a run of them is the only honest
trend line. This writes one line per test to <base>/tests.jsonl so reports can
show the history, name records, and tie logged mistakes to the test they came
from.

The scores are taken as given. They are whatever the test's own scoring
produced; this script does not second-guess or rescale them.

Example:
  log_test.py --name Saturn --date 2026-08-25 --exam toefl-ibt \\
      --source "mock platform" \\
      --reading 4.0 --listening 5.0 --writing 3.5 --speaking 4.0 --overall 4.0 \\
      --task build_a_sentence_errors=3 --task email=3 --task discussion=4 \\
      --task listen_and_repeat=5,5,5,5,4,4,2 --task interview=3,3,3,2.5

It prints the test's session id. Pass that id as --session when logging the
mistakes found in this test, so the catalog can count them per test.
"""

import argparse
import math
import re
import sys
from datetime import datetime

import state

TEST_LOG = "tests.jsonl"
CORE_SECTIONS = ("reading", "listening", "writing", "speaking")

# (lowest, highest, step) a section score may take, by exam family. A step of
# None means "any number in range". Unknown exams are not range-checked: the
# log should accept a test the script has never heard of.
SCALES = {
    "toefl": (1.0, 6.0, 0.5),
    "ielts": (0.0, 9.0, 0.5),
    "cefr": (80.0, 230.0, None),   # Cambridge English Scale
}
# Exams whose overall is the mean of the four sections rounded to a half band.
HALF_BAND_MEAN = ("toefl", "ielts")


def exam_family(exam):
    exam = str(exam or "").lower()
    for family in SCALES:
        if exam.startswith(family):
            return family
    return None


def round_half_band(value):
    """Nearest 0.5, with exact ties going up (4.75 -> 5.0, 4.25 -> 4.5)."""
    return math.floor(value * 2 + 0.5) / 2


def parse_number_list(raw):
    """'5,4,5' -> [5, 4, 5]; '4.5' -> 4.5. Raises ValueError."""
    parts = [p.strip() for p in str(raw).split(",") if p.strip()]
    if not parts:
        raise ValueError("no value given")
    numbers = []
    for part in parts:
        value = float(part)
        if not math.isfinite(value):
            raise ValueError("%r is not a finite number" % part)
        numbers.append(int(value) if value.is_integer() else value)
    return numbers if len(numbers) > 1 else numbers[0]


def parse_pairs(pairs, what):
    """['email=4.5', 'interview=3,3,2'] -> ({'email': 4.5, ...}, [errors])."""
    parsed, errors = {}, []
    for pair in pairs or ():
        key, sep, raw = str(pair).partition("=")
        key = re.sub(r"[\s-]+", "_", key.strip().lower())
        if not sep or not key:
            errors.append("--%s expects name=value (got %r)" % (what, pair))
            continue
        if not re.fullmatch(r"[a-z0-9_]+", key):
            errors.append("--%s name %r may only use letters, digits and _"
                          % (what, key))
            continue
        try:
            parsed[key] = parse_number_list(raw)
        except ValueError as exc:
            errors.append("--%s %s: %s" % (what, key, exc))
    return parsed, errors


def check_scale(exam, name, value):
    family = exam_family(exam)
    if family is None:
        return None if value >= 0 else "%s must not be negative" % name
    low, high, step = SCALES[family]
    if not low <= value <= high:
        return ("%s %g is outside the %s scale (%g–%g)"
                % (name, value, family.upper(), low, high))
    if step and abs(value / step - round(value / step)) > 1e-9:
        return ("%s %g is not on the %s scale (steps of %g)"
                % (name, value, family.upper(), step))
    return None


def session_id(name, when):
    return "test-%s-%s" % (state.slugify(name) or "test", when.strftime("%Y%m%d"))


def load_tests(base):
    """Every logged test, oldest first, with corrections applied: a re-logged
    test keeps only its latest entry, and a voided one is left out (the log
    is append-only, so a correction is always a newer line)."""
    rows, _skipped = state.read_jsonl(base / TEST_LOG)
    latest, order = {}, []
    for row in rows:
        session = row.get("session")
        if not session:
            continue
        if row.get("void"):
            latest.pop(session, None)
            continue
        if not row.get("name") or not isinstance(row.get("sections"), dict) \
                or not row["sections"]:
            continue
        if session not in order:
            order.append(session)
        latest[session] = row
    tests = [latest[session] for session in order if session in latest]
    tests.sort(key=lambda t: str(t.get("ts") or ""))
    return tests


def find_logged(tests, wanted):
    """A logged test by session id, or by name when only one has that name."""
    wanted = str(wanted).strip()
    for test in tests:
        if test["session"] == wanted:
            return test
    named = [t for t in tests if str(t["name"]).lower() == wanted.lower()]
    return named[0] if len(named) == 1 else None


def build_parser():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--name", default=None,
                        help="what you call this test, e.g. Saturn or 'Mock 4'")
    parser.add_argument("--exam", default=None,
                        help="exam id, e.g. toefl-ibt, ielts-academic, cefr-c1")
    parser.add_argument("--void", default=None, metavar="TEST",
                        help="withdraw a test logged by mistake: its session "
                             "id, or its name if only one test has it")
    parser.add_argument("--date", default=None,
                        help="when it was taken, YYYY-MM-DD (default: today)")
    parser.add_argument("--source", default=None,
                        help="where the scores come from, e.g. the mock "
                             "platform's name, 'official practice test', "
                             "'real exam'")
    for section in CORE_SECTIONS:
        parser.add_argument("--" + section, type=float, default=None,
                            help="%s section score" % section)
    parser.add_argument("--section", action="append", default=[],
                        metavar="NAME=SCORE",
                        help="any other section, e.g. use_of_english=172")
    parser.add_argument("--overall", type=float, default=None,
                        help="overall score as reported (computed for TOEFL "
                             "and IELTS when all four sections are given)")
    parser.add_argument("--task", action="append", default=[],
                        metavar="NAME=VALUE",
                        help="per-task detail: one number, or a comma list "
                             "for per-item scores. Repeatable.")
    parser.add_argument("--note", default=None,
                        help="one line of context, e.g. 'taken the day after "
                             "another full test'")
    parser.add_argument("--amend", action="store_true",
                        help="record a corrected entry for a test that is "
                             "already logged (the newer entry wins)")
    state.add_location_arguments(parser)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    errors = []

    if args.void:
        base = state.base_from_args(args)
        test = find_logged(load_tests(base), args.void)
        if test is None:
            print("error: no single logged test matches %r" % args.void,
                  file=sys.stderr)
            return 2
        try:
            state.append_jsonl(base / TEST_LOG, {
                "ts": datetime.now().isoformat(timespec="seconds"),
                "name": test["name"], "session": test["session"], "void": True})
        except OSError as exc:
            print("error: could not write %s: %s" % (base / TEST_LOG, exc),
                  file=sys.stderr)
            return 1
        print("withdrawn: %s (%s). Mistakes logged for it stay in the ledger "
              "as practice; withdraw those too if they were logged in error."
              % (test["name"], test["session"]))
        return 0

    if not args.name or not args.exam:
        print("error: --name and --exam are required", file=sys.stderr)
        return 2
    name = args.name.strip()
    exam = args.exam.strip()
    if not name:
        errors.append("--name must not be blank")
    if not exam:
        errors.append("--exam must not be blank")

    when = datetime.now()
    if args.date:
        try:
            when = datetime.strptime(args.date.strip(), "%Y-%m-%d")
        except ValueError:
            errors.append("--date must be YYYY-MM-DD (got %r)" % args.date)

    sections = {s: getattr(args, s) for s in CORE_SECTIONS
                if getattr(args, s) is not None}
    extra, pair_errors = parse_pairs(args.section, "section")
    errors += pair_errors
    for key, value in extra.items():
        if isinstance(value, list):
            errors.append("--section %s takes one score, not a list" % key)
        else:
            sections[key] = float(value)
    if not sections and not errors:
        errors.append("give at least one section score (--reading, "
                      "--listening, --writing, --speaking or --section)")

    for key, value in sections.items():
        if not math.isfinite(value):
            errors.append("%s must be a finite number" % key)
            continue
        problem = check_scale(exam, key, value)
        if problem:
            errors.append(problem)

    if args.overall is not None:
        if not math.isfinite(args.overall):
            errors.append("--overall must be a finite number")
        else:
            problem = check_scale(exam, "overall", args.overall)
            if problem:
                errors.append(problem)

    tasks, pair_errors = parse_pairs(args.task, "task")
    errors += pair_errors

    if errors:
        for error in errors:
            print("error: %s" % error, file=sys.stderr)
        return 2

    base = state.base_from_args(args)
    session = session_id(name, when)
    already = any(t["session"] == session for t in load_tests(base))
    if already and not args.amend:
        print("error: %s (%s) is already logged as %s. Pass --amend to record "
              "a corrected entry." % (name, when.strftime("%Y-%m-%d"), session),
              file=sys.stderr)
        return 2

    def clean(value):
        return int(value) if float(value).is_integer() else float(value)

    record = {
        "ts": when.strftime("%Y-%m-%dT00:00:00") if args.date
        else when.isoformat(timespec="seconds"),
        "name": name,
        "session": session,
        "exam": exam,
        "sections": {key: clean(value) for key, value in sections.items()},
    }
    if args.source and args.source.strip():
        record["source"] = args.source.strip()
    if args.overall is not None:
        record["overall"] = clean(args.overall)
    elif exam_family(exam) in HALF_BAND_MEAN \
            and all(s in sections for s in CORE_SECTIONS):
        mean = sum(sections[s] for s in CORE_SECTIONS) / len(CORE_SECTIONS)
        record["overall"] = clean(round_half_band(mean))
        # Say so: a figure we derived is not one the test reported.
        record["overall_computed"] = True
    if tasks:
        record["tasks"] = tasks
    if args.note and args.note.strip():
        record["note"] = args.note.strip()

    try:
        state.append_jsonl(base / TEST_LOG, record)
    except OSError as exc:
        print("error: could not write %s: %s" % (base / TEST_LOG, exc),
              file=sys.stderr)
        return 1

    scores = " · ".join("%s %g" % (key[:1].upper() if key in CORE_SECTIONS else key,
                                   value)
                        for key, value in record["sections"].items())
    overall = ""
    if "overall" in record:
        overall = " · overall %g%s" % (
            record["overall"], " (computed)" if record.get("overall_computed") else "")
    print("%s test: %s (%s) %s%s"
          % ("amended" if already else "logged", name,
             when.strftime("%Y-%m-%d"), scores, overall))
    print("session id: %s — use it as --session when logging this test's "
          "mistakes" % session)
    return 0


if __name__ == "__main__":
    sys.exit(main())
