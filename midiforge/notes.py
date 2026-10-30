"""音符抽取：把「音符开 / 音符关」事件对整理成音符列表。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .events import NOTE_OFF, NOTE_ON, ChannelEvent
from .gm import DRUM_CHANNEL, pitch_label
from .tempo import TempoMap


@dataclass
class Note:
    """一个已经配好对的音符。"""

    track: int
    channel: int
    pitch: int
    velocity: int
    start: int
    end: int
    off_velocity: int = 0
    unterminated: bool = False
    tempo_map: Optional[TempoMap] = field(default=None, repr=False, compare=False)

    @property
    def duration(self) -> int:
        """时值（tick），至少为 0。"""
        return max(0, self.end - self.start)

    @property
    def start_sec(self) -> float:
        """起始时间（秒）；无 tempo map 时返回 0.0。"""
        if self.tempo_map is None:
            return 0.0
        return self.tempo_map.tick_to_seconds(self.start)

    @property
    def end_sec(self) -> float:
        """结束时间（秒）。"""
        if self.tempo_map is None:
            return 0.0
        return self.tempo_map.tick_to_seconds(self.end)

    @property
    def duration_sec(self) -> float:
        """时长（秒）。"""
        return self.end_sec - self.start_sec

    @property
    def is_drum(self) -> bool:
        """是否位于打击乐通道（9）。"""
        return self.channel == DRUM_CHANNEL

    @property
    def label(self) -> str:
        """可读音名 / 鼓件名。"""
        return pitch_label(self.pitch, self.channel)

    def to_dict(self) -> dict:
        """转成 JSON 友好字典。"""
        return {
            "track": self.track,
            "channel": self.channel,
            "pitch": self.pitch,
            "note": self.label,
            "velocity": self.velocity,
            "start_tick": self.start,
            "end_tick": self.end,
            "duration_ticks": self.duration,
            "start_sec": round(self.start_sec, 4),
            "end_sec": round(self.end_sec, 4),
            "duration_sec": round(self.duration_sec, 4),
            "drum": self.is_drum,
            "unterminated": self.unterminated,
        }

    def __str__(self) -> str:
        return "%-4s v=%-3d [%d→%d] %d ticks" % (
            self.label,
            self.velocity,
            self.start,
            self.end,
            self.duration,
        )


def extract_notes(
    midi,
    tempo_map: Optional[TempoMap] = None,
    include_drums: bool = True,
    close_unterminated: bool = True,
) -> List[Note]:
    """从 MIDI 中抽取全部音符。

    Args:
        midi: :class:`MidiFile` 对象。
        tempo_map: 用于计算秒数的时间映射；为空则只输出 tick。
        include_drums: 是否包含打击乐通道（9）的音符。
        close_unterminated: 缺失音符关时，是否在轨道末尾自动收尾。

    Returns:
        按 ``(start, track, channel, pitch)`` 排序的 :class:`Note` 列表。

    说明：
        力度为 0 的 ``note_on`` 按规范等价于 ``note_off``；
        同一（通道, 音高）多开时采用先进先出配对。
    """
    notes: List[Note] = []
    for track_index, track in enumerate(midi.tracks):
        pending: Dict[Tuple[int, int], List[ChannelEvent]] = {}
        last_tick = track.end_tick
        for ev in sorted(track.channel_events(), key=lambda e: e.tick):
            if ev.etype not in (NOTE_ON, NOTE_OFF):
                continue
            key = (ev.channel, ev.pitch)
            if ev.is_note_off:
                stack = pending.get(key)
                if stack:
                    on = stack.pop(0)
                    _emit(notes, track_index, on, ev, ev.data2, False, tempo_map)
                # 孤儿 note_off：无法配对，忽略（validate 会报告）
            else:
                pending.setdefault(key, []).append(ev)
        if close_unterminated:
            for (channel, pitch), stack in pending.items():
                for on in stack:
                    _emit(
                        notes,
                        track_index,
                        on,
                        None,
                        0,
                        True,
                        tempo_map,
                        fallback_end=last_tick,
                    )
    if not include_drums:
        notes = [n for n in notes if not n.is_drum]
    notes.sort(key=lambda n: (n.start, n.track, n.channel, n.pitch))
    return notes


def _emit(
    notes: List[Note],
    track_index: int,
    on: ChannelEvent,
    off: Optional[ChannelEvent],
    off_velocity: int,
    unterminated: bool,
    tempo_map: Optional[TempoMap],
    fallback_end: int = 0,
) -> None:
    if off is not None:
        end = off.tick
        if end < on.tick:  # 异常数据：结束早于开始
            end = on.tick
    else:
        end = max(fallback_end, on.tick)
    notes.append(
        Note(
            track=track_index,
            channel=on.channel,
            pitch=on.pitch,
            velocity=on.data2,
            start=on.tick,
            end=end,
            off_velocity=off_velocity,
            unterminated=unterminated,
            tempo_map=tempo_map,
        )
    )


def note_density(notes: List[Note], window_ticks: int, end_tick: int) -> List[int]:
    """按固定窗口统计音符密度（每窗口的音符起始数）。"""
    if window_ticks <= 0:
        raise ValueError("window_ticks 必须为正")
    buckets = [0] * (end_tick // window_ticks + 1)
    for n in notes:
        idx = n.start // window_ticks
        if idx < len(buckets):
            buckets[idx] += 1
        else:
            buckets.extend([0] * (idx - len(buckets) + 1))
            buckets[idx] += 1
    return buckets


def polyphony_profile(notes: List[Note]) -> Dict[int, int]:
    """统计同时发声数分布：``{同时发声数: 出现的采样点数}``。"""
    events: List[Tuple[int, int]] = []
    for n in notes:
        events.append((n.start, 1))
        events.append((n.end, -1))
    events.sort()
    profile: Dict[int, int] = {}
    current = 0
    for _, delta in events:
        current += delta
        current = max(0, current)
        profile[current] = profile.get(current, 0) + 1
    return profile


def max_polyphony(notes: List[Note]) -> int:
    """最大同时发声数。"""
    profile = polyphony_profile(notes)
    return max(profile) if profile else 0


__all__ = [
    "Note",
    "extract_notes",
    "note_density",
    "polyphony_profile",
    "max_polyphony",
]
