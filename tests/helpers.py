"""Shared helpers for the script tests (stdlib only)."""

import contextlib
import io
import json
import os
import subprocess
import sys
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_DIR = REPO_ROOT / "plugins" / "english-exam-coach"
# The plugin ships ONE self-contained skill: everything a session needs
# (instructions, reference data, scripts) lives inside this folder, because
# some surfaces copy only the skill's own folder.
SKILL_DIR = PLUGIN_DIR / "skills" / "english-exam-coach"
SCRIPTS = SKILL_DIR / "scripts"
DATA = SKILL_DIR / "data"
REFERENCES = SKILL_DIR / "references"
LOG_ATTEMPT = SCRIPTS / "log_attempt.py"
BUILD_REPORT = SCRIPTS / "build_report.py"
PROFILE = SCRIPTS / "learner_profile.py"
CONVERT_SCORE = SCRIPTS / "convert_score.py"
COACH = SCRIPTS / "coach.py"


def run_script(script, args, env_overrides=None):
    env = dict(os.environ)
    # A developer's own settings must never steer a test into real data.
    env.pop("EXAM_COACH_HOME", None)
    env.pop("EXAM_COACH_LEARNER", None)
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        [sys.executable, str(script)] + [str(a) for a in args],
        capture_output=True, text=True, env=env,
    )


def coach(base, *args, learner=None):
    """Run a command through the dispatcher, the way a session does.

    In-process, because a new interpreter per call makes the suite slow; the
    result has the same returncode / stdout / stderr as a real run. The few
    tests that are about the real process use run_script(COACH, ...) instead.
    """
    argv = ["--base", str(base)]
    if learner:
        argv += ["--learner", learner]
    argv += [str(a) for a in args]
    names = ("EXAM_COACH_HOME", "EXAM_COACH_LEARNER")
    saved_env = {name: os.environ.pop(name, None) for name in names}
    saved_argv0 = sys.argv[0]
    out, err = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = _coach_module().main(argv)
            except SystemExit as exc:       # argparse: --help, usage errors
                code = exc.code if isinstance(exc.code, int) else \
                    (0 if exc.code is None else 1)
    finally:
        sys.argv[0] = saved_argv0
        for name, value in saved_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
    return types.SimpleNamespace(returncode=code or 0, stdout=out.getvalue(),
                                 stderr=err.getvalue())


def _coach_module():
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    import coach as module
    return module


def log_attempt(base, **fields):
    """Log one attempt with sensible defaults; returns CompletedProcess."""
    defaults = {
        "exam": "cefr-c1",
        "skill": "reading-use-of-english",
        "task-type": "key-word-transformation",
        "level": "C1",
        "seconds": 540,
        "session": "2026-07-08-am",
    }
    defaults.update(fields)
    args = ["--base", str(base)]
    for key, value in defaults.items():
        if value is None:
            continue
        args += ["--" + key, str(value)]
    return run_script(LOG_ATTEMPT, args)


def read_log_lines(base):
    path = Path(base) / "attempts.jsonl"
    if not path.exists():
        return []
    return [line for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def parsed_log(base):
    return [json.loads(line) for line in read_log_lines(base)]
