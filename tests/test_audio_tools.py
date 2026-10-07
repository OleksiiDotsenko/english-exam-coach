"""Tests for the three scripts that start other programs, and the repeat check.

speak.py, transcribe.py and timed_speak.py drive the machine's own speech
synthesiser, recogniser and audio player. The real programs are not assumed
to exist: each test puts stand-ins on PATH that record how they were called,
so what is checked is our side of the conversation — the right arguments,
text passed through files rather than the command line, a clean exit code
when the machine has no audio at all.
"""

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

from helpers import SCRIPTS, coach

sys.path.insert(0, str(SCRIPTS))
import repeat_check  # noqa: E402
import speak  # noqa: E402
import transcribe  # noqa: E402

SPEAK = SCRIPTS / "speak.py"
TRANSCRIBE = SCRIPTS / "transcribe.py"
TIMED = SCRIPTS / "timed_speak.py"

# Every stand-in appends its arguments to $STUB_LOG as one JSON line.
STUB_HEAD = '''
import json, os, sys, wave
with open(os.environ["STUB_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps([os.path.basename(sys.argv[0])[:-3]] + sys.argv[1:]) + "\\n")
args = sys.argv[1:]
def after(flag):
    return args[args.index(flag) + 1] if flag in args else None
def write_wav(path, seconds):
    with wave.open(path, "wb") as out:
        out.setnchannels(1); out.setsampwidth(2); out.setframerate(8000)
        out.writeframes(b"\\x00\\x00" * int(8000 * seconds))
'''
STUBS = {
    "say": '''
if args[:2] == ["-v", "?"]:
    print("Samantha (English (US)) en_US    # Hello")
    print("Daniel (English (UK)) en_GB    # Hello")
    print("Karen               en_AU    # Hello")
    print("Bad News            en_US    # Hello")
    print("Anna                de_DE    # Hallo")
    sys.exit(0)
if after("-o"):
    words = len(open(after("-f"), encoding="utf-8").read().split())
    write_wav(after("-o"), 0.25 * words)
''',
    "espeak-ng": '''
words = len(open(after("-f"), encoding="utf-8").read().split())
write_wav(after("-w"), 0.25 * words)
''',
    "afplay": "",
    "aplay": "",
    "ffmpeg": '''
write_wav(args[-1], 6.0)
''',
    "whisper-cli": '''
segments = json.loads(os.environ.get("STUB_SEGMENTS", "[]"))
with open(after("-of") + ".json", "w", encoding="utf-8") as out:
    json.dump({"transcription": [
        {"offsets": {"from": int(s * 1000), "to": int(e * 1000)}, "text": " " + t}
        for s, e, t in segments]}, out)
''',
}


@unittest.skipIf(os.name == "nt", "the stand-in programs are POSIX scripts")
class ToolCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.bin = self.dir / "bin"
        self.bin.mkdir()
        self.home = self.dir / "home"
        self.home.mkdir()
        self.log = self.dir / "calls.jsonl"

    def tearDown(self):
        self._tmp.cleanup()

    def install(self, *names):
        for name in names:
            body = self.bin / (name + ".py")
            body.write_text(STUB_HEAD + STUBS[name], encoding="utf-8")
            launcher = self.bin / name
            launcher.write_text('#!/bin/sh\nexec "%s" "%s" "$@"\n'
                                % (sys.executable, body), encoding="utf-8")
            launcher.chmod(launcher.stat().st_mode | stat.S_IEXEC)

    def run_tool(self, script, *args, **env):
        environment = {"PATH": str(self.bin), "HOME": str(self.home),
                       "STUB_LOG": str(self.log), "TMPDIR": str(self.dir)}
        environment.update(env)
        return subprocess.run([sys.executable, str(script)] + [str(a) for a in args],
                              capture_output=True, text=True, env=environment)

    def calls(self, program=None):
        if not self.log.exists():
            return []
        rows = [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]
        return [row for row in rows if program is None or row[0] == program]


class ScriptParsingTests(unittest.TestCase):
    def test_labels_name_speakers_and_markdown_is_ignored(self):
        turns = speak.parse_script(
            "> **Woman:** Hi, I'm calling about the machine. It\n"
            "> stopped again.\n"
            "> **Man:** Again? I thought it was fixed.\n")
        self.assertEqual(turns, [
            ("Woman", None, "Hi, I'm calling about the machine. It stopped again."),
            ("Man", None, "Again? I thought it was fixed.")])

    def test_a_list_of_prompts_is_one_item_per_line(self):
        turns = speak.parse_script(
            "1. Welcome to the campus bookshop. *(5 words)*\n"
            "2. New textbooks are on the shelves by the window. *(9)*\n")
        self.assertEqual([t[2] for t in turns],
                         ["Welcome to the campus bookshop.",
                          "New textbooks are on the shelves by the window."])
        self.assertEqual({t[0] for t in turns}, {""})

    def test_a_colon_in_a_sentence_is_not_a_speaker(self):
        turns = speak.parse_script("Attention, please. Note: the lab closes at five.\n"
                                   "Remember: bring your card.")
        self.assertEqual(len(turns), 2)
        self.assertEqual(turns[1][2], "Remember: bring your card.")
        self.assertEqual(turns[0][0], "")

    def test_two_sentences_with_colons_are_not_two_speakers(self):
        turns = speak.parse_script("One thing: the lab closes at five.\n"
                                   "Another point: bring your own gloves.")
        self.assertEqual([t[0] for t in turns], ["", ""])
        self.assertEqual(turns[0][2], "One thing: the lab closes at five.")

    def test_names_and_repeated_labels_are_speakers(self):
        turns = speak.parse_script("Anna: Are you coming?\nTom: In a minute.\n"
                                   "Anna: We will be late.")
        self.assertEqual([t[0] for t in turns], ["Anna", "Tom", "Anna"])
        turns = speak.parse_script("Front desk: Good morning.\nGuest: Hello.\n"
                                   "Front desk: Your key.")
        self.assertEqual([t[0] for t in turns], ["Front desk", "Guest", "Front desk"])

    def test_a_clock_time_is_not_a_label(self):
        turns = speak.parse_script("The bus leaves at 10:30 sharp.")
        self.assertEqual(turns, [("", None, "The bus leaves at 10:30 sharp.")])

    def test_a_single_labelled_monologue_is_still_a_speaker(self):
        turns = speak.parse_script("Professor: Today we look at canals.\nThey are old.")
        self.assertEqual(turns, [("Professor", None,
                                  "Today we look at canals. They are old.")])

    def test_a_voice_can_be_named_in_the_script(self):
        turns = speak.parse_script("Guide [Karen]: This way, please.\nGuide: Mind the step.")
        self.assertEqual(turns[0][:2], ("Guide", "Karen"))

    def test_an_empty_script_has_no_turns(self):
        self.assertEqual(speak.parse_script("\n> \n\n"), [])


class VoiceChoiceTests(unittest.TestCase):
    AVAILABLE = {"Samantha": "Samantha (English (US))", "Karen": "Karen",
                 "Daniel": "Daniel (English (UK))", "Alex": "Alex"}

    def test_labels_decide_and_two_speakers_never_share_a_voice(self):
        voices = speak.assign_voices(["Woman", "Man", "Student", "Professor"],
                                     "say", self.AVAILABLE)
        self.assertEqual(voices["Woman"], "Samantha (English (US))")
        self.assertEqual(voices["Man"], "Daniel (English (UK))")
        self.assertEqual(len(set(voices.values())), 4)

    def test_unlabelled_speakers_alternate(self):
        voices = speak.assign_voices(["Receptionist", "Caller"], "say", self.AVAILABLE)
        self.assertIn(voices["Receptionist"], ("Samantha (English (US))", "Karen"))
        self.assertIn(voices["Caller"], ("Daniel (English (UK))", "Alex"))

    def test_an_explicit_choice_wins(self):
        voices = speak.assign_voices(["Woman", "Man"], "say", self.AVAILABLE,
                                     {"Woman": "Karen"})
        self.assertEqual(voices["Woman"], "Karen")

    def test_gender_is_read_from_whole_words_only(self):
        self.assertEqual(speak.guess_gender("Woman"), "female")
        self.assertEqual(speak.guess_gender("Mr Lee"), "male")
        self.assertIsNone(speak.guess_gender("Manager"))       # not "man"
        self.assertIsNone(speak.guess_gender("Sheila"))        # not "she"

    def test_espeak_gets_its_own_voice_names(self):
        voices = speak.assign_voices(["Woman", "Man"], "espeak-ng", {})
        self.assertEqual((voices["Woman"], voices["Man"]), ("en-us+f3", "en-us+m3"))


DIALOGUE = "Woman: Is the library open today?\nMan: Only until five, I think.\n"


class SpeakTests(ToolCase):
    def render(self, text=DIALOGUE, *args):
        script = self.dir / "script.txt"
        script.write_text(text, encoding="utf-8")
        return self.run_tool(SPEAK, "render", "--file", script, "--out",
                             self.dir / "audio", *args)

    def test_no_synthesiser_is_a_clean_status_three(self):
        result = self.run_tool(SPEAK, "check")
        self.assertEqual(result.returncode, 3)
        self.assertIn("read-once", result.stdout)
        rendered = self.render()
        self.assertEqual(rendered.returncode, 3)
        self.assertNotIn("Traceback", rendered.stderr)

    def test_check_lists_real_voices_and_leaves_out_novelty_ones(self):
        self.install("say", "afplay")
        result = self.run_tool(SPEAK, "check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("synthesiser: say · player: afplay", result.stdout)
        self.assertIn("Samantha", result.stdout)
        self.assertNotIn("Bad News", result.stdout)
        self.assertNotIn("Anna", result.stdout)        # not an English voice

    def test_render_writes_one_file_per_turn_and_a_manifest(self):
        self.install("say", "afplay")
        result = self.render()
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads((self.dir / "audio" / "manifest.json").read_text())
        self.assertEqual([i["speaker"] for i in manifest["items"]], ["Woman", "Man"])
        self.assertEqual(manifest["items"][0]["voice"], "Samantha (English (US))")
        self.assertEqual(manifest["items"][1]["voice"], "Daniel (English (UK))")
        self.assertEqual(manifest["items"][0]["words"], 5)
        self.assertEqual(manifest["items"][0]["seconds"], 1.25)
        for item in manifest["items"]:
            with wave.open(str(self.dir / "audio" / item["file"])) as audio:
                self.assertGreater(audio.getnframes(), 0)
        self.assertIn("2 items", result.stdout)

    def test_the_text_never_reaches_the_command_line(self):
        self.install("say", "afplay")
        self.assertEqual(self.render("Woman: -v Zarvox --attack \"; rm -rf ~\n"
                                     "Man: Fine.\n").returncode, 0)
        for call in self.calls("say"):
            self.assertNotIn("Zarvox", " ".join(call))
            self.assertNotIn("rm -rf", " ".join(call))
            if "-o" in call:
                self.assertIn("-f", call)

    def test_rate_and_voice_options_reach_the_synthesiser(self):
        self.install("say", "afplay")
        result = self.render(DIALOGUE, "--rate", "140", "--voice", "Man=Karen")
        self.assertEqual(result.returncode, 0, result.stderr)
        renders = [c for c in self.calls("say") if "-o" in c]
        self.assertTrue(all(c[c.index("-r") + 1] == "140" for c in renders))
        self.assertEqual(renders[1][renders[1].index("-v") + 1], "Karen")

    def test_one_voice_for_a_list_of_prompts(self):
        self.install("say", "afplay")
        self.assertEqual(self.render("Welcome to the shop.\nThe till is on the left.\n",
                                     "--one-voice").returncode, 0)
        manifest = json.loads((self.dir / "audio" / "manifest.json").read_text())
        self.assertEqual(len({i["voice"] for i in manifest["items"]}), 1)

    def test_play_all_then_one_item_and_refuse_a_missing_item(self):
        self.install("say", "afplay")
        self.render()
        audio = self.dir / "audio"
        everything = self.run_tool(SPEAK, "play", audio, "--gap", "0")
        self.assertEqual(everything.returncode, 0, everything.stderr)
        self.assertEqual([Path(c[1]).name for c in self.calls("afplay")],
                         ["001.wav", "002.wav"])
        self.log.unlink()
        self.assertEqual(self.run_tool(SPEAK, "play", audio, "--item", "2").returncode, 0)
        self.assertEqual([Path(c[1]).name for c in self.calls("afplay")], ["002.wav"])
        missing = self.run_tool(SPEAK, "play", audio, "--item", "9")
        self.assertEqual(missing.returncode, 2)
        self.assertIn("items 1-2", missing.stderr)

    def test_playing_twice_for_the_exams_that_play_twice(self):
        self.install("say", "afplay")
        self.render()
        result = self.run_tool(SPEAK, "play", self.dir / "audio", "--gap", "0",
                               "--plays", "2")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.calls("afplay")), 4)

    def test_clean_removes_its_own_folder_and_nothing_else(self):
        self.install("say", "afplay")
        self.render()
        audio = self.dir / "audio"
        (audio / "keep.txt").write_text("mine", encoding="utf-8")
        result = self.run_tool(SPEAK, "clean", audio)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sorted(p.name for p in audio.iterdir()), ["keep.txt"])
        stranger = self.dir / "documents"
        stranger.mkdir()
        (stranger / "thesis.wav").write_text("x", encoding="utf-8")
        refused = self.run_tool(SPEAK, "clean", stranger)
        self.assertEqual(refused.returncode, 2)
        self.assertTrue((stranger / "thesis.wav").exists())

    def test_a_forged_manifest_cannot_delete_outside_its_folder(self):
        victim = self.dir / "victim.wav"
        victim.write_text("x", encoding="utf-8")
        folder = self.dir / "forged"
        folder.mkdir()
        (folder / "manifest.json").write_text(json.dumps(
            {"marker": speak.MARKER, "items": [{"file": "../victim.wav"}]}),
            encoding="utf-8")
        self.run_tool(SPEAK, "clean", folder)
        self.assertTrue(victim.exists())

    def test_linux_synthesiser_and_player(self):
        self.install("espeak-ng", "aplay")
        result = self.render()
        self.assertEqual(result.returncode, 0, result.stderr)
        call = self.calls("espeak-ng")[0]
        self.assertEqual(call[call.index("-v") + 1], "en-us+f3")
        self.assertIn("-w", call)
        self.assertEqual(self.run_tool(SPEAK, "play", self.dir / "audio", "--gap",
                                       "0").returncode, 0)
        self.assertEqual(len(self.calls("aplay")), 2)

    def test_an_empty_script_is_an_error(self):
        self.install("say", "afplay")
        result = self.render("\n\n")
        self.assertEqual(result.returncode, 2)

    def test_audio_is_never_rendered_into_someone_elses_folder(self):
        self.install("say", "afplay")
        project = self.dir / "webapp"
        project.mkdir()
        (project / "manifest.json").write_text('{"name": "My app"}', encoding="utf-8")
        script = self.dir / "script.txt"
        script.write_text(DIALOGUE, encoding="utf-8")
        result = self.run_tool(SPEAK, "render", "--file", script, "--out", project)
        self.assertEqual(result.returncode, 2)
        self.assertIn("choose another --out", result.stderr)
        self.assertEqual((project / "manifest.json").read_text(encoding="utf-8"),
                         '{"name": "My app"}')
        self.assertEqual([p.name for p in project.iterdir()], ["manifest.json"])

    def test_a_folder_it_made_can_be_rendered_into_again(self):
        self.install("say", "afplay")
        self.assertEqual(self.render().returncode, 0)
        self.assertEqual(self.render("Woman: Once more.\n").returncode, 0)
        manifest = json.loads((self.dir / "audio" / "manifest.json").read_text())
        self.assertEqual(len(manifest["items"]), 1)


class MeasureTests(unittest.TestCase):
    SEGMENTS = [(0.4, 3.4, "Well, I usually go to the library twice a week."),
                (5.6, 9.4, "Um, mostly I go there to study in the evenings."),
                (9.6, 12.4, "I also borrow books for my course.")]

    def test_pace_pauses_and_start_delay(self):
        result = transcribe.measure(self.SEGMENTS, duration=13.0)
        self.assertEqual(result["words"], 27)
        self.assertEqual(result["speaking_seconds"], 12.0)
        self.assertEqual(result["words_per_minute"], 135)
        self.assertEqual(result["start_delay"], 0.4)
        self.assertEqual(result["long_pauses"],
                         [{"seconds": 2.2, "after": "library twice a week."}])
        self.assertEqual(result["fillers_heard"], 1)
        self.assertTrue(result["text"].startswith("Well, I usually"))
        self.assertIn("tidies speech", result["caveat"])

    def test_silence_is_not_a_crash_and_claims_no_pace(self):
        result = transcribe.measure([], duration=4.0)
        self.assertEqual((result["words"], result["words_per_minute"]), (0, None))

    def test_a_two_second_answer_gets_no_pace_figure(self):
        result = transcribe.measure([(0.0, 2.0, "Yes I do.")])
        self.assertIsNone(result["words_per_minute"])

    def test_both_recogniser_formats_are_read(self):
        cpp = {"transcription": [{"offsets": {"from": 500, "to": 2500}, "text": " Hi there"},
                                 {"offsets": {"from": 2500, "to": 2600}, "text": "  "}]}
        self.assertEqual(transcribe.segments_from_whisper_cpp(cpp), [(0.5, 2.5, "Hi there")])
        openai = {"segments": [{"start": 0.5, "end": 2.5, "text": " Hi there"}]}
        self.assertEqual(transcribe.segments_from_openai(openai), [(0.5, 2.5, "Hi there")])


class TranscribeTests(ToolCase):
    def recording(self, name="answer.m4a"):
        path = self.dir / name
        path.write_bytes(b"not really audio")
        return path

    def model(self, name="ggml-base.en.bin", folder=".cache/whisper.cpp"):
        directory = self.home / folder
        directory.mkdir(parents=True, exist_ok=True)
        (directory / name).write_bytes(b"model")
        return directory / name

    def test_no_recogniser_is_a_clean_status_three(self):
        check = self.run_tool(TRANSCRIBE, "check")
        self.assertEqual(check.returncode, 3)
        self.assertIn("typed transcript", check.stdout)
        result = self.run_tool(TRANSCRIBE, self.recording())
        self.assertEqual(result.returncode, 3)
        self.assertNotIn("Traceback", result.stderr)

    def test_a_recogniser_without_a_model_is_also_status_three(self):
        self.install("whisper-cli")
        check = self.run_tool(TRANSCRIBE, "check")
        self.assertEqual(check.returncode, 3)
        self.assertIn("no model file", check.stdout)

    def test_the_best_model_on_disk_is_chosen(self):
        self.install("whisper-cli", "ffmpeg")
        self.model("ggml-tiny.bin")
        self.model("ggml-large-v3-turbo.bin", "Models/whisper")
        self.model("ggml-small.en.bin")
        check = self.run_tool(TRANSCRIBE, "check")
        self.assertEqual(check.returncode, 0, check.stderr)
        self.assertIn("whisper-cli with ggml-large-v3-turbo.bin", check.stdout)
        self.assertIn("converter: ffmpeg", check.stdout)

    def test_a_recording_becomes_a_transcript_with_delivery_figures(self):
        self.install("whisper-cli", "ffmpeg")
        model = self.model()
        segments = json.dumps([[0.5, 3.0, "I go to the library twice a week."],
                               [4.8, 6.0, "Mostly to study."]])
        result = self.run_tool(TRANSCRIBE, self.recording(), "--json",
                               STUB_SEGMENTS=segments)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)[0]
        self.assertEqual(data["file"], "answer.m4a")
        self.assertEqual(data["text"], "I go to the library twice a week. Mostly to study.")
        self.assertEqual(data["words"], 11)
        self.assertEqual(data["seconds"], 6.0)            # from the converted audio
        self.assertEqual(data["long_pauses"][0]["seconds"], 1.8)
        # converted first, then recognised with the model that was found
        programs = [call[0] for call in self.calls()]
        self.assertEqual(programs, ["ffmpeg", "whisper-cli"])
        recogniser = self.calls("whisper-cli")[0]
        self.assertEqual(recogniser[recogniser.index("-m") + 1], str(model))

    def test_plain_output_carries_the_caveat(self):
        self.install("whisper-cli", "ffmpeg")
        self.model()
        result = self.run_tool(TRANSCRIBE, self.recording(),
                               STUB_SEGMENTS=json.dumps([[0.0, 6.0, "One two three four."]]))
        self.assertIn("One two three four.", result.stdout)
        self.assertIn("pace: about 40 words a minute", result.stdout)
        self.assertIn("confirm it before judging accuracy", result.stdout)

    def test_nothing_is_left_behind(self):
        self.install("whisper-cli", "ffmpeg")
        self.model()
        self.run_tool(TRANSCRIBE, self.recording(),
                      STUB_SEGMENTS=json.dumps([[0.0, 1.0, "Hi."]]))
        leftovers = [p.name for p in self.dir.iterdir()
                     if p.name.startswith("exam-coach-stt-")]
        self.assertEqual(leftovers, [])

    def test_a_missing_file_is_a_usage_error(self):
        self.install("whisper-cli", "ffmpeg")
        self.model()
        result = self.run_tool(TRANSCRIBE, self.dir / "nope.wav")
        self.assertEqual(result.returncode, 2)

    def test_only_audio_recordings_are_handed_to_a_converter(self):
        self.install("whisper-cli", "ffmpeg")
        self.model()
        for name in ("playlist.m3u8", "notes.txt", "list.ffconcat", "id_rsa"):
            path = self.dir / name
            path.write_text("file '/etc/passwd'\n", encoding="utf-8")
            result = self.run_tool(TRANSCRIBE, path)
            self.assertEqual(result.returncode, 2, name)
            self.assertIn("not an audio recording", result.stderr)
        self.assertEqual(self.calls(), [])          # no program was started

    def test_the_converter_is_confined_to_local_files(self):
        self.install("whisper-cli", "ffmpeg")
        self.model()
        self.run_tool(TRANSCRIBE, self.recording(),
                      STUB_SEGMENTS=json.dumps([[0.0, 1.0, "Hi."]]))
        call = self.calls("ffmpeg")[0]
        self.assertEqual(call[call.index("-protocol_whitelist") + 1], "file")
        self.assertIn("-nostdin", call)

    def test_an_unconvertible_format_is_explained(self):
        self.install("whisper-cli")           # no converter at all
        self.model()
        result = self.run_tool(TRANSCRIBE, self.recording("answer.m4a"))
        self.assertEqual(result.returncode, 3)
        self.assertIn("install ffmpeg", result.stderr)


class RepeatCheckTests(unittest.TestCase):
    TARGET = "If the card reader stops working, restart it and try the payment again."

    def test_an_exact_repeat_ignores_capitals_and_punctuation(self):
        result = repeat_check.compare(self.TARGET, "if the card reader stops working "
                                      "restart it and try the payment again")
        self.assertTrue(result["exact"])
        self.assertEqual((result["matched"], result["words"]), (13, 13))

    def test_dropped_changed_and_added_words_are_told_apart(self):
        result = repeat_check.compare(self.TARGET, "If the card reader stop working, "
                                      "restart and try payment again please")
        self.assertFalse(result["exact"])
        self.assertEqual(result["matched"], 10)
        self.assertEqual(result["omitted"], ["it", "the"])
        self.assertEqual(result["changed"], [("stops", "stop")])
        self.assertEqual(result["added"], ["please"])
        self.assertEqual(result["accuracy"], 0.77)

    def test_numerals_from_a_recogniser_match_number_words(self):
        result = repeat_check.compare("Returns are accepted within two weeks.",
                                      "returns are accepted within 2 weeks")
        self.assertTrue(result["exact"])

    def test_contractions_are_words_of_their_own(self):
        result = repeat_check.compare("You'll need your card.", "You will need your card.")
        self.assertFalse(result["exact"])
        self.assertEqual(result["changed"], [("you'll", "you will")])

    def test_nothing_said_scores_nothing(self):
        result = repeat_check.compare(self.TARGET, "")
        self.assertEqual((result["matched"], result["accuracy"]), (0, 0.0))
        self.assertFalse(result["exact"])

    def test_the_summary_names_the_first_sentence_that_broke_down(self):
        results = [repeat_check.compare("Welcome to the shop.", "welcome to the shop"),
                   repeat_check.compare("New books are by the window.", "New books are by window"),
                   repeat_check.compare(self.TARGET, "If the card reader stops")]
        summary = repeat_check.summarise(results)
        self.assertEqual(summary["exact"], 1)
        self.assertEqual(summary["first_breakdown"], {"item": 3, "words": 13})
        self.assertEqual(summary["matched"], 4 + 5 + 5)


class RepeatCommandTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.targets = self.dir / "targets.txt"
        self.targets.write_text("Welcome to the campus bookshop.\n"
                                "New textbooks are on the shelves by the window.\n"
                                "Returns are accepted within two weeks of purchase.\n",
                                encoding="utf-8")
        self.said = self.dir / "said.txt"

    def tearDown(self):
        self._tmp.cleanup()

    def test_a_set_from_two_files_with_a_skipped_item(self):
        self.said.write_text("1. welcome to the campus bookshop\n2. -\n"
                             "3. Returns are accepted in 2 weeks of purchase\n",
                             encoding="utf-8")
        result = coach(self.dir, "repeat", "--targets", self.targets, "--said", self.said)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(" 1   5/5  words  exact", result.stdout)
        self.assertIn("nothing repeated", result.stdout)
        self.assertIn("said “in” for “within”", result.stdout)
        self.assertIn("1 of 3 repeated exactly · 12 of 22 words (55%)", result.stdout)
        self.assertIn("pronunciation is not judged", result.stdout)

    def test_targets_can_come_from_a_rendered_audio_folder(self):
        audio = self.dir / "audio"
        audio.mkdir()
        (audio / "manifest.json").write_text(json.dumps(
            {"marker": speak.MARKER,
             "items": [{"n": 1, "text": "Welcome to the campus bookshop.", "file": "001.wav"}]}),
            encoding="utf-8")
        self.said.write_text("Welcome to campus bookshop\n", encoding="utf-8")
        result = coach(self.dir, "repeat", "--audio", audio, "--said", self.said, "--json")
        data = json.loads(result.stdout)
        self.assertEqual(data["items"][0]["omitted"], ["the"])
        self.assertEqual(data["summary"]["matched"], 4)

    def test_a_single_pair_on_the_command_line(self):
        result = coach(self.dir, "repeat", "--target", "Mind the step.",
                       "--said", "Mind the step")
        self.assertIn("1 of 1 repeated exactly", result.stdout)

    def test_input_errors_are_reported_not_raised(self):
        self.said.write_text("a\nb\nc\nd\n", encoding="utf-8")
        for args in (["--targets", self.targets],
                     ["--target", "x", "--targets", self.targets, "--said", "y"],
                     ["--targets", self.targets, "--said", self.said],      # 4 for 3
                     ["--targets", self.dir / "missing.txt", "--said", self.said],
                     ["--audio", self.dir / "no-audio", "--said", self.said]):
            result = coach(self.dir, "repeat", *args)
            self.assertEqual(result.returncode, 2, args)
            self.assertNotIn("Traceback", result.stderr)


class TimedSpeakTests(ToolCase):
    def test_it_reports_the_real_clock_and_how_to_log_it(self):
        result = self.run_tool(TIMED, "--prep", "0", "--answer", "1", "--items", "2",
                               "--quiet")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--timing-source script", result.stdout)
        self.assertIn("Item 2 of 2", result.stdout)

    def test_json_goes_to_stdout_alone(self):
        result = self.run_tool(TIMED, "--task", "toefl-take-an-interview", "--exam",
                               "toefl-ibt", "--answer", "1", "--items", "1", "--json")
        data = json.loads(result.stdout)
        self.assertEqual(data["timing_source"], "script")
        self.assertEqual(data["items"], 1)
        self.assertGreaterEqual(data["answer_seconds_total"], 1.0)
        self.assertLess(data["answer_seconds_total"], 2.0)
        self.assertIn("Timed speaking", result.stderr)

    def test_known_tasks_carry_the_exam_clocks(self):
        sys.path.insert(0, str(SCRIPTS))
        import timed_speak
        self.assertEqual(timed_speak.TASK_CLOCKS["toefl-take-an-interview"],
                         {"prep": 0, "answer": 45, "items": 4})
        self.assertEqual(timed_speak.TASK_CLOCKS["toefl-listen-and-repeat"]["prep"], 0)
        self.assertEqual(timed_speak.TASK_CLOCKS["ielts-part2-long-turn"],
                         {"prep": 60, "answer": 120, "items": 1})

    def test_an_unknown_task_without_a_clock_is_an_error(self):
        result = self.run_tool(TIMED, "--task", "made-up-task")
        self.assertEqual(result.returncode, 2)
        self.assertIn("Known tasks", result.stderr)

    def test_with_audio_each_prompt_is_played_before_its_clock(self):
        self.install("say", "afplay")
        script = self.dir / "prompts.txt"
        script.write_text("Welcome to the shop.\nThe till is on the left.\n",
                          encoding="utf-8")
        audio = self.dir / "audio"
        self.assertEqual(self.run_tool(SPEAK, "render", "--file", script, "--out",
                                       audio, "--one-voice").returncode, 0)
        self.log.unlink()
        result = self.run_tool(TIMED, "--task", "toefl-listen-and-repeat", "--audio",
                               audio, "--answer", "1", "--quiet", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["items"], 2)                 # one clock per prompt
        self.assertEqual([Path(c[1]).name for c in self.calls("afplay")],
                         ["001.wav", "002.wav"])
        self.assertIn("prompt_seconds", data["items_detail"][0])

    def test_audio_from_a_folder_it_did_not_make_is_refused(self):
        self.install("afplay")
        result = self.run_tool(TIMED, "--answer", "1", "--audio", self.dir, "--quiet")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)

    def test_audio_without_a_player_is_status_three(self):
        self.install("say")
        script = self.dir / "prompts.txt"
        script.write_text("Welcome to the shop.\n", encoding="utf-8")
        self.run_tool(SPEAK, "render", "--file", script, "--out", self.dir / "audio")
        result = self.run_tool(TIMED, "--answer", "1", "--audio", self.dir / "audio",
                               "--quiet")
        self.assertEqual(result.returncode, 3)


if __name__ == "__main__":
    unittest.main()
