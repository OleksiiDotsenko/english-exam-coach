"""Shared helpers for the progress-tracker script tests (stdlib only)."""

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = (REPO_ROOT / "plugins" / "english-exam-coach" / "skills"
           / "progress-tracker" / "scripts")
LOG_ATTEMPT = SCRIPTS / "log_attempt.py"
BUILD_REPORT = SCRIPTS / "build_report.py"


def run_script(script, args, env_overrides=None):
    env = dict(os.environ)
    env.pop("EXAM_COACH_HOME", None)
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        [sys.executable, str(script)] + [str(a) for a in args],
        capture_output=True, text=True, env=env,
    )


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
