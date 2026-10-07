#!/usr/bin/env python3
"""Compare what a learner repeated with the sentence they heard.

For repeat-after-me tasks (TOEFL Listen and Repeat). The comparison is word
for word and mechanical, so it is done by rule: which words came back, which
were dropped, which were changed, which were added. Nothing here judges
pronunciation — a typed or machine-made transcript cannot show it.

  repeat_check.py --target "Please ask for a student card." \\
                  --said "Please ask a student card."
  repeat_check.py --targets sentences.txt --said said.txt
  repeat_check.py --audio DIR --said said.txt     targets from speak.py's folder

In a file, one sentence per line, in order; a number in front ("3.") is
ignored, and an empty line or a lone "-" means nothing was said for that one.
The result is a count of words, not a band: the exam's own 0-5 scale for
these items also weighs intelligibility, which this cannot see.
"""

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

import fileguard

NUMBER_WORDS = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four",
                "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "nine",
                "10": "ten", "11": "eleven", "12": "twelve"}
BREAKDOWN = 0.8     # below this share of words, the sentence did not survive
AUDIO_MARKER = "english-exam-coach-audio"      # what speak.py stamps its folders with


def words_of(sentence):
    """Lower-case words, punctuation gone, small numerals spelt out — so
    that '4 o'clock' typed by a recogniser equals 'four o'clock'."""
    text = str(sentence).lower().replace("’", "'").replace("‘", "'")
    words = re.findall(r"[a-z0-9]+(?:'[a-z]+)?", text)
    return [NUMBER_WORDS.get(word, word) for word in words]


def compare(target, said):
    """How much of `target` is in `said`, and what changed."""
    wanted, given = words_of(target), words_of(said)
    matcher = difflib.SequenceMatcher(None, wanted, given, autojunk=False)
    matched, omitted, added, changed = 0, [], [], []
    for tag, a0, a1, b0, b1 in matcher.get_opcodes():
        if tag == "equal":
            matched += a1 - a0
        elif tag == "delete":
            omitted += wanted[a0:a1]
        elif tag == "insert":
            added += given[b0:b1]
        else:
            changed.append((" ".join(wanted[a0:a1]), " ".join(given[b0:b1])))
    total = len(wanted)
    return {
        "target": " ".join(str(target).split()),
        "said": " ".join(str(said).split()),
        "words": total,
        "matched": matched,
        "accuracy": round(matched / float(total), 2) if total else 0.0,
        "exact": bool(total) and wanted == given,
        "omitted": omitted,
        "added": added,
        "changed": changed,
    }


def summarise(results):
    exact = sum(1 for r in results if r["exact"])
    total_words = sum(r["words"] for r in results)
    matched = sum(r["matched"] for r in results)
    broke = next((r for r in results if r["accuracy"] < BREAKDOWN), None)
    return {
        "items": len(results),
        "exact": exact,
        "words": total_words,
        "matched": matched,
        "accuracy": round(matched / float(total_words), 2) if total_words else 0.0,
        "first_breakdown": ({"item": results.index(broke) + 1, "words": broke["words"]}
                            if broke else None),
    }


def read_lines(path):
    """Sentences from a file: numbering stripped, blanks kept as empty."""
    raw = fileguard.read_text(path)
    lines = [line.strip() for line in raw.replace("\r", "").split("\n")]
    while lines and not lines[-1]:
        lines.pop()
    cleaned = []
    for line in lines:
        line = re.sub(r"^\(?\d{1,2}[.):]\s*", "", line)
        cleaned.append("" if line in ("-", "—") else line)
    return cleaned


def targets_from_audio(directory):
    """The sentences in a folder rendered by speak.py (and only such a
    folder: any other manifest.json is refused)."""
    data = json.loads((Path(directory).expanduser() / "manifest.json")
                      .read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("marker") != AUDIO_MARKER:
        raise ValueError("%s is not an audio folder made by speak.py" % directory)
    return [str(item.get("text") or "") for item in data.get("items") or []]


def render(results):
    summary = summarise(results)
    lines = []
    for number, result in enumerate(results, 1):
        head = "%2d  %2d/%-2d words" % (number, result["matched"], result["words"])
        if result["exact"]:
            lines.append("%s  exact" % head)
            continue
        if not result["said"]:
            lines.append("%s  nothing repeated" % head)
            continue
        notes = []
        if result["omitted"]:
            notes.append("dropped: %s" % ", ".join(result["omitted"]))
        for wanted, given in result["changed"]:
            notes.append("said “%s” for “%s”" % (given, wanted))
        if result["added"]:
            notes.append("added: %s" % ", ".join(result["added"]))
        lines.append("%s  %s" % (head, "; ".join(notes)))
    lines.append("")
    lines.append("%d of %d repeated exactly · %d of %d words (%d%%)"
                 % (summary["exact"], summary["items"], summary["matched"],
                    summary["words"], round(100 * summary["accuracy"])))
    if summary["first_breakdown"]:
        lines.append("First sentence to break down: item %d, %d words long."
                     % (summary["first_breakdown"]["item"],
                        summary["first_breakdown"]["words"]))
    lines.append("Word counts only: pronunciation is not judged here.")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", default=None, help="the sentence that was heard")
    parser.add_argument("--targets", default=None, metavar="FILE",
                        help="the sentences heard, one per line (or - for stdin)")
    parser.add_argument("--audio", default=None, metavar="DIR",
                        help="take the sentences from a folder made by speak.py")
    parser.add_argument("--said", default=None,
                        help="what the learner said: the sentence itself with "
                             "--target, otherwise a file with one line per item")
    parser.add_argument("--json", action="store_true")
    # Accepted so one prefix works for every command; no data is read here.
    parser.add_argument("--base", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--learner", default=None, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    sources = [s for s in (args.target, args.targets, args.audio) if s is not None]
    if len(sources) != 1 or args.said is None:
        print("error: give one of --target, --targets or --audio, and --said",
              file=sys.stderr)
        return 2
    try:
        if args.target is not None:
            targets, said = [args.target], [args.said]
        else:
            targets = targets_from_audio(args.audio) if args.audio \
                else read_lines(args.targets)
            said = read_lines(args.said)
    except (OSError, ValueError) as exc:
        print("error: could not read the sentences: %s" % exc, file=sys.stderr)
        return 2
    targets = [t for t in targets if t.strip()] if args.target is None else targets
    if not targets or not any(words_of(t) for t in targets):
        print("error: there is no sentence to compare against", file=sys.stderr)
        return 2
    if len(said) > len(targets):
        print("error: %d lines were said for %d sentence%s"
              % (len(said), len(targets), "" if len(targets) == 1 else "s"),
              file=sys.stderr)
        return 2
    said += [""] * (len(targets) - len(said))

    results = [compare(target, spoken) for target, spoken in zip(targets, said)]
    if args.json:
        print(json.dumps({"summary": summarise(results), "items": results},
                         ensure_ascii=False, indent=1))
    else:
        print(render(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
