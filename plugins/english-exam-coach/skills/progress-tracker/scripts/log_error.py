#!/usr/bin/env python3
"""Record one specific mistake, so it can be re-tested later instead of forgotten.

Scores say a learner is B2. The error ledger says *why*: which point, in which
task, in their own words. It is the memory that turns a grader into a coach —
`queue.py` schedules these points for re-testing and `drill_context.py` picks
what to drill next from them.

The taxonomy is a CLOSED enum on purpose. Free-form tags drift ("articles",
"article", "determiners") until nothing groups, and a mis-tagged error silently
drills the wrong thing for weeks. The specific target goes in --point, which is
required and free text.

Writes one JSON line to <base>/errors.jsonl, append-only, via the state contract.

Examples:
  log_error.py --category grammar --subtype article \\
      --point "zero article with uncountable nouns" \\
      --evidence "the information were useful" --fix "the information was useful" \\
      --exam ielts-academic --skill writing-evaluator --task-type ielts-task2-essay

  log_error.py --list-taxonomy
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import state

ERROR_LOG = "errors.jsonl"

# category -> subtype -> what it means. Closed by design; extend deliberately,
# in the same commit as the skills that will emit the new tag.
TAXONOMY = {
    "grammar": {
        "verb-form": "tense, aspect or voice chosen or formed wrongly",
        "agreement": "subject-verb or number agreement",
        "article": "a/an/the/zero article",
        "preposition": "wrong or missing preposition",
        "word-order": "constituents in the wrong order, including inversion",
        "clause": "relative, subordinate or conditional clause structure",
        "countability": "countable/uncountable treatment of a noun",
        "modality": "modal verb choice or strength",
        "punctuation": "punctuation that changes or obscures meaning",
    },
    "lexis": {
        "word-choice": "a real word, wrong for this meaning",
        "collocation": "words that do not go together in natural English",
        "register": "formality that does not fit the task or reader",
        "word-formation": "wrong derived form (noun/adjective/adverb)",
        "spelling": "misspelling, including exam-relevant variants",
        "range": "over-repetition where the level expects variation",
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
        "location": "could not find where the answer was",
        "instruction": "broke the item's own rules (word limit, letter, form)",
    },
    "delivery": {
        "fluency": "hesitation or self-correction that breaks the message",
        "pace": "too fast or too slow for the task",
        "intelligibility": "a word or sound that a listener genuinely misheard",
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


def taxonomy_text():
    lines = ["Error taxonomy (closed enum — use --point for the specific target):"]
    for category in sorted(TAXONOMY):
        lines.append("")
        lines.append("  %s" % category)
        for subtype in sorted(TAXONOMY[category]):
            lines.append("    %-16s %s" % (subtype, TAXONOMY[category][subtype]))
    return "\n".join(lines)


def validate(args):
    errors = []
    category = (args.category or "").strip().lower()
    subtype = (args.subtype or "").strip().lower()

    if category not in TAXONOMY:
        errors.append("--category must be one of %s (got %r)"
                      % ("/".join(sorted(TAXONOMY)), args.category))
    elif subtype not in TAXONOMY[category]:
        errors.append("--subtype for %s must be one of %s (got %r)"
                      % (category, "/".join(sorted(TAXONOMY[category])), args.subtype))

    if not (args.point or "").strip():
        errors.append("--point is required: name the specific thing to re-test, "
                      "e.g. \"past perfect after 'by the time'\"")
    elif len(args.point.strip()) < 4:
        errors.append("--point is too short to be a re-testable target (got %r)"
                      % args.point)

    if args.level is not None:
        if args.level.strip().upper() not in ("A1", "A2", "B1", "B2", "C1", "C2"):
            errors.append("--level must be a CEFR level (got %r)" % args.level)

    if args.ts is not None:
        try:
            datetime.fromisoformat(args.ts.replace("Z", "+00:00"))
        except ValueError:
            errors.append("--ts must be an ISO 8601 timestamp (got %r)" % args.ts)
    return errors


def build_record(args, now):
    stamp = now
    if args.ts:
        stamp = datetime.fromisoformat(args.ts.replace("Z", "+00:00"))
        if stamp.tzinfo is not None:
            stamp = stamp.astimezone().replace(tzinfo=None)
    record = {
        "ts": stamp.isoformat(timespec="seconds"),
        "category": args.category.strip().lower(),
        "subtype": args.subtype.strip().lower(),
        "point": args.point.strip(),
    }
    for name, value in (("exam", args.exam), ("skill", args.skill),
                        ("task_type", args.task_type), ("evidence", args.evidence),
                        ("fix", args.fix)):
        if value and str(value).strip():
            record[name] = str(value).strip()
    if args.level:
        record["level"] = args.level.strip().upper()
    if args.item is not None:
        record["item"] = args.item
    record["session"] = (args.session.strip() if args.session and args.session.strip()
                         else "{:%Y-%m-%d}-{}".format(stamp,
                                                      "am" if stamp.hour < 12 else "pm"))
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--list-taxonomy", action="store_true",
                        help="print the closed enum and exit")
    parser.add_argument("--category", default=None)
    parser.add_argument("--subtype", default=None)
    parser.add_argument("--point", default=None,
                        help="the specific, re-testable target (required)")
    parser.add_argument("--evidence", default=None,
                        help="the learner's own words that show the error")
    parser.add_argument("--fix", default=None, help="the corrected version")
    parser.add_argument("--exam", default=None)
    parser.add_argument("--skill", default=None)
    parser.add_argument("--task-type", default=None, dest="task_type")
    parser.add_argument("--level", default=None)
    parser.add_argument("--item", type=int, default=None,
                        help="item number, for objective drills")
    parser.add_argument("--session", default=None)
    parser.add_argument("--ts", default=None)
    parser.add_argument("--base", default=None)
    args = parser.parse_args(argv)

    if args.list_taxonomy:
        print(taxonomy_text())
        return 0

    errors = validate(args)
    if errors:
        for error in errors:
            print("error: %s" % error, file=sys.stderr)
        print("\nRun with --list-taxonomy to see the valid categories.",
              file=sys.stderr)
        return 2

    base = state.resolve_base(args.base)
    record = build_record(args, datetime.now())
    try:
        state.append_jsonl(base / ERROR_LOG, record)
    except OSError as exc:
        print("error: could not write %s: %s" % (base / ERROR_LOG, exc),
              file=sys.stderr)
        return 1

    print("noted: %s/%s — %s" % (record["category"], record["subtype"],
                                 record["point"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
