#!/usr/bin/env python3
"""Schedule the points a learner got wrong for re-testing, Leitner style.

An explanation given once is forgotten on the usual curve. This turns each
logged error into a scheduled re-test: pass it and it comes back later, miss it
and it comes back tomorrow. What gets re-tested is a *point* — the drill itself
is generated fresh each time, so nothing can be answered from memory of the
card.

State lives in <base>/queue.json and is written ONLY by this script (atomically,
via the state contract). If the file is ever corrupt it is quarantined and
rebuilt from the error log rather than lost.

Intervals match the vocabulary Leitner boxes already used by the plugin:
  box 1 = next session · box 2 = 1 day · box 3 = 3 days · box 4 = 7 days ·
  box 5 = 30 days (mature)

Examples:
  queue.py sync                      # pull new points out of errors.jsonl
  queue.py due --limit 5
  queue.py review --id g-article-3f2 --result pass
  queue.py show
"""

import argparse
import hashlib
import re
import sys
from datetime import datetime, date, timedelta

import state

QUEUE_NAME = "queue.json"
ERROR_LOG = "errors.jsonl"

# Days until the next re-test, by box. Box 1 means "next session", which we
# store as due today so it surfaces immediately.
BOX_INTERVALS = {1: 0, 2: 1, 3: 3, 4: 7, 5: 30}
MAX_BOX = 5


def normalize_point(text):
    """Collapse a free-text point to a grouping key.

    'Past perfect after "by the time".' and 'past perfect after by the time'
    must land on the same queue item, or the same weakness is scheduled twice.
    """
    text = str(text).lower().strip()
    text = re.sub(r"[^a-z0-9\s]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def item_id(category, subtype, point):
    digest = hashlib.sha1(
        ("%s|%s|%s" % (category, subtype, normalize_point(point))).encode("utf-8")
    ).hexdigest()[:6]
    return "%s-%s-%s" % (category[:1], subtype, digest)


def load_queue(base):
    """Return (queue_dict, note). A corrupt queue is quarantined, never fatal."""
    data, note = state.read_json(base / QUEUE_NAME,
                                 default={"version": state.STATE_VERSION,
                                          "items": []},
                                 quarantine_on_error=True)
    if not isinstance(data.get("items"), list):
        data["items"] = []
    return data, note


def save_queue(base, queue):
    state.stamp_version(queue)
    return state.write_json(base / QUEUE_NAME, queue)


def sync_from_errors(base, queue, today=None):
    """Fold new error-log points into the queue. Returns (added, bumped)."""
    today = today or date.today()
    rows, _skipped = state.read_jsonl(base / ERROR_LOG,
                                      required_keys=("category", "subtype", "point"))
    by_id = {item["id"]: item for item in queue["items"] if item.get("id")}
    added, bumped = 0, 0
    for row in rows:
        ident = item_id(row["category"], row["subtype"], row["point"])
        seen_at = str(row.get("ts") or "")
        existing = by_id.get(ident)
        if existing is None:
            item = {
                "id": ident,
                "category": row["category"],
                "subtype": row["subtype"],
                "point": str(row["point"]).strip(),
                "box": 1,
                "due": today.isoformat(),
                "added": seen_at or datetime.now().isoformat(timespec="seconds"),
                "occurrences": 1,
                "reviews": 0,
                "lapses": 0,
                "last_seen": seen_at,
            }
            for key in ("exam", "skill", "task_type", "level"):
                if row.get(key):
                    item[key] = row[key]
            queue["items"].append(item)
            by_id[ident] = item
            added += 1
        elif seen_at and seen_at > str(existing.get("last_seen") or ""):
            # The same point again: it is more urgent, not just more numerous.
            existing["occurrences"] = int(existing.get("occurrences", 1)) + 1
            existing["last_seen"] = seen_at
            if int(existing.get("box", 1)) > 1:
                existing["box"] = 1
                existing["due"] = today.isoformat()
                existing["lapses"] = int(existing.get("lapses", 0)) + 1
            bumped += 1
    return added, bumped


def due_items(queue, today=None, limit=None, min_occurrences=1):
    today = today or date.today()
    due = []
    for item in queue["items"]:
        if int(item.get("occurrences", 1)) < min_occurrences:
            continue
        try:
            when = datetime.strptime(str(item.get("due")), "%Y-%m-%d").date()
        except ValueError:
            when = today  # an unparseable due date should surface, not vanish
        if when <= today:
            due.append(item)
    # Most-repeated first, then oldest due, so the standing weaknesses lead.
    due.sort(key=lambda i: (-int(i.get("occurrences", 1)), str(i.get("due"))))
    return due[:limit] if limit else due


def review(queue, ident, passed, today=None):
    """Promote or demote one item. Returns the updated item, or None."""
    today = today or date.today()
    for item in queue["items"]:
        if item.get("id") == ident:
            box = int(item.get("box", 1))
            if passed:
                box = min(MAX_BOX, box + 1)
            else:
                box = 1
                item["lapses"] = int(item.get("lapses", 0)) + 1
            item["box"] = box
            item["due"] = (today + timedelta(days=BOX_INTERVALS[box])).isoformat()
            item["reviews"] = int(item.get("reviews", 0)) + 1
            item["last_review"] = today.isoformat()
            return item
    return None


def format_item(item, verbose=False):
    head = "%-22s %s/%s — %s" % (item.get("id"), item.get("category"),
                                 item.get("subtype"), item.get("point"))
    if not verbose:
        return head
    return "%s\n%26sbox %s · due %s · seen %sx · %s reviews, %s lapses" % (
        head, "", item.get("box"), item.get("due"),
        item.get("occurrences", 1), item.get("reviews", 0), item.get("lapses", 0))


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    for name, helptext in (("sync", "fold new points out of errors.jsonl"),
                           ("due", "list what is due for re-testing"),
                           ("show", "list the whole queue")):
        p = sub.add_parser(name, help=helptext)
        p.add_argument("--base", default=None)
        if name == "due":
            p.add_argument("--limit", type=int, default=None)
            p.add_argument("--min-occurrences", type=int, default=1,
                           dest="min_occurrences",
                           help="ignore points seen fewer times than this")

    rev = sub.add_parser("review", help="record the result of a re-test")
    rev.add_argument("--id", required=True, dest="ident")
    rev.add_argument("--result", required=True, choices=("pass", "fail"))
    rev.add_argument("--base", default=None)

    args = parser.parse_args(argv)
    base = state.resolve_base(args.base)
    queue, note = load_queue(base)
    if note:
        print("warning: %s" % note, file=sys.stderr)

    if args.command == "sync":
        added, bumped = sync_from_errors(base, queue)
        save_queue(base, queue)
        print("queue: %d new point%s, %d repeat%s, %d total"
              % (added, "" if added == 1 else "s",
                 bumped, "" if bumped == 1 else "s", len(queue["items"])))
        return 0

    if args.command == "due":
        items = due_items(queue, limit=args.limit,
                          min_occurrences=args.min_occurrences)
        if not items:
            print("Nothing is due for re-testing.")
            return 0
        print("Due for re-testing (%d):" % len(items))
        for item in items:
            print("  " + format_item(item, verbose=True))
        return 0

    if args.command == "show":
        if not queue["items"]:
            print("The queue is empty — run `queue.py sync` after logging errors.")
            return 0
        for item in sorted(queue["items"], key=lambda i: str(i.get("due"))):
            print("  " + format_item(item, verbose=True))
        print("\n%d point%s tracked." % (len(queue["items"]),
                                         "" if len(queue["items"]) == 1 else "s"))
        return 0

    item = review(queue, args.ident, args.result == "pass")
    if item is None:
        print("error: no queue item with id %r (run `queue.py show`)" % args.ident,
              file=sys.stderr)
        return 2
    save_queue(base, queue)
    print("%s: box %s, next due %s" % (args.ident, item["box"], item["due"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
