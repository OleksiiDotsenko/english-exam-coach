#!/usr/bin/env python3
"""Decide what to drill next, and say why in one sentence.

Every surface that asks "what should I practise?" — /daily-drill, /start-prep,
the end of any scored task — funnels through here, so the answer is the same
wherever it is asked and can always be explained.

It reads, in this order of authority:
  1. queue.json   points that are due for re-testing (time-sensitive: a point
                  re-tested late is a point being forgotten)
  2. errors.jsonl what has been going wrong most often
  3. attempts.jsonl  the weakest task type, level-relative
  4. profile.json the target, so the reason can reference it

It never invents work: with an empty history it says so and suggests the
diagnostic instead of guessing.

Examples:
  drill_context.py
  drill_context.py --json
"""

import argparse
import json
import sys
from datetime import date

import build_report
import learner_profile as profile_module
import review_queue as queue_module
import state

ERROR_LOG = "errors.jsonl"


def recent_error_counts(base, limit=40):
    """How often each category/subtype has come up lately."""
    rows, _skipped = state.read_errors(base)
    counts = {}
    for row in rows[-limit:]:
        key = (row["category"], row["subtype"])
        counts[key] = counts.get(key, 0) + 1
    return counts


def weakest_task(base):
    """(task_type, attainment, attempts, level) from the attempts log, or None."""
    log_path = base / "attempts.jsonl"
    rows, _skipped = state.read_jsonl(
        log_path, required_keys=("exam", "skill", "task_type"))
    rows = [r for r in rows if r.get("ts") and r.get("session")]
    if not rows:
        return None
    ranked = build_report.rank_task_types(rows)
    if not ranked:
        return None
    task_type, attainment, count = ranked[0]
    sample = next((r for r in rows if str(r.get("task_type")) == task_type), {})
    return task_type, attainment, count, sample.get("level")


def choose(base, today=None):
    """Return one recommendation as a dict. Always explains itself."""
    today = today or date.today()
    queue, note = queue_module.load_queue(base)
    due = queue_module.due_items(queue, today=today, limit=5)
    errors = recent_error_counts(base)
    weakest = weakest_task(base)
    learner = profile_module.read_profile(base)

    target_clause = ""
    if learner.get("target_cefr") and learner.get("exam"):
        target_clause = (" Your target is %s (about CEFR %s)."
                         % (learner.get("target_score") or learner["exam"],
                            learner["target_cefr"]))

    if due:
        lead = due[0]
        points = [{"id": i["id"], "category": i["category"],
                   "subtype": i["subtype"], "point": i["point"],
                   "occurrences": i.get("occurrences", 1), "box": i.get("box", 1)}
                  for i in due]
        reason = ("%d point%s %s due for re-testing; the oldest is %s (%s/%s), "
                  "which you have got wrong %s time%s."
                  % (len(due), "" if len(due) == 1 else "s",
                     "is" if len(due) == 1 else "are",
                     lead["point"], lead["category"], lead["subtype"],
                     lead.get("occurrences", 1),
                     "" if lead.get("occurrences", 1) == 1 else "s"))
        return {
            "action": "re-test",
            "headline": "Re-test %d point%s you have missed before"
                        % (len(due), "" if len(due) == 1 else "s"),
            "reason": reason + target_clause,
            "points": points,
            "task_type": lead.get("task_type"),
            "exam": lead.get("exam") or learner.get("exam"),
            "level": lead.get("level"),
            "instruction": ("Generate a FRESH item for each point — never reuse "
                            "the original wording. Then record each result with "
                            "`coach queue review --id <id> --result pass|fail`."),
            "note": note,
        }

    if errors:
        (category, subtype), count = max(errors.items(), key=lambda kv: kv[1])
        if count >= 2:
            return {
                "action": "target-error-type",
                "headline": "Drill %s (%s)" % (subtype, category),
                "reason": ("%s/%s has come up %d times in your recent work and "
                           "nothing is due for re-testing yet."
                           % (category, subtype, count)) + target_clause,
                "points": [],
                "exam": learner.get("exam"),
                "instruction": ("Build a short set that forces this exact "
                                "structure, then log any misses with "
                                "`coach log-error` so they enter the queue."),
                "note": note,
            }

    if weakest:
        task_type, attainment, count, level = weakest
        return {
            "action": "weakest-task",
            "headline": "Drill %s" % build_report.display_task(task_type),
            "reason": ("It is your weakest task type over %s — %s."
                       % (build_report.plural(count, "attempt"),
                          build_report.attainment_phrase(attainment)))
                      + target_clause,
            "points": [],
            "task_type": task_type,
            "level": level,
            "exam": learner.get("exam"),
            "instruction": ("Run a normal drill of this task type, and log any "
                            "specific misses with `coach log-error` so the queue can "
                            "bring them back."),
            "note": note,
        }

    return {
        "action": "cold-start",
        "headline": "Start with a level check",
        "reason": ("There is nothing logged yet, so there is no evidence to "
                   "choose from — a 15-minute diagnostic gives the log its "
                   "first data point.") + target_clause,
        "points": [],
        "exam": learner.get("exam"),
        "instruction": "Run /assess-level, or pick any task type to begin.",
        "note": note,
    }


def render(choice):
    lines = ["**%s**" % choice["headline"], "", choice["reason"]]
    if choice.get("points"):
        lines.append("")
        for point in choice["points"]:
            lines.append("- `%s` %s/%s — %s (missed %sx, box %s)"
                         % (point["id"], point["category"], point["subtype"],
                            point["point"], point["occurrences"], point["box"]))
    lines += ["", choice["instruction"]]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    state.add_location_arguments(parser)
    parser.add_argument("--json", action="store_true",
                        help="machine-readable output")
    args = parser.parse_args(argv)

    base = state.base_from_args(args)
    choice = choose(base)
    if choice.get("note"):
        print("warning: %s" % choice["note"], file=sys.stderr)

    if args.json:
        print(json.dumps(choice, ensure_ascii=False))
    else:
        print(render(choice))
    return 0


if __name__ == "__main__":
    sys.exit(main())
