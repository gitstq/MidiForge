"""MIDI 文件与轨道的数据模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, List, Optional, Sequence

from .events import (
    META_END_OF_TRACK,
    META_INSTRUMENT,
    META_TEMPO,
    META_TIME_SIGNATURE,
    META_TRACK_NAME,
    ChannelEvent,
    Event,
    MetaEvent,
    SysExEvent,
)


@dataclass
class Track:
    """一条 MIDI 轨道。

    Attributes:
        events: 事件列表（按 tick 升序维护；构造时不强制排序）。
    """

    events: List[Event] = field(default_factory=list)

    # -- 基础访问 --------------------------------------------------

    @property
    def name(self) -> str:
        """轨道名（track_name 元事件），没有则返回空串。"""
        for ev in self.events:
            if isinstance(ev, MetaEvent) and ev.mtype == META_TRACK_NAME:
                return ev.text
        return ""

    @name.setter
    def name(self, value: str) -> None:
        payload = value.encode("utf-8")
        for ev in self.events:
            if isinstance(ev, MetaEvent) and ev.mtype == META_TRACK_NAME:
                ev.data = payload
                return
        self.events.insert(
            0, MetaEvent(tick=0, mtype=META_TRACK_NAME, data=payload)
        )

    @property
    def instrument(self) -> str:
        """乐器名元事件文本。"""
        for ev in self.events:
            if isinstance(ev, MetaEvent) and ev.mtype == META_INSTRUMENT:
                return ev.text
        return ""

    def channel_events(self) -> Iterator[ChannelEvent]:
        """迭代所有通道事件。"""
        for ev in self.events:
            if isinstance(ev, ChannelEvent):
                yield ev

    def meta_events(self, mtype: Optional[int] = None) -> Iterator[MetaEvent]:
        """迭代元事件；给定 ``mtype`` 时只返回该类型。"""
        for ev in self.events:
            if isinstance(ev, MetaEvent) and (mtype is None or ev.mtype == mtype):
                yield ev

    def sysex_events(self) -> Iterator[SysExEvent]:
        """迭代 SysEx 事件。"""
        for ev in self.events:
            if isinstance(ev, SysExEvent):
                yield ev

    # -- 维护 ------------------------------------------------------

    def sort(self) -> "Track":
        """按 ``(tick, 稳定次序)`` 排序，原地修改并返回自身。

        排序键附带 ``kind`` 优先级：同一 tick 上，元事件排在最前
        （tempo / 轨道名等应优先于通道事件），保证写出后语义正确。
        """
        order = {"meta": 0, "sysex": 1, "channel": 2}
        self.events.sort(
            key=lambda e: (e.tick, order.get(getattr(e, "kind", "channel"), 2))
        )
        return self

    @property
    def end_tick(self) -> int:
        """轨道中最后一个事件的 tick（无事件时为 0）。"""
        return max((e.tick for e in self.events), default=0)

    def has_end_of_track(self) -> bool:
        """是否包含 end_of_track 元事件。"""
        return any(
            isinstance(e, MetaEvent) and e.mtype == META_END_OF_TRACK
            for e in self.events
        )

    def add(self, event: Event) -> "Track":
        """追加一个事件并返回自身（便于链式调用）。"""
        self.events.append(event)
        return self

    def __len__(self) -> int:
        return len(self.events)

    def __iter__(self) -> Iterator[Event]:
        return iter(self.events)


@dataclass
class MidiFile:
    """Standard MIDI File 内存表示。

    Attributes:
        format: 0（单轨）、1（多轨同步）、2（多轨独立）。
        division: MThd 中的 division 字段原值。
            ``>= 0`` 表示每四分音符 tick 数；``< 0`` 表示 SMPTE。
        tracks: 轨道列表。
    """

    format: int = 1
    division: int = 480
    tracks: List[Track] = field(default_factory=list)

    # -- division --------------------------------------------------

    @property
    def is_smpte(self) -> bool:
        """是否为 SMPTE 时间码时基。"""
        return self.division < 0

    @property
    def ticks_per_quarter(self) -> int:
        """每四分音符的 tick 数；SMPTE 文件时回退为 480。"""
        if self.is_smpte:
            return 480
        return self.division & 0x7FFF

    @property
    def smpte(self):
        """SMPTE 模式下返回 ``(frames_per_second, ticks_per_frame)``。"""
        if not self.is_smpte:
            raise ValueError("该 MIDI 文件不是 SMPTE 时基")
        raw = -self.division
        fps_byte = (raw >> 8) & 0xFF
        fps_map = {0xE8: 24, 0xE7: 25, 0xE3: 29.97, 0xE2: 30}
        return (fps_map.get(fps_byte, 30), raw & 0xFF)

    # -- 全局视图 --------------------------------------------------

    def all_events(self, sorted_: bool = True) -> List[Event]:
        """返回所有轨道的事件（按 tick 排序）。"""
        events: List[Event] = []
        for track in self.tracks:
            events.extend(track.events)
        if sorted_:
            order = {"meta": 0, "sysex": 1, "channel": 2}
            events.sort(
                key=lambda e: (e.tick, order.get(getattr(e, "kind", "channel"), 2))
            )
        return events

    def tempo_events(self) -> List[MetaEvent]:
        """全部 tempo 元事件，按 tick 升序。"""
        out: List[MetaEvent] = []
        for track in self.tracks:
            out.extend(track.meta_events(META_TEMPO))
        out.sort(key=lambda e: e.tick)
        return out

    def time_signatures(self) -> List[MetaEvent]:
        """全部拍号元事件，按 tick 升序。"""
        out: List[MetaEvent] = []
        for track in self.tracks:
            out.extend(track.meta_events(META_TIME_SIGNATURE))
        out.sort(key=lambda e: e.tick)
        return out

    @property
    def end_tick(self) -> int:
        """全曲最后一个事件的 tick。"""
        return max((t.end_tick for t in self.tracks), default=0)

    def duration_seconds(self, tempo_map=None) -> float:
        """全曲时长（秒）。``tempo_map`` 缺省时内部临时构造。"""
        if tempo_map is None:
            from .tempo import TempoMap

            tempo_map = TempoMap.from_midi(self)
        return tempo_map.tick_to_seconds(self.end_tick)

    def track_by_name(self, name: str) -> Optional[Track]:
        """按轨道名查找轨道（区分大小写）。"""
        for track in self.tracks:
            if track.name == name:
                return track
        return None

    def summary(self) -> dict:
        """返回概览字典，供 CLI / JSON 输出使用。"""
        from .tempo import TempoMap

        tempo_map = TempoMap.from_midi(self)
        ts = self.time_signatures()
        time_sig = "%d/%d" % ts[0].time_signature[:2] if ts else "4/4"
        channel_counts: dict = {}
        note_count = 0
        for track in self.tracks:
            for ev in track.channel_events():
                channel_counts[ev.channel] = channel_counts.get(ev.channel, 0) + 1
                if ev.etype in (0x8, 0x9):
                    note_count += 1
        return {
            "format": self.format,
            "division": self.division,
            "ticks_per_quarter": self.ticks_per_quarter,
            "smpte": (not self.is_smpte) is False,
            "tracks": len(self.tracks),
            "events": sum(len(t.events) for t in self.tracks),
            "note_events": note_count,
            "end_tick": self.end_tick,
            "duration_seconds": round(tempo_map.tick_to_seconds(self.end_tick), 3),
            "initial_bpm": round(tempo_map.initial_bpm, 2),
            "time_signature": time_sig,
            "tempo_changes": len(self.tempo_events()),
            "channels": sorted(channel_counts),
            "track_names": [t.name for t in self.tracks],
        }


def new_midi(format: int = 1, division: int = 480, tracks: int = 1) -> MidiFile:
    """创建一个空的 :class:`MidiFile`（自动补齐指定数量的空轨道）。"""
    if format not in (0, 1, 2):
        raise ValueError("MIDI 格式必须为 0 / 1 / 2: %r" % format)
    return MidiFile(
        format=format,
        division=division,
        tracks=[Track() for _ in range(max(0, tracks))],
    )


__all__ = ["Track", "MidiFile", "new_midi", "Event", "Sequence"]
