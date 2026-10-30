"""Standard MIDI File 序列化器。"""

from __future__ import annotations

from typing import Optional

from .errors import MidiWriteError
from .events import (
    META_END_OF_TRACK,
    ChannelEvent,
    Event,
    MetaEvent,
    SysExEvent,
)
from .midifile import MidiFile, Track
from .vlq import write_vlq


def serialize(midi: MidiFile, use_running_status: bool = True) -> bytes:
    """把 :class:`MidiFile` 序列化为 SMF 字节流。

    会自动为每条轨道补齐 ``end_of_track`` 元事件，并把事件按 tick 排序。

    Args:
        midi: 待写出的 MIDI 对象。
        use_running_status: 是否使用 running status 压缩（默认开启，符合规范）。

    Raises:
        MidiWriteError: 事件数据越界或轨道数超过 65535。
    """
    if len(midi.tracks) > 0xFFFF:
        raise MidiWriteError("轨道数超过 65535")

    out = bytearray()
    out += b"MThd"
    out += (6).to_bytes(4, "big")
    out += midi.format.to_bytes(2, "big")
    out += len(midi.tracks).to_bytes(2, "big")
    out += _encode_division(midi.division).to_bytes(2, "big")

    for track in midi.tracks:
        body = _serialize_track(track, use_running_status)
        out += b"MTrk"
        out += len(body).to_bytes(4, "big")
        out += body
    return bytes(out)


def write_file(midi: MidiFile, path: str, use_running_status: bool = True) -> None:
    """序列化并写入磁盘文件。"""
    data = serialize(midi, use_running_status=use_running_status)
    with open(path, "wb") as fh:
        fh.write(data)


# ---------------------------------------------------------------- 内部实现


def _encode_division(division: int) -> int:
    """把内部 division 表示还原成 MThd 的 16 位原值。"""
    if division < 0:
        # SMPTE：高字节是帧率（0xE7=-25 / 0xE8=-24 …），低位是每帧 tick 数
        raw = -division
        return 0x8000 | (raw & 0x7F00) | (raw & 0x00FF)
    return division & 0x7FFF


def _serialize_track(track: Track, use_running_status: bool) -> bytes:
    # end_of_track 必须排在轨道最末尾：否则解析器会提前结束、丢弃其后的事件
    ends = [
        e
        for e in track.events
        if isinstance(e, MetaEvent) and e.mtype == META_END_OF_TRACK
    ]
    rest = [
        e
        for e in track.events
        if not (isinstance(e, MetaEvent) and e.mtype == META_END_OF_TRACK)
    ]
    events = sorted(
        rest,
        key=lambda e: (e.tick, {"meta": 0, "sysex": 1, "channel": 2}.get(e.kind, 2)),
    )
    if ends:
        end = ends[0]
        end_tick = max(max((e.tick for e in events), default=0), end.tick)
        end = end.with_tick(end_tick) if end_tick != end.tick else end
    else:
        end_tick = max((e.tick for e in events), default=0)
        end = MetaEvent(tick=end_tick, mtype=META_END_OF_TRACK, data=b"")
    events = list(events) + [end]

    out = bytearray()
    last_tick = 0
    running_status: Optional[int] = None
    for ev in events:
        delta = ev.tick - last_tick
        if delta < 0:  # pragma: no cover - 排序后不可能出现
            raise MidiWriteError("事件 tick 出现回退: %d" % ev.tick)
        last_tick = ev.tick
        out += write_vlq(delta)

        if isinstance(ev, ChannelEvent):
            status = ev.status
            if use_running_status and status == running_status:
                pass
            else:
                out.append(status)
                running_status = status
            out.append(ev.data1 & 0x7F)
            if ev.etype not in (0xC, 0xD):
                out.append(ev.data2 & 0x7F)
        elif isinstance(ev, MetaEvent):
            out.append(0xFF)
            out.append(ev.mtype & 0x7F)
            out += write_vlq(len(ev.data))
            out += ev.data
            running_status = None
        elif isinstance(ev, SysExEvent):
            out.append(ev.stype & 0xFF)
            out += write_vlq(len(ev.data))
            out += ev.data
            running_status = None
        else:  # pragma: no cover
            raise MidiWriteError("未知事件类型: %r" % ev)
    return bytes(out)


__all__ = ["serialize", "write_file"]
