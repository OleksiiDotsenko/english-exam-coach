"""Tests for what v3.0 added to the state contract and for the dispatcher.

Tutor mode keeps each learner in a directory of their own; export/import is
how progress survives on surfaces with no persistent home directory; and
`coach.py` is the one entry point a session is allowed to run freely — which
is only safe while nothing reachable from it can start a process or open a
connection. That last promise is checked here, statically.
"""

import ast
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from helpers import SCRIPTS, coach, run_script

sys.path.insert(0, str(SCRIPTS))
import coach as coach_module  # noqa: E402
import state  # noqa: E402

# Modules that would let a script start a program or reach the network.
FORBIDDEN_IMPORTS = {
    "subprocess", "socket", "urllib", "http", "ftplib", "smtplib", "ssl",
    "requests", "asyncio", "multiprocessing", "ctypes", "pty", "webbrowser",
    "xmlrpc", "telnetlib", "poplib", "imaplib",
}
FORBIDDEN_CALLS = {"system", "popen", "spawnl", "spawnv", "execv", "execl",
                   "execvp", "startfile", "fork"}


def imported_names(tree):
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


def reachable_modules():
    """Every local module the dispatcher can end up importing."""
    local = {p.stem for p in SCRIPTS.glob("*.py")}
    seen, todo = set(), ["coach"] + [m for m, _d in coach_module.COMMANDS.values()]
    while todo:
        name = todo.pop()
        if name in seen or name not in local:
            continue
        seen.add(name)
        tree = ast.parse((SCRIPTS / (name + ".py")).read_text(encoding="utf-8"))
        todo.extend(imported_names(tree) & local)
    return sorted(seen)


class DispatcherSafetyTests(unittest.TestCase):
    def test_every_command_names_a_module_that_exists(self):
        for command, (module, description) in coach_module.COMMANDS.items():
            self.assertTrue((SCRIPTS / (module + ".py")).is_file(),
                            "%s -> %s.py is missing" % (command, module))
            self.assertTrue(description.strip())

    def test_nothing_reachable_can_start_a_process_or_open_a_connection(self):
        for name in reachable_modules():
            source = (SCRIPTS / (name + ".py")).read_text(encoding="utf-8")
            tree = ast.parse(source)
            bad = imported_names(tree) & FORBIDDEN_IMPORTS
            self.assertFalse(bad, "%s.py imports %s" % (name, sorted(bad)))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func = node.func
                    called = getattr(func, "attr", getattr(func, "id", ""))
                    self.assertNotIn(called, FORBIDDEN_CALLS,
                                     "%s.py calls %s()" % (name, called))
                    self.assertNotIn(called, ("eval", "exec", "__import__"),
                                     "%s.py calls %s()" % (name, called))

    def test_the_scripts_that_do_start_programs_are_not_routed(self):
        routed = {module for module, _d in coach_module.COMMANDS.values()}
        for path in SCRIPTS.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            if imported_names(tree) & FORBIDDEN_IMPORTS:
                self.assertNotIn(path.stem, routed)
                self.assertNotIn(path.stem, reachable_modules())

    def test_no_module_shadows_the_standard_library(self):
        # queue.py and profile.py once did, which broke `import queue` for
        # anything run from this folder.
        stdlib = set(getattr(sys, "stdlib_module_names", ()))
        for path in SCRIPTS.glob("*.py"):
            self.assertNotIn(path.stem, stdlib, "%s shadows the stdlib" % path.name)


class DispatcherBehaviourTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name) / "progress"

    def tearDown(self):
        self._tmp.cleanup()

    def test_help_lists_every_command(self):
        result = run_script(SCRIPTS / "coach.py", ["--help"])
        self.assertEqual(result.returncode, 0)
        for command in coach_module.COMMANDS:
            self.assertIn(command, result.stdout)

    def test_unknown_command_is_an_error_not_a_crash(self):
        result = coach(self.base, "frobnicate")
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown command", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_a_global_option_without_a_value_is_an_error(self):
        result = run_script(SCRIPTS / "coach.py", ["--base"])
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)

    def test_every_command_answers_help(self):
        # A real process: how argparse names the program depends on how the
        # interpreter was started.
        for command in coach_module.COMMANDS:
            result = run_script(SCRIPTS / "coach.py", [command, "--help"])
            self.assertEqual(result.returncode, 0,
                             "%s --help failed: %s" % (command, result.stderr))
            self.assertIn("coach %s" % command, result.stdout)

    def test_global_options_reach_the_command(self):
        result = coach(self.base, "log-error", "--category", "grammar",
                       "--subtype", "article", "--point", "a before a count noun",
                       learner="Dana K.")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.base / "learners" / "dana-k" / "errors.jsonl").is_file())
        self.assertFalse((self.base / "errors.jsonl").exists())

    def test_equals_form_of_global_options(self):
        result = run_script(SCRIPTS / "coach.py",
                            ["--base=%s" % self.base, "--learner=sam", "state", "show"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(str(self.base / "learners" / "sam"), result.stdout)


class LearnerDirectoryTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name) / "progress"

    def tearDown(self):
        self._tmp.cleanup()

    def test_slug_is_folder_safe_and_keeps_non_latin_names(self):
        self.assertEqual(state.slugify("Dana K."), "dana-k")
        self.assertEqual(state.slugify("  Олена  "), "олена")
        self.assertEqual(state.slugify("a/../b"), "a-b")
        self.assertEqual(state.slugify("../.."), "")
        self.assertEqual(state.slugify("***"), "")

    def test_a_hostile_learner_name_cannot_leave_the_base(self):
        for name in ("../../etc", "/abs/path", "..", "a/../../b", "~root"):
            resolved = state.resolve_base(str(self.base), name).resolve()
            self.assertTrue(resolved == self.base.resolve()
                            or self.base.resolve() in resolved.parents,
                            "%r escaped to %s" % (name, resolved))

    def test_no_learner_means_the_classic_solo_layout(self):
        self.assertEqual(state.resolve_base(str(self.base), ""), self.base)
        self.assertEqual(state.resolve_base(str(self.base), "***"), self.base)

    def test_learners_do_not_share_logs(self):
        for name, point in (("anna", "articles with jobs"), ("ben", "then vs than")):
            result = coach(self.base, "log-error", "--category", "grammar",
                           "--subtype", "article", "--point", point, learner=name)
            self.assertEqual(result.returncode, 0, result.stderr)
        anna = (self.base / "learners" / "anna" / "errors.jsonl").read_text(encoding="utf-8")
        ben = (self.base / "learners" / "ben" / "errors.jsonl").read_text(encoding="utf-8")
        self.assertIn("articles with jobs", anna)
        self.assertNotIn("then vs than", anna)
        self.assertIn("then vs than", ben)

    def test_learner_from_the_environment(self):
        result = run_script(SCRIPTS / "state.py", ["show", "--base", self.base],
                            env_overrides={"EXAM_COACH_LEARNER": "Mira"})
        self.assertIn(str(self.base / "learners" / "mira"), result.stdout)

    def test_the_flag_beats_the_environment(self):
        result = run_script(SCRIPTS / "state.py",
                            ["show", "--base", self.base, "--learner", "omar"],
                            env_overrides={"EXAM_COACH_LEARNER": "Mira"})
        self.assertIn(str(self.base / "learners" / "omar"), result.stdout)

    def test_learners_command_lists_who_has_data(self):
        coach(self.base, "log-test", "--name", "One", "--exam", "toefl-ibt",
              "--reading", "4", learner="anna")
        coach(self.base, "log-error", "--category", "lexis", "--subtype",
              "spelling", "--point", "truly, one l", learner="ben")
        result = coach(self.base, "state", "learners")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(result.stdout, r"anna\s+1 test, 0 attempts, 0 logged errors")
        self.assertRegex(result.stdout, r"ben\s+0 tests, 0 attempts, 1 logged error\b")

    def test_learners_command_on_an_empty_root(self):
        result = coach(self.base, "state", "learners")
        self.assertEqual(result.returncode, 0)
        self.assertIn("No learners", result.stdout)


class ExportImportTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.base = self.root / "progress"
        self.archive = self.root / "out" / "progress.zip"
        state.append_jsonl(self.base / "attempts.jsonl", {"n": 1})
        state.append_jsonl(self.base / "errors.jsonl", {"n": 2})
        state.write_json(self.base / "profile.json", {"exam": "toefl-ibt"})
        state.append_jsonl(self.base / "learners" / "anna" / "tests.jsonl", {"n": 3})
        (self.base / "sheets").mkdir()
        (self.base / "sheets" / "articles.md").write_text("# Sheet", encoding="utf-8")
        (self.base / "reports").mkdir()
        (self.base / "reports" / "old.md").write_text("derived", encoding="utf-8")
        (self.base / "learners" / "anna" / "reports").mkdir()
        (self.base / "learners" / "anna" / "reports" / "x.md").write_text(
            "derived", encoding="utf-8")
        (self.base / "queue.json.corrupt-20260101-000000").write_text("{", encoding="utf-8")
        # Things that merely live in the same folder — a progress directory
        # may sit inside a vault of unrelated notes.
        (self.base / "diary.md").write_text("private", encoding="utf-8")
        (self.base / "keys").mkdir()
        (self.base / "keys" / "id_rsa").write_text("secret", encoding="utf-8")
        (self.base / "sheets" / "run.sh").write_text("#!/bin/sh", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    KEPT = ["attempts.jsonl", "errors.jsonl", "learners/anna/tests.jsonl",
            "profile.json", "sheets/articles.md"]

    def test_export_takes_the_layout_and_nothing_else(self):
        path, count = state.export_state(self.base, self.archive)
        self.assertEqual(count, 5)
        with zipfile.ZipFile(path) as archive:
            self.assertEqual(sorted(archive.namelist()), self.KEPT)

    def test_round_trip_restores_every_byte(self):
        state.export_state(self.base, self.archive)
        target = self.root / "restored"
        count, skipped = state.import_state(target, self.archive)
        self.assertEqual((count, skipped), (5, []))
        for name in self.KEPT:
            self.assertEqual((target / name).read_bytes(), (self.base / name).read_bytes())

    def test_import_refuses_to_merge_into_existing_data(self):
        state.export_state(self.base, self.archive)
        with self.assertRaises(ValueError):
            state.import_state(self.base, self.archive)
        rows, _skipped = state.read_jsonl(self.base / "attempts.jsonl")
        self.assertEqual(len(rows), 1)   # untouched

    def test_import_into_a_directory_holding_only_reports_is_allowed(self):
        state.export_state(self.base, self.archive)
        target = self.root / "restored"
        (target / "reports").mkdir(parents=True)
        self.assertEqual(state.import_state(target, self.archive)[0], 5)

    def test_an_archive_cannot_plant_files_that_are_not_progress(self):
        crafted = self.root / "crafted.zip"
        with zipfile.ZipFile(crafted, "w") as archive:
            archive.writestr("attempts.jsonl", "{}\n")
            archive.writestr("conf.d/startup.fish", "echo owned")
            archive.writestr(".zshrc", "echo owned")
            archive.writestr("sheets/run.sh", "echo owned")
            archive.writestr("learners/anna/../../escape.jsonl", "{}")
            archive.writestr("learners/Anna B/errors.jsonl", "{}")     # not a slug
        target = self.root / "restored"
        count, skipped = state.import_state(target, crafted)
        self.assertEqual(count, 1)
        self.assertEqual(len(skipped), 5)
        self.assertEqual(sorted(p.name for p in target.rglob("*")), ["attempts.jsonl"])
        self.assertFalse((self.root / "escape.jsonl").exists())

    def test_an_archive_with_nothing_usable_is_refused_and_writes_nothing(self):
        evil = self.root / "evil.zip"
        with zipfile.ZipFile(evil, "w") as archive:
            archive.writestr("../escaped.txt", "x")
        target = self.root / "restored"
        with self.assertRaises(ValueError):
            state.import_state(target, evil)
        self.assertFalse((self.root / "escaped.txt").exists())
        self.assertFalse(target.exists())   # nothing half-unpacked

    def test_export_does_not_swallow_its_own_archive(self):
        inside = self.base / "backup.zip"
        state.export_state(self.base, inside)
        with zipfile.ZipFile(inside) as archive:
            self.assertNotIn("backup.zip", archive.namelist())

    def test_export_writes_only_archives_and_only_over_archives(self):
        for name in ("progress.txt", ".zshrc", "page.html"):
            result = coach(self.base, "state", "export", "-o", self.root / name)
            self.assertEqual(result.returncode, 2, name)
            self.assertFalse((self.root / name).exists())
        victim = self.root / "thesis.zip"
        victim.write_text("not an archive, despite its name", encoding="utf-8")
        result = coach(self.base, "state", "export", "-o", victim)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(victim.read_text(encoding="utf-8"),
                         "not an archive, despite its name")
        photos = self.root / "photos.zip"                 # a real archive, not ours
        with zipfile.ZipFile(photos, "w") as archive:
            archive.writestr("holiday.txt", "sea")
        result = coach(self.base, "state", "export", "-o", photos)
        self.assertEqual(result.returncode, 2)
        self.assertIn("was not written by this tool", result.stderr)
        with zipfile.ZipFile(photos) as archive:
            self.assertEqual(archive.namelist(), ["holiday.txt"])
        # an earlier export may be replaced
        self.assertEqual(coach(self.base, "state", "export", "-o", self.archive).returncode, 0)
        self.assertEqual(coach(self.base, "state", "export", "-o", self.archive).returncode, 0)

    def test_cli_export_then_import_for_one_learner(self):
        out = self.root / "anna.zip"
        result = coach(self.base, "state", "export", "-o", out, learner="anna")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("exported 1 file", result.stdout)
        other = self.root / "elsewhere"
        result = coach(other, "state", "import", out, learner="anna")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("imported 1 file", result.stdout)
        rows, _s = state.read_jsonl(other / "learners" / "anna" / "tests.jsonl")
        self.assertEqual(rows, [{"n": 3}])

    def test_cli_import_says_what_it_left_out(self):
        crafted = self.root / "crafted.zip"
        with zipfile.ZipFile(crafted, "w") as archive:
            archive.writestr("errors.jsonl", "{}\n")
            archive.writestr("notes/todo.md", "x")
        result = coach(self.root / "fresh", "state", "import", crafted)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("left out 1 file", result.stdout)
        self.assertIn("notes/todo.md", result.stdout)

    def test_cli_export_of_nothing_is_an_error(self):
        result = coach(self.root / "nowhere", "state", "export")
        self.assertEqual(result.returncode, 2)
        self.assertIn("nothing to export", result.stderr)

    def test_cli_import_of_a_non_archive_is_an_error_not_a_crash(self):
        bogus = self.root / "bogus.zip"
        bogus.write_text("not a zip", encoding="utf-8")
        result = coach(self.root / "fresh", "state", "import", bogus)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)


class LayoutTests(unittest.TestCase):
    def test_what_counts_as_part_of_a_progress_directory(self):
        for name in ("attempts.jsonl", "errors.jsonl", "tests.jsonl", "queue.json",
                     "profile.json", "vocab-box.json", "plan.md", "sheets/a.md",
                     "sheets/a.html", "learners/anna/errors.jsonl",
                     "learners/олена/sheets/x.md"):
            self.assertTrue(state.in_layout(name), name)
        for name in ("reports/x.md", "notes.md", ".zshrc", "sheets/run.sh",
                     "sheets/deep/a.md", "../attempts.jsonl", "/etc/passwd",
                     "learners/anna/../../x.jsonl", "learners/Anna B/errors.jsonl",
                     "learners/anna/learners/ben/errors.jsonl", "a/attempts.jsonl",
                     "attempts.jsonl/x", ""):
            self.assertFalse(state.in_layout(name), name)


class StateInventoryTests(unittest.TestCase):
    def test_show_and_validate_know_the_test_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "tests.jsonl").write_text('{"name": "A"}\nnot json\n',
                                              encoding="utf-8")
            self.assertIn("tests.jsonl", state.describe(base))
            self.assertTrue(any("tests.jsonl" in p for p in state.validate(base)))


if __name__ == "__main__":
    unittest.main()
