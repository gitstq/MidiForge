"""测试辅助：构造最小 MIDI 字节流与便捷断言。"""

from __future__ import annotations

import os
import tempfile

from midiforge.events import ChannelEvent, MetaEvent, SysExEvent
from midiforge.midifile import MidiFile, Track
from midiforge.writer import serialize

TMP_DIR = tempfile.mkdtemp(prefix="midiforge-tests-")


def mtrk(events: bytes) -> bytes:
    """把事件字节流包装成 MTrk 块。"""
    return b"MTrk" + len(events).to_bytes(4, "big") + events


def mthd(fmt: int = 1, ntrks: int = 1, division: int = 480) -> bytes:
    """构造 MThd 块。"""
    return (
        b"MThd"
        + (6).to_bytes(4, "big")
        + fmt.to_bytes(2, "big")
        + ntrks.to_bytes(2, "big")
        + division.to_bytes(2, "big")
    )


def simple_midi(notes=((60, 0, 240, 90), (62, 240, 240, 80)), bpm: float = 120.0,
                division: int = 480, fmt: int = 1) -> MidiFile:
    """构造一个单轨 MIDI 对象（含 tempo 与拍号）。"""
    from midiforge.events import bpm_to_tempo_bytes

    midi = MidiFile(format=fmt, division=division, tracks=[])
    track = Track()
    track.name = "test"
    track.add(MetaEvent(tick=0, mtype=0x51, data=bpm_to_tempo_bytes(bpm)))
    for pitch, start, duration, vel in notes:
        track.add(ChannelEvent(tick=start, channel=0, etype=0x9, data1=pitch, data2=vel))
        track.add(
            ChannelEvent(tick=start + duration, channel=0, etype=0x8, data1=pitch, data2=0)
        )
    track.sort()
    midi.tracks.append(track)
    return midi


def tmp_path(name: str) -> str:
    """返回一个临时文件路径。"""
    return os.path.join(TMP_DIR, name)


def write_temp(name: str, midi: MidiFile) -> str:
    """把 MIDI 写到临时目录并返回路径。"""
    path = tmp_path(name)
    with open(path, "wb") as fh:
        fh.write(serialize(midi))
    return path


__all__ = ["mtrk", "mthd", "simple_midi", "tmp_path", "write_temp", "TMP_DIR",
           "ChannelEvent", "MetaEvent", "SysExEvent"]
