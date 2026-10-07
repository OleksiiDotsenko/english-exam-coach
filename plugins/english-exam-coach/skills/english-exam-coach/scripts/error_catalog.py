#!/usr/bin/env python3
"""Build the error catalog: what goes wrong, how often, and in how many tests.

A single test review says what went wrong today. The catalog says what goes
wrong *every time* — the difference between a slip and a habit — by laying
every logged mistake across the run of full tests:

  - error types and specific points, ranked, with "in N of M tests";
  - a point x test matrix, so a returning error is visible at a glance;
  - mistakes repeated word for word (the cheapest ones to fix);
  - mistakes carried over from the learner's first language;
  - a habit state for every point, using one rule throughout: a point is
    closed only after it has stayed out of FOUR tests in a row.

Everything here is counted from the logs. Nothing is estimated, and nothing
is invented when the logs are thin: with fewer than two tests the per-test
tables are simply left out.

  error_catalog.py                 summary on screen, full report to reports/
  error_catalog.py --full          print the full catalog as well
  error_catalog.py --points        the point labels already in use (reuse them)
  error_catalog.py --full --ids    every mistake with its id, for corrections
  error_catalog.py --json          the same data, for building another layout
"""

import argparse
import json
import math
import sys

import log_test
import review_queue
import state
from report_utils import (DISCLAIMER, NONE_IN_CELL, bar, bold, cell, fmt,
                          plural, short_date, table)

ERROR_LOG = "errors.jsonl"
CLOSED_AFTER = 4          # clean tests in a row before a point counts as closed
CHRONIC_SHARE = 0.7       # share of all tests that makes a point chronic

STATE_ORDER = ("chronic", "returned", "recurring", "new", "fading", "closed",
               "one-off")
STATE_MEANING = {
    "chronic": "in most tests — the standing habits",
    "returned": "back after two or more clean tests",
    "recurring": "keeps appearing, not yet in most tests",
    "new": "first seen in the latest test",
    "fading": "missing from the last 1–%d tests; not closed yet" % (CLOSED_AFTER - 1),
    "closed": "out of %d tests in a row" % CLOSED_AFTER,
    "one-off": "seen in a single test, not since",
}


def classify(presence, closed_after=CLOSED_AFTER):
    """Habit state from a point's test-by-test presence, oldest test first.

    The rule that matters is the last one a learner wants to hear: an error
    that stays away for two tests has not gone. It is `fading` until it has
    been absent `closed_after` tests running, and `returned` the moment it
    comes back.
    """
    total = len(presence)
    hits = [i for i, present in enumerate(presence) if present]
    if not hits:
        return None
    last = hits[-1]
    clean = total - 1 - last
    share = len(hits) / float(total)
    if clean >= closed_after:
        return "closed"
    if clean == 0:
        if len(hits) == 1:
            return "new"
        if last - hits[-2] - 1 >= 2:
            return "returned"
        if total >= 4 and share >= CHRONIC_SHARE:
            return "chronic"
        return "recurring"
    if len(hits) == 1:
        return "one-off"
    if clean == 1 and total >= 4 and share >= CHRONIC_SHARE:
        return "chronic"   # one clean test does not break a standing habit
    return "fading"


def load(base):
    """(tests oldest-first, error rows) from a progress directory."""
    tests = log_test.load_tests(base)
    errors, _skipped = state.read_errors(base)
    return tests, errors


def unit_key(row, by):
    if by == "type":
        return (row["category"], row["subtype"])
    return (row["category"], row["subtype"],
            review_queue.normalize_point(row["point"]))


def build_units(tests, errors, by="point", closed_after=CLOSED_AFTER):
    """Group mistakes into units (points, or error types) with per-test counts.

    Returns units sorted most frequent first. Each unit carries: label, tag,
    cases (rows), per_test (counts aligned with `tests`), tests_hit, practice
    (cases not tied to any logged test) and, with 2+ tests, a habit state.
    """
    index = {t["session"]: i for i, t in enumerate(tests)}
    units = {}
    for row in errors:
        key = unit_key(row, by)
        unit = units.get(key)
        if unit is None:
            unit = units[key] = {
                "key": key, "category": row["category"], "subtype": row["subtype"],
                "labels": {}, "cases": [], "per_test": [0] * len(tests),
                "practice": 0,
            }
        unit["cases"].append(row)
        label = str(row["point"]).strip()
        unit["labels"][label] = unit["labels"].get(label, 0) + 1
        position = index.get(row.get("session"))
        if position is None:
            unit["practice"] += 1
        else:
            unit["per_test"][position] += 1

    result = []
    for unit in units.values():
        tag = "%s/%s" % (unit["category"], unit["subtype"])
        if by == "type":
            label = tag
        else:
            # The wording used most often; ties go to the one seen first.
            label = max(unit["labels"], key=lambda text: unit["labels"][text])
        presence = [count > 0 for count in unit["per_test"]]
        unit.update({
            "label": label, "tag": tag, "count": len(unit["cases"]),
            "tests_hit": sum(presence),
            "state": classify(presence, closed_after) if len(tests) >= 2 else None,
        })
        del unit["labels"]
        result.append(unit)
    result.sort(key=lambda u: (-u["count"], -u["tests_hit"], u["tag"], u["label"]))
    return result


def short_names(tests):
    """Compact, unique column heads for the matrix: Saturn -> SAT."""
    names, used = [], set()
    for test in tests:
        base = "".join(ch for ch in str(test["name"]) if ch.isalnum())[:3].upper() \
            or "T"
        name, extra = base, 2
        while name in used:
            name = "%s%d" % (base, extra)
            extra += 1
        used.add(name)
        names.append(name)
    return names


def normalise(text):
    return review_queue.normalize_point(text)


def verbatim_repeats(tests, errors):
    """The same wrong form corrected to the same right form, 2+ times."""
    names = {t["session"]: t["name"] for t in tests}
    groups = {}
    for row in errors:
        wrong, right = str(row.get("evidence") or ""), str(row.get("fix") or "")
        if not wrong.strip() or not right.strip():
            continue
        key = (normalise(wrong), normalise(right))
        group = groups.setdefault(key, {"evidence": wrong.strip(),
                                        "fix": right.strip(), "count": 0,
                                        "where": []})
        group["count"] += 1
        where = names.get(row.get("session"))
        if where and where not in group["where"]:
            group["where"].append(where)
    repeats = [g for g in groups.values() if g["count"] >= 2]
    repeats.sort(key=lambda g: (-g["count"], -len(g["where"]), g["evidence"]))
    return repeats


def transfer_cases(tests, errors):
    names = {t["session"]: t["name"] for t in tests}
    rows = [r for r in errors if str(r.get("transfer") or "").strip()]
    return [{"evidence": str(r.get("evidence") or "").strip(),
             "transfer": str(r["transfer"]).strip(),
             "fix": str(r.get("fix") or "").strip(),
             "point": str(r["point"]).strip(),
             "test": names.get(r.get("session"), "")} for r in rows]


def category_rows(errors, points):
    totals = {}
    for row in errors:
        totals[row["category"]] = totals.get(row["category"], 0) + 1
    distinct = {}
    for point in points:
        distinct[point["category"]] = distinct.get(point["category"], 0) + 1
    return sorted(((name, distinct.get(name, 0), count)
                   for name, count in totals.items()), key=lambda r: -r[2])


# ---- rendering ---------------------------------------------------------

def spread(unit, total_tests):
    return "%d of %d" % (unit["tests_hit"], total_tests) if total_tests else ""


def section_header(tests, errors, points):
    linked = sum(1 for p in points for c in p["cases"]) - sum(p["practice"] for p in points)
    lines = ["# Error catalog", ""]
    scope = "%s · %s" % (plural(len(errors), "mistake"),
                         plural(len(points), "distinct point"))
    if tests:
        scope += " · %s (%s → %s)" % (
            plural(len(tests), "test"), short_date(tests[0]["ts"]),
            short_date(tests[-1]["ts"]))
    lines += [bold(scope), ""]
    practice = len(errors) - linked
    if tests and practice:
        lines += ["%s from practice outside the logged tests %s counted in the "
                  "totals but not in the per-test tables."
                  % (plural(practice, "mistake"),
                     "is" if practice == 1 else "are"), ""]
    if len(tests) < 2:
        lines += ["Per-test tables and habit states need at least two logged "
                  "tests; they are left out rather than guessed.", ""]
    return lines


def section_categories(errors, points):
    rows = category_rows(errors, points)
    largest = max((r[2] for r in rows), default=0)
    total = float(len(errors)) or 1.0
    return ["## By category", "",
            table(["Category", "Points", "Mistakes", "Share", ""],
                  [[name, distinct, count, "%d%%" % round(100 * count / total),
                    bar(count, largest)] for name, distinct, count in rows],
                  ["l", "r", "r", "r", "l"]), ""]


def section_types(types, total_tests):
    largest = max((t["count"] for t in types), default=0)
    headers = ["#", "Error type", "Mistakes"] + (["Tests"] if total_tests else []) + [""]
    rows = []
    for number, unit in enumerate(types, 1):
        row = [number, unit["tag"], unit["count"]]
        if total_tests:
            row.append(spread(unit, total_tests))
        rows.append(row + [bar(unit["count"], largest)])
    return ["## By error type", "",
            table(headers, rows, ["r", "l", "r"] + (["r"] if total_tests else []) + ["l"]),
            ""]


def section_points(points, total_tests, limit):
    shown = points[:limit] if limit else points
    largest = max((p["count"] for p in shown), default=0)
    headers = ["#", "Point", "Type", "Mistakes"] + (["Tests"] if total_tests else []) + [""]
    rows = []
    for number, unit in enumerate(shown, 1):
        row = [number, unit["label"], unit["tag"], unit["count"]]
        if total_tests:
            row.append(spread(unit, total_tests))
        rows.append(row + [bar(unit["count"], largest)])
    lines = ["## Points, most frequent first", "",
             table(headers, rows,
                   ["r", "l", "l", "r"] + (["r"] if total_tests else []) + ["l"]), ""]
    if limit and len(points) > limit:
        lines += ["…and %d more in the full report." % (len(points) - limit), ""]
    return lines


def section_matrix(points, tests, min_tests, limit):
    eligible = [p for p in points if p["tests_hit"] >= min_tests]
    if len(tests) < 2 or not eligible:
        return []
    shown = eligible[:limit] if limit else eligible
    heads = short_names(tests)
    rows = [[unit["label"]] + [count or NONE_IN_CELL for count in unit["per_test"]]
            + [sum(unit["per_test"])] for unit in shown]
    lines = ["## Point × test", "",
             "Points seen in at least %s. Columns run oldest to newest: %s."
             % (plural(min_tests, "test"),
                ", ".join("%s = %s" % (h, t["name"]) for h, t in zip(heads, tests))),
             "",
             table(["Point"] + heads + ["Σ"], rows,
                   ["l"] + ["r"] * (len(heads) + 1)), ""]
    if limit and len(eligible) > limit:
        lines += ["…and %d more in the full report." % (len(eligible) - limit), ""]
    return lines


def section_habits(points, tests, limit):
    if len(tests) < 2:
        return []
    lines = ["## Habit states", "",
             "One rule throughout: a point is closed only after it stays out "
             "of %d tests in a row. Two clean tests is not closed." % CLOSED_AFTER,
             ""]
    rows = []
    for name in STATE_ORDER:
        members = [p for p in points if p["state"] == name]
        if not members:
            continue
        listed = members[:limit] if limit else members
        text = " · ".join("%s (%d)" % (p["label"], p["count"]) for p in listed)
        if limit and len(members) > limit:
            text += " · …%d more" % (len(members) - limit)
        rows.append(["%s (%d)" % (name, len(members)), STATE_MEANING[name], text])
    lines += [table(["State", "Means", "Points"], rows), ""]
    return lines


def section_repeats(repeats, limit):
    if not repeats:
        return []
    shown = repeats[:limit] if limit else repeats
    total = sum(r["count"] for r in repeats)
    lines = ["## Repeated word for word", "",
             "The cheapest part of the catalog: %s, %s. One card each."
             % (plural(len(repeats), "exact slip"), plural(total, "mistake")),
             "",
             table(["Written or said", "Should be", "Times", "Where"],
                   [[r["evidence"], r["fix"], r["count"], " · ".join(r["where"])]
                    for r in shown], ["l", "l", "r", "l"]), ""]
    if limit and len(repeats) > limit:
        lines += ["…and %d more in the full report." % (len(repeats) - limit), ""]
    return lines


def section_transfer(cases, limit):
    if not cases:
        return []
    shown = cases[:limit] if limit else cases
    lines = ["## Carried over from the first language", "",
             "%s translated rather than mis-learned. These respond to "
             "contrast pairs (how we say it → how English says it), not to "
             "another explanation of the rule." % plural(len(cases), "mistake"),
             "",
             table(["Written or said", "Comes from", "Should be", "Test"],
                   [[c["evidence"], c["transfer"], c["fix"], c["test"]]
                    for c in shown]), ""]
    if limit and len(cases) > limit:
        lines += ["…and %d more in the full report." % (len(cases) - limit), ""]
    return lines


def section_full(points, tests, ids=False):
    names = {t["session"]: t["name"] for t in tests}
    lines = ["## Full catalog", ""]
    category = subtype = None
    for unit in sorted(points, key=lambda u: (u["category"], u["subtype"],
                                              -u["count"], u["label"])):
        if unit["category"] != category:
            category, subtype = unit["category"], None
            lines += ["### %s" % category.capitalize(), ""]
        if unit["subtype"] != subtype:
            subtype = unit["subtype"]
            lines += ["#### %s" % subtype, ""]
        state_note = " — %s" % unit["state"] if unit["state"] else ""
        lines.append("**%s** (%d)%s" % (cell(unit["label"]), unit["count"], state_note))
        lines.append("")
        for row in unit["cases"]:
            wrong = str(row.get("evidence") or "").strip()
            right = str(row.get("fix") or "").strip()
            where = [names.get(row.get("session"), ""), str(row.get("task_type") or "")]
            where = " · ".join(w for w in where if w)
            if wrong and right:
                text = "*%s* → %s" % (wrong, right)
            else:
                text = wrong or right or "(no quotation logged)"
            lines.append("- %s%s%s" % (text, " — %s" % where if where else "",
                                       " `%s`" % row["id"] if ids and row.get("id") else ""))
        lines.append("")
    return lines


def render(tests, errors, full=False, top=25, closed_after=CLOSED_AFTER,
           min_tests=None, ids=False):
    points = build_units(tests, errors, "point", closed_after)
    types = build_units(tests, errors, "type", closed_after)
    total = len(tests)
    if min_tests is None:
        min_tests = max(2, int(math.ceil(total / 3.0)))
    limit = None if full else top
    lines = section_header(tests, errors, points)
    lines += section_categories(errors, points)
    lines += section_types(types, total)
    lines += section_points(points, total, limit)
    lines += section_matrix(points, tests, min_tests, limit)
    lines += section_habits(points, tests, None if full else 12)
    lines += section_repeats(verbatim_repeats(tests, errors), limit)
    lines += section_transfer(transfer_cases(tests, errors), limit)
    if full:
        lines += section_full(points, tests, ids)
    lines += [DISCLAIMER, ""]
    return "\n".join(lines)


def as_data(tests, errors, closed_after=CLOSED_AFTER, with_cases=False):
    """The same catalog as plain data, for building a different layout."""
    def unit_data(unit):
        data = {"label": unit["label"], "category": unit["category"],
                "subtype": unit["subtype"], "mistakes": unit["count"],
                "tests_hit": unit["tests_hit"], "per_test": unit["per_test"],
                "practice": unit["practice"], "state": unit["state"]}
        if with_cases:
            data["cases"] = unit["cases"]
        return data

    points = build_units(tests, errors, "point", closed_after)
    types = build_units(tests, errors, "type", closed_after)
    return {
        "tests": [{"name": t["name"], "session": t["session"],
                   "date": short_date(t["ts"])} for t in tests],
        "mistakes": len(errors),
        "closed_after": closed_after,
        "categories": [{"category": name, "points": distinct, "mistakes": count}
                       for name, distinct, count in category_rows(errors, points)],
        "types": [unit_data(u) for u in types],
        "points": [unit_data(u) for u in points],
        "repeats": verbatim_repeats(tests, errors),
        "transfer": transfer_cases(tests, errors),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--full", action="store_true",
                        help="print every table in full, and the complete "
                             "list of mistakes")
    parser.add_argument("--points", action="store_true",
                        help="list the point labels already in use, so a new "
                             "mistake can reuse one instead of coining a variant")
    parser.add_argument("--json", action="store_true",
                        help="print the catalog as JSON instead of Markdown")
    parser.add_argument("--ids", action="store_true",
                        help="with --full, show each mistake's id — what "
                             "`coach log-error --void` and `--amend` take")
    parser.add_argument("--top", type=int, default=25,
                        help="rows per table in the summary (default 25)")
    parser.add_argument("--min-tests", type=int, default=None, dest="min_tests",
                        help="smallest number of tests a point must appear in "
                             "to enter the matrix (default: a third of them)")
    parser.add_argument("--closed-after", type=int, default=CLOSED_AFTER,
                        dest="closed_after",
                        help="clean tests in a row that close a point "
                             "(default %d)" % CLOSED_AFTER)
    parser.add_argument("--no-write", action="store_true",
                        help="do not write the full report to reports/")
    state.add_location_arguments(parser)
    args = parser.parse_args(argv)
    if args.closed_after < 1 or args.top < 1:
        print("error: --closed-after and --top must be 1 or more", file=sys.stderr)
        return 2

    base = state.base_from_args(args)
    tests, errors = load(base)
    if not errors:
        print("No mistakes are logged in %s yet — the catalog is built from "
              "`coach log-error`." % base)
        return 0

    if args.points:
        for unit in sorted(build_units(tests, errors, "point", args.closed_after),
                           key=lambda u: (u["tag"], -u["count"], u["label"])):
            print("%-28s %3d  %s" % (unit["tag"], unit["count"], unit["label"]))
        return 0

    if args.json:
        print(json.dumps(as_data(tests, errors, args.closed_after, args.full),
                         ensure_ascii=False, indent=1))
        return 0

    print(render(tests, errors, args.full, args.top, args.closed_after,
                 args.min_tests, args.ids))
    if not args.no_write:
        reports = base / "reports"
        reports.mkdir(parents=True, exist_ok=True)
        path = reports / "error-catalog.md"
        path.write_text(render(tests, errors, True, args.top, args.closed_after,
                               args.min_tests), encoding="utf-8")
        print("full catalog written: %s" % path, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
