#!/usr/bin/env python3
"""The state-directory contract: how every script reads and writes user data.

One module owns the rules so the scripts cannot drift apart. Run it directly
to inspect, validate or move a progress directory:

  state.py show              # what is in the directory, and is it readable
  state.py validate          # exit 1 if anything is structurally broken
  state.py learners          # tutor mode: who has data here
  state.py export -o x.zip   # one file to carry between sessions or machines
  state.py import x.zip      # restore it into an empty directory

## Where the data lives

  --base <dir>  >  $EXAM_COACH_HOME  >  ~/english-exam-coach/

A tutor keeps one directory per learner: `--learner <name>` (or
$EXAM_COACH_LEARNER) selects `<base>/learners/<name>/`, which has exactly the
same layout as a solo learner's directory. Nothing is shared between learners.

## The contract

Layout of a progress directory (nothing here is required; every file is
created on demand):

  attempts.jsonl   append-only log of scored attempts   (v0.1.1+)
  errors.jsonl     append-only log of tagged mistakes   (v2.0)
  tests.jsonl      append-only log of full test results (v3.0)
  queue.json       spaced re-testing state              (v2.0, mediated)
  profile.json     target exam, score, date             (v0.1.8)
  vocab-box.json   vocabulary Leitner boxes             (legacy, LLM-written)
  plan.md          study plan                           (legacy, LLM-written)
  reports/         derived Markdown/HTML, always regenerable
  sheets/          practice sheets written for the learner (v3.0)
  learners/        one such directory per learner       (v3.0, tutor mode)

Rules, in force for every writer:

1. **Append-only logs are append-only.** `attempts.jsonl`, `errors.jsonl` and
   `tests.jsonl` are opened in append mode, never truncated, never rewritten.
   A correction is a newer line: an amended or voided test, a voided mistake.
   Readers apply the corrections; the history of what was written stays.
   Deleting history is a deliberate act by the user, never a side effect.
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
import hashlib
import json
import os
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath

import fileguard

STATE_VERSION = 2

APPEND_LOGS = ("attempts.jsonl", "errors.jsonl", "tests.jsonl")
JSON_STATE = ("profile.json", "queue.json", "vocab-box.json")
LEGACY_FILES = ("vocab-box.json", "plan.md")
LEARNERS_DIR = "learners"
SHEETS_DIR = "sheets"
SHEET_SUFFIXES = (".md", ".html")


def in_layout(relative):
    """Is this path part of a progress directory, as the contract lays it out?

    Export and import move these files and no others. A progress directory
    may sit inside a folder of unrelated notes, and an archive may come from
    anywhere: neither must turn into a way of copying, or planting,
    arbitrary files.
    """
    parts = PurePosixPath(str(relative).replace("\\", "/")).parts
    if any(part in ("", ".", "..") or part.startswith("/") for part in parts):
        return False
    if len(parts) >= 3 and parts[0] == LEARNERS_DIR and slugify(parts[1]) == parts[1]:
        parts = parts[2:]
    if len(parts) == 1:
        return parts[0] in APPEND_LOGS + JSON_STATE + ("plan.md",)
    if len(parts) == 2 and parts[0] == SHEETS_DIR:
        return PurePosixPath(parts[1]).suffix.lower() in SHEET_SUFFIXES
    return False


def default_base():
    env = os.environ.get("EXAM_COACH_HOME", "").strip()
    if env:
        return Path(env).expanduser()
    return Path.home() / "english-exam-coach"


def slugify(name):
    """A folder-safe, readable id that keeps non-Latin names intact.

    'Dana K.' -> 'dana-k'; 'Олена' stays 'олена'. Returns '' for a name with
    nothing usable in it, which callers treat as "no learner".
    """
    slug = re.sub(r"[^\w]+", "-", str(name).strip().lower(), flags=re.UNICODE)
    return slug.strip("-_")


def resolve_base(base_arg=None, learner_arg=None):
    """The progress directory for this invocation.

    Without a learner this is the directory itself (a solo learner's layout,
    unchanged since v0.1). With one, it is that learner's own subdirectory, so
    a tutor's students can never bleed into each other's logs or queues.
    """
    root = Path(base_arg).expanduser() if base_arg else default_base()
    learner = learner_arg if learner_arg is not None \
        else os.environ.get("EXAM_COACH_LEARNER", "")
    slug = slugify(learner) if learner else ""
    return root / LEARNERS_DIR / slug if slug else root


def add_location_arguments(parser):
    """The two flags every script shares for choosing a progress directory."""
    parser.add_argument("--base", default=None,
                        help="progress directory (default: $EXAM_COACH_HOME "
                             "or ~/english-exam-coach)")
    parser.add_argument("--learner", default=None,
                        help="tutor mode: keep this learner's data in its own "
                             "subdirectory (default: $EXAM_COACH_LEARNER)")


def base_from_args(args):
    return resolve_base(getattr(args, "base", None), getattr(args, "learner", None))


def list_learners(root):
    """[(slug, path)] for every learner directory under a root."""
    folder = Path(root) / LEARNERS_DIR
    if not folder.is_dir():
        return []
    return sorted((p.name, p) for p in folder.iterdir() if p.is_dir())


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


def error_id(row):
    """A mistake's id: its own, or — for a row written before ids existed —
    a stable one derived from its content, so that any row can be corrected."""
    if row.get("id"):
        return str(row["id"])
    basis = "|".join(str(row.get(key) or "") for key in
                     ("ts", "category", "subtype", "point", "evidence", "session"))
    return "e-" + hashlib.sha1(basis.encode("utf-8")).hexdigest()[:8]


def read_errors(base):
    """The error ledger with its corrections applied. Returns (rows, skipped).

    Every reader goes through here. A `void` line withdraws the mistake it
    names; the withdrawn row and the marker are both left out, and every row
    returned carries its `id`.
    """
    raw, skipped = read_jsonl(Path(base) / "errors.jsonl")
    voided = {str(row["void"]) for row in raw if row.get("void")}
    rows = []
    for row in raw:
        if row.get("void"):
            continue
        if not all(row.get(key) for key in ("category", "subtype", "point")):
            skipped += 1
            continue
        row = dict(row, id=error_id(row))
        if row["id"] not in voided:
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
        corrections = sum(1 for row in rows if row.get("void"))
        if corrections:
            detail += ", %d of them correction%s" % (
                corrections, "" if corrections == 1 else "s")
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
        count = len([f for f in reports.iterdir() if f.is_file()])
        lines.append("  %-16s %d file%s (derived, regenerable)"
                     % ("reports/", count, "" if count == 1 else "s"))
    learners = list_learners(base)
    if learners:
        lines.append("  %-16s %s" % ("learners/", ", ".join(n for n, _p in learners)))
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


def export_state(base, out_path):
    """Write a progress directory into one zip file. Returns (path, count).

    Surfaces without a persistent home directory lose the directory when the
    session ends; this is how progress survives there, and how it moves
    between machines. Only the files of the layout are taken: reports are
    derived and are left out, and so is anything else that happens to live
    in the same folder.
    """
    base = Path(base)
    out_path = fileguard.check_zip_target(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.comment = fileguard.ZIP_STAMP
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            relative = path.relative_to(base).as_posix()
            if in_layout(relative) and path.resolve() != out_path.resolve():
                archive.write(path, relative)
                count += 1
    return out_path, count


def import_state(base, archive_path):
    """Unpack an export into an empty progress directory. Returns
    (files written, names left out).

    Refuses to merge into existing data: two histories cannot be combined
    safely by overwriting, and silently replacing a log would break rule 1.
    Only files of the layout are written, so an archive from anywhere cannot
    plant anything else.
    """
    base = Path(base)
    if base.exists() and any(p.name != "reports" for p in base.iterdir()):
        raise ValueError("%s already holds data; import needs an empty "
                         "directory (choose another --base or --learner)" % base)
    with zipfile.ZipFile(archive_path) as archive:
        members = [m for m in archive.infolist() if not m.is_dir()]
        wanted = [m for m in members if in_layout(m.filename)]
        skipped = [m.filename for m in members if not in_layout(m.filename)]
        if not wanted:
            raise ValueError("%s holds no progress files" % archive_path)
        for member in wanted:
            target = (base / member.filename).resolve()
            # Belt and braces: nothing may land outside the directory.
            if base.resolve() not in target.parents:
                raise ValueError("refusing to unpack %r outside %s"
                                 % (member.filename, base))
        base.mkdir(parents=True, exist_ok=True)
        for member in wanted:
            target = base / member.filename
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(member))
    return len(wanted), skipped


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command",
                        choices=("show", "validate", "learners", "export", "import"))
    parser.add_argument("archive", nargs="?", default=None,
                        help="zip file to read, for `import`")
    parser.add_argument("-o", "--output", default=None,
                        help="zip file to write, for `export`")
    add_location_arguments(parser)
    args = parser.parse_args(argv)
    base = base_from_args(args)

    if args.command == "show":
        print(describe(base))
        return 0

    if args.command == "learners":
        root = resolve_base(args.base, "")
        learners = list_learners(root)
        if not learners:
            print("No learners under %s. Add one by passing --learner <name> "
                  "to any command." % root)
            return 0
        for name, path in learners:
            tests, _s = read_jsonl(path / "tests.jsonl")
            attempts, _s = read_jsonl(path / "attempts.jsonl")
            errors, _s = read_jsonl(path / "errors.jsonl")
            print("%-20s %d test%s, %d attempt%s, %d logged error%s"
                  % (name, len(tests), "" if len(tests) == 1 else "s",
                     len(attempts), "" if len(attempts) == 1 else "s",
                     len(errors), "" if len(errors) == 1 else "s"))
        return 0

    if args.command == "export":
        if not base.exists():
            print("error: nothing to export — %s does not exist" % base,
                  file=sys.stderr)
            return 2
        stamp = datetime.now().strftime("%Y%m%d")
        out = Path(args.output) if args.output else \
            Path.cwd() / ("english-exam-coach-progress-%s.zip" % stamp)
        try:
            path, count = export_state(base, out)
        except fileguard.Refused as exc:
            print("error: %s" % exc, file=sys.stderr)
            return 2
        except OSError as exc:
            print("error: could not write %s: %s" % (out, exc), file=sys.stderr)
            return 1
        print("exported %d file%s: %s" % (count, "" if count == 1 else "s", path))
        return 0

    if args.command == "import":
        if not args.archive:
            print("error: import needs the zip file to read", file=sys.stderr)
            return 2
        try:
            count, skipped = import_state(base, args.archive)
        except (ValueError, OSError, zipfile.BadZipFile) as exc:
            print("error: %s" % exc, file=sys.stderr)
            return 2
        print("imported %d file%s into %s"
              % (count, "" if count == 1 else "s", base))
        if skipped:
            print("left out %d file%s that are not part of a progress "
                  "directory: %s" % (len(skipped), "" if len(skipped) == 1 else "s",
                                     ", ".join(skipped[:5])))
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
