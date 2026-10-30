"""General MIDI 名称表：音色、鼓组、音高名、调性。零依赖内置数据。"""

from __future__ import annotations

from typing import List

NOTE_NAMES_SHARP: List[str] = [
    "C",
    "C#",
    "D",
    "D#",
    "E",
    "F",
    "F#",
    "G",
    "G#",
    "A",
    "A#",
    "B",
]

NOTE_NAMES_FLAT: List[str] = [
    "C",
    "Db",
    "D",
    "Eb",
    "E",
    "F",
    "Gb",
    "G",
    "Ab",
    "A",
    "Bb",
    "B",
]

#: GM1 音色表（索引 0-127 对应 program 0-127）
GM_PROGRAMS: List[str] = [
    "Acoustic Grand Piano",
    "Bright Acoustic Piano",
    "Electric Grand Piano",
    "Honky-tonk Piano",
    "Electric Piano 1",
    "Electric Piano 2",
    "Harpsichord",
    "Clavi",
    "Celesta",
    "Glockenspiel",
    "Music Box",
    "Vibraphone",
    "Marimba",
    "Xylophone",
    "Tubular Bells",
    "Dulcimer",
    "Drawbar Organ",
    "Percussive Organ",
    "Rock Organ",
    "Church Organ",
    "Reed Organ",
    "Accordion",
    "Harmonica",
    "Tango Accordion",
    "Acoustic Guitar (nylon)",
    "Acoustic Guitar (steel)",
    "Electric Guitar (jazz)",
    "Electric Guitar (clean)",
    "Electric Guitar (muted)",
    "Overdriven Guitar",
    "Distortion Guitar",
    "Guitar Harmonics",
    "Acoustic Bass",
    "Electric Bass (finger)",
    "Electric Bass (pick)",
    "Fretless Bass",
    "Slap Bass 1",
    "Slap Bass 2",
    "Synth Bass 1",
    "Synth Bass 2",
    "Violin",
    "Viola",
    "Cello",
    "Contrabass",
    "Tremolo Strings",
    "Pizzicato Strings",
    "Orchestral Harp",
    "Timpani",
    "String Ensemble 1",
    "String Ensemble 2",
    "Synth Strings 1",
    "Synth Strings 2",
    "Choir Aahs",
    "Voice Oohs",
    "Synth Voice",
    "Orchestra Hit",
    "Trumpet",
    "Trombone",
    "Tuba",
    "Muted Trumpet",
    "French Horn",
    "Brass Section",
    "Synth Brass 1",
    "Synth Brass 2",
    "Soprano Sax",
    "Alto Sax",
    "Tenor Sax",
    "Baritone Sax",
    "Oboe",
    "English Horn",
    "Bassoon",
    "Clarinet",
    "Piccolo",
    "Flute",
    "Recorder",
    "Pan Flute",
    "Blown Bottle",
    "Shakuhachi",
    "Whistle",
    "Ocarina",
    "Lead 1 (square)",
    "Lead 2 (sawtooth)",
    "Lead 3 (calliope)",
    "Lead 4 (chiff)",
    "Lead 5 (charang)",
    "Lead 6 (voice)",
    "Lead 7 (fifths)",
    "Lead 8 (bass + lead)",
    "Pad 1 (new age)",
    "Pad 2 (warm)",
    "Pad 3 (polysynth)",
    "Pad 4 (choir)",
    "Pad 5 (bowed)",
    "Pad 6 (metallic)",
    "Pad 7 (halo)",
    "Pad 8 (sweep)",
    "FX 1 (rain)",
    "FX 2 (soundtrack)",
    "FX 3 (crystal)",
    "FX 4 (atmosphere)",
    "FX 5 (brightness)",
    "FX 6 (goblins)",
    "FX 7 (echoes)",
    "FX 8 (sci-fi)",
    "Sitar",
    "Banjo",
    "Shamisen",
    "Koto",
    "Kalimba",
    "Bagpipe",
    "Fiddle",
    "Shanai",
    "Tinkle Bell",
    "Agogo",
    "Steel Drums",
    "Woodblock",
    "Taiko Drum",
    "Melodic Tom",
    "Synth Drum",
    "Reverse Cymbal",
    "Guitar Fret Noise",
    "Breath Noise",
    "Seashore",
    "Bird Tweet",
    "Telephone Ring",
    "Helicopter",
    "Applause",
    "Gunshot",
]

#: GM 打击乐键位表（仅通道 9 生效）
DRUM_MAP = {
    35: "Acoustic Bass Drum",
    36: "Bass Drum 1",
    37: "Side Stick",
    38: "Acoustic Snare",
    39: "Hand Clap",
    40: "Electric Snare",
    41: "Low Floor Tom",
    42: "Closed Hi-Hat",
    43: "High Floor Tom",
    44: "Pedal Hi-Hat",
    45: "Low Tom",
    46: "Open Hi-Hat",
    47: "Low-Mid Tom",
    48: "Hi-Mid Tom",
    49: "Crash Cymbal 1",
    50: "High Tom",
    51: "Ride Cymbal 1",
    52: "Chinese Cymbal",
    53: "Ride Bell",
    54: "Tambourine",
    55: "Splash Cymbal",
    56: "Cowbell",
    57: "Crash Cymbal 2",
    58: "Vibraslap",
    59: "Ride Cymbal 2",
    60: "Hi Bongo",
    61: "Low Bongo",
    62: "Mute Hi Conga",
    63: "Open Hi Conga",
    64: "Low Conga",
    65: "High Timbale",
    66: "Low Timbale",
    67: "High Agogo",
    68: "Low Agogo",
    69: "Cabasa",
    70: "Maracas",
    71: "Short Whistle",
    72: "Long Whistle",
    73: "Short Guiro",
    74: "Long Guiro",
    75: "Claves",
    76: "Hi Wood Block",
    77: "Low Wood Block",
    78: "Mute Cuica",
    79: "Open Cuica",
    80: "Mute Triangle",
    81: "Open Triangle",
}

#: 打击乐通道（GM 标准）
DRUM_CHANNEL = 9

#: 五度圈（升号调 / 降号调）
KEY_NAMES_SHARP = ["C", "G", "D", "A", "E", "B", "F#", "C#"]
KEY_NAMES_FLAT = ["F", "Bb", "Eb", "Ab", "Db", "Gb", "Cb"]

#: 音名对应的字母序列（用于求关系小调）
_LETTERS = ["C", "D", "E", "F", "G", "A", "B"]

#: 升号调在 ``prefer_flat`` 下的等价降号写法
_SHARP_TO_FLAT = {5: "Cb", 6: "Gb", 7: "Db"}


def fifths_of_pitch_class(pitch_class: int) -> int:
    """音级（0-11）→ 五度圈位置（-6..6）。如 C=0、G=1、F=-1。"""
    value = (pitch_class * 7) % 12
    if value > 6:
        value -= 12
    return value


def note_name(pitch: int, prefer_flat: bool = False) -> str:
    """音高（0-127）→ 科学音名，如 ``60 → C4``。"""
    names = NOTE_NAMES_FLAT if prefer_flat else NOTE_NAMES_SHARP
    return "%s%d" % (names[pitch % 12], pitch // 12 - 1)


def program_name(program: int) -> str:
    """音色编号（0-127）→ GM 音色名。"""
    if 0 <= program < len(GM_PROGRAMS):
        return GM_PROGRAMS[program]
    return "program_%d" % program


def drum_name(pitch: int) -> str:
    """打击乐通道上的键位名。"""
    return DRUM_MAP.get(pitch, "drum_%d" % pitch)


def pitch_label(pitch: int, channel: int = 0, prefer_flat: bool = False) -> str:
    """根据通道自动选择音名或鼓件名。"""
    if channel == DRUM_CHANNEL:
        return drum_name(pitch)
    return note_name(pitch, prefer_flat)


def key_name(fifths: int, minor: bool = False, prefer_flat: bool = False) -> str:
    """由调号五度圈位置得到调名，如 ``(0, True) → Am``、``(-1, True) → Dm``。

    Args:
        fifths: 调号的五度圈位置（-7..7），正数表示升号个数。
        minor: 是否为小调（取关系小调，即主音字母下移两个字母）。
        prefer_flat: 在存在等价写法时优先用降号（如 F# → Gb）。
    """
    if fifths >= 0:
        base = KEY_NAMES_SHARP[fifths % 7]
        if prefer_flat:
            base = _SHARP_TO_FLAT.get(fifths, base)
    else:
        idx = -fifths - 1
        base = KEY_NAMES_FLAT[idx] if 0 <= idx < len(KEY_NAMES_FLAT) else "C"
    if minor:
        letter = base[0]
        accidental = base[1:]
        base = _LETTERS[(_LETTERS.index(letter) - 2) % 7] + accidental
    return base + ("m" if minor else "")


def ticks_to_note_name(ticks: int, division: int) -> str:
    """把时值（tick）转成标准音符名，如 ``480/480`` → ``1/4``（四分音符）。

    时值以「拍数」为中间量：``beats = ticks / division``，全音符 = 4 拍。
    非整比时给出 ``~`` 前缀的近似值。
    """
    if ticks <= 0 or division <= 0:
        return "0"
    beats = float(ticks) / float(division)
    known = [
        (0.125, "1/32"),
        (0.25, "1/16"),
        (0.5, "1/8"),
        (1.0, "1/4"),
        (2.0, "1/2"),
        (4.0, "1/1"),
        (8.0, "2/1"),
    ]
    best = min(known, key=lambda kv: abs(kv[0] - beats))
    if abs(best[0] - beats) / best[0] < 0.12:
        return best[1]
    if beats >= 4:
        return "~%d/1" % max(1, int(round(beats / 4.0)) or 1)
    return "~1/%d" % max(1, int(round(4.0 / beats)) or 1)
