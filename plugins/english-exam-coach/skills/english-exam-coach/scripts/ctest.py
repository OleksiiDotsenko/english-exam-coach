#!/usr/bin/env python3
"""Build and mark a "Complete the Words" item (TOEFL iBT, from January 2026).

The task is a C-test, and its shape is mechanical, so it is built by rule
rather than by eye. Getting it wrong by hand is easy — a blank too many, a
gap in the wrong word — and a learner cannot recover from a miscounted blank.

The rule, as the official practice material applies it:

  - one paragraph of about 70-80 words;
  - the first sentence is left whole, to set the topic;
  - from the second sentence, the second half of every second word is
    removed, starting with the SECOND word, until 10 words are gapped;
  - a word of n letters keeps its first n // 2 letters and loses the rest
    (fruit -> fr + 3 blanks, of -> o + 1 blank, gardeners -> gard + 5);
  - one blank is printed for each missing letter;
  - the rest of the paragraph is left whole;
  - the answer to each gap is the missing letters.

Words that cannot fairly be gapped are not counted at all: numbers, names,
abbreviations, one-letter words, words with an apostrophe or a hyphen, and
any term listed with --keep (a technical word the context cannot supply).

  ctest.py make --file paragraph.txt
  ctest.py make --text "First sentence. Second sentence ..." --style dash
  ctest.py check --file paragraph.txt --answers "ple all ere ow uit ..."
  ctest.py check --file paragraph.txt --filled "the learner's whole paragraph"

`check` rebuilds the item from the same paragraph and options, so the key
never has to be stored or retyped. Write the paragraph yourself; this script
only cuts it.
"""

import argparse
import json
import re
import sys

import fileguard

DEFAULT_GAPS = 10
STYLES = ("spaced", "dash")
START_MARK = "||"
NBSP = "\u00a0"
# Our own wording: the official instruction is not reproduced.
INSTRUCTION = "Complete each gapped word: type the letters that are missing."

# A full stop after one of these does not end a sentence.
ABBREVIATIONS = {"mr", "mrs", "ms", "dr", "prof", "st", "vs", "etc", "e.g", "i.e",
                 "no", "fig", "approx", "ca", "jr", "sr", "inc", "ltd", "co",
                 "a.m", "p.m", "u.s", "u.k"}
CLOSERS = "\"'”’)]"
OPENERS = "\"'“‘(["


def split_first_sentence(text):
    """(first sentence, rest). An explicit || in the text wins."""
    if START_MARK in text:
        first, _mark, rest = text.partition(START_MARK)
        return first.strip(), rest.strip()
    for match in re.finditer(r"[.!?]+[%s]*\s+" % re.escape(CLOSERS), text):
        before = text[:match.start()]
        last_word = before.split()[-1].lower().lstrip(OPENERS) if before.split() else ""
        if text[match.start()] == "." and (last_word in ABBREVIATIONS
                                           or len(last_word) == 1):
            continue      # "Dr. Lee", "J. Smith" — not the end of a sentence
        following = text[match.end():].lstrip(OPENERS)
        if following[:1].isupper() or following[:1].isdigit():
            return text[:match.end()].strip(), text[match.end():].strip()
    return text.strip(), ""


def split_token(token):
    """(leading punctuation, core, trailing punctuation) of one word."""
    start, end = 0, len(token)
    while start < end and not token[start].isalnum():
        start += 1
    while end > start and not token[end - 1].isalnum():
        end -= 1
    return token[:start], token[start:end], token[end:]


def ends_sentence(core, trail):
    """Does this word close a sentence (so the next one starts with a capital)?"""
    mark = trail.rstrip(CLOSERS)
    if not mark.endswith((".", "!", "?")):
        return False
    if mark.endswith(".") and (core.lower() in ABBREVIATIONS or len(core) == 1):
        return False
    return True


def is_eligible(core, sentence_initial, keep):
    """Can this word fairly be gapped, and so is it counted?"""
    if len(core) < 2 or not core.isalpha():
        return False          # numbers, one-letter words, don't, well-known
    if core.lower() in keep:
        return False
    if sum(1 for ch in core if ch.isupper()) > 1:
        return False          # DNA, UNESCO
    if core[0].isupper() and not sentence_initial:
        return False          # a name
    return True


def gap_word(core, style):
    """(letters shown, letters missing, the word as printed)."""
    shown, missing = core[:len(core) // 2], core[len(core) // 2:]
    if style == "dash":
        blanks = "-" * len(missing)
    else:
        # Non-breaking spaces, so a gap is never split across two lines.
        blanks = NBSP.join("_" * len(missing))
    return shown, missing, shown + blanks


def make_item(text, gaps=DEFAULT_GAPS, style="spaced", keep=()):
    """Cut a paragraph into a Complete-the-Words item.

    Returns a dict: item (the gapped paragraph), gaps (one entry per gap, in
    order), first_sentence, words, tokens (for marking) and notes (things the
    author should look at). Raises ValueError if the paragraph cannot carry
    the number of gaps asked for.
    """
    if style not in STYLES:
        raise ValueError("style must be one of %s" % ", ".join(STYLES))
    if gaps < 1:
        raise ValueError("an item needs at least one gap")
    text = " ".join(str(text).split())
    if not text:
        raise ValueError("the paragraph is empty")
    keep = {str(word).strip().lower() for word in keep if str(word).strip()}

    first, rest = split_first_sentence(text)
    if not rest:
        raise ValueError("only one sentence was found. The first sentence is "
                         "left whole, so the paragraph needs more after it "
                         "(mark the split with %s if it was missed)" % START_MARK)

    tokens = rest.split()
    out, found, counted, sentence_initial, last_gap = [], [], 0, True, -1
    for position, token in enumerate(tokens):
        lead, core, trail = split_token(token)
        eligible = is_eligible(core, sentence_initial, keep)
        if eligible:
            counted += 1
        if eligible and counted % 2 == 0 and len(found) < gaps:
            shown, missing, printed = gap_word(core, style)
            found.append({"n": len(found) + 1, "word": core, "shown": shown,
                          "missing": missing, "blanks": len(missing),
                          "token": position})
            out.append(lead + printed + trail)
            last_gap = position
        else:
            out.append(token)
        if core:
            sentence_initial = ends_sentence(core, trail)

    if len(found) < gaps:
        raise ValueError(
            "the paragraph only carries %d gap%s after its first sentence, not "
            "%d. Add about %d more words, or pass --gaps %d"
            % (len(found), "" if len(found) == 1 else "s", gaps,
               2 * (gaps - len(found)) + 6, len(found)))

    words = len(text.replace(START_MARK, " ").split())
    after = len(tokens) - 1 - last_gap
    notes = []
    if not 60 <= words <= 95:
        notes.append("%d words: official paragraphs run about 70-80" % words)
    if len(first.split()) < 8:
        notes.append("the first sentence is only %d words — it is all the "
                     "context the learner gets" % len(first.split()))
    if after < 8:
        notes.append("only %d word%s after the last gap; official items end "
                     "with a whole sentence or two" % (after, "" if after == 1 else "s"))
    return {
        "instruction": INSTRUCTION,
        "item": "%s %s" % (first, " ".join(out)),
        "first_sentence": first,
        "gaps": found,
        "words": words,
        "style": style,
        "tokens": tokens,
        "notes": notes,
    }


def normalise(answer):
    return re.sub(r"[^\w]", "", str(answer).lower(), flags=re.UNICODE).replace("_", "")


def mark_answers(item, answers):
    """Mark a list of answers, one per gap. Each may be the missing letters
    or the whole word. Returns (results, score)."""
    results, score = [], 0
    for index, gap in enumerate(item["gaps"]):
        given = answers[index] if index < len(answers) else ""
        cleaned = normalise(given)
        correct = bool(cleaned) and cleaned in (gap["missing"].lower(),
                                                gap["word"].lower())
        score += correct
        results.append({"n": gap["n"], "word": gap["word"], "missing": gap["missing"],
                        "given": str(given).strip(), "correct": correct})
    return results, score


def answers_from_filled(item, filled):
    """Pull the gap words out of a paragraph the learner typed in full."""
    first_words = len(item["first_sentence"].split())
    words = " ".join(str(filled).replace(START_MARK, " ").split()).split()
    expected = first_words + len(item["tokens"])
    if len(words) != expected:
        raise ValueError("the filled-in paragraph has %d words and the "
                         "original has %d, so the gaps cannot be lined up. "
                         "Mark it from a list of answers instead (--answers)"
                         % (len(words), expected))
    rest = words[first_words:]
    return [split_token(rest[gap["token"]])[1] for gap in item["gaps"]]


def split_answers(raw):
    """'ple, all ere' -> ['ple', 'all', 'ere']; a lone '-' or '?' is a blank."""
    parts = [p for p in re.split(r"[,\s;/]+", str(raw).strip()) if p]
    return ["" if p in ("-", "?", "_") else p for p in parts]


def render_item(item):
    """The part the learner sees."""
    return "%s\n\n%s" % (item["instruction"], item["item"])


def render_key(item):
    return "\n".join("  %2d  %-8s %s" % (gap["n"], gap["missing"], gap["word"])
                     for gap in item["gaps"])


def render_make(item):
    lines = ["Complete the Words — %d gaps, %d words"
             % (len(item["gaps"]), item["words"]), "",
             "SHOW THE LEARNER", "", render_item(item), "",
             "KEEP BACK — the key", "", render_key(item)]
    for note in item["notes"]:
        lines += ["", "note: %s" % note]
    return "\n".join(lines)


def render_check(results, score):
    lines = ["%d / %d" % (score, len(results)), ""]
    for result in results:
        if result["correct"]:
            lines.append("  %2d  right   %s" % (result["n"], result["word"]))
        else:
            lines.append("  %2d  wrong   %s  (missing letters: %s; answered: %s)"
                         % (result["n"], result["word"], result["missing"],
                            result["given"] or "nothing"))
    return "\n".join(lines)


def read_paragraph(args):
    if args.text is not None:
        return args.text
    return fileguard.read_text(args.file)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("action", choices=("make", "check"))
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--text", default=None, help="the whole paragraph")
    source.add_argument("--file", default=None,
                        help="a file holding the paragraph, or - for stdin")
    parser.add_argument("--gaps", type=int, default=DEFAULT_GAPS,
                        help="words to gap (default %d)" % DEFAULT_GAPS)
    parser.add_argument("--style", choices=STYLES, default="spaced",
                        help="spaced: fr_ _ _ (default); dash: fr---")
    parser.add_argument("--keep", action="append", default=[], metavar="WORD",
                        help="a word to leave whole and uncounted, e.g. a "
                             "technical term. Repeatable; commas allowed.")
    parser.add_argument("--answers", default=None,
                        help="check: the learner's answers in order — missing "
                             "letters or whole words, separated by spaces or "
                             "commas; - for one left blank")
    parser.add_argument("--filled", default=None,
                        help="check: the learner's whole paragraph, filled in")
    parser.add_argument("--json", action="store_true")
    # Accepted so one prefix works for every command; no data is read here.
    parser.add_argument("--base", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--learner", default=None, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    keep = [word for entry in args.keep for word in entry.split(",")]
    try:
        item = make_item(read_paragraph(args), args.gaps, args.style, keep)
    except (OSError, UnicodeDecodeError) as exc:
        print("error: could not read the paragraph: %s" % exc, file=sys.stderr)
        return 2
    except ValueError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2

    if args.action == "make":
        if args.json:
            print(json.dumps({k: v for k, v in item.items() if k != "tokens"},
                             ensure_ascii=False, indent=1))
        else:
            print(render_make(item))
        return 0

    if (args.answers is None) == (args.filled is None):
        print("error: check needs exactly one of --answers or --filled",
              file=sys.stderr)
        return 2
    try:
        answers = split_answers(args.answers) if args.answers is not None \
            else answers_from_filled(item, args.filled)
    except ValueError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    if len(answers) > len(item["gaps"]):
        print("error: %d answers for %d gaps" % (len(answers), len(item["gaps"])),
              file=sys.stderr)
        return 2
    results, score = mark_answers(item, answers)
    if args.json:
        print(json.dumps({"score": score, "out_of": len(results),
                          "results": results}, ensure_ascii=False, indent=1))
    else:
        print(render_check(results, score))
    return 0


if __name__ == "__main__":
    sys.exit(main())
