#!/usr/bin/env python3
"""The state-directory contract: how every script reads and writes user data.

One module owns the rules so the scripts cannot drift apart. Run it directly
to inspect or validate a progress directory:

  state.py show        # what is in the directory, and is it readable
  state.py validate    # exit 1 if anything is structurally broken

## The contract

Layout of <base>/ (nothing here is required; every file is created on demand):

  attempts.jsonl   append-only log of scored attempts   (v0.1.1+)
  errors.jsonl     append-only log of tagged mistakes   (v2.0)
  queue.json       spaced re-testing state              (v2.0, mediated)
  profile.json     target exam, score, date             (v0.1.8)
  vocab-box.json   vocabulary Leitner boxes             (legacy, LLM-written)
  plan.md          study plan                           (legacy, LLM-written)
  reports/         derived Markdown, always regenerable

Rules, in force for every writer:

1. **Append-only logs are append-only.** `attempts.jsonl` and `errors.jsonl`
   are opened in append mode, never truncated, never rewritten. Deleting
   history is a deliberate act by the user, never a side effect.
2. **Fields are additive-only.** A field that has ever been written keeps its
   name and meaning forever. Add new fields; never repurpose or remove one.
   Old logs must stay readable by every future version.
3. **JSON state is written atomically** — temp file then `os.replace`, so an
   interrupted write can never leave a half-written file.
4. **Readers are tolerant; writers are strict.** A corrupt line is skipped,
   never fatal. A corrupt JSON state file is quarantined and rebuilt, and the
   user is told. Nothing the LLM produces is trusted to be well-formed.
5. **Unknown keys survive.** Readers preserve fields they do not understand,
   so an older script cannot silently strip a newer one's data.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

STATE_VERSION = 2

APPEND_LOGS = ("attempts.jsonl", "errors.jsonl")
JSON_STATE = ("profile.json", "queue.json", "vocab-box.json")
LEGACY_FILES = ("vocab-box.json", "plan.md")


def default_base():
    env = os.environ.get("EXAM_COACH_HOME", "").strip()
    if env:
        return Path(env).expanduser()
    return Path.home() / "english-exam-coach"


def resolve_base(base_arg=None):
    return Path(base_arg).expanduser() if base_arg else default_base()


def read_jsonl(path, required_keys=()):
    """Return (rows, skipped). Malformed or wrong-shape lines are skipped.

    Tolerant by rule 4: one bad line can never make a log unreadable.
    """
    rows, skipped = [], 0
    path = Path(path)
    if not path.exists():
        return rows, skipped
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return rows, skipped
    for raw in text.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            row = json.loads(raw)
        except ValueError:
            skipped += 1
            continue
        if not isinstance(row, dict) or not all(row.get(k) for k in required_keys):
            skipped += 1
            continue
        rows.append(row)
    return rows, skipped


def append_jsonl(path, record):
    """Append exactly one JSON line, guarding against a missing final newline.

    Returns the path written. Never truncates (rule 1); strict JSON only, so a
    NaN can never enter the log.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False, allow_nan=False)
    prefix = ""
    if path.exists() and path.stat().st_size > 0:
        with open(path, "rb") as handle:
            handle.seek(-1, 2)
            if handle.read(1) != b"\n":
                prefix = "\n"
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(prefix + line + "\n")
    return path


def write_json(path, data):
    """Atomically replace a JSON state file (rule 3)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False,
                              allow_nan=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path


def quarantine(path, reason="unreadable"):
    """Move a corrupt state file aside so a fresh one can be built.

    Returns the quarantine path, or None if there was nothing to move. The
    caller must tell the user — silent data loss is worse than a broken file.
    """
    path = Path(path)
    if not path.exists():
        return None
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = path.with_name("%s.corrupt-%s" % (path.name, stamp))
    try:
        os.replace(path, target)
    except OSError:
        return None
    return target


def read_json(path, default=None, quarantine_on_error=False):
    """Read a JSON state file. Returns (data, note).

    `note` is None on success, or a human-readable sentence the caller should
    surface (rule 4: the user always learns when state was quarantined).
    """
    path = Path(path)
    if not path.exists():
        return (default if default is not None else {}), None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        note = "%s was unreadable" % path.name
        if quarantine_on_error:
            moved = quarantine(path)
            note += (" and was moved to %s; starting a fresh one"
                     % moved.name if moved else "; starting a fresh one")
        return (default if default is not None else {}), note
    if not isinstance(data, dict):
        note = "%s did not contain an object" % path.name
        if quarantine_on_error:
            moved = quarantine(path)
            note += (" and was moved to %s; starting a fresh one"
                     % moved.name if moved else "; starting a fresh one")
        return (default if default is not None else {}), note
    return data, None


def stamp_version(data):
    """Mark a state object with the contract version, preserving unknown keys."""
    data.setdefault("version", STATE_VERSION)
    data["updated"] = datetime.now().isoformat(timespec="seconds")
    return data


def describe(base):
    """Human-readable inventory of a progress directory."""
    base = Path(base)
    lines = ["Progress directory: %s" % base]
    if not base.exists():
        lines.append("  (does not exist yet — it is created on first write)")
        return "\n".join(lines)
    for name in APPEND_LOGS:
        path = base / name
        if not path.exists():
            continue
        rows, skipped = read_jsonl(path)
        detail = "%d record%s" % (len(rows), "" if len(rows) == 1 else "s")
        if skipped:
            detail += ", %d unreadable line%s skipped" % (
                skipped, "" if skipped == 1 else "s")
        lines.append("  %-16s %s" % (name, detail))
    for name in JSON_STATE:
        path = base / name
        if not path.exists():
            continue
        data, note = read_json(path)
        detail = note or "ok (%d key%s)" % (len(data), "" if len(data) == 1 else "s")
        legacy = " [legacy, written by the assistant]" if name in LEGACY_FILES else ""
        lines.append("  %-16s %s%s" % (name, detail, legacy))
    plan = base / "plan.md"
    if plan.exists():
        lines.append("  %-16s %d lines [legacy, written by the assistant]"
                     % ("plan.md", len(plan.read_text(encoding="utf-8").splitlines())))
    reports = base / "reports"
    if reports.exists():
        count = len(list(reports.glob("*.md")))
        lines.append("  %-16s %d file%s (derived, regenerable)"
                     % ("reports/", count, "" if count == 1 else "s"))
    if len(lines) == 1:
        lines.append("  (empty)")
    return "\n".join(lines)


def validate(base):
    """Return a list of structural problems (empty = healthy)."""
    base = Path(base)
    problems = []
    if not base.exists():
        return problems
    for name in APPEND_LOGS:
        path = base / name
        if not path.exists():
            continue
        _rows, skipped = read_jsonl(path)
        if skipped:
            problems.append("%s: %d unreadable line(s) — they are skipped when "
                            "reporting, but the log has been damaged by "
                            "something other than these scripts" % (name, skipped))
        text = path.read_text(encoding="utf-8")
        if text and not text.endswith("\n"):
            problems.append("%s: last line has no trailing newline — the next "
                            "append will repair it" % name)
    for name in JSON_STATE:
        path = base / name
        if not path.exists():
            continue
        _data, note = read_json(path)
        if note:
            problems.append(note)
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("show", "validate"))
    parser.add_argument("--base", default=None)
    args = parser.parse_args(argv)
    base = resolve_base(args.base)

    if args.command == "show":
        print(describe(base))
        return 0

    problems = validate(base)
    if not problems:
        print("state ok: %s" % base)
        return 0
    for problem in problems:
        print("problem: %s" % problem, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
