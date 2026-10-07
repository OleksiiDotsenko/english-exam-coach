#!/usr/bin/env python3
"""Translate a score between an exam's own scale and CEFR.

Every exam reports on its own scale, but progress is compared in CEFR. This
converts in both directions so a target ("TOEFL 4.5", "IELTS 7") can be
stated as a CEFR level, and a CEFR level can be stated back in the scale the
learner actually cares about.

Alignments are the public ones already used by build_report.py; they are
coarse by design and always reported as a level or a range, never as false
precision.

Scales:
  toefl        1-6 band scale (tests from 21 Jan 2026), half bands
  toefl-legacy 0-120 total (pre-2026 logs, TOEFL iBT Australia)
  ielts        0-9 band scale, half bands
  cambridge    Cambridge English Scale, 80-230
  cefr         A1-C2

Examples:
  convert_score.py --from toefl --score 4.5
  convert_score.py --from ielts --score 7
  convert_score.py --from cefr --level C1 --to ielts
  convert_score.py --from toefl --score 5 --to toefl-legacy
"""

import argparse
import sys

CEFR_LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")

# (minimum score, CEFR) — first row whose minimum is met wins.
TOEFL_TO_CEFR = ((6.0, "C2"), (5.0, "C1"), (4.0, "B2"),
                 (3.0, "B1"), (2.0, "A2"), (0.0, "A1"))
IELTS_TO_CEFR = ((8.5, "C2"), (7.0, "C1"), (5.5, "B2"), (4.0, "B1"), (0.0, "A2"))
CAMBRIDGE_TO_CEFR = ((200, "C2"), (180, "C1"), (160, "B2"),
                     (140, "B1"), (120, "A2"), (80, "A1"))
# Official concordance published with the 2026 redesign (overall score).
TOEFL_TO_LEGACY = {6.0: "114-120", 5.5: "107-113", 5.0: "95-106", 4.5: "86-94",
                   4.0: "72-85", 3.5: "58-71", 3.0: "44-57", 2.5: "31-43",
                   2.0: "18-30", 1.5: "9-17", 1.0: "0-8"}

# CEFR -> the range of that exam's scale which maps to the level.
CEFR_TO_SCALE = {
    "toefl": {"C2": "6.0", "C1": "5.0-5.5", "B2": "4.0-4.5",
              "B1": "3.0-3.5", "A2": "2.0-2.5", "A1": "1.0-1.5"},
    "ielts": {"C2": "8.5-9.0", "C1": "7.0-8.0", "B2": "5.5-6.5",
              "B1": "4.0-5.0", "A2": "below 4.0", "A1": "below 4.0"},
    "cambridge": {"C2": "200-230", "C1": "180-199", "B2": "160-179",
                  "B1": "140-159", "A2": "120-139", "A1": "80-119"},
    "toefl-legacy": {"C2": "114-120", "C1": "95-113", "B2": "72-94",
                     "B1": "44-71", "A2": "18-43", "A1": "0-17"},
}

SCALE_BOUNDS = {"toefl": (1.0, 6.0), "ielts": (0.0, 9.0),
                "cambridge": (80.0, 230.0), "toefl-legacy": (0.0, 120.0)}

SCALES = ("toefl", "toefl-legacy", "ielts", "cambridge", "cefr")


def from_cuts(value, cuts):
    for threshold, level in cuts:
        if value >= threshold:
            return level
    return None


def score_to_cefr(scale, score):
    if scale == "toefl":
        return from_cuts(score, TOEFL_TO_CEFR)
    if scale == "ielts":
        return from_cuts(score, IELTS_TO_CEFR)
    if scale == "cambridge":
        return from_cuts(score, CAMBRIDGE_TO_CEFR)
    if scale == "toefl-legacy":
        # Read the published concordance backwards: find the band whose
        # legacy range contains this score, then map that band to CEFR.
        for band in sorted(TOEFL_TO_LEGACY, reverse=True):
            low, high = TOEFL_TO_LEGACY[band].split("-")
            if float(low) <= score <= float(high):
                return from_cuts(band, TOEFL_TO_CEFR)
    return None


def cefr_to_score(scale, level):
    return CEFR_TO_SCALE.get(scale, {}).get(level)


def toefl_band_to_legacy(score):
    """Nearest published half band -> legacy 0-120 range."""
    nearest = min(TOEFL_TO_LEGACY, key=lambda b: abs(b - score))
    return TOEFL_TO_LEGACY[nearest], nearest


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from", required=True, dest="from_scale",
                        choices=SCALES, help="scale the input is on")
    parser.add_argument("--to", default="cefr", choices=SCALES,
                        help="scale to convert to (default: cefr)")
    parser.add_argument("--score", type=float, default=None,
                        help="numeric score, when --from is not cefr")
    parser.add_argument("--level", default=None,
                        help="CEFR level, when --from is cefr")
    # Accepted so one prefix works for every command; no data is read here.
    parser.add_argument("--base", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--learner", default=None, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    if args.from_scale == "cefr":
        level = (args.level or "").strip().upper()
        if level not in CEFR_LEVELS:
            print("error: --level must be one of %s" % "/".join(CEFR_LEVELS),
                  file=sys.stderr)
            return 2
        if args.to == "cefr":
            print(level)
            return 0
        target = cefr_to_score(args.to, level)
        if target is None:
            print("error: cannot convert CEFR to %s" % args.to, file=sys.stderr)
            return 2
        print("%s on the %s scale is about %s" % (level, args.to, target))
        return 0

    if args.score is None:
        print("error: --score is required when --from is not cefr",
              file=sys.stderr)
        return 2

    low, high = SCALE_BOUNDS[args.from_scale]
    if not low <= args.score <= high:
        print("error: --score %g is outside the %s range (%g-%g)"
              % (args.score, args.from_scale, low, high), file=sys.stderr)
        return 2

    if args.to == "cefr":
        level = score_to_cefr(args.from_scale, args.score)
        if level is None:
            print("error: could not map that score to CEFR", file=sys.stderr)
            return 2
        print("%s %g is about CEFR %s" % (args.from_scale, args.score, level))
        return 0

    # Direct TOEFL band <-> legacy conversion uses the published concordance;
    # every other cross-scale hop goes through CEFR and is coarser, so say so.
    if args.from_scale == "toefl" and args.to == "toefl-legacy":
        legacy, band = toefl_band_to_legacy(args.score)
        note = "" if band == args.score else " (nearest published band %g)" % band
        print("TOEFL band %g is about %s on the legacy 0-120 scale%s"
              % (args.score, legacy, note))
        return 0

    level = score_to_cefr(args.from_scale, args.score)
    if level is None:
        print("error: could not map that score to CEFR", file=sys.stderr)
        return 2
    target = cefr_to_score(args.to, level)
    if target is None:
        print("error: cannot convert to %s" % args.to, file=sys.stderr)
        return 2
    print("%s %g is about CEFR %s, which is about %s on the %s scale "
          "(via CEFR, so this is indicative only)"
          % (args.from_scale, args.score, level, target, args.to))
    return 0


if __name__ == "__main__":
    sys.exit(main())
