"""Keep the bookkeeping tool to the files it is meant to touch.

`coach.py` is the kind of command a user allows once and stops reading. So
it must stay harmless even when it is pointed somewhere it should not be —
by a mistake, or by text in a learner's essay that talks the assistant into
it. Two rules, enforced here for every command that takes a path:

- **It reads only working files.** A path given to be read must be a plain
  text working file — .txt, .md, .json, .jsonl — after any symbolic link is
  followed. It will not print a key file, a shell profile or a credentials
  file back, whatever it is called on the command line.
- **It overwrites only its own output.** A page or an archive is written to
  a name with the right extension, and an existing file is replaced only if
  this tool made it.
"""

import sys
import zipfile
from pathlib import Path

TEXT_SUFFIXES = (".txt", ".md", ".markdown", ".json", ".jsonl")
MAX_INPUT_BYTES = 2 * 1024 * 1024
GENERATOR = "english-exam-coach"
ZIP_STAMP = b"english-exam-coach progress export"


class Refused(ValueError):
    """A path this tool will not read or write."""


def read_text(source, suffixes=TEXT_SUFFIXES):
    """The text of a working file, or of stdin for "-". Raises Refused or
    OSError."""
    if str(source) == "-":
        return sys.stdin.read()
    path = Path(source).expanduser()
    real = path.resolve()
    if path.suffix.lower() not in suffixes or real.suffix.lower() not in suffixes:
        raise Refused("%s is not a working file this tool reads (%s). Save "
                      "the text under one of those extensions first."
                      % (path.name, ", ".join(suffixes)))
    if real.is_file() and real.stat().st_size > MAX_INPUT_BYTES:
        raise Refused("%s is larger than %d MB" % (path.name,
                                                   MAX_INPUT_BYTES // (1024 * 1024)))
    return real.read_text(encoding="utf-8")


def check_html_target(target):
    """A page may be written to a new .html file, or over a page this tool
    wrote earlier — never over anything else."""
    target = Path(target).expanduser()
    if target.suffix.lower() not in (".html", ".htm"):
        raise Refused("the page must be written to a .html file (got %s)"
                      % target.name)
    if target.exists():
        try:
            head = target.read_text(encoding="utf-8", errors="replace")[:2000]
        except OSError as exc:
            raise Refused("cannot check %s before replacing it: %s" % (target, exc))
        if 'name="generator" content="%s"' % GENERATOR not in head:
            raise Refused("%s exists and was not written by this tool; "
                          "choose another name" % target)
    return target


def check_zip_target(target):
    """An archive may be written to a new .zip file, or over an archive this
    tool wrote earlier (it stamps its archives) — never over anything else."""
    target = Path(target).expanduser()
    if target.suffix.lower() != ".zip":
        raise Refused("the archive must be written to a .zip file (got %s)"
                      % target.name)
    if target.exists():
        try:
            with zipfile.ZipFile(target) as existing:
                ours = existing.comment == ZIP_STAMP
        except (zipfile.BadZipFile, OSError):
            ours = False
        if not ours:
            raise Refused("%s exists and was not written by this tool; "
                          "choose another name" % target)
    return target
