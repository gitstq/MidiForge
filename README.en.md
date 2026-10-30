<div align="center">

# 🎼 MidiForge

**A zero-dependency MIDI (Standard MIDI File) toolkit for parsing, analysis, transformation and validation**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Dependencies](https://img.shields.io/badge/dependencies-0-brightgreen.svg)](https://github.com/gitstq/MidiForge/blob/main/pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Tests](https://img.shields.io/badge/tests-380%20passed-brightgreen.svg)](./tests)
[![Offline](https://img.shields.io/badge/network-not%20required-orange.svg)](#-core-features)

**🌐 Language Switcher / 語言切換：**

[简体中文](./README.md) · [繁體中文](./README.zh-TW.md) · [English](./README.en.md)

</div>

---

## 🎉 Introduction

MIDI files (`.mid`, Standard MIDI File, or **SMF**) are the universal exchange format between music production tools, game audio engines, scorewriters and hardware synths. They are compact and information-dense — and notoriously awkward to read. Variable-length quantities, running status, SMPTE timebase, multi-track tempo maps, and the fact that a note-on with velocity 0 actually means note-off: get any one of these subtly wrong and your output is silently wrong.

The pain usually shows up like this:

- 🎹 You just want the key, chord progression and velocity distribution of a song, but first you need `mido`, `pretty_midi` or `music21` — plus their transitive dependencies.
- 🐛 You have a corrupt `.mid`, your player refuses to open it, and you have no idea *which byte* is broken.
- 🔁 You need to transpose, quantize or trim a few hundred files, so you end up clicking through a DAW by hand.
- 📊 You are prototyping something in Music Information Retrieval (MIR), but the existing libraries are either too heavy, too opaque, or non-deterministic.

**MidiForge exists to remove that friction.** It is a MIDI toolkit implemented **entirely on the Python standard library**, with **no third-party dependencies**, running **fully offline**, and usable both as a **Python library** and as a **command-line tool**:

```python
import midiforge
midi = midiforge.read_file("song.mid")
print(midi.summary()["duration_seconds"])   # 8.0
```

```bash
midiforge info song.mid
```

MidiForge does not try to be a DAW. It tries to be a **sharp, reliable, embeddable** Swiss Army knife: it reads what you give it, lets you change it, tells you what is inside, and checks whether it is actually healthy.

> **Why "zero dependencies"?**
> Dependency trees in the audio/MIR world are fragile: `numpy` version conflicts, `pybind11` build failures, a missing system `libsndfile`. MidiForge only touches stdlib modules (`argparse`, `struct`, `dataclasses`, `math`, `random`, `json`, `csv`), so it installs and works in **constrained environments** — air-gapped networks, CI containers, embedded Python, classroom machines — and it will never be broken by an upstream breaking change.

---

## ✨ Core Features

### 🔍 Reading and writing: the spec, properly

| Capability | Details |
|---|---|
| 📄 Format 0 / 1 / 2 | Merged single track, synchronized multi-track, and multi-song sets |
| 🧩 MThd / MTrk chunks | Unknown chunks (`XFIH`, vendor-private) are skipped safely instead of failing |
| ⚡ Running status | Omitted status bytes are fully reconstructed |
| 🎛 Channel events | Note On/Off, Poly Aftertouch, CC, Program Change, Channel Aftertouch, Pitch Bend |
| 🏷 Meta events | Tempo, time signature, key signature, track name, lyrics, markers, SMPTE offset, … |
| 📡 SysEx | `0xF0` / `0xF7` split system-exclusive messages |
| ⏱ SMPTE timebase | Correctly restores frame rate (24/25/29/30 fps) and ticks-per-frame when division is negative |
| 🚨 Byte-offset errors | On failure you get the **offending byte offset** and a readable reason, not a bare `struct.error` |

### 🧠 Musical analysis: more than "just decoded"

- **🎯 Key detection** — Krumhansl-Kessler pitch-class profiles combined with Pearson correlation; returns key, mode and confidence (e.g. `C major (confidence 0.97)`)
- **🎸 Chord recognition** — matches simultaneous pitch sets against templates: `maj / min / dim / aug / sus4 / maj7 / min7 / dom7 / m7b5 / dim7 / add9 / 6`
- **📈 Distributions** — pitch-class histogram, velocity histogram, duration (rhythm) histogram, note density, polyphony profile, max simultaneous voices
- **🔁 Repeated-phrase detection** — finds melodic fragments that recur, with their occurrence counts
- **🎼 Instrument inventory** — GM program names per channel, plus GM drum-map naming on channel 9 (snare, bass drum, hi-hat, …)

### 🛠 Transformation and generation: built for batch work

`transpose` · `quantize` (with strength and swing) · `velocity` (scale / offset / dynamic compression) · `humanize` (seeded, reproducible) · `set_bpm` / `scale_tempo` · `trim` (auto-repairs notes crossing the boundaries) · `merge_tracks` / `split_by_channel` · `to_format` · `strip` · `clean`.

Every transform **returns a new object** by default (`inplace=False`), so your source data is never mutated behind your back.

### ✅ Structural validation: 20 rules, a real health check

Built-in rules **MF001–MF020** across three levels (`error` / `warning` / `info`): missing `end_of_track`, orphan note-off, unterminated note-on, zero-length notes, overlapping same-pitch notes, missing or invalid tempo, missing time signature, events after `end_of_track`, out-of-range velocity, zero timebase, unknown meta type …

```bash
$ midiforge validate broken.mid
MF004  error   note_off ch1 60 has no matching note_on [track=2] @1430
MF005  warning note_on ch0 72 is never closed [track=1] @960
── total 2 (error 1 / warning 1 / info 0)
```

### 🖥 Command line: 18 ready-to-use subcommands

`info` · `validate` (alias `lint`) · `notes` · `stats` (alias `analyze`) · `roll` · `diff` · `demo` · `transpose` · `quantize` · `velocity` · `humanize` · `tempo` · `trim` · `merge` · `split` · `convert` · `strip` · `clean`

> 🎁 **No MIDI files handy?** `midiforge demo -o song.mid` generates a 4-track demo song (conductor / melody / harmony / drums) so you can try everything immediately.

### 📤 Export and visualisation

- `notes_to_csv` / `notes_to_json` / `notes_to_markdown` — feed the note table straight into Excel, pandas or your docs
- `piano_roll` — an **ASCII piano roll in your terminal**; see the melodic contour without any GUI
- `diff_midi` — note-level diff between two files (added / removed / modified / unchanged + similarity %)

### 🔒 Engineering properties

| Property | Details |
|---|---|
| Zero dependencies | Standard library only; nothing is pulled in at install time |
| Offline | No network requests at runtime |
| Deterministic | Everything is a pure function except `humanize`, which takes a `seed` |
| Type-friendly | `dataclasses` + type hints throughout, ships `py.typed` |
| Well tested | 380 unit tests covering VLQ, parsing, writing, tempo, analysis, transforms, validation and the CLI |
| Cross-platform | Pure Python; identical behavior on Windows, macOS and Linux |

---

## 🚀 Quick Start

### 📦 Install

```bash
# Option 1: from PyPI (recommended)
pip install midiforge

# Option 2: from source (no network deps needed)
git clone https://github.com/gitstq/MidiForge.git
cd MidiForge
pip install .

# Option 3: no install at all — run it as a module
python -m midiforge --help
```

> **Requirements:** Python ≥ 3.8. Nothing else.

### ⚡ Up and running in 60 seconds

```bash
# 1) Generate the built-in demo song (no assets required)
midiforge demo -o song.mid

# 2) See what it looks like
midiforge info song.mid

# 3) Run a structural health check
midiforge validate song.mid

# 4) Analyse the music: key, chords, rhythm, dynamics
midiforge stats song.mid

# 5) Draw the piano roll right in your terminal
midiforge roll song.mid --width 72

# 6) Transpose up 3 semitones and save
midiforge transpose song.mid -s 3 -o song_up.mid
```

### 🐍 Minimal Python example

```python
import midiforge

midi = midiforge.read_file("song.mid")

print(midi.format, midi.division, len(midi.tracks))   # 1 480 4
print(midi.duration_seconds())                         # 8.88

notes = midiforge.extract_notes(midi)
for n in notes[:5]:
    print(n.label, n.start, n.duration, n.velocity)

# Musical analysis
print(midiforge.guess_key(notes))        # {'key': 'C', 'scale': 'major', ...}
print(midiforge.chord_progression(notes))

# Transform and write back
up = midiforge.transpose(midi, semitones=3)
midiforge.write_file(up, "song_up.mid")
```

---

## 📖 Detailed Usage Guide

### 🖥 CLI overview

```bash
midiforge --help            # top-level help
midiforge <command> --help  # per-command help
midiforge --version
```

| Command | Purpose | Common flags |
|---|---|---|
| `info` | File overview | `--json` |
| `validate` / `lint` | Structural validation | `--json`, `--strict` |
| `notes` | List notes | `--json`, `--no-drums`, `--limit N` |
| `stats` / `analyze` | Musical content analysis | `--json` |
| `roll` | ASCII piano roll | `--width N`, `--rows N` |
| `diff` | Note-level diff of two files | `--json`, `--tolerance N` |
| `demo` | Generate the built-in demo song | `--bpm`, `--bars`, `-o` |
| `transpose` | Transpose | `-s/--semitones N`, `--channels 0,1` |
| `quantize` | Quantize | `-g/--grid` (`16`, `1/16`, or ticks), `--strength`, `--swing` |
| `velocity` | Adjust velocity | `--scale`, `--offset`, `--ratio` |
| `humanize` | Humanize timing/velocity | `--tick N`, `--velocity N`, `--seed N` |
| `tempo` | Tempo operations | `--set BPM`, `--scale F`, `--stretch F` |
| `trim` | Trim to a range | `--start`, `--end` |
| `merge` | Merge all tracks into one | `-o` |
| `split` | Split by channel | `-o` |
| `convert` | Convert / export | `--format 0\|1\|2`, `--to csv\|json\|md` |
| `strip` | Remove events by category | `--sysex`, `--cc`, `--program`, `--pitch-bend`, `--aftertouch`, `--lyrics`, `--markers` |
| `clean` | Repair common corruption | `-o` |

#### Useful combinations

```bash
# Normalise a folder: 120 BPM, quantised to 16ths, velocity at 80%
for f in raw/*.mid; do
  midiforge tempo "$f" --set 120 -o "tmp1.mid" &&
  midiforge quantize tmp1.mid -g 16 -o "tmp2.mid" &&
  midiforge velocity tmp2.mid --scale 0.8 -o "out/$(basename "$f")"
done

# Export the note table for Excel / pandas
midiforge convert song.mid --to csv -o notes.csv

# Export the full structure (including the tempo map) as JSON
midiforge convert song.mid --to json -o song.json

# Cut bars 2–4 (at 480 tpq a bar is 1920 ticks)
midiforge trim song.mid --start 1920 --end 7680 -o clip.mid

# Compare an original against a hand-arranged version
midiforge diff original.mid arranged.mid
```

Exit codes: `0` success · `1` validation found errors · `2` parse/write/argument failure. Ready to use as a CI gate.

### 🐍 Python API guide

#### 1️⃣ Reading and writing

```python
from midiforge import read_file, write_file, parse, serialize

midi = read_file("song.mid")          # from disk
blob = open("song.mid", "rb").read()
midi = parse(blob)                    # from bytes

data = serialize(midi)                # → bytes
write_file(midi, "out.mid")           # to disk
```

#### 2️⃣ The file model

```python
midi.format          # 0 / 1 / 2
midi.division        # 480 means 480 tpq; negative means SMPTE
midi.is_smpte        # bool
midi.ticks_per_quarter
midi.tracks          # List[Track]
midi.all_events()    # every event, flattened and sorted by tick
midi.tempo_events()  # all tempo meta events
midi.time_signatures()
midi.end_tick
midi.duration_seconds()
midi.track_by_name("melody")
midi.summary()       # → dict, one-shot overview
```

#### 3️⃣ The event model

```python
from midiforge import ChannelEvent, MetaEvent, SysExEvent

ev = ChannelEvent(tick=0, channel=0, etype=0x9, data1=60, data2=88)
ev.status            # 0x90
ev.type_name         # 'note_on'
ev.is_note_on        # True (False when velocity is 0)
ev.is_note_off       # False (also True for "note_on with velocity 0")
ev.pitch             # 60
ev.velocity          # 88
ev.controller_name   # 'Sustain' (for CC events)
ev.pitch_bend        # -8192 … 8191 (for pitch bend events)

meta = MetaEvent(tick=0, mtype=0x51, data=b"\x07\xa1\x20")
meta.tempo           # 500000 (µs per quarter note)
meta.bpm             # 120.0

track_name = MetaEvent(tick=0, mtype=0x03, data="melody".encode())
track_name.text      # 'melody'
```

#### 4️⃣ Extracting notes

```python
from midiforge import extract_notes, max_polyphony, note_density

notes = extract_notes(midi, include_drums=False, close_unterminated=True)
n = notes[0]
n.pitch, n.label      # 60, 'C4'
n.start, n.end        # start / end tick
n.duration            # duration in ticks
n.start_sec           # start time in seconds (via the tempo map)
n.is_drum             # drum channel?
n.unterminated        # was it left open? (False once repaired)
n.to_dict()           # → dict, ready for JSON

max_polyphony(midi)   # max simultaneous voices
```

#### 5️⃣ Time axis: the tempo map

```python
from midiforge import TempoMap

tm = TempoMap.from_midi(midi)
tm.bpm_at(1920)              # BPM at a given tick
tm.tick_to_seconds(1920)     # tick → seconds (piecewise, handles tempo changes)
tm.seconds_to_tick(4.0)      # seconds → tick
tm.tick_to_mbt(1920)         # → (bar, beat, tick)
tm.to_list()                 # [(tick, µs per beat), ...]
```

> ⚠️ For anything with tempo changes (ritardando / accelerando), always convert through `TempoMap`. A single "BPM × ticks" approximation will drift.

#### 6️⃣ Musical analysis

```python
from midiforge import guess_key, chord_at, chord_progression, stats
from midiforge.analysis import pitch_class_histogram, velocity_histogram, rhythm_histogram

guess_key(notes)             # {'key': 'A', 'scale': 'minor', 'confidence': 0.93, ...}
chord_at([60, 64, 67, 71])   # 'Cmaj7'
chord_progression(notes, grid=480)
stats(midi)                  # summary dict: notes, range, density, velocity, polyphony, key, histograms…
```

#### 7️⃣ Transforms (immutable by default)

```python
from midiforge import transpose, quantize, velocity, humanize
from midiforge import set_bpm, scale_tempo, trim, merge_tracks, split_by_channel
from midiforge import to_format, strip, clean, remove_duplicate_notes

up      = transpose(midi, semitones=3, include_drums=False)
tight   = quantize(midi, grid=120, strength=0.8, swing=0.15)
soft    = velocity(midi, scale=0.8, offset=-5, ratio=0.9)
alive   = humanize(midi, tick_jitter=8, velocity_jitter=6, seed=42)  # reproducible
fast    = set_bpm(midi, 140)
clip    = trim(midi, start=1920, end=7680)      # repairs notes crossing the edges
merged  = merge_tracks(midi)
split   = split_by_channel(midi)
fmt0    = to_format(midi, 0)
lean    = strip(midi, sysex=True, cc=True, lyrics=True)
fixed   = clean(midi)                            # orphans / closures / duplicates
```

Pass `inplace=True` when you really want to mutate in place.

#### 8️⃣ Validation

```python
from midiforge import validate
from midiforge.validate import summarize, is_healthy, RULE_TITLES

issues = validate(midi, strict=False)
for it in issues:
    print(it.code, it.level, it.message, it.track, it.tick)

summarize(issues)     # {'error': 1, 'warning': 1, 'info': 0}
is_healthy(midi)      # True when there are no errors
```

Rule reference:

| Code | Meaning | Code | Meaning |
|---|---|---|---|
| MF001 | Missing end_of_track | MF011 | Missing time signature |
| MF002 | Track has no name | MF012 | Events after end_of_track |
| MF003 | Empty track | MF013 | Duplicate end_of_track |
| MF004 | Orphan note-off | MF014 | Tempo outside the first track |
| MF005 | Unterminated note-on | MF015 | File contains no notes |
| MF006 | Zero-length note | MF016 | Velocity above 127 |
| MF007 | Note-on with velocity 0 | MF017 | Invalid MIDI format value |
| MF008 | Overlapping same-pitch notes | MF018 | More than 65535 tracks |
| MF009 | Missing tempo | MF019 | Timebase (division) is 0 |
| MF010 | Invalid tempo value | MF020 | Unknown meta event type |

#### 9️⃣ Diffing

```python
from midiforge import diff_midi, diff_notes
from midiforge.diff import format_diff

report = diff_midi(before, after)
report["similarity"]     # similarity, 0.0 - 1.0
report["counts"]          # {"added": n, "removed": n, "modified": n, "unchanged": n}
report["added"]           # list of added notes (same for removed / modified)
print(format_diff(report))
```

#### 🔟 Export and visualisation

```python
from midiforge import notes_to_csv, notes_to_json, notes_to_markdown, piano_roll
from midiforge.export import midi_to_json

open("notes.csv", "w").write(notes_to_csv(notes))
print(piano_roll(notes, width=72, max_rows=24))
```

```
C4    │▏████████████████▏█████████████████▏█████████████████▏██████████████████
E4    │▏███▏█▏██████████▏████▏█▏███████████···▏██▏██············▏█▏███·········
G4    │▏███████▏█████████········▏██···············▏██···············▏██·······
      └────────────────────────────────────────────────────────────────────────
```

#### 1️⃣1️⃣ Building a MIDI file from scratch

```python
from midiforge import new_midi, Track, write_file
from midiforge.events import make_tempo
from midiforge import MetaEvent, ChannelEvent

midi = new_midi(format=1, division=480, tracks=1)
t = midi.tracks[0]
t.name = "my melody"
t.add(make_tempo(0, 120))                                      # tempo: 120 BPM
t.add(MetaEvent(tick=0, mtype=0x58, data=bytes([4, 2, 24, 8]))) # 4/4
t.add(ChannelEvent(tick=0,   channel=0, etype=0xC, data1=0))    # program 0
t.add(ChannelEvent(tick=0,   channel=0, etype=0x9, data1=60, data2=90))
t.add(ChannelEvent(tick=480, channel=0, etype=0x8, data1=60, data2=0))
t.add(MetaEvent(tick=480, mtype=0x2F, data=b""))                # end_of_track
write_file(midi, "mine.mid")
```

You can also generate one in a single line with `from_notes([(pitch, start, duration, velocity), ...])`.

### 🧪 Error handling

```python
from midiforge import MidiParseError, MidiWriteError, MidiValueError, MidiForgeError

try:
    midi = read_file("maybe_broken.mid")
except MidiParseError as exc:
    print(exc.message)   # human-readable reason
    print(exc.offset)    # offending byte offset (-1 if unknown)
```

---

## 💡 Design Notes and Roadmap

### 🏛 Layering

```
┌─────────────────────────────────────────────────────────────┐
│  CLI        cli.py (18 subcommands, argparse)                │
├─────────────────────────────────────────────────────────────┤
│  Capability analysis · transform · validate · diff · export  │
│            builder (construction)                            │
├─────────────────────────────────────────────────────────────┤
│  Semantic   notes (pairing) · tempo (timeline) · gm (tables) │
├─────────────────────────────────────────────────────────────┤
│  Model      midifile (MidiFile/Track) · events               │
├─────────────────────────────────────────────────────────────┤
│  Codec      reader (parse) · writer (serialize) · vlq        │
└─────────────────────────────────────────────────────────────┘
```

Each layer only depends on the layers below it — **no upward dependencies** — and the capability modules stay decoupled from each other (`analysis` knows `notes` and `gm`, but nothing about `cli`). Adding an analysis feature never touches the parser.

### 🎯 Key decisions

| Decision | Rationale |
|---|---|
| **Zero third-party dependencies** | Trades some raw speed (pure-Python bit twiddling) for deployment reliability and embeddability. MIDI files are usually tens of KB, so speed is a non-issue. |
| **dataclasses over bare tuples** | Event fields (`tick` / `channel` / `etype` / `data1` / `data2`) as tuples invite magic numbers everywhere. Dataclasses give readable reprs, `to_dict()`, and IDE support. |
| **Immutable by default (`inplace=False`)** | Batch audio scripts get wrecked by half-applied mutations. Returning new objects makes `a → b → c` pipelines naturally rewindable; the cost is one `deepcopy`. |
| **Corrupt files are "read + reported", not rejected** | The real world is full of truncated MIDI. Reading whatever is recoverable and then getting a health report is far more useful than `invalid file`. |
| **Determinism first** | Everything except `humanize` is a pure function, so identical input always gives identical output — which makes snapshot tests and diffs trivial. |
| **`humanize` takes a seed** | Randomness must be controllable and reproducible, otherwise it cannot be regression-tested. |
| **Standard notation for durations** | Denominators are relative to the whole note (`1/4` = quarter note), avoiding the ambiguity of beat-based naming. |
| **`end_of_track` is always last** | Serialisation forces it to the end of the track; otherwise a parser stops early and silently swallows the remaining events. |

### 🗺 Roadmap

**v1.0.0 (current)** — complete SMF read/write, note extraction, key/chord/rhythm analysis, 11 transform families, 20 validation rules, 18 CLI commands, 380 tests.

**v1.1.0 (planned)**
- 🎵 MusicXML import/export (interop with scorewriters)
- 🥁 Finer-grained drum mapping and user-defined drum maps
- 📐 Bar-line-aligned quantisation (`--align-bars`)
- 🧹 Batch directory processing and parallelism in the CLI

**v1.2.0 (planned)**
- 🎹 RMID support (MIDI with embedded resources)
- 🔊 WAV export (optional dependency; the core stays dependency-free)
- 🧬 Stylistic transforms: arpeggiator, harmony generator
- 📊 HTML visual report (built-in template, works offline)

**v2.0.0 (longer term)**
- 🤖 Simple melodic completion / continuation (statistical n-gram, still zero-dependency)
- 🌐 WebAssembly build for in-browser parsing
- 🔌 Plugin mechanism for user-registered validation rules

> Two lines we will not cross: **the core package stays dependency-free**, and **the core package stays offline**. Anything needing an external library ships as an optional extra.

---

## 📦 Packaging and Deployment

### 🧑‍💻 Local development

```bash
git clone https://github.com/gitstq/MidiForge.git
cd MidiForge

# Run the whole suite (no dependencies to install)
python -m unittest discover -s tests -t .

# Try the CLI without installing
python -m midiforge demo -o /tmp/demo.mid
python -m midiforge info /tmp/demo.mid
```

### 📦 Building distributions

```bash
# Build tooling (needed only for building)
pip install build twine

# Build sdist + wheel
python -m build

# Artifacts land in dist/
#   midiforge-1.0.0.tar.gz
#   midiforge-1.0.0-py3-none-any.whl

# Check metadata
twine check dist/*
```

Or use the bundled scripts:

```bash
bash scripts/build.sh        # build
bash scripts/release.sh      # build + check + print the upload command
```

### 🚀 Publishing to PyPI

```bash
# Upload to TestPyPI first
twine upload --repository testpypi dist/*

# Then the real thing
twine upload dist/*
```

### 🐳 Single-file / binary distribution

MidiForge is pure Python, so you can freeze it into a standalone binary if you like (**optional**; it does not affect the zero-dependency core):

```bash
pip install pyinstaller
pyinstaller --onefile --name midiforge midiforge/__main__.py
# Output: dist/midiforge (dist/midiforge.exe on Windows)
```

### 🔧 Embedding in your project

```python
# You can literally copy the midiforge/ directory into your project
from midiforge import read_file, extract_notes
```

Or declare it as a normal dependency:

```toml
# pyproject.toml
dependencies = ["midiforge>=1.0.0"]
```

### 🤖 Using it in CI

```yaml
- name: Validate all MIDI files
  run: |
    pip install midiforge
    for f in assets/**/*.mid; do midiforge validate "$f" || exit 1; done
```

`validate` exits with `1` when it finds errors, so it works directly as a pipeline gate.

### 📁 Layout

```
MidiForge/
├── midiforge/            # core package (zero dependencies)
│   ├── __init__.py       # public API surface + __version__
│   ├── __main__.py       # python -m midiforge
│   ├── cli.py            # command line (18 subcommands)
│   ├── reader.py         # SMF parsing
│   ├── writer.py         # SMF serialisation
│   ├── vlq.py            # variable-length quantity codec
│   ├── midifile.py       # MidiFile / Track model
│   ├── events.py         # event model and constant tables
│   ├── notes.py          # note pairing and polyphony analysis
│   ├── tempo.py          # TempoMap (tick ↔ seconds ↔ MBT)
│   ├── gm.py             # GM programs / drum map / note names / durations
│   ├── analysis.py       # key, chords, histograms, statistics
│   ├── transform.py      # transpose, quantize, velocity, trim, …
│   ├── validate.py       # MF001–MF020 rules
│   ├── diff.py           # note-level diff
│   ├── export.py         # CSV / JSON / Markdown / piano roll
│   ├── builder.py        # build MIDI from scratch
│   ├── errors.py         # exception hierarchy
│   └── py.typed          # PEP 561 marker
├── tests/                # 380 unit tests
├── examples/             # runnable examples
├── scripts/              # build / release scripts
├── docs/                 # supplementary docs
├── .github/workflows/    # CI
├── pyproject.toml
├── LICENSE               # MIT
├── CHANGELOG.md
└── README.md             # 简体中文 / 繁體中文 / English
```

---

## 🤝 Contributing

Contributions of every kind are welcome: 🐛 bug reports, 💡 feature ideas, 📝 documentation fixes, 🔧 code.

### 🏁 Quick workflow

```bash
# 1. Fork and clone
git clone https://github.com/<your-username>/MidiForge.git
cd MidiForge

# 2. Create a feature branch
git checkout -b feat/your-feature

# 3. Write code + tests
#    New capabilities must come with tests under tests/

# 4. Run the full local suite
python -m unittest discover -s tests -t .

# 5. Commit using the Angular convention
git commit -m "feat: add XXX capability"

# 6. Push and open a Pull Request
git push origin feat/your-feature
```

### 📜 Commit message convention (Angular)

| Prefix | Use for | Example |
|---|---|---|
| `feat:` | New feature | `feat: support RMID parsing` |
| `fix:` | Bug fix | `fix: correct SMPTE frame-rate parsing` |
| `docs:` | Documentation only | `docs: add CLI examples` |
| `refactor:` | Restructure, no behaviour change | `refactor: split _parse_track` |
| `test:` | Tests only | `test: add trim edge cases` |
| `perf:` | Performance | `perf: reuse TempoMap cache` |
| `chore:` | Build / tooling / misc | `chore: bump CI Python version` |
| `style:` | Formatting | `style: unify quote style` |

### ✅ Hard requirements for a PR

1. **Tests pass** — `python -m unittest discover -s tests -t .` is green;
2. **New code is tested** — happy path, edge cases, and error paths;
3. **Stay dependency-free** — no third-party imports inside `midiforge/` (stdlib only);
4. **Stay offline** — no network calls anywhere;
5. **Type hints** — new public functions need annotations and a docstring;
6. **Python 3.8+ compatible** — no 3.9+-only syntax (use `List[str]`, not `list[str]`);
7. **Self-review before pushing** — no `__pycache__`, virtualenvs or build artifacts (`.gitignore` covers these).

### 🐛 Reporting bugs

Please include:

- MidiForge version (`python -m midiforge --version`) and Python version;
- The full traceback (including `offset` and the message);
- A minimal MIDI file that reproduces the issue — or the output of `midiforge demo` plus the commands you ran;
- Expected behaviour vs actual behaviour.

### 💬 Code of conduct

Be kind and stay on topic. When discussing a technical approach, bring reasoning and context, not just a verdict.

---

## 📄 License

This project is released under the **MIT License** — see [LICENSE](./LICENSE).

### 📝 What you may do

- ✅ Use it freely for **personal, educational and commercial** projects;
- ✅ Modify, redistribute and sublicense it;
- ✅ Ship it as part of a closed-source product (**without open-sourcing your product**);
- ✅ Use it privately without notifying the authors.

### ⚠️ What you must do

- **Keep the copyright and permission notice** in all copies or substantial portions of the software;
- In practice: ship the full `LICENSE` text (including `Copyright (c) 2026 MidiForge Contributors`) with your distribution.

### 🚫 Disclaimer

The software is provided **"AS IS"**, **without warranty of any kind**, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose and non-infringement. In no event shall the authors or copyright holders be liable for any claim, damages or other liability arising from the use of the software.

### 🔗 Third-party notes

- MidiForge **contains and copies no third-party source code**. The implementation follows the public **Standard MIDI Files 1.0 specification** (MIDI Manufacturers Association) and public music-theory references (Krumhansl-Kessler pitch-class profiles, the General MIDI instrument table, etc.).
- There are **no runtime third-party dependencies**, so there is no transitive license-compliance burden.
- MIDI data produced by `examples/` and `tests/` is generated algorithmically by built-in routines; it contains no copyrighted musical works.

---

<div align="center">

If MidiForge helped you, consider giving it a ⭐ **Star** — and feel free to share your use case in Issues!

Made with ❤️ and zero dependencies.

[简体中文](./README.md) · [繁體中文](./README.zh-TW.md) · [English](./README.en.md)

</div>
