"""The package must be what its own documents say it is.

Instructions are the product here: the assistant does what the Markdown tells
it to. A command that does not exist, an option the script rejects, a path to
a file that moved — each of those fails in front of a learner, mid-session.
These tests read the instructions the way the assistant does and check every
checkable claim against the code.

They also pin what the plugin directory and a careful user need to be true:
the skill is self-contained, the listing says what the plugin runs, and the
versions agree.
"""

import ast
import json
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from helpers import COACH, PLUGIN_DIR, REPO_ROOT, SCRIPTS, SKILL_DIR, coach

sys.path.insert(0, str(SCRIPTS))
import coach as coach_module  # noqa: E402
import speak  # noqa: E402
import transcribe  # noqa: E402

SKILL = SKILL_DIR / "SKILL.md"
COMMANDS_DIR = PLUGIN_DIR / "commands"
HELPERS = ("speak.py", "timed_speak.py", "transcribe.py")
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".webp")
ENVIRONMENT_VARIABLES = {"EXAM_COACH_HOME", "EXAM_COACH_LEARNER"}
SUBCOMMANDS = {"queue": ("sync", "due", "show", "review"),
               "profile": ("show", "set"),
               "state": ("show", "validate", "learners", "export", "import"),
               "ctest": ("make", "check"),
               "sentence": ("make", "check")}
GLOBAL_OPTIONS = {"--base", "--learner", "--help"}


def instruction_files():
    return [SKILL] + sorted((SKILL_DIR / "references").glob("*.md")) \
        + sorted(SKILL_DIR.glob("data/**/*.md")) + sorted(COMMANDS_DIR.glob("*.md"))


def front_matter(path):
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    return (match.group(1) if match else None), text[match.end():] if match else text


def joined_commands(text):
    """Every `coach …` invocation in a document, with line continuations and
    Markdown line wraps folded, as (command, [tokens])."""
    found = []
    # fenced blocks: logical lines, backslash continuations joined
    for block in re.findall(r"```(?:bash|text|sh)?\n(.*?)```", text, re.S):
        logical = re.sub(r"\\\n\s*", " ", block)
        for line in logical.splitlines():
            line = line.split("#")[0].strip()
            if line.startswith("coach "):
                found.append(line.split())
    # inline code spans, which may wrap across a line break in prose
    for span in re.findall(r"`(coach [^`]+)`", text):
        found.append(" ".join(span.split()).split())
    result = []
    for tokens in found:
        rest = tokens[1:]
        while rest and rest[0] in ("--base", "--learner"):
            rest = rest[2:]
        if rest:
            result.append((rest[0], rest[1:]))
    return result


_HELP = {}


def help_text(command, sub=None):
    key = (command, sub)
    if key not in _HELP:
        args = [command] + ([sub] if sub else []) + ["--help"]
        _HELP[key] = coach(tempfile.gettempdir(), *args).stdout
    return _HELP[key]


class SkillFileTests(unittest.TestCase):
    def setUp(self):
        self.meta, self.body = front_matter(SKILL)

    def test_there_is_exactly_one_skill(self):
        skills = [p.parent.name for p in (PLUGIN_DIR / "skills").glob("*/SKILL.md")]
        self.assertEqual(skills, ["english-exam-coach"])

    def test_front_matter_names_the_skill_and_describes_when_to_use_it(self):
        self.assertIsNotNone(self.meta)
        self.assertRegex(self.meta, r"(?m)^name: english-exam-coach$")
        description = re.search(r"description: >\n((?:  .*\n?)+)", self.meta).group(1)
        description = " ".join(description.split())
        self.assertLessEqual(len(description), 1024,
                             "a description past 1,024 characters is cut off")
        self.assertGreater(len(description), 300)
        for word in ("IELTS", "TOEFL", "B1", "C2", "writing", "speaking",
                     "listening", "vocabulary", "tutor", "printable"):
            self.assertIn(word, description)

    def test_the_router_stays_short(self):
        self.assertLess(len(SKILL.read_text(encoding="utf-8").splitlines()), 500)
        for path in (SKILL_DIR / "references").glob("*.md"):
            self.assertLess(len(path.read_text(encoding="utf-8").splitlines()), 400,
                            path.name)

    def test_nothing_is_pre_approved(self):
        # The user decides what may run without asking. A skill that grants
        # itself a tool widens what a hostile essay could talk it into.
        self.assertFalse("allowed-tools" in self.meta)
        self.assertFalse("allowed-tools" in SKILL.read_text(encoding="utf-8"))

    def test_every_reference_file_is_routed_to(self):
        text = SKILL.read_text(encoding="utf-8")
        for path in (SKILL_DIR / "references").glob("*.md"):
            self.assertTrue("references/%s" % path.name in text,
                            "%s is not reachable from SKILL.md" % path.name)

    def test_every_command_is_in_the_table(self):
        for command in coach_module.COMMANDS:
            self.assertTrue("`coach %s`" % command in self.body, command)

    def test_reference_files_carry_no_front_matter(self):
        # They are read as documents, not loaded as skills.
        for path in (SKILL_DIR / "references").glob("*.md"):
            self.assertFalse(path.read_text(encoding="utf-8").startswith("---"),
                             path.name)

    def test_the_path_variable_appears_only_where_a_path_belongs(self):
        # Claude Code fills the variable in everywhere in this file. A
        # sentence *about* the placeholder would then read as a sentence
        # about a real folder, and send a session off to look for a folder
        # it already has. So the variable is written only inside the two
        # commands that use it, and the prose describes it without naming it.
        text = SKILL.read_text(encoding="utf-8")
        tails = re.findall(r"\$\{CLAUDE_SKILL_DIR\}(.{0,9})", text)
        self.assertEqual(tails, ["/scripts/"] * 2)
        self.assertNotIn("CLAUDE_SKILL_DIR", text.replace("${CLAUDE_SKILL_DIR}", ""))
        self.assertTrue("a dollar sign and a name in braces" in " ".join(text.split()))

    def lookup_block(self):
        blocks = [block for block in re.findall(r"```bash\n(.*?)```", self.body, re.S)
                  if "find " in block]
        self.assertEqual(len(blocks), 1, "SKILL.md carries exactly one lookup")
        return blocks[0]

    def run_lookup(self, block, folder, home):
        script = block.replace('D="FOLDER"', 'D="%s"' % folder)
        done = subprocess.run(["bash", "-c", script], capture_output=True, text=True,
                              env={"HOME": str(home), "PATH": "/usr/bin:/bin"})
        self.assertEqual(done.returncode, 0, done.stderr)
        prefix = "skill folder for the shell: "
        self.assertTrue(done.stdout.startswith(prefix), done.stdout)
        return done.stdout.strip()[len(prefix):]

    def test_the_shell_lookup_is_confined_to_where_skills_are_installed(self):
        # A chat sandbox fills in no variable, and hands the skill a folder
        # that its file tool can read and its shell cannot see. Left to work
        # that out alone, a session ran `find /` for coach.py. The skill now
        # gives one lookup, and it must never be a search of the whole disk.
        block = self.lookup_block()
        self.assertIn('D="FOLDER"', block)
        roots = re.search(r"find (.*?) -type f", block).group(1).split()
        self.assertEqual(roots, ["~/.claude/plugins", "~/.claude/skills", "/mnt/skills"])
        self.assertNotRegex(block, r"find\s+(/|~|\$HOME)\s")
        prose = " ".join(self.body.split())
        self.assertTrue("never widen it to the whole disk" in prose)
        self.assertTrue("`not found`, say so and stop" in prose)

    @unittest.skipUnless(shutil.which("bash"), "the lookup is a shell command")
    def test_the_shell_lookup_finds_the_folder_in_each_layout(self):
        block = self.lookup_block()
        given = "/mnt/skills/plugins/english-exam-coach:english-exam-coach"
        layouts = {
            "synced": ".claude/plugins/synced/a_b/english-exam-coach/skills/"
                      "english-exam-coach",
            "cache": ".claude/plugins/cache/shop/english-exam-coach/3.0.0/skills/"
                     "english-exam-coach",
            "personal": ".claude/skills/english-exam-coach",
        }
        with tempfile.TemporaryDirectory() as tmp:
            for name, relative in layouts.items():
                home = Path(tmp) / ("home with a space " + name)
                folder = home / relative
                (folder / "scripts").mkdir(parents=True)
                (folder / "scripts" / "coach.py").write_text("", encoding="utf-8")
                # The folder the session was given is not there for the shell.
                self.assertEqual(self.run_lookup(block, given, home), str(folder), name)
                # The placeholder left as it is still ends in the right place.
                self.assertEqual(self.run_lookup(block, "FOLDER", home), str(folder), name)
                # A folder that is right is used as it stands: no search.
                self.assertEqual(self.run_lookup(block, str(SKILL_DIR), home),
                                 str(SKILL_DIR), name)
            empty = Path(tmp) / "empty"
            empty.mkdir()
            self.assertEqual(self.run_lookup(block, given, empty), "not found")


class InstructionAccuracyTests(unittest.TestCase):
    def test_every_path_an_instruction_names_exists(self):
        pattern = re.compile(r"`((?:references|data|scripts)/[\w./<>*-]+)`")
        for path in instruction_files():
            for name in pattern.findall(path.read_text(encoding="utf-8")):
                if "<" in name or "*" in name:
                    stem = re.split(r"[<*]", name)[0]
                    self.assertTrue((SKILL_DIR / stem).exists() or
                                    list(SKILL_DIR.glob(stem + "*")),
                                    "%s: %s" % (path.name, name))
                else:
                    self.assertTrue((SKILL_DIR / name.rstrip("/")).exists(),
                                    "%s names %s, which does not exist"
                                    % (path.name, name))

    def test_every_coach_command_in_the_instructions_exists(self):
        for path in instruction_files():
            for command, _tokens in joined_commands(path.read_text(encoding="utf-8")):
                if command in ("<command>", "…", "..."):
                    continue
                self.assertIn(command, coach_module.COMMANDS,
                              "%s tells the assistant to run `coach %s`"
                              % (path.name, command))

    def test_every_option_in_the_instructions_is_accepted(self):
        checked = 0
        for path in instruction_files():
            for command, tokens in joined_commands(path.read_text(encoding="utf-8")):
                if command not in coach_module.COMMANDS:
                    continue
                sub = tokens[0] if tokens and tokens[0] in SUBCOMMANDS.get(command, ()) \
                    else None
                known = help_text(command) + (help_text(command, sub) if sub else "")
                for token in tokens:
                    option = re.match(r"^(--[a-z][a-z-]*)", token)
                    if not option or option.group(1) in GLOBAL_OPTIONS:
                        continue
                    checked += 1
                    self.assertRegex(
                        known, r"%s\b" % re.escape(option.group(1)),
                        "%s: `coach %s` has no option %s"
                        % (path.name, " ".join([command] + ([sub] if sub else [])),
                           option.group(1)))
        self.assertGreater(checked, 100, "the option check found too little to check")

    def test_every_subcommand_in_the_instructions_exists(self):
        for path in instruction_files():
            for command, tokens in joined_commands(path.read_text(encoding="utf-8")):
                if command in SUBCOMMANDS and tokens and not tokens[0].startswith("-") \
                        and re.fullmatch(r"[a-z]+", tokens[0]):
                    self.assertIn(tokens[0], SUBCOMMANDS[command],
                                  "%s: `coach %s %s`" % (path.name, command, tokens[0]))

    def test_helper_scripts_named_in_the_instructions_exist(self):
        for path in instruction_files():
            for name in set(re.findall(r"\b([a-z_]+\.py)\b", path.read_text(encoding="utf-8"))):
                self.assertTrue((SCRIPTS / name).is_file(),
                                "%s mentions %s" % (path.name, name))

    def test_helper_options_in_the_instructions_are_accepted(self):
        helps = {}
        for name in HELPERS:
            texts = [subprocess.run([sys.executable, str(SCRIPTS / name), "--help"],
                                    capture_output=True, text=True).stdout]
            if name == "speak.py":
                for sub in ("render", "play", "clean"):
                    texts.append(subprocess.run(
                        [sys.executable, str(SCRIPTS / name), sub, "--help"],
                        capture_output=True, text=True).stdout)
            helps[name] = "\n".join(texts)
        for path in instruction_files():
            text = " ".join(path.read_text(encoding="utf-8").split())
            for name in HELPERS:
                for span in re.findall(r"`(%s [^`]+)`" % re.escape(name), text):
                    for option in re.findall(r"(--[a-z][a-z-]*)", span):
                        self.assertTrue(option in helps[name],
                                        "%s: `%s` has no option %s"
                                        % (path.name, name, option))

    def test_nothing_points_at_the_old_layout(self):
        gone = ("CLAUDE_PLUGIN_ROOT", "progress-tracker", "queue.py", "profile.py",
                "writing-evaluator skill", "speaking-coach skill",
                "listening-trainer skill", "exam-router skill",
                "study-planner", "test_report.py")
        for path in instruction_files():
            text = path.read_text(encoding="utf-8")
            text = text.replace("review_queue.py", "").replace("learner_profile.py", "")
            if path.parent == COMMANDS_DIR:
                # A command sits outside the skill and may point into it.
                text = text.replace("${CLAUDE_PLUGIN_ROOT}/skills/english-exam-coach/"
                                    "SKILL.md", "")
            for name in gone:
                self.assertFalse(name in text, "%s still mentions %s" % (path.name, name))

    def test_area_labels_in_the_instructions_are_the_fixed_ones(self):
        labels = {"writing-evaluator", "speaking-coach", "reading-use-of-english",
                  "listening-trainer", "vocabulary-builder", "exam-router"}
        for path in instruction_files():
            for label in re.findall(r"--skill ([a-z-]+)", path.read_text(encoding="utf-8")):
                self.assertIn(label, labels, "%s: --skill %s" % (path.name, label))

    def test_task_types_in_the_instructions_are_canonical(self):
        table = (SKILL_DIR / "data" / "task-types.md").read_text(encoding="utf-8")
        slugs = set(re.findall(r"^\| `([a-z0-9-]+)` \|", table, re.M))
        self.assertGreater(len(slugs), 40)
        for path in instruction_files():
            for slug in re.findall(r"--task-type ([a-z][a-z0-9-]+)",
                                   path.read_text(encoding="utf-8")):
                self.assertIn(slug, slugs, "%s: --task-type %s" % (path.name, slug))

    def test_error_tags_in_the_instructions_are_in_the_closed_list(self):
        import log_error
        valid = {"%s/%s" % (c, s) for c, subs in log_error.TAXONOMY.items() for s in subs}
        categories = "|".join(log_error.TAXONOMY)
        for path in instruction_files():
            text = path.read_text(encoding="utf-8")
            for tag in re.findall(r"`((?:%s)/[a-z-]+)`" % categories, text):
                self.assertIn(tag, valid, "%s uses the tag %s" % (path.name, tag))


class CommandFileTests(unittest.TestCase):
    EXPECTED = {"start-prep", "assess-level", "daily-drill", "mock-exam",
                "session-report", "progress", "review-test", "error-catalog",
                "worksheet"}

    def test_the_commands_are_the_documented_nine(self):
        self.assertEqual({p.stem for p in COMMANDS_DIR.glob("*.md")}, self.EXPECTED)

    def test_each_command_has_a_description_and_hands_over_to_the_skill(self):
        for path in COMMANDS_DIR.glob("*.md"):
            meta, body = front_matter(path)
            self.assertIsNotNone(meta, path.name)
            self.assertRegex(meta, r"(?m)^description: .{20,}$", path.name)
            self.assertTrue("$ARGUMENTS" in body, path.name)
            self.assertLess(len(body.split()), 220,
                            "%s should point at the skill, not repeat it" % path.name)

    def test_each_command_loads_the_skill_by_its_full_name_with_a_fallback(self):
        # A command is not the skill. Told only to "use the skill", a session
        # once re-invoked the command itself, never found the skill's folder,
        # and improvised its own files. So every command names the skill in
        # full, gives the path to read if it cannot be invoked, and forbids
        # both searching the disk and improvising.
        for path in COMMANDS_DIR.glob("*.md"):
            body = " ".join(front_matter(path)[1].split())
            self.assertTrue("skill named `english-exam-coach`" in body, path.name)
            self.assertTrue("`english-exam-coach:english-exam-coach`" in body, path.name)
            self.assertTrue("${CLAUDE_PLUGIN_ROOT}/skills/english-exam-coach/SKILL.md"
                            in body, path.name)
            self.assertTrue("Do not search the disk" in body, path.name)
            self.assertTrue("do not improvise" in body, path.name)
            self.assertLess(body.index("First load the coach"),
                            body.index("Then"), path.name)
        self.assertTrue((PLUGIN_DIR / "skills" / "english-exam-coach" / "SKILL.md").is_file())

    def test_a_command_survives_an_unfilled_arguments_placeholder(self):
        # A chat surface loads a command as a skill and fills in nothing, so
        # its first line ends in the bare placeholder. The note that says so
        # must not contain the placeholder: where arguments are filled in,
        # every occurrence is.
        for path in COMMANDS_DIR.glob("*.md"):
            body = front_matter(path)[1]
            self.assertEqual(body.count("$ARGUMENTS"), 1, path.name)
            self.assertTrue(body.lstrip().splitlines()[0].endswith("$ARGUMENTS"),
                            path.name)
            self.assertTrue("bare placeholder" in " ".join(body.split()), path.name)

    def test_every_command_is_listed_in_both_readmes(self):
        for readme in (REPO_ROOT / "README.md", PLUGIN_DIR / "README.md"):
            text = readme.read_text(encoding="utf-8")
            for name in self.EXPECTED:
                self.assertTrue("/%s" % name in text, "%s lacks /%s" % (readme, name))


class SelfContainedTests(unittest.TestCase):
    def test_the_skill_never_reaches_outside_its_own_folder(self):
        for path in sorted(SKILL_DIR.rglob("*.md")):
            text = path.read_text(encoding="utf-8")
            self.assertFalse("../" in text, path.name)
        for path in SCRIPTS.glob("*.py"):
            source = path.read_text(encoding="utf-8")
            self.assertFalse("CLAUDE_PLUGIN_ROOT" in source, path.name)
            self.assertNotRegex(source, r"parent\.parent\.parent", path.name)

    def test_every_script_has_a_purpose(self):
        routed = {module for module, _d in coach_module.COMMANDS.values()}
        shared = {"coach", "state", "report_utils", "fileguard"}
        for path in SCRIPTS.glob("*.py"):
            self.assertIn(path.stem, routed | shared | {h[:-3] for h in HELPERS},
                          "%s is neither a command, a helper nor shared code" % path.name)

    def test_a_copy_of_the_skill_folder_alone_runs_and_writes_nothing_into_itself(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "skill"
            shutil.copytree(SKILL_DIR, copy, ignore=shutil.ignore_patterns("__pycache__"))
            before = sorted(str(p.relative_to(copy)) for p in copy.rglob("*"))
            home = Path(tmp) / "home"
            home.mkdir()
            env = {"HOME": str(home), "PATH": "/usr/bin:/bin"}
            tool = [sys.executable, str(copy / "scripts" / "coach.py")]

            def run(*args):
                done = subprocess.run(tool + [str(a) for a in args], capture_output=True,
                                      text=True, env=env, cwd=tmp)
                self.assertEqual(done.returncode, 0, "%s\n%s" % (args, done.stderr))
                return done.stdout

            run("log-test", "--name", "One", "--date", "2026-07-01", "--exam",
                "toefl-ibt", "--reading", "4", "--listening", "4", "--writing", "4",
                "--speaking", "4")
            run("log-error", "--category", "grammar", "--subtype", "article",
                "--point", "a before a job", "--evidence", "she is doctor",
                "--fix", "she is a doctor", "--session", "test-one-20260701")
            run("log-attempt", "--exam", "toefl-ibt", "--skill", "writing-evaluator",
                "--task-type", "toefl-write-email", "--level", "B2",
                "--band-estimate", "4.0-4.5", "--cefr-estimate", "B2", "--seconds", "420")
            run("queue", "sync")
            self.assertIn("a before a job", run("next"))
            run("report", "--scope", "all")
            run("tests")
            run("catalog")
            run("render", home / "english-exam-coach" / "reports" / "error-catalog.md")
            self.assertIn("about CEFR B2", run("convert", "--from", "toefl", "--score", "4.5"))
            self.assertIn("state ok", run("state", "validate"))
            run("state", "export", "-o", Path(tmp) / "out.zip")

            # everything landed in the home directory's progress folder…
            progress = home / "english-exam-coach"
            for name in ("tests.jsonl", "errors.jsonl", "attempts.jsonl", "queue.json",
                         "reports/error-catalog.html"):
                self.assertTrue((progress / name).is_file(), name)
            # …and the skill folder is exactly as it was copied.
            after = sorted(str(p.relative_to(copy)) for p in copy.rglob("*"))
            self.assertEqual(after, before)


class DisclosureTests(unittest.TestCase):
    """The listing must name every program the plugin can start."""

    def started_programs(self, path):
        """Program names written literally where a command line is built:
        the first element of a list passed to run(), or assigned to
        `command`."""
        names = set()
        tree = ast.parse(path.read_text(encoding="utf-8"))

        def first_literal(node):
            if isinstance(node, ast.List) and node.elts \
                    and isinstance(node.elts[0], ast.Constant) \
                    and isinstance(node.elts[0].value, str):
                names.add(node.elts[0].value)

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                called = getattr(node.func, "attr", getattr(node.func, "id", ""))
                if called == "run" and node.args:
                    first_literal(node.args[0])
            elif isinstance(node, ast.Assign) and any(
                    getattr(target, "id", "") == "command" for target in node.targets):
                first_literal(node.value)
        return names

    def test_the_helpers_declare_every_program_they_start(self):
        declared = set(speak.ENGINES) | set(speak.PLAYERS) \
            | set(transcribe.RECOGNISERS) | set(transcribe.CONVERTERS)
        for name in HELPERS:
            started = self.started_programs(SCRIPTS / name)
            self.assertLessEqual(started, declared,
                                 "%s starts %s without declaring it"
                                 % (name, sorted(started - declared)))

    def test_the_listing_names_every_program(self):
        listing = (PLUGIN_DIR / "README.md").read_text(encoding="utf-8")
        for program in speak.ENGINES + speak.PLAYERS + transcribe.RECOGNISERS \
                + transcribe.CONVERTERS:
            self.assertTrue("`%s`" % program in listing,
                            "the listing does not mention %s" % program)
        for helper in HELPERS:
            self.assertTrue(helper in listing, helper)

    def test_the_listing_says_what_matters(self):
        listing = (PLUGIN_DIR / "README.md").read_text(encoding="utf-8")
        flat = " ".join(listing.split())
        self.assertGreaterEqual(len(listing.split()), 40)
        for claim in ("no network connection", "no telemetry", "no MCP server",
                      "no hook", "standard library only", "It does not record",
                      "not affiliated", "Indicative, not official"):
            self.assertTrue(claim in flat, "the listing does not say: %s" % claim)

    def test_the_environment_is_read_for_two_settings_and_nothing_else(self):
        # The directory's scan treats a plugin that reads the environment as
        # one that may be reading a credential. So the reads are counted:
        # two optional settings, named in the listing, and never written.
        read, written = set(), []
        for path in SCRIPTS.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) \
                        and ast.unparse(node.func) in ("os.environ.get", "os.getenv"):
                    self.assertIsInstance(node.args[0], ast.Constant, path.name)
                    read.add(node.args[0].value)
                elif isinstance(node, ast.Subscript) \
                        and ast.unparse(node.value) == "os.environ":
                    written.append("%s: %s" % (path.name, ast.unparse(node)))
                elif isinstance(node, ast.Attribute) and ast.unparse(node) in (
                        "os.putenv", "os.environ.update", "os.environ.setdefault",
                        "os.environ.pop", "os.environb"):
                    written.append("%s: %s" % (path.name, ast.unparse(node)))
        self.assertEqual(read, ENVIRONMENT_VARIABLES)
        self.assertEqual(written, [])
        listing = (PLUGIN_DIR / "README.md").read_text(encoding="utf-8")
        for name in ENVIRONMENT_VARIABLES:
            self.assertTrue("`%s`" % name in listing, name)
        self.assertTrue("not credentials" in " ".join(listing.split()))

    def test_only_the_helpers_can_start_a_program(self):
        for path in SCRIPTS.glob("*.py"):
            source = path.read_text(encoding="utf-8")
            if path.name in HELPERS:
                continue
            self.assertFalse("subprocess" in source, path.name)


class PublishingTests(unittest.TestCase):
    def tracked(self):
        listing = subprocess.run(["git", "ls-files", "plugins"], cwd=str(REPO_ROOT),
                                 capture_output=True, text=True)
        if listing.returncode != 0 or not listing.stdout.strip():
            self.skipTest("not a git checkout")
        return [REPO_ROOT / line for line in listing.stdout.splitlines()]

    def test_versions_agree_everywhere(self):
        plugin = json.loads((PLUGIN_DIR / ".claude-plugin" / "plugin.json")
                            .read_text(encoding="utf-8"))
        market = json.loads((REPO_ROOT / ".claude-plugin" / "marketplace.json")
                            .read_text(encoding="utf-8"))
        version = plugin["version"]
        self.assertRegex(version, r"^\d+\.\d+\.\d+$")
        self.assertEqual(market["metadata"]["version"], version)
        self.assertTrue("version-%s-" % version in
                        (REPO_ROOT / "README.md").read_text(encoding="utf-8"),
                        "the README badge is not at %s" % version)
        changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertEqual(re.search(r"^## (\d+\.\d+\.\d+)", changelog, re.M).group(1),
                         version)

    def test_the_manifest_has_what_a_listing_needs(self):
        plugin = json.loads((PLUGIN_DIR / ".claude-plugin" / "plugin.json")
                            .read_text(encoding="utf-8"))
        self.assertEqual(plugin["name"], "english-exam-coach")
        self.assertEqual(plugin["displayName"], "English Exam Coach")
        self.assertEqual(plugin["license"], "MIT")
        self.assertTrue(40 <= len(plugin["description"]) <= 300)
        self.assertTrue((PLUGIN_DIR / "LICENSE").is_file())
        self.assertEqual((PLUGIN_DIR / "LICENSE").read_text(encoding="utf-8"),
                         (REPO_ROOT / "LICENSE").read_text(encoding="utf-8"))

    def test_the_plugin_folder_is_small_text_and_free_of_system_files(self):
        files = self.tracked()
        self.assertLess(len(files), 512)
        images = [path for path in files if path.suffix.lower() in IMAGE_SUFFIXES]
        self.assertEqual([path.name for path in images], ["icon.png"],
                         "the icon is the only binary file the plugin ships")
        for path in files:
            self.assertNotIn(path.name, (".DS_Store", "Thumbs.db", "desktop.ini"), path)
            self.assertNotIn("__MACOSX", path.parts)
            self.assertNotIn("__pycache__", path.parts)
            if path in images:
                continue
            self.assertLess(path.stat().st_size, 256 * 1024, path)
            path.read_text(encoding="utf-8")        # every other file is text

    def test_the_listing_icon_is_what_the_directory_accepts(self):
        # A square PNG, 512 to 2048 px a side, under 2 MB.
        icon = PLUGIN_DIR / ".claude-plugin" / "icon.png"
        data = icon.read_bytes()
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(data[12:16], b"IHDR")
        width, height = struct.unpack(">II", data[16:24])
        self.assertEqual(width, height)
        self.assertTrue(512 <= width <= 2048, width)
        self.assertLess(len(data), 2 * 1024 * 1024)
        self.assertEqual(data[-12:-8], b"\x00\x00\x00\x00")   # a complete file: IEND
        self.assertEqual(data[-8:-4], b"IEND")

    def test_the_icon_is_reproducible_from_its_generator(self):
        sys.path.insert(0, str(REPO_ROOT / "tools"))
        import make_icon
        self.assertEqual(make_icon.build(),
                         (PLUGIN_DIR / ".claude-plugin" / "icon.png").read_bytes(),
                         "run tools/make_icon.py and commit the result")

    def test_no_real_learner_data_is_shipped(self):
        for path in self.tracked():
            self.assertNotIn(path.suffix, (".jsonl", ".zip", ".wav", ".pdf"), path)


if __name__ == "__main__":
    unittest.main()
