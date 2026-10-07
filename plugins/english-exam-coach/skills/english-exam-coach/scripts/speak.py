#!/usr/bin/env python3
"""Turn a listening script into audio with the computer's own voice, and play it.

Listening and repeat-after-me tasks are only real if they are heard. This
uses the speech synthesiser that is already on the machine — `say` on macOS,
`espeak-ng` or `espeak` on Linux — so nothing is downloaded and no text
leaves the computer. If there is no synthesiser, it says so and exits with
status 3, and the coach falls back to a read-once script.

It STARTS OTHER PROGRAMS (the synthesiser and an audio player), which is why
it is a separate script and is never run through coach.py.

  speak.py check                         what would be used on this machine
  speak.py render --file script.txt      one audio file per turn; prints DIR
  speak.py play DIR                      the whole script, in order
  speak.py play DIR --item 3             one item only (heard once, no replay)
  speak.py clean DIR                     delete the audio when the drill ends

A script is plain text, one turn per line. A label before a colon names the
speaker, and each speaker gets a voice of their own:

  Woman: Hi, I'm calling about the washing machine in flat six.
  Man: Again? I thought the engineer replaced the pump last month.

Markdown quote marks and bold around the labels are ignored, so a script can
be pasted as it is written in a drill. A line with no label continues the
turn above it. For separate prompts (Listen and Choose a Response, Listen and
Repeat) put one prompt per line and play them one at a time with --item.

Rendering first and playing afterwards matters: synthesis takes a moment, and
that moment must not turn into thinking time in a task that is heard once.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

# Every program this script may start. The README lists them; a test keeps
# the two in step.
ENGINES = ("say", "espeak-ng", "espeak")
PLAYERS = ("afplay", "paplay", "aplay", "ffplay")

MANIFEST = "manifest.json"
MARKER = "english-exam-coach-audio"
DEFAULT_RATE = 160          # words per minute: a natural, unhurried exam pace
NO_ENGINE = 3

# Voices worth using, best first. Novelty voices are left out on purpose.
FEMALE_VOICES = ("Samantha", "Karen", "Moira", "Tessa", "Serena", "Kate",
                 "Allison", "Ava", "Susan", "Fiona", "Zoe", "Flo", "Sandy",
                 "Shelley", "Kathy")
MALE_VOICES = ("Daniel", "Alex", "Aaron", "Tom", "Oliver", "Rishi", "Eddy",
               "Reed", "Rocko", "Fred")
FEMALE_HINTS = ("woman", "female", "girl", "mrs", "ms", "miss", "madam", "she",
                "mother", "mum", "mom", "sister", "daughter", "aunt", "wife",
                "lady", "waitress")
MALE_HINTS = ("man", "male", "boy", "mr", "sir", "he", "father", "dad",
              "brother", "son", "uncle", "husband", "waiter")
ESPEAK_VOICES = {"female": ("en-us+f3", "en-gb+f4", "en-us+f2"),
                 "male": ("en-us+m3", "en-gb+m2", "en-us+m7")}
BEEP_SOUNDS = ("/System/Library/Sounds/Tink.aiff",
               "/usr/share/sounds/freedesktop/stereo/message.oga")

SPEAKER_WORDS = ("speaker", "narrator", "professor", "student", "teacher",
                 "lecturer", "interviewer", "examiner", "candidate", "caller",
                 "receptionist", "customer", "assistant", "manager", "trainer",
                 "supervisor", "guide", "host", "guest", "announcer", "librarian",
                 "doctor", "patient", "officer", "clerk", "agent", "tutor",
                 "presenter", "researcher", "advisor", "adviser", "a", "b")
# Words that open a sentence and are followed by a colon without being a name.
NOT_SPEAKERS = ("note", "remember", "attention", "warning", "reminder",
                "important", "example", "tip", "question", "answer", "first",
                "second", "third", "finally", "also", "today", "tomorrow", "now",
                "next", "then", "so", "well", "ok", "okay", "and", "but",
                "because", "however", "please")

LABEL = re.compile(r"^([A-Za-z][\w .'’-]{0,30}?)\s*(?:\[([^\]]+)\])?\s*:\s+(.*)$")


def find_engine():
    for name in ENGINES:
        if shutil.which(name):
            return name
    return None


def find_player():
    for name in PLAYERS:
        if shutil.which(name):
            return name
    return None


def run(command, timeout=120):
    """Run one helper program quietly. Returns (ok, error text)."""
    try:
        done = subprocess.run(command, stdout=subprocess.DEVNULL,
                              stderr=subprocess.PIPE, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    if done.returncode != 0:
        return False, done.stderr.decode("utf-8", "replace").strip()[:300]
    return True, ""


def installed_voices(engine):
    """{base name: full name} of the English voices `say` offers."""
    if engine != "say":
        return {}
    try:
        listing = subprocess.run(["say", "-v", "?"], capture_output=True,
                                 text=True, timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        return {}
    voices = {}
    for line in listing.splitlines():
        match = re.match(r"^(.+?)\s+(en[_-][A-Za-z]{2})\s+#", line)
        if not match:
            continue
        full = match.group(1).strip()
        base = full.split(" (")[0]
        # Prefer the plain or US variant when a voice exists in several.
        if base not in voices or "(US)" in full:
            voices[base] = full
    return voices


def guess_gender(label):
    words = re.findall(r"[a-z]+", label.lower())
    if any(word in FEMALE_HINTS for word in words):
        return "female"
    if any(word in MALE_HINTS for word in words):
        return "male"
    return None


def assign_voices(speakers, engine, available, chosen=None):
    """A voice for every speaker: explicit choice first, then by the label,
    then alternating, and never the same voice for two speakers if avoidable."""
    chosen = dict(chosen or {})
    pools = {"female": [], "male": []}
    if engine == "say":
        pools["female"] = [available[v] for v in FEMALE_VOICES if v in available]
        pools["male"] = [available[v] for v in MALE_VOICES if v in available]
    elif engine:
        pools = {gender: list(names) for gender, names in ESPEAK_VOICES.items()}
    used, result, turn = set(), {}, 0
    for speaker in speakers:
        if speaker in chosen:
            result[speaker] = chosen[speaker]
            used.add(chosen[speaker])
            continue
        gender = guess_gender(speaker)
        if gender is None:
            gender = ("female", "male")[turn % 2]
            turn += 1
        pool = pools[gender] or pools["female"] or pools["male"]
        voice = next((v for v in pool if v not in used), pool[0] if pool else None)
        result[speaker] = voice
        if voice:
            used.add(voice)
    return result


def clean_line(raw):
    """Strip the Markdown a drill wraps round a spoken line."""
    line = raw.strip().lstrip(">").strip()
    line = re.sub(r"^\d{1,2}[.)]\s+", "", line)                       # "3. ..."
    line = line.replace("**", "").replace("__", "")
    return re.sub(r"\*\((?:\d+ words?|\d+)\)\*\s*$", "", line).strip()    # *(9 words)*


def is_speaker(label, counts):
    """Is the text before a colon a speaker's name, or just part of a
    sentence ("Note: bring your card", "One thing: be early")?

    `counts` says how often each candidate label occurs in the script. A
    label is a speaker when it says so (Woman, Professor, Mr Lee), when it
    comes back, or when it is a single name among other labelled lines.
    """
    words = re.findall(r"[a-z]+", label.lower())
    if not words or len(label.split()) > 3 or words[0] in NOT_SPEAKERS:
        return False
    if guess_gender(label) is not None or any(w in SPEAKER_WORDS for w in words):
        return True
    if counts.get(label, 0) >= 2:
        return True
    return len(label.split()) == 1 and label[:1].isupper() and len(counts) >= 2


def parse_script(text):
    """[(speaker, wanted voice or None, words to say)], one per turn."""
    lines = [clean_line(raw) for raw in str(text).replace("\r", "").split("\n")]
    lines = [line for line in lines if line]
    matches = [LABEL.match(line) for line in lines]
    counts = {}
    for match in matches:
        if match:
            label = match.group(1).strip()
            counts[label] = counts.get(label, 0) + 1
    turns = []
    for line, match in zip(lines, matches):
        if match and is_speaker(match.group(1).strip(), counts):
            turns.append([match.group(1).strip(), match.group(2), match.group(3).strip()])
        elif turns and turns[-1][0]:
            turns[-1][2] += " " + line          # a labelled turn runs on
        else:
            turns.append(["", None, line])      # a list of separate prompts
    cleaned = []
    for speaker, voice, words in turns:
        words = re.sub(r"[*_`]+", "", words).strip()
        if words:
            cleaned.append((speaker, voice.strip() if voice else None, words))
    return cleaned


def wav_seconds(path):
    try:
        with wave.open(str(path), "rb") as audio:
            return audio.getnframes() / float(audio.getframerate() or 1)
    except (wave.Error, OSError, EOFError):
        return None


def synthesise(engine, voice, rate, words, target):
    """Write `words` to a WAV file. The text goes through a file, never the
    command line, so nothing in a script can be read as an option."""
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False,
                                     encoding="utf-8") as handle:
        handle.write(words + "\n")
        text_file = handle.name
    try:
        if engine == "say":
            command = ["say", "-r", str(rate), "-o", str(target),
                       "--data-format=LEI16@22050", "-f", text_file]
            if voice:
                command[1:1] = ["-v", voice]
        else:
            command = [engine, "-s", str(rate), "-w", str(target), "-f", text_file]
            if voice:
                command[1:1] = ["-v", voice]
        return run(command)
    finally:
        Path(text_file).unlink(missing_ok=True)


def play_file(player, path):
    if player == "ffplay":
        return run(["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(path)],
                   timeout=600)
    return run([player, str(path)], timeout=600)


def beep(player=None):
    """A short signal that it is the learner's turn. Silent if nothing can
    make one — never an error."""
    player = player or find_player()
    for sound in BEEP_SOUNDS:
        if player and Path(sound).exists() and play_file(player, sound)[0]:
            return True
    sys.stderr.write("\a")
    sys.stderr.flush()
    return False


def load_manifest(directory):
    path = Path(directory) / MANIFEST
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("marker") != MARKER or not isinstance(data.get("items"), list):
        raise ValueError("%s is not an audio folder made by this script" % directory)
    return data


def render(text, out_dir=None, rate=DEFAULT_RATE, chosen=None, one_voice=False):
    """Render every turn. Returns (manifest dict, directory). Raises
    RuntimeError when there is no synthesiser or it fails."""
    engine = find_engine()
    if not engine:
        raise RuntimeError("no speech synthesiser found (looked for %s)"
                           % ", ".join(ENGINES))
    turns = parse_script(text)
    if not turns:
        raise ValueError("the script has no lines to say")
    speakers = []
    for speaker, _voice, _words in turns:
        if speaker not in speakers:
            speakers.append(speaker)
    chosen = dict(chosen or {})
    for speaker, voice, _words in turns:
        if voice and speaker not in chosen:
            chosen[speaker] = voice
    available = installed_voices(engine)
    # A voice asked for by its short name becomes the name the engine knows.
    chosen = {speaker: available.get(voice, voice) for speaker, voice in chosen.items()}
    if one_voice:
        voices = assign_voices(speakers[:1], engine, available, chosen)
        voices = {speaker: voices[speakers[0]] for speaker in speakers}
    else:
        voices = assign_voices(speakers, engine, available, chosen)

    if out_dir:
        directory = Path(out_dir).expanduser()
        if directory.exists() and any(directory.iterdir()):
            # Only reuse a folder this script made: the files it writes have
            # fixed names, and must never land on someone else's manifest.
            try:
                load_manifest(directory)
            except (OSError, ValueError):
                raise ValueError("%s is not empty and is not an audio folder "
                                 "made by this script; choose another --out"
                                 % directory)
    else:
        directory = Path(tempfile.mkdtemp(prefix="exam-coach-audio-"))
    directory.mkdir(parents=True, exist_ok=True)
    items = []
    for number, (speaker, _voice, words) in enumerate(turns, 1):
        target = directory / ("%03d.wav" % number)
        ok, error = synthesise(engine, voices.get(speaker), rate, words, target)
        if not ok or not target.exists():
            raise RuntimeError("%s could not render item %d: %s"
                               % (engine, number, error or "no file written"))
        seconds = wav_seconds(target)
        items.append({"n": number, "speaker": speaker, "voice": voices.get(speaker),
                      "words": len(words.split()), "text": words,
                      "file": target.name,
                      "seconds": round(seconds, 2) if seconds else None})
    manifest = {"marker": MARKER, "engine": engine, "rate": rate, "items": items}
    (directory / MANIFEST).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return manifest, directory


def play(directory, first=None, last=None, gap=0.5, plays=1):
    """Play items first..last (all by default). Returns seconds of audio."""
    manifest = load_manifest(directory)
    player = find_player()
    if not player:
        raise RuntimeError("no audio player found (looked for %s)"
                           % ", ".join(PLAYERS))
    items = [i for i in manifest["items"]
             if (first is None or i["n"] >= first) and (last is None or i["n"] <= last)]
    if not items:
        raise ValueError("no such item; this folder holds items 1-%d"
                         % len(manifest["items"]))
    total = 0.0
    for round_number in range(plays):
        if round_number:
            time.sleep(max(gap, 1.5))
        for position, item in enumerate(items):
            ok, error = play_file(player, Path(directory) / item["file"])
            if not ok:
                raise RuntimeError("%s could not play %s: %s"
                                   % (player, item["file"], error))
            total += item.get("seconds") or 0
            if position < len(items) - 1:
                time.sleep(gap)
    return total


def clean(directory):
    """Delete an audio folder — but only one this script made."""
    directory = Path(directory)
    manifest = load_manifest(directory)
    removed = 0
    for item in manifest["items"]:
        target = directory / str(item.get("file"))
        if target.name == item.get("file") and target.suffix == ".wav" and target.exists():
            target.unlink()
            removed += 1
    (directory / MANIFEST).unlink(missing_ok=True)
    try:
        directory.rmdir()
    except OSError:
        pass                   # something else is in there: leave it alone
    return removed


def describe(manifest, directory):
    lines = ["audio: %s" % directory, "engine: %s at %d words a minute"
             % (manifest["engine"], manifest["rate"]), ""]
    for item in manifest["items"]:
        lines.append("  %2d  %-10s %-24s %3d words  %5.1fs"
                     % (item["n"], item["speaker"] or "-", item["voice"] or "default",
                        item["words"], item["seconds"] or 0))
    total = sum(item["seconds"] or 0 for item in manifest["items"])
    lines += ["", "%d item%s, %.0f seconds of audio."
              % (len(manifest["items"]), "" if len(manifest["items"]) == 1 else "s",
                 total)]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("check", help="say what would be used on this machine")

    make = sub.add_parser("render", help="render a script, one file per turn")
    source = make.add_mutually_exclusive_group(required=True)
    source.add_argument("--file", default=None, help="the script, or - for stdin")
    source.add_argument("--text", default=None, help="the script itself")
    make.add_argument("--out", default=None,
                      help="folder for the audio (default: a new temporary one)")
    make.add_argument("--rate", type=int, default=DEFAULT_RATE,
                      help="words per minute (default %d; about 140 is slow)"
                           % DEFAULT_RATE)
    make.add_argument("--voice", action="append", default=[], metavar="SPEAKER=VOICE",
                      help="choose a speaker's voice. Repeatable.")
    make.add_argument("--one-voice", action="store_true", dest="one_voice",
                      help="one speaker says every line (a list of prompts)")
    make.add_argument("--json", action="store_true")

    sound = sub.add_parser("play", help="play rendered audio")
    sound.add_argument("directory")
    sound.add_argument("--item", type=int, default=None, help="play this item only")
    sound.add_argument("--from", type=int, default=None, dest="first")
    sound.add_argument("--to", type=int, default=None, dest="last")
    sound.add_argument("--gap", type=float, default=0.5,
                       help="seconds of silence between turns (default 0.5)")
    sound.add_argument("--plays", type=int, default=1,
                       help="how many times to play it (the exam's number)")

    remove = sub.add_parser("clean", help="delete a rendered audio folder")
    remove.add_argument("directory")

    args = parser.parse_args(argv)

    if args.command == "check":
        engine, player = find_engine(), find_player()
        if not engine or not player:
            print("No audio here: synthesiser %s, player %s. Use a read-once "
                  "script instead." % (engine or "not found", player or "not found"))
            return NO_ENGINE
        voices = installed_voices(engine)
        women = [v for v in FEMALE_VOICES if v in voices] or list(ESPEAK_VOICES["female"])
        men = [v for v in MALE_VOICES if v in voices] or list(ESPEAK_VOICES["male"])
        print("synthesiser: %s · player: %s" % (engine, player))
        print("voices for women: %s" % ", ".join(women[:6]))
        print("voices for men: %s" % ", ".join(men[:6]))
        return 0

    try:
        if args.command == "render":
            if args.rate < 80 or args.rate > 300:
                print("error: --rate must be between 80 and 300", file=sys.stderr)
                return 2
            chosen = {}
            for pair in args.voice:
                speaker, sep, voice = pair.partition("=")
                if not sep or not speaker.strip() or not voice.strip():
                    print("error: --voice expects SPEAKER=VOICE (got %r)" % pair,
                          file=sys.stderr)
                    return 2
                chosen[speaker.strip()] = voice.strip()
            if args.text is not None:
                text = args.text.replace("\\n", "\n")
            elif args.file == "-":
                text = sys.stdin.read()
            else:
                text = Path(args.file).expanduser().read_text(encoding="utf-8")
            manifest, directory = render(text, args.out, args.rate, chosen,
                                         args.one_voice)
            if args.json:
                print(json.dumps(dict(manifest, directory=str(directory)),
                                 ensure_ascii=False, indent=1))
            else:
                print(describe(manifest, directory))
            return 0

        if args.command == "play":
            first = args.item if args.item is not None else args.first
            last = args.item if args.item is not None else args.last
            if args.plays < 1 or args.gap < 0:
                print("error: --plays must be 1 or more and --gap 0 or more",
                      file=sys.stderr)
                return 2
            seconds = play(args.directory, first, last, args.gap, args.plays)
            print("played %.0f seconds of audio" % seconds)
            return 0

        removed = clean(args.directory)
        print("deleted %d audio file%s" % (removed, "" if removed == 1 else "s"))
        return 0
    except RuntimeError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return NO_ENGINE
    except (OSError, ValueError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
