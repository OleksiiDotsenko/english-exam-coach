#!/usr/bin/env python3
"""Report on full tests: the history across all of them, or one in detail.

  full_tests.py                    history: every test, records, halves, tasks
  full_tests.py --test Saturn      one test: scores against the earlier ones,
                                   its logged mistakes, and which of them are
                                   new, which are back, which stayed away
  full_tests.py --json             the same data, for building another layout

One score on one day is noise; the report is built to make that visible. It
shows each section against the previous test AND against the average of all
earlier ones, and it never extrapolates a trend from fewer than four tests.
"""

import argparse
import json
import sys

import error_catalog
import log_test
import state
from report_utils import (DISCLAIMER, band, bold, cell, fmt, mean, plural,
                          short_date, signed, table)

CORE = log_test.CORE_SECTIONS
NO_SOURCE = "not stated"


def section_names(tests):
    """Every section that appears, the four core skills first."""
    seen = []
    for test in tests:
        for name in test["sections"]:
            if name not in seen:
                seen.append(name)
    return [s for s in CORE if s in seen] + [s for s in seen if s not in CORE]


def title_of(name):
    return str(name).replace("_", " ").capitalize()


def section_sum(test, sections):
    values = [test["sections"].get(s) for s in sections]
    return sum(values) if all(v is not None for v in values) else None


def find_test(tests, wanted):
    """Match by session id, exact name, or unique case-insensitive prefix."""
    wanted = str(wanted).strip()
    for test in tests:
        if test["session"] == wanted:
            return test
    lowered = wanted.lower()
    exact = [t for t in tests if str(t["name"]).lower() == lowered]
    if exact:
        return exact[-1]
    partial = [t for t in tests if str(t["name"]).lower().startswith(lowered)]
    return partial[-1] if len(partial) == 1 else None


def metric_value(value):
    """A task metric as one number: a list of item scores becomes its mean."""
    if isinstance(value, list):
        return mean(value)
    return value


# ---- history -----------------------------------------------------------

def history_table(tests, sections):
    bests = {s: max((t["sections"][s] for t in tests if s in t["sections"]),
                    default=None) for s in sections}
    overalls = [t.get("overall") for t in tests if t.get("overall") is not None]
    best_overall = max(overalls) if overalls else None
    # Scores from different places are not the same kind of number: when the
    # tests do not all come from one source, say where each came from.
    mixed_sources = len({str(t.get("source") or "") for t in tests}) > 1
    rows = []
    for number, test in enumerate(tests, 1):
        row = [number, test["name"], short_date(test["ts"])]
        for name in sections:
            value = test["sections"].get(name)
            text = band(value)
            # Mark the record so it reads at a glance; with one test there is
            # nothing to compare against, so nothing is marked.
            if value is not None and len(tests) > 1 and value == bests[name]:
                text = bold(text)
            row.append(text)
        total = section_sum(test, sections)
        row.append(fmt(total))
        overall = test.get("overall")
        text = band(overall) + ("*" if test.get("overall_computed") else "")
        if overall is not None and len(tests) > 1 and overall == best_overall:
            text = bold(text)
        row.append(text)
        if mixed_sources:
            row.append(str(test.get("source") or NO_SOURCE))
        rows.append(row)
    headers = ["#", "Test", "Date"] + [title_of(s) for s in sections] + ["Sum", "Overall"]
    align = ["r", "l", "l"] + ["r"] * (len(sections) + 2)
    if mixed_sources:
        headers.append("Source")
        align.append("l")
    lines = [table(headers, rows, align), ""]
    if any(t.get("overall_computed") for t in tests):
        lines += ["\\* overall computed from the four sections, not reported "
                  "by the test.", ""]
    if len(tests) > 1 and all(bests[s] is not None for s in sections):
        best_sum = sum(bests[s] for s in sections)
        note = "Best score in each section, added up: %s" % bold(fmt(best_sum))
        if log_test.exam_family(tests[-1].get("exam")) in log_test.HALF_BAND_MEAN \
                and set(sections) == set(CORE):
            note += " → an overall of %s if they all land in one test" % bold(
                band(log_test.round_half_band(best_sum / 4.0)))
        lines += [note + ". Each of those has happened; they have not happened "
                  "together.", ""]
    return lines


def halves_table(tests, sections):
    """First half against second half — only with enough tests to mean it."""
    if len(tests) < 4:
        return []
    middle = len(tests) // 2
    labels = ("Tests 1–%d" % middle, "Tests %d–%d" % (middle + 1, len(tests)))
    averages = []
    for group in (tests[:middle], tests[middle:]):
        row = [mean([t["sections"].get(name) for t in group]) for name in sections]
        row.append(mean([section_sum(t, sections) for t in group]))
        row.append(mean([t.get("overall") for t in group]))
        averages.append(row)
    rows = [[label] + [fmt(value) for value in row]
            for label, row in zip(labels, averages)]
    rows.append(["Change"] + [
        signed(after - before) if before is not None and after is not None else ""
        for before, after in zip(*averages)])
    return ["## First half against second half", "",
            table(["Period"] + [title_of(s) for s in sections] + ["Sum", "Overall"],
                  rows, ["l"] + ["r"] * (len(sections) + 2)), ""]


def tasks_table(tests):
    names = []
    for test in tests:
        for key in (test.get("tasks") or {}):
            if key not in names:
                names.append(key)
    if not names:
        return []
    heads = error_catalog.short_names(tests)
    rows = []
    for name in names:
        row = [title_of(name)]
        for test in tests:
            value = (test.get("tasks") or {}).get(name)
            row.append(fmt(metric_value(value)) if value is not None else "")
        rows.append(row)
    lines = ["## Inside the sections", "",
             table(["Task"] + heads, rows, ["l"] + ["r"] * len(heads)), "",
             "Per-item scores are shown as their average. Columns: %s."
             % ", ".join("%s = %s" % (h, t["name"]) for h, t in zip(heads, tests)),
             ""]
    return lines


def render_history(tests):
    sections = section_names(tests)
    exams = sorted({str(t.get("exam")) for t in tests})
    lines = ["# Test history", "",
             bold("%s · %s → %s · %s" % (
                 plural(len(tests), "test"), short_date(tests[0]["ts"]),
                 short_date(tests[-1]["ts"]), ", ".join(exams))), ""]
    lines += history_table(tests, sections)
    if len(tests) >= 2:
        latest, previous = tests[-1], tests[-2]
        deltas = []
        for name in sections:
            now, before = latest["sections"].get(name), previous["sections"].get(name)
            if now is not None and before is not None:
                deltas.append("%s %s" % (title_of(name), signed(now - before)))
        if deltas:
            lines += ["%s against %s: %s." % (bold(latest["name"]),
                                              previous["name"], " · ".join(deltas)),
                      ""]
    lines += halves_table(tests, sections)
    lines += tasks_table(tests)
    notes = [(t["name"], t["note"]) for t in tests if t.get("note")]
    if notes:
        lines += ["## Notes", ""] + ["- **%s:** %s" % (n, cell(t)) for n, t in notes] + [""]
    if len(tests) < 4:
        lines += ["With fewer than four tests, a difference between two of "
                  "them is not yet a trend.", ""]
    lines += [DISCLAIMER, ""]
    return "\n".join(lines)


# ---- one test ----------------------------------------------------------

def render_review(tests, errors, test, closed_after=error_catalog.CLOSED_AFTER):
    position = tests.index(test)
    earlier = tests[:position]
    upto = tests[:position + 1]
    sections = section_names([test])

    lines = ["# Test review — %s" % test["name"], ""]
    facts = [short_date(test["ts"]), str(test.get("exam") or "")]
    if test.get("source"):
        facts.append(str(test["source"]))
    facts.append("test %d of %d logged" % (position + 1, len(tests)))
    lines += [bold(" · ".join(f for f in facts if f)), ""]

    # Scores against the previous test and against everything before it.
    rows = []
    for name in sections + ["overall"]:
        value = test.get("overall") if name == "overall" else test["sections"].get(name)
        if value is None:
            continue

        def earlier_value(other):
            return other.get("overall") if name == "overall" \
                else other["sections"].get(name)

        history = [earlier_value(t) for t in earlier if earlier_value(t) is not None]
        previous = history[-1] if history else None
        average = mean(history)
        mark = ""
        if history:
            if value > max(history):
                mark = "record"
            elif value == max(history):
                mark = "ties the record"
            elif value < min(history):
                mark = "lowest so far"
        rows.append([title_of(name), band(value),
                     signed(value - previous) if previous is not None else "",
                     signed(value - average) if average is not None else "",
                     mark])
    lines += ["## Scores", "",
              table(["Section", "Score", "vs previous", "vs earlier average", ""],
                    rows, ["l", "r", "r", "r", "l"]), ""]
    if test.get("overall_computed"):
        lines += ["Overall computed from the four sections, not reported by "
                  "the test.", ""]

    tasks = test.get("tasks") or {}
    if tasks:
        rows = []
        for name, value in tasks.items():
            detail = " ".join(fmt(v) for v in value) if isinstance(value, list) else ""
            before = [metric_value((t.get("tasks") or {}).get(name)) for t in earlier
                      if (t.get("tasks") or {}).get(name) is not None]
            rows.append([title_of(name), fmt(metric_value(value)), detail,
                         fmt(before[-1]) if before else "",
                         fmt(mean(before)) if before else ""])
        lines += ["## Inside the sections", "",
                  table(["Task", "This test", "Per item", "Previous", "Earlier average"],
                        rows, ["l", "r", "l", "r", "r"]), ""]

    # Mistakes: what is new, what came back, what stayed away.
    points = error_catalog.build_units(upto, errors, "point", closed_after)
    here = [p for p in points if p["per_test"][position] > 0]
    if not here:
        lines += ["## Mistakes", "",
                  "No mistakes are logged for this test yet. Log them with "
                  "`coach log-error --batch … --session %s` and rebuild."
                  % test["session"], ""]
    else:
        total = sum(p["per_test"][position] for p in here)
        new = [p for p in here if p["tests_hit"] == 1]
        again = [p for p in here if p["tests_hit"] > 1]
        lines += ["## Mistakes", "",
                  bold("%s in %s — %d new, %d seen before"
                       % (plural(total, "mistake"), plural(len(here), "point"),
                          len(new), len(again))), ""]
        if again:
            rows = []
            for unit in sorted(again, key=lambda u: (-u["tests_hit"], -u["count"])):
                where = [t["name"] for t, c in zip(upto, unit["per_test"]) if c]
                rows.append([unit["label"], unit["tag"],
                             unit["per_test"][position],
                             "%d of %d" % (unit["tests_hit"], len(upto)),
                             " · ".join(where[:-1])])
            lines += ["### Seen before", "",
                      table(["Point", "Type", "Here", "Tests", "Earlier in"],
                            rows, ["l", "l", "r", "r", "l"]), ""]
        if new:
            lines += ["### New in this test", "",
                      table(["Point", "Type", "Here"],
                            [[u["label"], u["tag"], u["per_test"][position]]
                             for u in new], ["l", "l", "r"]), ""]

        lines += ["### What was written or said", ""]
        for unit in sorted(here, key=lambda u: (u["category"], u["subtype"],
                                                u["label"])):
            lines.append("**%s** — %s" % (cell(unit["label"]), unit["tag"]))
            lines.append("")
            for row in unit["cases"]:
                if row.get("session") != test["session"]:
                    continue
                wrong = str(row.get("evidence") or "").strip()
                right = str(row.get("fix") or "").strip()
                text = "*%s* → %s" % (wrong, right) if wrong and right \
                    else wrong or right or "(no quotation logged)"
                extra = []
                if row.get("task_type"):
                    extra.append(str(row["task_type"]))
                if row.get("transfer"):
                    extra.append("from the first language: %s" % row["transfer"])
                lines.append("- %s%s" % (text, " — %s" % "; ".join(extra) if extra else ""))
            lines.append("")

    # Points that used to appear and did not this time.
    away = [p for p in points if p["per_test"][position] == 0 and p["tests_hit"] > 0]
    if away and earlier:
        rows = []
        for unit in sorted(away, key=lambda u: (-u["tests_hit"], -u["count"])):
            last = max(i for i, c in enumerate(unit["per_test"]) if c)
            clean = position - last
            if clean >= closed_after:
                verdict = "closed"
            else:
                verdict = "%d clean, %d to go" % (clean, closed_after - clean)
            rows.append([unit["label"], unit["tag"],
                         "%d of %d" % (unit["tests_hit"], len(upto)),
                         upto[last]["name"], verdict])
        lines += ["## Stayed away this time", "",
                  "A point counts as closed after %d clean tests in a row — "
                  "not before." % closed_after, "",
                  table(["Point", "Type", "Tests", "Last seen", "Status"],
                        rows[:30], ["l", "l", "r", "l", "l"]), ""]

    if test.get("note"):
        lines += ["## Note", "", cell(test["note"]), ""]
    lines += [DISCLAIMER, ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--test", default=None,
                        help="review one test: its name, a unique start of "
                             "its name, or its session id")
    parser.add_argument("--json", action="store_true",
                        help="print the logged tests as JSON")
    parser.add_argument("--no-write", action="store_true",
                        help="print the report without writing a file")
    state.add_location_arguments(parser)
    args = parser.parse_args(argv)

    base = state.base_from_args(args)
    tests, errors = error_catalog.load(base)
    if not tests:
        print("No full tests are logged in %s yet — record one with "
              "`coach log-test`." % base)
        return 0

    if args.json:
        print(json.dumps({"tests": tests}, ensure_ascii=False, indent=1))
        return 0

    if args.test:
        test = find_test(tests, args.test)
        if test is None:
            print("error: no single test matches %r. Logged: %s"
                  % (args.test, ", ".join(t["name"] for t in tests)),
                  file=sys.stderr)
            return 2
        report = render_review(tests, errors, test)
        filename = "%s.md" % test["session"]
    else:
        report = render_history(tests)
        filename = "tests-history.md"

    print(report)
    if not args.no_write:
        reports = base / "reports"
        reports.mkdir(parents=True, exist_ok=True)
        path = reports / filename
        path.write_text(report, encoding="utf-8")
        print("written: %s" % path, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
