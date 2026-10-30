"""速度映射：tick ↔ 秒 / 拍 / 小节 的换算。"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from typing import List, Tuple

from .events import META_TEMPO, MetaEvent

DEFAULT_TEMPO_US = 500000  # 120 BPM


@dataclass(frozen=True)
class TempoChange:
    """一次速度变化。"""

    tick: int
    us_per_quarter: int

    @property
    def bpm(self) -> float:
        """每分钟四分音符数。"""
        return 60000000.0 / self.us_per_quarter


class TempoMap:
    """速度映射表。

    支持两种时基：

    * 普通时基（division >= 0）：由 tempo 元事件分段积分
    * SMPTE 时基（division < 0）：线性换算，忽略 tempo 事件
    """

    def __init__(
        self,
        changes: List[TempoChange],
        division: int,
        smpte: bool = False,
        fps: float = 30.0,
        ticks_per_frame: int = 40,
    ) -> None:
        self.changes = sorted(changes, key=lambda c: c.tick) or [
            TempoChange(0, DEFAULT_TEMPO_US)
        ]
        if self.changes[0].tick != 0:
            self.changes.insert(0, TempoChange(0, self.changes[0].us_per_quarter))
        self.division = division
        self.smpte = smpte
        self.fps = fps
        self.ticks_per_frame = ticks_per_frame
        self._ticks = [c.tick for c in self.changes]
        # 预累计：每个速度段起始的“秒”
        self._seconds: List[float] = [0.0]
        for i in range(1, len(self.changes)):
            prev = self.changes[i - 1]
            span = self.changes[i].tick - prev.tick
            self._seconds.append(
                self._seconds[i - 1] + span * prev.us_per_quarter / 1e6 / self.tpq
            )

    # -- 构造 ------------------------------------------------------

    @classmethod
    def from_midi(cls, midi) -> "TempoMap":
        """从 :class:`MidiFile` 构造速度映射。"""
        if midi.is_smpte:
            fps, tpf = midi.smpte
            return cls([], midi.division, smpte=True, fps=fps, ticks_per_frame=tpf)
        changes: List[TempoChange] = []
        for ev in midi.tempo_events():
            try:
                changes.append(TempoChange(ev.tick, ev.tempo))
            except ValueError:
                continue
        return cls(changes, midi.ticks_per_quarter)

    @classmethod
    def from_bpm(cls, bpm: float, division: int = 480) -> "TempoMap":
        """用单一 BPM 构造。"""
        us = int(round(60000000.0 / bpm))
        return cls([TempoChange(0, max(1, us))], division)

    # -- 属性 ------------------------------------------------------

    @property
    def tpq(self) -> int:
        """每四分音符 tick 数（SMPTE 模式下回退 480）。"""
        return 480 if self.smpte else (self.division & 0x7FFF)

    @property
    def initial_bpm(self) -> float:
        """起始 BPM。"""
        if self.smpte:
            return 120.0
        return self.changes[0].bpm

    def bpm_at(self, tick: int) -> float:
        """指定 tick 处的 BPM。"""
        if self.smpte:
            return self.initial_bpm
        idx = bisect_right(self._ticks, tick) - 1
        idx = max(0, min(idx, len(self.changes) - 1))
        return self.changes[idx].bpm

    # -- 换算 ------------------------------------------------------

    def tick_to_seconds(self, tick: int) -> float:
        """tick → 秒。"""
        if self.smpte:
            return tick / float(self.fps * self.ticks_per_frame)
        idx = bisect_right(self._ticks, tick) - 1
        idx = max(0, min(idx, len(self.changes) - 1))
        change = self.changes[idx]
        return self._seconds[idx] + (tick - change.tick) * change.us_per_quarter / 1e6 / self.tpq

    def seconds_to_tick(self, seconds: float) -> int:
        """秒 → tick（分段线性反解，向下取整）。"""
        if self.smpte:
            return int(round(seconds * self.fps * self.ticks_per_frame))
        if seconds <= 0:
            return 0
        for i in range(len(self.changes) - 1, -1, -1):
            if self._seconds[i] <= seconds:
                change = self.changes[i]
                per_tick = change.us_per_quarter / 1e6 / self.tpq
                return int((seconds - self._seconds[i]) / per_tick) + change.tick
        return 0

    def tick_to_beats(self, tick: int) -> float:
        """tick → 拍数（以四分音符为单位）。"""
        return tick / float(self.tpq)

    def beats_to_tick(self, beats: float) -> int:
        """拍数 → tick。"""
        return int(round(beats * self.tpq))

    def tick_to_bars(self, tick: int, beats_per_bar: float = 4.0) -> float:
        """tick → 小节数。"""
        return self.tick_to_beats(tick) / beats_per_bar

    def tick_to_mbt(self, tick: int, beats_per_bar: float = 4.0) -> Tuple[int, int, int]:
        """tick → ``(小节, 拍, tick)`` 三元组（1-based 小节与拍）。"""
        beats = self.tick_to_beats(tick)
        bar = int(beats // beats_per_bar)
        beat = int(beats % beats_per_bar)
        rem = int(round(tick - self.beats_to_tick(bar * beats_per_bar + beat)))
        return (bar + 1, beat + 1, max(0, rem))

    def to_list(self) -> List[dict]:
        """导出为字典列表（JSON 输出用）。"""
        out = []
        for c in self.changes:
            out.append(
                {
                    "tick": c.tick,
                    "bpm": round(c.bpm, 3),
                    "us_per_quarter": c.us_per_quarter,
                    "seconds": round(self.tick_to_seconds(c.tick), 3),
                }
            )
        return out

    def __len__(self) -> int:
        return len(self.changes)

    def __repr__(self) -> str:  # pragma: no cover
        return "TempoMap(changes=%d, tpq=%d, bpm=%.2f)" % (
            len(self.changes),
            self.tpq,
            self.initial_bpm,
        )


def apply_tempo_changes(midi, changes: List[Tuple[int, float]]) -> None:
    """把 ``[(tick, bpm), ...]`` 写入 MIDI（替换所有既有 tempo 事件）。"""
    for track in midi.tracks:
        track.events = [
            e
            for e in track.events
            if not (isinstance(e, MetaEvent) and e.mtype == META_TEMPO)
        ]
    if not midi.tracks:
        return
    from .events import bpm_to_tempo_bytes

    for tick, bpm in sorted(changes):
        midi.tracks[0].events.append(
            MetaEvent(tick=int(tick), mtype=META_TEMPO, data=bpm_to_tempo_bytes(bpm))
        )
    midi.tracks[0].sort()


__all__ = ["TempoMap", "TempoChange", "apply_tempo_changes", "DEFAULT_TEMPO_US"]
