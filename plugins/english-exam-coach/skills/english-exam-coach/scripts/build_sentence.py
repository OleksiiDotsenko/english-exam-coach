#!/usr/bin/env python3
"""Build and mark "Build a Sentence" items (TOEFL iBT, from January 2026).

Each item is TWO sentences: one that somebody says, and a reply the learner
assembles from word tiles. The shape, as the official practice material
shows it:

  - the first sentence is given whole (a question, a piece of news, a plan);
  - the reply is a frame of blanks, one blank per tile, 5 to 7 blanks; a word
    or two may already be printed in the frame ("The", "she will be"), and
    the closing full stop or question mark is shown;
  - the tiles are lower-case words and short phrases, in scrambled order;
  - some items carry ONE extra tile that is not used;
  - the item is right only if the whole reply is right.

You write the two sentences; this script cuts the reply into the frame and
the scrambled tiles, so the blanks always match the tiles, and marks answers
all-or-nothing.

Mark the tiles in the reply with | and anything pre-printed with [ ]:

  build_sentence.py make \\
      --context "The lab is closed on Friday." \\
      --answer "do | you | know | if | [we can] | hand in | the report | on Monday ?" \\
      --distractor "does"

  build_sentence.py make --batch set.json        a numbered set with its key
  build_sentence.py check --batch set.json --responses answers.txt
  build_sentence.py check --answer "…" --response "the learner's sentence"

A batch file is a JSON list of objects with the same names: context, answer,
distractor (optional), also (optional list of other replies to accept).
"""

import argparse
import json
import re
import sys
import zlib

import fileguard

MIN_BLANKS, MAX_BLANKS = 5, 7
BLANK = "_____"
# Our own wording: the official instruction is not reproduced.
INSTRUCTION = "Put the tiles in order to build each reply."
END_MARKS = (".", "?", "!")
# A reply that opens with one of these keeps its capital as a tile.
ALWAYS_CAPITAL = re.compile(r"^I(?:['’](?:m|ll|ve|d))?$")


def parse_answer(marked):
    """'do | you | [we can] | go ?' -> (parts, end mark).

    parts is a list of ("tile" | "fixed", text) in sentence order.
    """
    text = " ".join(str(marked).split())
    end = ""
    if text.endswith(END_MARKS):
        end, text = text[-1], text[:-1].rstrip()
    if not text:
        raise ValueError("the reply is empty")
    parts = []
    for segment in text.split("|"):
        # A segment may hold pre-printed words beside a tile: "[The] guides".
        position = 0
        for match in re.finditer(r"\[([^\[\]]*)\]", segment):
            before = segment[position:match.start()].strip()
            if before:
                parts.append(("tile", before))
            if match.group(1).strip():
                parts.append(("fixed", match.group(1).strip()))
            position = match.end()
        rest = segment[position:].strip()
        if rest:
            parts.append(("tile", rest))
    if any("[" in part or "]" in part for _kind, part in parts):
        raise ValueError("unbalanced [ ] in the reply")
    if not any(kind == "tile" for kind, _text in parts):
        raise ValueError("the reply has no tiles: separate them with |")
    return parts, end


def shuffled(tiles, extra, seed_text):
    """The tiles (plus the extra one, if any) in a scrambled order that is the
    same every time for the same item.

    A tiny generator of our own rather than `random`, so the order printed on
    a sheet can never change with the Python version. The real tiles are
    never left in their answer order, with or without the extra tile among
    them.
    """
    items = list(tiles) + ([extra] if extra else [])
    order = list(range(len(items)))
    state = zlib.crc32(seed_text.encode("utf-8")) or 1
    for _attempt in range(50):
        for index in range(len(order) - 1, 0, -1):
            state = (state * 1103515245 + 12345) & 0x7FFFFFFF
            other = state % (index + 1)
            order[index], order[other] = order[other], order[index]
        real = [items[i] for i in order if i < len(tiles)]
        if real != list(tiles) or len(set(tiles)) < 2:
            break
    return [items[i] for i in order]


def tile_text(text, opens_reply, keep_case):
    """How a tile is printed: the reply's first word loses its capital, so the
    capital cannot give the first tile away."""
    if keep_case or not opens_reply:
        return text
    first = text.split()[0]
    if ALWAYS_CAPITAL.match(first):
        return text
    return text[:1].lower() + text[1:]


def make_item(context, answer, distractor=None, also=(), keep_case=False,
              min_blanks=MIN_BLANKS, max_blanks=MAX_BLANKS):
    """One item: frame, scrambled tiles and key. Raises ValueError."""
    context = " ".join(str(context or "").split())
    if not context:
        raise ValueError("the first sentence (context) is missing: every item "
                         "is two sentences")
    parts, end = parse_answer(answer)
    if not end:
        raise ValueError("the reply must end with . ? or ! so the frame can "
                         "show it")
    blanks = sum(1 for kind, _text in parts if kind == "tile")
    if not min_blanks <= blanks <= max_blanks:
        raise ValueError("the reply has %d tile%s; official items have %d to %d. "
                         "Merge or split tiles, or pre-print a word with [ ]"
                         % (blanks, "" if blanks == 1 else "s", min_blanks, max_blanks))

    tiles, frame = [], []
    for index, (kind, text) in enumerate(parts):
        if kind == "fixed":
            frame.append(text[:1].upper() + text[1:] if index == 0 else text)
        else:
            tiles.append(tile_text(text, index == 0, keep_case))
            frame.append(BLANK)

    notes = []
    extra = " ".join(str(distractor or "").split())
    if extra:
        if extra.lower() in [t.lower() for t in tiles]:
            raise ValueError("the extra tile %r is one of the real tiles" % extra)
        notes.append("check that the reply cannot be built correctly with %r "
                     "in place of another tile" % extra)

    full = " ".join(text for _kind, text in parts) + end
    full = full[:1].upper() + full[1:]
    # The end mark sits against a printed word, and apart from a blank.
    ends_on_blank = parts[-1][0] == "tile"
    return {
        "context": context,
        "frame": " ".join(frame) + (" " if ends_on_blank else "") + end,
        "tiles": shuffled(tiles, extra, full),
        "answer": full,
        "also": [" ".join(str(a).split()) for a in also if str(a).strip()],
        "in_order": tiles,
        "blanks": blanks,
        "unused": extra or None,
        "notes": notes,
    }


def normalise(sentence):
    """Compare on words only: case, punctuation and spacing do not count."""
    text = str(sentence).lower().replace("’", "'")
    text = re.sub(r"[^\w'\s]", " ", text, flags=re.UNICODE)
    return " ".join(text.split())


def mark(item, response):
    """All-or-nothing, as the exam marks it. The learner may type the whole
    reply, or only the tiles in their order."""
    given = normalise(response)
    accepted = [normalise(item["answer"]), normalise(" ".join(item["in_order"]))]
    accepted += [normalise(other) for other in item["also"]]
    return bool(given) and given in accepted


def load_batch(path):
    rows = json.loads(fileguard.read_text(path))
    if not isinstance(rows, list) or not rows \
            or not all(isinstance(r, dict) for r in rows):
        raise ValueError("expected a JSON list of items")
    return rows


def items_from_args(args):
    """(items, errors). One item from flags, or many from --batch."""
    if args.batch:
        rows = load_batch(args.batch)
    else:
        rows = [{"context": args.context, "answer": args.answer,
                 "distractor": args.distractor, "also": args.also}]
    items, errors = [], []
    for number, row in enumerate(rows, 1):
        try:
            also = row.get("also") or []
            if isinstance(also, str):
                also = [also]
            items.append(make_item(row.get("context"), row.get("answer") or "",
                                   row.get("distractor"), also,
                                   bool(row.get("keep_case")) or args.keep_case,
                                   args.min_blanks, args.max_blanks))
        except ValueError as exc:
            errors.append(("item %d: " % number if args.batch else "") + str(exc))
    return items, errors


def read_responses(args, count):
    """The learner's sentences, lined up with the items.

    Lines that all carry their item number ("3. What time ...") are placed by
    that number, so a skipped item does not shift the ones after it.
    """
    if not args.responses:
        return list(args.response or [])
    raw = fileguard.read_text(args.responses)
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    numbered = [re.match(r"^\(?(\d{1,2})[.):]\s*(.*)$", line) for line in lines]
    numbers = [int(m.group(1)) for m in numbered if m]
    if lines and len(numbers) == len(lines) and len(set(numbers)) == len(numbers) \
            and all(1 <= n <= count for n in numbers):
        placed = [""] * max(numbers)
        for match in numbered:
            placed[int(match.group(1)) - 1] = match.group(2)
        return placed
    return lines


def render_set(items):
    """The part the learner sees: instruction, then each numbered item."""
    lines = [INSTRUCTION, ""]
    for number, item in enumerate(items, 1):
        lines += ["%d. %s" % (number, item["context"]), "",
                  "   %s" % item["frame"], "",
                  "   %s" % " / ".join(item["tiles"]), ""]
    return "\n".join(lines).rstrip("\n")


def render_key(items):
    lines = []
    for number, item in enumerate(items, 1):
        extra = "   (not used: %s)" % item["unused"] if item["unused"] else ""
        lines.append("%d. %s%s" % (number, item["answer"], extra))
        for other in item["also"]:
            lines.append("   also accepted: %s" % other)
    return "\n".join(lines)


def render_make(items):
    lines = ["Build a Sentence — %d item%s" % (len(items), "" if len(items) == 1 else "s"),
             "", "SHOW THE LEARNER", "", render_set(items), "",
             "KEEP BACK — the key", "", render_key(items)]
    notes = ["item %d: %s" % (n, note) for n, item in enumerate(items, 1)
             for note in item["notes"]]
    if len(items) >= 5:
        # What the official practice set looks like, for comparison.
        with_extra = sum(1 for item in items if item["unused"])
        questions = sum(1 for item in items if item["answer"].endswith("?"))
        if questions * 2 < len(items):
            notes.append("only %d of %d replies are questions; in the official "
                         "practice set most are" % (questions, len(items)))
        if with_extra * 3 > len(items):
            notes.append("%d of %d items carry an extra tile; in the official "
                         "practice set only a few do" % (with_extra, len(items)))
    for note in notes:
        lines += ["", "note: %s" % note]
    return "\n".join(lines)


def render_check(items, results):
    score = sum(1 for r in results if r["correct"])
    lines = ["%d / %d" % (score, len(items)), ""]
    for result in results:
        if result["correct"]:
            lines.append("  %2d  right   %s" % (result["n"], result["answer"]))
        else:
            lines.append("  %2d  wrong   %s" % (result["n"], result["answer"]))
            lines.append("              answered: %s" % (result["given"] or "nothing"))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=("make", "check"))
    parser.add_argument("--context", default=None,
                        help="the first sentence, the one somebody says")
    parser.add_argument("--answer", default=None,
                        help="the reply, tiles separated by |, pre-printed "
                             "words in [ ], ending in . ? or !")
    parser.add_argument("--distractor", default=None,
                        help="one extra tile that is not used")
    parser.add_argument("--also", action="append", default=[],
                        help="another complete reply to accept. Repeatable.")
    parser.add_argument("--batch", default=None, metavar="FILE",
                        help="a JSON list of items (or - for stdin)")
    parser.add_argument("--response", action="append", default=[],
                        help="check: the learner's sentence. Repeatable, in "
                             "item order.")
    parser.add_argument("--responses", default=None, metavar="FILE",
                        help="check: the learner's sentences, one per line "
                             "(or - for stdin)")
    parser.add_argument("--keep-case", action="store_true", dest="keep_case",
                        help="print the tiles exactly as written (use when "
                             "the reply opens with a name)")
    parser.add_argument("--min-blanks", type=int, default=MIN_BLANKS, dest="min_blanks")
    parser.add_argument("--max-blanks", type=int, default=MAX_BLANKS, dest="max_blanks")
    parser.add_argument("--json", action="store_true")
    # Accepted so one prefix works for every command; no data is read here.
    parser.add_argument("--base", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--learner", default=None, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    if bool(args.batch) == bool(args.answer):
        print("error: give either --batch, or --context with --answer",
              file=sys.stderr)
        return 2
    try:
        items, errors = items_from_args(args)
    except (OSError, ValueError) as exc:
        print("error: could not read the items: %s" % exc, file=sys.stderr)
        return 2
    if errors:
        for error in errors:
            print("error: %s" % error, file=sys.stderr)
        return 2

    if args.action == "make":
        print(json.dumps(items, ensure_ascii=False, indent=1) if args.json
              else render_make(items))
        return 0

    try:
        responses = read_responses(args, len(items))
    except (OSError, ValueError) as exc:
        print("error: could not read the responses: %s" % exc, file=sys.stderr)
        return 2
    if not responses:
        print("error: check needs --response or --responses", file=sys.stderr)
        return 2
    if len(responses) > len(items):
        print("error: %d responses for %d item%s"
              % (len(responses), len(items), "" if len(items) == 1 else "s"),
              file=sys.stderr)
        return 2
    results = []
    for number, item in enumerate(items, 1):
        given = responses[number - 1] if number <= len(responses) else ""
        results.append({"n": number, "answer": item["answer"],
                        "given": given.strip(), "correct": mark(item, given)})
    if args.json:
        print(json.dumps({"score": sum(1 for r in results if r["correct"]),
                          "out_of": len(items), "results": results},
                         ensure_ascii=False, indent=1))
    else:
        print(render_check(items, results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
