"""MidiForge —— 零依赖 MIDI（Standard MIDI File）处理与分析工具箱。

同时提供 **Python 库 API** 与 **命令行工具**：

>>> import midiforge
>>> midi = midiforge.read_file("song.mid")
>>> midi.summary()["duration_seconds"]
8.0

命令行等价写法::

    $ midiforge info song.mid

设计原则：**只依赖 Python 标准库**、**完全离线**、**确定性输出**。
"""

from __future__ import annotations

from .analysis import (
    chord_at,
    chord_progression,
    guess_key,
    rhythm_histogram,
    stats,
)
from .builder import demo_song, from_notes
from .diff import diff_midi, diff_notes
from .errors import (
    MidiForgeError,
    MidiParseError,
    MidiValueError,
    MidiWriteError,
)
from .events import (
    ChannelEvent,
    Event,
    MetaEvent,
    SysExEvent,
    make_tempo,
)
from .export import (
    notes_to_csv,
    notes_to_json,
    notes_to_markdown,
    piano_roll,
)
from .midifile import MidiFile, Track, new_midi
from .notes import Note, extract_notes, max_polyphony
from .reader import parse, read_file
from .tempo import TempoMap, TempoChange
from .transform import (
    clean,
    humanize,
    merge_tracks,
    quantize,
    remove_duplicate_notes,
    scale_tempo,
    scale_ticks,
    set_bpm,
    split_by_channel,
    strip,
    to_format,
    transpose,
    trim,
    velocity,
)
from .validate import validate
from .writer import serialize, write_file

__version__ = "1.0.0"
__all__ = [
    # 版本
    "__version__",
    # 模型
    "MidiFile",
    "Track",
    "new_midi",
    "Event",
    "ChannelEvent",
    "MetaEvent",
    "SysExEvent",
    "make_tempo",
    "Note",
    "TempoMap",
    "TempoChange",
    # IO
    "parse",
    "read_file",
    "serialize",
    "write_file",
    # 分析
    "extract_notes",
    "max_polyphony",
    "stats",
    "guess_key",
    "chord_at",
    "chord_progression",
    "rhythm_histogram",
    "piano_roll",
    # 变换
    "transpose",
    "quantize",
    "velocity",
    "humanize",
    "scale_ticks",
    "scale_tempo",
    "set_bpm",
    "trim",
    "merge_tracks",
    "split_by_channel",
    "to_format",
    "strip",
    "clean",
    "remove_duplicate_notes",
    # 校验 / 对比 / 导出
    "validate",
    "diff_notes",
    "diff_midi",
    "notes_to_csv",
    "notes_to_json",
    "notes_to_markdown",
    # 构建
    "demo_song",
    "from_notes",
    # 异常
    "MidiForgeError",
    "MidiParseError",
    "MidiValueError",
    "MidiWriteError",
]
