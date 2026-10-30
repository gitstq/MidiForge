"""Standard MIDI File 解析器（零依赖，纯标准库）。

支持：

* Format 0 / 1 / 2
* MThd / MTrk 块，未知块（如 ``XFIH``）安全跳过
* running status（省略状态字节）
* 元事件、SysEx（0xF0 / 0xF7 分段）
* SMPTE 时基（division 为负）
* 损坏文件的偏移级报错
"""

from __future__ import annotations

from typing import Tuple

from .errors import MidiParseError
from .events import (
    META_END_OF_TRACK,
    ChannelEvent,
    Event,
    MetaEvent,
    SysExEvent,
)
from .midifile import MidiFile, Track
from .vlq import read_vlq


def parse(data: bytes) -> MidiFile:
    """把 MIDI 字节流解析为 :class:`MidiFile`。

    Raises:
        MidiParseError: 不是合法 MIDI 文件或结构损坏。
    """
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("data 必须是 bytes")
    data = bytes(data)
    if len(data) < 14:
        raise MidiParseError("文件过短，不是合法 MIDI 文件", 0)
    if data[:4] != b"MThd":
        raise MidiParseError("缺少 MThd 块头（魔数不是 'MThd'）", 0)

    pos = 4
    header_len = _read_u32(data, pos)
    pos += 4
    if header_len < 6:
        raise MidiParseError("MThd 长度非法: %d" % header_len, pos)
    fmt = _read_u16(data, pos)
    pos += 2
    ntrks = _read_u16(data, pos)
    pos += 2
    raw_division = _read_u16(data, pos)
    pos += 2
    # 其余 header 字节（扩展头部）跳过
    pos += header_len - 6

    division = _interpret_division(raw_division)
    midi = MidiFile(format=fmt, division=division, tracks=[])

    tracks_read = 0
    while pos < len(data):
        remaining = len(data) - pos
        if remaining < 8:
            # 尾部残余不足一个块头：可能是填充字节，直接忽略
            break
        chunk_id = data[pos : pos + 4]
        chunk_len = _read_u32(data, pos + 4)
        body_start = pos + 8
        body_end = body_start + chunk_len
        if body_end > len(data):
            raise MidiParseError(
                "块 %r 声明长度 %d 超出文件末尾" % (chunk_id, chunk_len), pos
            )
        if chunk_id == b"MTrk":
            track = _parse_track(data[body_start:body_end], body_start)
            midi.tracks.append(track)
            tracks_read += 1
        # 非 MTrk 块（XFIH、未知厂商块）跳过
        pos = body_end

    if ntrks and tracks_read != ntrks:
        # 声明数与实读数不一致时以实际为准，交由 validate 报告
        pass
    if not midi.tracks:
        raise MidiParseError("文件中没有找到任何 MTrk 轨道", 0)
    return midi


def read_file(path: str) -> MidiFile:
    """从磁盘读取 MIDI 文件。"""
    with open(path, "rb") as fh:
        return parse(fh.read())


# ---------------------------------------------------------------- 内部实现


def _read_u16(data: bytes, pos: int) -> int:
    if pos + 2 > len(data):
        raise MidiParseError("读取 u16 时数据被截断", pos)
    return (data[pos] << 8) | data[pos + 1]


def _read_u32(data: bytes, pos: int) -> int:
    if pos + 4 > len(data):
        raise MidiParseError("读取 u32 时数据被截断", pos)
    return (
        (data[pos] << 24) | (data[pos + 1] << 16) | (data[pos + 2] << 8) | data[pos + 3]
    )


def _interpret_division(raw: int) -> int:
    """把 MThd 中的 16 位 division 转换成内部表示。

    * ``raw & 0x8000 == 0`` → 正数，每四分音符 tick 数
    * 否则为 SMPTE，转成负数内部表示：``-(fps_byte << 8 | tpf)``
    """
    if raw & 0x8000:
        # 保留完整的高字节（0xE7=25fps / 0xE8=24fps 等），仅用符号位标记 SMPTE
        return -raw
    return raw & 0x7FFF


def _parse_track(body: bytes, base_offset: int) -> Track:
    """解析单个 MTrk 块体。``base_offset`` 仅用于错误信息定位。"""
    track = Track()
    pos = 0
    tick = 0
    running_status = None
    saw_end_of_track = False

    while pos < len(body):
        # 已经读过 end_of_track 后仍存在字节：多为填充/对齐数据，直接忽略
        if saw_end_of_track:
            break

        # 1) delta time（VLQ）
        try:
            delta, pos = read_vlq(body, pos)
        except MidiParseError as exc:
            raise MidiParseError(str(exc), base_offset + pos) from exc
        tick += delta

        if pos >= len(body):
            raise MidiParseError("delta time 后数据被截断", base_offset + pos)
        status = body[pos]

        if status == 0xFF:
            pos += 1
            if pos >= len(body):
                raise MidiParseError("元事件缺少类型字节", base_offset + pos)
            mtype = body[pos]
            pos += 1
            length, pos = read_vlq(body, pos)
            if pos + length > len(body):
                raise MidiParseError(
                    "元事件 0x%02X 负载被截断" % mtype, base_offset + pos
                )
            payload = body[pos : pos + length]
            pos += length
            track.events.append(MetaEvent(tick=tick, mtype=mtype, data=payload))
            running_status = None
            if mtype == META_END_OF_TRACK:
                saw_end_of_track = True
            continue

        if status in (0xF0, 0xF7):
            pos += 1
            length, pos = read_vlq(body, pos)
            if pos + length > len(body):
                raise MidiParseError("SysEx 负载被截断", base_offset + pos)
            payload = body[pos : pos + length]
            pos += length
            track.events.append(SysExEvent(tick=tick, stype=status, data=payload))
            running_status = None
            continue

        if status & 0x80:
            running_status = status
            pos += 1
        else:
            # running status：复用上一个状态字节，本字节是 data1
            if running_status is None:
                raise MidiParseError(
                    "出现数据字节但没有可用的 running status", base_offset + pos
                )
            status = running_status

        etype = (status >> 4) & 0x0F
        channel = status & 0x0F
        if etype == 0xF:
            # 0xF1-0xF6 / 0xF8-0xFE 系统公共与实时消息不出现在 SMF 中
            raise MidiParseError("非法的系统状态字节 0x%02X" % status, base_offset + pos)

        if etype in (0xC, 0xD):
            if pos >= len(body):
                raise MidiParseError("通道事件数据被截断", base_offset + pos)
            data1 = body[pos]
            pos += 1
            data2 = 0
        else:
            if pos + 2 > len(body):
                raise MidiParseError("通道事件数据被截断", base_offset + pos)
            data1 = body[pos]
            data2 = body[pos + 1]
            pos += 2

        if data1 & 0x80 or data2 & 0x80:
            raise MidiParseError(
                "通道事件数据字节最高位不应为 1: 0x%02X/0x%02X" % (data1, data2),
                base_offset + pos,
            )

        track.events.append(
            ChannelEvent(
                tick=tick, channel=channel, etype=etype, data1=data1, data2=data2
            )
        )

    if not saw_end_of_track:
        # 缺失 end_of_track 是常见损坏，保留数据交由 validate 报告
        pass
    return track


def peek_header(data: bytes) -> Tuple[int, int, int]:
    """只读取头部，返回 ``(format, ntrks, division)``，用于快速探测。"""
    if len(data) < 14 or data[:4] != b"MThd":
        raise MidiParseError("不是合法 MIDI 文件", 0)
    return _read_u16(data, 8), _read_u16(data, 10), _interpret_division(_read_u16(data, 12))


__all__ = ["parse", "read_file", "peek_header", "Event"]
