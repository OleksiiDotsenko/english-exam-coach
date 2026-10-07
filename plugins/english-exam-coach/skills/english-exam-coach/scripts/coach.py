#!/usr/bin/env python3
"""One entry point for the coach's local tooling.

  coach.py [--base DIR] [--learner NAME] <command> [arguments...]

Every command here is plain Python standard library working on plain files in
the learner's own progress directory. None of them starts another program or
opens a network connection — that is a rule of this file, checked by the test
suite, and it is why a session can be allowed to run `coach.py` freely. The
tools that DO start other programs (speak.py for text-to-speech,
transcribe.py for speech recognition, timed_speak.py for the speaking clock)
are separate scripts and are never routed through here.

Run `coach.py <command> --help` for a command's own options.
"""

import importlib
import os
import sys

# Leave nothing behind in the skill's own folder: the only place this tooling
# writes is the learner's progress directory (and files it is pointed at).
sys.dont_write_bytecode = True

# command -> (module, one-line description). Keep this list honest: the test
# suite imports every module named here and fails on any that could start a
# process or reach the network.
COMMANDS = {
    "log-attempt": ("log_attempt", "record one scored attempt"),
    "log-error": ("log_error", "record one mistake, or a batch of them"),
    "log-test": ("log_test", "record the scores of a full test"),
    "report": ("build_report", "progress report for a session or for all time"),
    "tests": ("full_tests", "history and review of full tests"),
    "catalog": ("error_catalog", "error catalog: ranking, matrix, habit states"),
    "queue": ("review_queue", "points due for spaced re-testing"),
    "next": ("drill_context", "what to practise next, and why"),
    "profile": ("learner_profile", "target exam, target score, exam date"),
    "convert": ("convert_score", "translate a score to or from CEFR"),
    "state": ("state", "inspect, validate, export or import the directory"),
    "ctest": ("ctest", "build or check a Complete-the-Words item"),
    "sentence": ("build_sentence", "build or check Build-a-Sentence items"),
    "repeat": ("repeat_check", "compare a repeated sentence with the one heard"),
    "render": ("render", "turn a Markdown report or sheet into printable HTML"),
}


def usage():
    lines = [__doc__.strip(), "", "Commands:"]
    for name in COMMANDS:
        lines.append("  %-12s %s" % (name, COMMANDS[name][1]))
    return "\n".join(lines)


def split_global_options(argv):
    """Peel --base / --learner off the front; return (options, rest).

    They are accepted before the command so one prefix can be reused for
    every call in a session, and are handed on through the environment, which
    every script already reads.
    """
    def is_global(token):
        return token in ("--base", "--learner") \
            or token.startswith(("--base=", "--learner="))

    options, rest = {}, list(argv)
    while rest and is_global(rest[0]):
        token = rest.pop(0)
        if "=" in token:
            key, _, value = token.partition("=")
        elif rest:
            key, value = token, rest.pop(0)
        else:
            raise ValueError("%s needs a value" % token)
        options[key.lstrip("-")] = value
    return options, rest


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        options, rest = split_global_options(argv)
    except ValueError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2

    if not rest or rest[0] in ("-h", "--help", "help"):
        print(usage())
        return 0

    command, arguments = rest[0], rest[1:]
    if command not in COMMANDS:
        print("error: unknown command %r\n\n%s" % (command, usage()),
              file=sys.stderr)
        return 2

    if "base" in options:
        os.environ["EXAM_COACH_HOME"] = options["base"]
    if "learner" in options:
        os.environ["EXAM_COACH_LEARNER"] = options["learner"]

    module = importlib.import_module(COMMANDS[command][0])
    # So each command's own --help reads "coach <command>", not "coach.py".
    sys.argv[0] = "coach %s" % command
    return module.main(arguments)


if __name__ == "__main__":
    sys.exit(main())
