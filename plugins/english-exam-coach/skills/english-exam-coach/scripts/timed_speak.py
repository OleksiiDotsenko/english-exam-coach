#!/usr/bin/env python3
"""Run a speaking task under the real exam clock and report what actually happened.

Exam speaking is a timed performance. Reading a prompt and answering "when
ready" removes the constraint the task is built around, so this runs the real
prep and answer clocks, signals the transitions, and reports the true elapsed
time — which is then logged as script-timed evidence rather than an estimate.

It times and observes; it does not record or score. With --audio it first
plays each item's prompt, rendered beforehand by speak.py, so the learner
hears the question and answers at once, as in the exam. It STARTS OTHER
PROGRAMS (the system voice for cues, an audio player for prompts), which is
why it is a separate script and is never run through coach.py.

A run blocks for as long as the task lasts — several minutes for a set — so
give the command a time limit longer than that.

Examples:
  timed_speak.py --exam toefl-ibt --task toefl-take-an-interview
  timed_speak.py --prep 60 --answer 120        # IELTS Part 2 long turn
  timed_speak.py --task toefl-listen-and-repeat --audio DIR   # hear, then repeat
"""

import argparse
import json
import shutil
import subprocess
import sys
import time

sys.dont_write_bytecode = True      # leave nothing in the skill's own folder

# Authentic prep/answer clocks, from the format files. prep of 0 means the
# task starts immediately, which is itself part of its difficulty.
TASK_CLOCKS = {
    # TOEFL iBT (2026): no preparation time on either speaking task.
    "toefl-take-an-interview": {"prep": 0, "answer": 45, "items": 4},
    "toefl-listen-and-repeat": {"prep": 0, "answer": 12, "items": 7},
    # IELTS
    "ielts-part1-interview": {"prep": 0, "answer": 30, "items": 4},
    "ielts-part2-long-turn": {"prep": 60, "answer": 120, "items": 1},
    "ielts-part3-discussion": {"prep": 0, "answer": 60, "items": 4},
    # Cambridge B1-C2
    "speaking-interview": {"prep": 0, "answer": 30, "items": 4},
    "speaking-long-turn": {"prep": 0, "answer": 60, "items": 1},
    "speaking-collaborative": {"prep": 0, "answer": 180, "items": 1},
    "speaking-discussion": {"prep": 0, "answer": 60, "items": 3},
}


def cue(message, sound=True, out=sys.stdout):
    """Announce a transition and, where possible, make it audible.

    A speaking clock the user has to watch is not a speaking clock — the
    point is that they are looking away and talking.
    """
    print(message, file=out, flush=True)
    if not sound:
        return
    if shutil.which("say"):
        try:
            subprocess.run(["say", "-r", "220", message], timeout=10,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except (OSError, subprocess.SubprocessError):
            pass
    # Terminal bell: no dependency, works over ssh, silent if the user muted it.
    out.write("\a")
    out.flush()


def countdown(seconds, label, quiet=False, out=sys.stdout):
    """Sleep for `seconds`, showing a single rewritten status line.

    Returns the real elapsed seconds — never the nominal value, because a
    ^C or a slow machine must not be recorded as a clean run.
    """
    start = time.monotonic()
    if quiet:
        time.sleep(seconds)
        return time.monotonic() - start
    try:
        while True:
            elapsed = time.monotonic() - start
            left = seconds - elapsed
            if left <= 0:
                break
            # \r keeps this to one line so the transcript stays readable.
            out.write("\r  %s: %3ds remaining " % (label, int(left + 0.5)))
            out.flush()
            time.sleep(min(0.25, left))
    except KeyboardInterrupt:
        out.write("\r  %s: stopped early            \n" % label)
        out.flush()
        return time.monotonic() - start
    out.write("\r  %s: done                    \n" % label)
    out.flush()
    return time.monotonic() - start


def run_item(index, total, prep, answer, quiet=False, out=sys.stdout, audio=None):
    """Run one item's prep and answer clocks. Returns its timing record.

    With `audio` (a folder rendered by speak.py) the item's prompt is played
    first, and the transitions are signalled with a tone instead of words —
    a spoken "speak now" after a spoken question would be one voice too many.
    """
    label = "Item %d of %d" % (index, total) if total > 1 else "Task"
    print("\n%s" % label, file=out)
    record = {"item": index}
    if audio:
        import speak
        started = time.monotonic()
        speak.play(audio, index, index)
        record["prompt_seconds"] = round(time.monotonic() - started, 1)
    prep_elapsed = 0.0
    if prep > 0:
        cue("Preparation starts now: %d seconds." % prep, sound=not quiet, out=out)
        prep_elapsed = countdown(prep, "prep", quiet, out=out)
    if audio:
        print("Speak now.", file=out, flush=True)
        if not quiet:
            speak.beep()
    else:
        cue("Speak now." if prep > 0 else "Speak now — no preparation time.",
            sound=not quiet, out=out)
    answer_elapsed = countdown(answer, "answer", quiet, out=out)
    if audio:
        print("Stop.", file=out, flush=True)
        if not quiet:
            speak.beep()
    else:
        cue("Stop.", sound=not quiet, out=out)
    record.update({"prep_seconds": round(prep_elapsed, 1),
                   "answer_seconds": round(answer_elapsed, 1),
                   "prep_nominal": prep, "answer_nominal": answer})
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--task", default=None,
                        help="task-type slug; sets the authentic clocks")
    parser.add_argument("--exam", default=None, help="exam id, for the report only")
    parser.add_argument("--prep", type=int, default=None,
                        help="preparation seconds (overrides the task default)")
    parser.add_argument("--answer", type=int, default=None,
                        help="answer seconds (overrides the task default)")
    parser.add_argument("--items", type=int, default=None,
                        help="number of items to run (overrides the default)")
    parser.add_argument("--audio", default=None, metavar="DIR",
                        help="a folder rendered by speak.py: each item's "
                             "prompt is played once before its clock starts")
    parser.add_argument("--quiet", action="store_true",
                        help="no audible cues and no live countdown")
    parser.add_argument("--json", action="store_true",
                        help="print only the machine-readable summary")
    args = parser.parse_args(argv)

    clocks = TASK_CLOCKS.get(args.task, {})
    prep = args.prep if args.prep is not None else clocks.get("prep")
    answer = args.answer if args.answer is not None else clocks.get("answer")
    items = args.items if args.items is not None else clocks.get("items", 1)

    if args.audio:
        import speak
        try:
            prompts = len(speak.load_manifest(args.audio)["items"])
        except (OSError, ValueError) as exc:
            print("error: %s is not a folder rendered by speak.py (%s)"
                  % (args.audio, exc), file=sys.stderr)
            return 2
        if not speak.find_player():
            print("error: no audio player on this machine; run without --audio "
                  "and read the prompts aloud instead", file=sys.stderr)
            return 3
        if args.items is None:
            items = prompts             # one clock per rendered prompt
        elif args.items > prompts:
            print("error: --items %d but the folder holds %d prompt%s"
                  % (args.items, prompts, "" if prompts == 1 else "s"),
                  file=sys.stderr)
            return 2

    if answer is None:
        print("error: unknown task %r — pass --answer (and --prep) explicitly. "
              "Known tasks: %s" % (args.task, ", ".join(sorted(TASK_CLOCKS))),
              file=sys.stderr)
        return 2
    prep = prep or 0
    if prep < 0 or answer <= 0 or items <= 0:
        print("error: --prep must be >= 0, --answer and --items must be > 0",
              file=sys.stderr)
        return 2

    quiet = args.quiet or args.json
    # In --json mode stdout carries the summary and nothing else, so the
    # running commentary goes to stderr where a caller can still see it.
    out = sys.stderr if args.json else sys.stdout

    print("Timed speaking: %s%s" % (
        args.task or "custom",
        " (%s)" % args.exam if args.exam else ""), file=out)
    print("%d item%s · %ds preparation · %ds to answer"
          % (items, "" if items == 1 else "s", prep, answer), file=out)
    print("Speak aloud. The clock is real — do not pause it to think.", file=out)

    started = time.time()
    records = []
    for index in range(1, items + 1):
        try:
            records.append(run_item(index, items, prep, answer, quiet, out=out,
                                    audio=args.audio))
        except (RuntimeError, ValueError) as exc:
            print("error: could not play the prompt for item %d: %s"
                  % (index, exc), file=sys.stderr)
            return 3

    total_answer = sum(r["answer_seconds"] for r in records)
    # Time on task is the task's own clock (preparation + speaking). Wall-clock
    # elapsed also contains the spoken cues between items, which are the tool
    # talking, not the learner working — logging that would inflate every
    # short-item task several-fold.
    total_task = sum(r["prep_seconds"] + r["answer_seconds"] for r in records)
    total_elapsed = time.time() - started
    summary = {
        "task_type": args.task,
        "exam": args.exam,
        "items": items,
        "answer_seconds_total": round(total_answer, 1),
        "task_seconds_total": round(total_task, 1),
        "elapsed_seconds_total": round(total_elapsed, 1),
        "timing_source": "script",
        "items_detail": records,
    }

    if args.json:
        print(json.dumps(summary, ensure_ascii=False))
        return 0

    print("\nDone. Spoke for %ds across %d item%s; %ds on task including "
          "preparation." % (round(total_answer), items,
                            "" if items == 1 else "s", round(total_task)))
    print("Log this attempt with --seconds %d --timing-source script"
          % round(total_task))
    return 0


if __name__ == "__main__":
    sys.exit(main())
