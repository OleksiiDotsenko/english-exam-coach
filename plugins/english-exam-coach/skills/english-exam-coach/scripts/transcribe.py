#!/usr/bin/env python3
"""Transcribe a recorded answer on this computer, and measure how it was spoken.

A spoken answer typed up from memory keeps the ideas and loses the delivery.
If the learner has a recording — a voice memo, a file from any recorder — and
a local speech recogniser is installed, this turns it into a transcript with
real timing: how long they spoke, how fast, and where the long pauses fell.

Nothing is uploaded. It uses a recogniser that is already installed
(whisper.cpp's `whisper-cli`, or the `whisper` command) with a model file
that is already on disk, and converts the audio with `ffmpeg` or `afconvert`
if it needs to. If none of that is present it says so and exits with status 3,
and the coach asks for a typed transcript instead.

It STARTS OTHER PROGRAMS, which is why it is a separate script and is never
run through coach.py. It does not record: it only reads a file it is given.

  transcribe.py check                    what would be used on this machine
  transcribe.py answer.m4a               transcript and delivery figures
  transcribe.py a1.wav a2.wav --json     several answers at once

A machine transcript tidies speech. Recognisers drop many fillers and false
starts and quietly repair some grammar, so a transcript is good evidence of
what was said and how fast, and weak evidence of small slips such as a
missing article or a dropped ending. Show it to the learner to confirm
before judging accuracy from it.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

# Every program this script may start. The README lists them; a test keeps
# the two in step.
RECOGNISERS = ("whisper-cli", "whisper-cpp", "whisper")
CONVERTERS = ("ffmpeg", "afconvert")

NO_ENGINE = 3
LONG_PAUSE = 1.0            # seconds of silence between segments worth noting
NATIVE_FORMATS = (".wav", ".mp3", ".flac", ".ogg")
# What a recording may be. Anything else is refused before a converter sees
# it: converters will happily open playlists and other files that name
# further files or addresses to fetch.
AUDIO_FORMATS = NATIVE_FORMATS + (".m4a", ".aac", ".mp4", ".mov", ".webm", ".opus",
                                  ".oga", ".aiff", ".aif", ".caf", ".amr", ".3gp",
                                  ".wma")
MODEL_DIRS = ("~/.cache/whisper.cpp", "~/.cache/whisper", "~/Models/whisper",
              "~/models/whisper", "~/whisper.cpp/models",
              "/opt/homebrew/share/whisper-cpp", "/usr/local/share/whisper-cpp",
              "/usr/share/whisper.cpp/models")
# Larger models first: accuracy matters more than speed for a one-minute answer.
MODEL_ORDER = ("large-v3-turbo", "large-v3", "large-v2", "large", "medium.en",
               "medium", "small.en", "small", "base.en", "base", "tiny.en", "tiny")
FILLERS = ("um", "uh", "er", "erm", "hmm", "mm", "uhm", "eh")
CAVEAT = ("A machine transcript tidies speech: it drops many fillers and false "
          "starts and may repair small grammar slips. Ask the learner to "
          "confirm it before judging accuracy.")


def find_engine():
    for name in RECOGNISERS:
        if shutil.which(name):
            return name
    return None


def find_model(explicit=None):
    """A whisper.cpp model file: the one named with --model, or the best one
    found in the usual folders. Returns a Path or None."""
    if explicit:
        path = Path(explicit).expanduser()
        return path if path.is_file() else None
    found = []
    for folder in MODEL_DIRS:
        directory = Path(folder).expanduser()
        if directory.is_dir():
            found += sorted(directory.glob("ggml-*.bin"))
    for name in MODEL_ORDER:
        for path in found:
            if path.name == "ggml-%s.bin" % name:
                return path
    return found[0] if found else None


def run(command, timeout=900):
    try:
        done = subprocess.run(command, capture_output=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, "", str(exc)
    return (done.returncode == 0, done.stdout.decode("utf-8", "replace"),
            done.stderr.decode("utf-8", "replace"))


def wav_seconds(path):
    try:
        with wave.open(str(path), "rb") as audio:
            return audio.getnframes() / float(audio.getframerate() or 1)
    except (wave.Error, OSError, EOFError):
        return None


def to_wav(source, folder):
    """A 16 kHz mono WAV copy of the recording, or None if nothing here can
    convert it. Recognisers are trained on that format."""
    target = Path(folder) / "audio.wav"
    if shutil.which("ffmpeg"):
        # Local files only: a recording has no business naming an address.
        ok, _out, _err = run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error",
                              "-protocol_whitelist", "file",
                              "-i", str(source), "-vn", "-ar", "16000", "-ac", "1",
                              "-c:a", "pcm_s16le", str(target)])
        if ok and target.exists():
            return target
    if shutil.which("afconvert"):
        ok, _out, _err = run(["afconvert", "-f", "WAVE", "-d", "LEI16@16000",
                              "-c", "1", str(source), str(target)])
        if ok and target.exists():
            return target
    return None


def segments_from_whisper_cpp(data):
    """[(start s, end s, text)] from whisper.cpp's JSON."""
    segments = []
    for row in data.get("transcription") or []:
        offsets = row.get("offsets") or {}
        text = str(row.get("text") or "").strip()
        if text:
            segments.append((float(offsets.get("from", 0)) / 1000.0,
                             float(offsets.get("to", 0)) / 1000.0, text))
    return segments


def segments_from_openai(data):
    return [(float(s.get("start", 0)), float(s.get("end", 0)),
             str(s.get("text") or "").strip())
            for s in data.get("segments") or [] if str(s.get("text") or "").strip()]


def recognise(engine, model, audio, language, folder):
    """Run the recogniser. Returns segments. Raises RuntimeError."""
    prefix = Path(folder) / "out"
    if engine in ("whisper-cli", "whisper-cpp"):
        ok, _out, err = run([engine, "-m", str(model), "-f", str(audio),
                             "-l", language, "-oj", "-of", str(prefix), "-np"])
        result = Path(str(prefix) + ".json")
        if not ok or not result.exists():
            raise RuntimeError("%s failed: %s" % (engine, err.strip()[-300:] or "no output"))
        return segments_from_whisper_cpp(
            json.loads(result.read_text(encoding="utf-8", errors="replace")))
    ok, _out, err = run([engine, str(audio), "--language", language,
                         "--output_format", "json", "--output_dir", str(folder)])
    results = sorted(Path(folder).glob("*.json"))
    if not ok or not results:
        raise RuntimeError("%s failed: %s" % (engine, err.strip()[-300:] or "no output"))
    return segments_from_openai(json.loads(results[0].read_text(encoding="utf-8")))


def measure(segments, duration=None):
    """Delivery figures from timed segments: the part a typed transcript loses."""
    text = " ".join(part for _start, _end, part in segments)
    text = re.sub(r"\s+", " ", text).strip()
    words = re.findall(r"[A-Za-z0-9']+", text)
    if not segments:
        return {"text": "", "words": 0, "seconds": round(duration or 0, 1),
                "speaking_seconds": 0, "words_per_minute": None,
                "long_pauses": [], "fillers_heard": 0, "caveat": CAVEAT}
    first, last = segments[0][0], segments[-1][1]
    speaking = max(0.0, last - first)
    pauses = []
    for (_s0, end, before), (start, _e1, _after) in zip(segments, segments[1:]):
        if start - end >= LONG_PAUSE:
            pauses.append({"seconds": round(start - end, 1),
                           "after": " ".join(before.split()[-4:])})
    fillers = sum(1 for word in words if word.lower() in FILLERS)
    return {
        "text": text,
        "words": len(words),
        "seconds": round(duration if duration else last, 1),
        "speaking_seconds": round(speaking, 1),
        "start_delay": round(first, 1),
        "words_per_minute": round(len(words) / speaking * 60) if speaking >= 3 else None,
        "long_pauses": pauses,
        "fillers_heard": fillers,
        "caveat": CAVEAT,
    }


def transcribe(source, engine, model, language="en"):
    source = Path(source).expanduser()
    if not source.is_file():
        raise ValueError("no such file: %s" % source)
    if source.suffix.lower() not in AUDIO_FORMATS \
            or source.resolve().suffix.lower() not in AUDIO_FORMATS:
        raise ValueError("%s is not an audio recording this script reads (%s)"
                         % (source.name, ", ".join(AUDIO_FORMATS)))
    with tempfile.TemporaryDirectory(prefix="exam-coach-stt-") as folder:
        audio = to_wav(source, folder)
        if audio is None:
            if source.suffix.lower() not in NATIVE_FORMATS:
                raise RuntimeError("cannot convert %s: install ffmpeg, or give a "
                                   "wav, mp3, flac or ogg file" % source.suffix)
            audio = source
        segments = recognise(engine, model, audio, language, folder)
        result = measure(segments, wav_seconds(audio))
    result["file"] = source.name
    return result


def render(result):
    lines = ["%s — %s words in %ss" % (result["file"], result["words"],
                                       result["seconds"]), "", result["text"] or
             "(no speech recognised)", ""]
    if result["words_per_minute"]:
        lines.append("pace: about %d words a minute over %ss of speaking"
                     % (result["words_per_minute"], result["speaking_seconds"]))
    if result.get("start_delay", 0) >= 1.5:
        lines.append("started speaking after %ss" % result["start_delay"])
    if result["long_pauses"]:
        lines.append("long pauses: " + "; ".join(
            "%ss after “…%s”" % (p["seconds"], p["after"])
            for p in result["long_pauses"]))
    else:
        lines.append("no pause of %.0f second or more between phrases" % LONG_PAUSE)
    lines += ["", "note: %s" % CAVEAT]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("files", nargs="+",
                        help="recordings to transcribe, or the word `check`")
    parser.add_argument("--model", default=None,
                        help="a whisper.cpp model file (default: the best "
                             "one found on this machine)")
    parser.add_argument("--language", default="en")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    engine = find_engine()
    needs_model = engine in ("whisper-cli", "whisper-cpp")
    model = find_model(args.model) if needs_model else None

    if args.files == ["check"]:
        if not engine:
            print("No speech recogniser here (looked for %s). Ask for a typed "
                  "transcript." % ", ".join(RECOGNISERS))
            return NO_ENGINE
        if needs_model and not model:
            print("%s is installed but no model file was found. Pass --model "
                  "<file>. Ask for a typed transcript." % engine)
            return NO_ENGINE
        converter = "ffmpeg" if shutil.which("ffmpeg") else \
            "afconvert" if shutil.which("afconvert") else "none (wav/mp3/flac/ogg only)"
        print("recogniser: %s%s · converter: %s"
              % (engine, " with %s" % model.name if model else "", converter))
        return 0

    if not engine or (needs_model and not model):
        print("error: no usable speech recogniser on this machine (run "
              "`transcribe.py check`). Ask for a typed transcript.", file=sys.stderr)
        return NO_ENGINE

    results = []
    for name in args.files:
        try:
            results.append(transcribe(name, engine, model, args.language))
        except ValueError as exc:
            print("error: %s" % exc, file=sys.stderr)
            return 2
        except (RuntimeError, OSError) as exc:
            print("error: %s" % exc, file=sys.stderr)
            return NO_ENGINE
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=1))
    else:
        print("\n\n".join(render(result) for result in results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
