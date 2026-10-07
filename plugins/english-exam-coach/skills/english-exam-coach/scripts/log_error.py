#!/usr/bin/env python3
"""Record specific mistakes, so they can be re-tested later instead of forgotten.

Scores say a learner is B2. The error ledger says *why*: which point, in which
task, in their own words. It is the memory that turns a grader into a coach —
the review queue schedules these points for re-testing, the error catalog
counts how they spread across tests, and the drill selector picks what to
practise next from them.

The taxonomy is a CLOSED enum on purpose. Free-form tags drift ("articles",
"article", "determiners") until nothing groups, and a mis-tagged error silently
drills the wrong thing for weeks. The specific target goes in --point, which is
required and free text.

Writes JSON lines to <base>/errors.jsonl, append-only, via the state contract.

One mistake:
  log_error.py --category grammar --subtype article \\
      --point "zero article with uncountable nouns" \\
      --evidence "the information were useful" --fix "the information was useful" \\
      --exam ielts-academic --skill writing --task-type ielts-task2-essay

Many at once (a reviewed test usually yields dozens) — a JSON-lines file, or a
JSON array, of objects with the same field names. Flags given on the command
line fill in whatever a row leaves out. Nothing is written unless every row is
valid:
  log_error.py --batch errors.jsonl --session test-saturn-20260825 \\
      --exam toefl-ibt --level B2

  log_error.py --list-taxonomy

The log is append-only, so a mistake logged wrongly is corrected by a newer
line, never by editing the file. Every mistake has an id (`error_catalog.py
--full --ids` shows them):
  log_error.py --void e-3f2a9c1d --reason "not an error: both forms are fine"
  log_error.py --amend e-3f2a9c1d --subtype countability \
      --point "information as an uncountable noun"
"""

import argparse
import json
import sys
import uuid
from datetime import datetime

import fileguard
import state

ERROR_LOG = "errors.jsonl"
CEFR_LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")

# category -> subtype -> what it means. Closed by design; extend deliberately,
# in the same commit as the instructions that will emit the new tag.
TAXONOMY = {
    "grammar": {
        "verb-form": "tense, aspect or voice wrong, or the wrong verb form after "
                     "another word (look forward to meet)",
        "agreement": "subject-verb or number agreement",
        "article": "a/an/the/zero article: missing, extra or the wrong one",
        "preposition": "wrong or missing preposition",
        "word-order": "constituents in the wrong order, including inversion",
        "clause": "relative, subordinate or conditional clause structure",
        "countability": "countable/uncountable treatment of a noun",
        "modality": "the wrong modal for the meaning, or the wrong form after a "
                    "modal (must to go)",
        "pronoun": "wrong, missing or unnecessary pronoun, reflexives included",
        "omission": "a required word left out: be, a subject, an auxiliary",
        "punctuation": "punctuation that changes or obscures meaning",
    },
    "lexis": {
        "word-choice": "a real word, wrong for this meaning",
        "collocation": "words that do not go together in natural English",
        "register": "formality that does not fit the task or reader",
        "word-formation": "wrong derived form (noun/adjective/adverb)",
        "non-word": "a form that is not an English word at all",
        "spelling": "misspelling, including exam-relevant variants",
        "range": "over-repetition where the level expects variation",
        "redundancy": "words that repeat what has already been said",
    },
    "discourse": {
        "cohesion": "linkers and referencing across sentences",
        "paragraphing": "paragraph boundaries or internal structure",
        "coherence": "ideas ordered so the reader loses the thread",
        "development": "a point asserted but not developed or supported",
    },
    "task": {
        "task-response": "did not answer the question that was asked",
        "content-point": "a required content point missing or half-covered",
        "length": "under or over the word count the task sets",
        "format": "wrong genre conventions for the text type",
        "audience": "tone or stance wrong for the stated reader",
    },
    "comprehension": {
        "detail": "explicit information missed or misread",
        "inference": "an inference the text supports but the learner missed",
        "paraphrase": "did not recognise a restatement of the text",
        "distractor": "chose a deliberate trap option",
        "purpose": "why something is said, answered as if asked what is said",
        "main-idea": "chose a detail when the main point or topic was asked",
        "negation": "a negative question or a NOT/EXCEPT item read backwards",
        "structure": "how parts relate: paragraph roles, sentence insertion",
        "vocabulary": "did not know a word the item depended on",
        "location": "could not find where the answer was",
        "instruction": "broke the item's own rules (word limit, letter, form)",
    },
    "delivery": {
        "fluency": "hesitation or self-correction that breaks the message",
        "pace": "too fast or too slow for the task",
        "intelligibility": "a word or sound that a listener genuinely misheard",
        "repetition": "words dropped, replaced or mangled when repeating",
        "interaction": "turn-taking, responding, or holding the floor",
    },
    "vocabulary": {
        "recall": "could not produce a studied item when needed",
        "meaning": "recalled the item with the wrong meaning",
        "form": "right item, wrong grammatical form",
        "usage": "right meaning, wrong context or collocation",
    },
    "strategy": {
        "timing": "ran out of time or spent it in the wrong place",
        "planning": "started producing without a usable plan",
        "checking": "an error the learner could have caught by checking",
        "technique": "did not use the method the task type rewards",
    },
}

# Fields a record may carry. `transfer` notes what in the learner's first
# language produces the error ("зосередитися -> concentrate myself"): errors
# of that kind are translated, not mis-learned, and respond to contrast pairs
# rather than to another explanation of the rule.
TEXT_FIELDS = ("exam", "skill", "task_type", "evidence", "fix", "transfer")
FIELDS = ("category", "subtype", "point", "level", "item", "session", "ts") \
    + TEXT_FIELDS


def taxonomy_text():
    lines = ["Error taxonomy (closed enum — use --point for the specific target):"]
    for category in sorted(TAXONOMY):
        lines.append("")
        lines.append("  %s" % category)
        for subtype in sorted(TAXONOMY[category]):
            lines.append("    %-16s %s" % (subtype, TAXONOMY[category][subtype]))
    return "\n".join(lines)


def text(value):
    return "" if value is None else str(value).strip()


def parse_ts(value):
    """ISO 8601 -> naive local datetime (matching every other reader)."""
    stamp = datetime.fromisoformat(text(value).replace("Z", "+00:00"))
    if stamp.tzinfo is not None:
        stamp = stamp.astimezone().replace(tzinfo=None)
    return stamp


def validate_fields(fields):
    """Human-readable problems with one error's fields (empty list = valid)."""
    problems = []
    category = text(fields.get("category")).lower()
    subtype = text(fields.get("subtype")).lower()

    if category not in TAXONOMY:
        problems.append("category must be one of %s (got %r)"
                        % ("/".join(sorted(TAXONOMY)), fields.get("category")))
    elif subtype not in TAXONOMY[category]:
        problems.append("subtype for %s must be one of %s (got %r)"
                        % (category, "/".join(sorted(TAXONOMY[category])),
                           fields.get("subtype")))

    point = text(fields.get("point"))
    if not point:
        problems.append("point is required: name the specific thing to "
                        "re-test, e.g. \"past perfect after 'by the time'\"")
    elif len(point) < 4:
        problems.append("point is too short to be a re-testable target "
                        "(got %r)" % fields.get("point"))

    level = text(fields.get("level"))
    if level and level.upper() not in CEFR_LEVELS:
        problems.append("level must be a CEFR level (got %r)" % fields.get("level"))

    item = fields.get("item")
    if item is not None and item != "":
        try:
            int(item)
        except (TypeError, ValueError):
            problems.append("item must be a whole number (got %r)" % (item,))

    if text(fields.get("ts")):
        try:
            parse_ts(fields["ts"])
        except ValueError:
            problems.append("ts must be an ISO 8601 timestamp (got %r)"
                            % fields.get("ts"))
    return problems


def build_record(fields, now):
    stamp = parse_ts(fields["ts"]) if text(fields.get("ts")) else now
    record = {
        "ts": stamp.isoformat(timespec="seconds"),
        "id": "e-" + uuid.uuid4().hex[:8],
        "category": text(fields["category"]).lower(),
        "subtype": text(fields["subtype"]).lower(),
        "point": text(fields["point"]),
    }
    for name in TEXT_FIELDS:
        if text(fields.get(name)):
            record[name] = text(fields[name])
    if text(fields.get("level")):
        record["level"] = text(fields["level"]).upper()
    if fields.get("item") not in (None, ""):
        record["item"] = int(fields["item"])
    record["session"] = text(fields.get("session")) or \
        "{:%Y-%m-%d}-{}".format(stamp, "am" if stamp.hour < 12 else "pm")
    return record


def read_batch(source):
    """Rows from a JSON-lines file or a JSON array. Raises ValueError."""
    raw = fileguard.read_text(source)
    stripped = raw.strip()
    if not stripped:
        return []
    if stripped.startswith("["):
        rows = json.loads(stripped)
    else:
        rows = []
        for number, line in enumerate(stripped.splitlines(), 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except ValueError as exc:
                raise ValueError("line %d is not valid JSON (%s)" % (number, exc))
    if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
        raise ValueError("expected a list of objects, one per mistake")
    return rows


def build_parser():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--list-taxonomy", action="store_true",
                        help="print the closed enum and exit")
    parser.add_argument("--batch", default=None, metavar="FILE",
                        help="JSON-lines file (or JSON array, or - for stdin) "
                             "of mistakes; other flags become row defaults")
    parser.add_argument("--category", default=None)
    parser.add_argument("--subtype", default=None)
    parser.add_argument("--point", default=None,
                        help="the specific, re-testable target (required)")
    parser.add_argument("--evidence", default=None,
                        help="the learner's own words that show the error")
    parser.add_argument("--fix", default=None, help="the corrected version")
    parser.add_argument("--transfer", default=None,
                        help="what in the learner's first language produces "
                             "this error, when that is the cause")
    parser.add_argument("--exam", default=None)
    parser.add_argument("--skill", default=None)
    parser.add_argument("--task-type", default=None, dest="task_type")
    parser.add_argument("--level", default=None)
    parser.add_argument("--item", type=int, default=None,
                        help="item number, for objective drills")
    parser.add_argument("--session", default=None,
                        help="session or test id this mistake belongs to")
    parser.add_argument("--ts", default=None)
    parser.add_argument("--void", action="append", default=[], metavar="ID",
                        help="withdraw a mistake that was logged in error. "
                             "Repeatable.")
    parser.add_argument("--amend", default=None, metavar="ID",
                        help="replace a mistake: give its id and only the "
                             "fields that change")
    parser.add_argument("--reason", default=None,
                        help="why a mistake is being withdrawn (kept in the log)")
    state.add_location_arguments(parser)
    return parser


def correct(args, defaults):
    """Handle --void and --amend. Corrections are new lines, never edits."""
    base = state.base_from_args(args)
    active = {row["id"]: row for row in state.read_errors(base)[0]}
    wanted = list(args.void) + ([args.amend] if args.amend else [])
    missing = [ident for ident in wanted if ident not in active]
    if missing:
        print("error: no logged mistake has the id %s (ids are listed by "
              "`coach catalog --full --ids`). Nothing was written."
              % ", ".join(missing), file=sys.stderr)
        return 2
    now = datetime.now()
    stamp = now.isoformat(timespec="seconds")
    try:
        if args.amend:
            old = active[args.amend]
            fields = {name: old.get(name) for name in FIELDS if old.get(name) is not None}
            fields.update(defaults)
            problems = validate_fields(fields)
            if problems:
                for problem in problems:
                    print("error: --%s" % problem, file=sys.stderr)
                print("\nNothing was written.", file=sys.stderr)
                return 2
            record = build_record(fields, now)
            record["amends"] = args.amend
            # The replacement first, the withdrawal second: if anything fails
            # in between, the result is a duplicate rather than a loss.
            state.append_jsonl(base / ERROR_LOG, record)
            state.append_jsonl(base / ERROR_LOG, {
                "ts": stamp, "void": args.amend,
                "reason": "amended as %s" % record["id"]})
            print("amended: %s/%s — %s (id %s, replacing %s)"
                  % (record["category"], record["subtype"], record["point"],
                     record["id"], args.amend))
        for ident in args.void:
            marker = {"ts": stamp, "void": ident}
            if text(args.reason):
                marker["reason"] = text(args.reason)
            state.append_jsonl(base / ERROR_LOG, marker)
        if args.void:
            print("withdrawn %d mistake%s"
                  % (len(args.void), "" if len(args.void) == 1 else "s"))
    except OSError as exc:
        print("error: could not write %s: %s" % (base / ERROR_LOG, exc),
              file=sys.stderr)
        return 1
    print("Run `coach queue sync` so the queue follows the correction.")
    return 0


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.list_taxonomy:
        print(taxonomy_text())
        return 0

    defaults = {name: getattr(args, name) for name in FIELDS
                if getattr(args, name, None) is not None}

    if args.void or args.amend:
        if args.batch:
            print("error: --void and --amend cannot be combined with --batch",
                  file=sys.stderr)
            return 2
        return correct(args, defaults)

    if args.batch:
        try:
            rows = read_batch(args.batch)
        except (OSError, ValueError) as exc:
            print("error: could not read the batch: %s" % exc, file=sys.stderr)
            return 2
        if not rows:
            print("error: the batch is empty", file=sys.stderr)
            return 2
        merged = [dict(defaults, **{k: v for k, v in row.items() if v is not None})
                  for row in rows]
    else:
        merged = [defaults]

    # Validate everything before writing anything: a half-imported batch
    # would have to be untangled by hand in an append-only log.
    failures = []
    for number, fields in enumerate(merged, 1):
        for problem in validate_fields(fields):
            prefix = "row %d: " % number if args.batch else "--"
            failures.append(prefix + problem)
    if failures:
        for failure in failures:
            print("error: %s" % failure, file=sys.stderr)
        print("\nNothing was written. Run with --list-taxonomy to see the "
              "valid categories.", file=sys.stderr)
        return 2

    base = state.base_from_args(args)
    now = datetime.now()
    records = [build_record(fields, now) for fields in merged]
    try:
        for record in records:
            state.append_jsonl(base / ERROR_LOG, record)
    except OSError as exc:
        print("error: could not write %s: %s" % (base / ERROR_LOG, exc),
              file=sys.stderr)
        return 1

    if args.batch:
        by_category = {}
        for record in records:
            by_category[record["category"]] = by_category.get(record["category"], 0) + 1
        summary = ", ".join("%d %s" % (count, name)
                            for name, count in sorted(by_category.items(),
                                                      key=lambda kv: -kv[1]))
        print("noted %d mistake%s (%s)"
              % (len(records), "" if len(records) == 1 else "s", summary))
    else:
        record = records[0]
        print("noted: %s/%s — %s (id %s)" % (record["category"], record["subtype"],
                                             record["point"], record["id"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
