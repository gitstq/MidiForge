"""内置示例曲生成器。

用于 :command:`midiforge demo`、单元自检与文档示例——
不依赖任何外部 .mid 素材，任何环境都能一键造出可分析的样本。
"""

from __future__ import annotations

from typing import List, Sequence, Tuple

from .events import (
    META_TEMPO,
    META_TIME_SIGNATURE,
    META_TRACK_NAME,
    ChannelEvent,
    MetaEvent,
    bpm_to_tempo_bytes,
)
from .gm import DRUM_CHANNEL
from .midifile import MidiFile, Track


def demo_song(bpm: float = 108.0, division: int = 480, bars: int = 4) -> MidiFile:
    """生成一段 4/4 拍的示例曲（钢琴旋律 + 弦乐和弦 + 鼓组）。

    Args:
        bpm: 速度。
        division: 每四分音符 tick 数。
        bars: 小节数。

    Returns:
        可以直接 :func:`serialize` 的 :class:`MidiFile`。
    """
    midi = MidiFile(format=1, division=division, tracks=[])
    bar = division * 4

    # ---- 轨道 0：速度 / 拍号（指挥轨）
    conductor = Track()
    conductor.name = "conductor"
    conductor.add(MetaEvent(tick=0, mtype=META_TEMPO, data=bpm_to_tempo_bytes(bpm)))
    conductor.add(
        MetaEvent(tick=0, mtype=META_TIME_SIGNATURE, data=bytes([4, 2, 24, 8]))
    )
    midi.tracks.append(conductor)

    # ---- 轨道 1：旋律（C 大调音阶 + 琶音）
    melody = Track()
    melody.name = "melody"
    melody.add(ChannelEvent(tick=0, channel=0, etype=0xC, data1=0, data2=0))  # 钢琴
    scale = [60, 62, 64, 65, 67, 69, 71, 72]
    for i in range(bars * 8):
        pitch = scale[i % len(scale)]
        start = i * (division // 2)
        melody.add(
            ChannelEvent(tick=start, channel=0, etype=0x9, data1=pitch, data2=88)
        )
        melody.add(
            ChannelEvent(
                tick=start + division // 2 - 10, channel=0, etype=0x8, data1=pitch, data2=0
            )
        )
    midi.tracks.append(melody)

    # ---- 轨道 2：和弦（C - Am - F - G）
    chords: Sequence[Tuple[int, ...]] = ((60, 64, 67), (57, 60, 64), (53, 57, 60), (55, 59, 62))
    harmony = Track()
    harmony.name = "harmony"
    harmony.add(ChannelEvent(tick=0, channel=1, etype=0xC, data1=48, data2=0))  # 弦乐
    for bar_index in range(bars):
        chord = chords[bar_index % len(chords)]
        start = bar_index * bar
        for pitch in chord:
            harmony.add(
                ChannelEvent(tick=start, channel=1, etype=0x9, data1=pitch, data2=72)
            )
            harmony.add(
                ChannelEvent(
                    tick=start + bar - 10, channel=1, etype=0x8, data1=pitch, data2=0
                )
            )
    midi.tracks.append(harmony)

    # ---- 轨道 3：鼓组
    drums = Track()
    drums.name = "drums"
    for bar_index in range(bars):
        base = bar_index * bar
        hits: List[Tuple[int, int, int]] = [
            (0, 36, 100),          # 底鼓
            (division, 42, 70),    # 闭合镲
            (division * 2, 38, 95),  # 军鼓
            (division * 3, 42, 70),
        ]
        for offset, pitch, vel in hits:
            drums.add(
                ChannelEvent(
                    tick=base + offset, channel=DRUM_CHANNEL, etype=0x9, data1=pitch, data2=vel
                )
            )
            drums.add(
                ChannelEvent(
                    tick=base + offset + 20,
                    channel=DRUM_CHANNEL,
                    etype=0x8,
                    data1=pitch,
                    data2=0,
                )
            )
    midi.tracks.append(drums)

    for track in midi.tracks:
        track.sort()
        if not track.has_end_of_track():
            track.add(MetaEvent(tick=track.end_tick, mtype=0x2F, data=b""))
    return midi


def from_notes(
    notes: Sequence[Tuple[int, int, int, int]],
    bpm: float = 120.0,
    division: int = 480,
    channel: int = 0,
    program: int = 0,
    name: str = "track",
) -> MidiFile:
    """用 ``(pitch, start_tick, duration_tick, velocity)`` 元组快速构造单轨 MIDI。

    Args:
        notes: 音符元组列表。
        bpm: 速度。
        division: 时基。
        channel: 目标通道。
        program: 音色编号。
        name: 轨道名。

    Returns:
        单轨（Format 0 风格结构，但标记为 Format 1）的 :class:`MidiFile`。
    """
    midi = MidiFile(format=1, division=division, tracks=[])
    track = Track()
    track.name = name
    track.add(MetaEvent(tick=0, mtype=META_TEMPO, data=bpm_to_tempo_bytes(bpm)))
    track.add(ChannelEvent(tick=0, channel=channel, etype=0xC, data1=program, data2=0))
    for pitch, start, duration, vel in notes:
        track.add(
            ChannelEvent(tick=start, channel=channel, etype=0x9, data1=pitch, data2=vel)
        )
        track.add(
            ChannelEvent(
                tick=start + duration, channel=channel, etype=0x8, data1=pitch, data2=0
            )
        )
    track.sort()
    if not track.has_end_of_track():
        track.add(MetaEvent(tick=track.end_tick, mtype=0x2F, data=b""))
    midi.tracks.append(track)
    return midi


__all__ = ["demo_song", "from_notes"]
