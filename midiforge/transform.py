"""MIDI 变换：移调、量化、力度、时间缩放、裁剪、合并、拆分、清理。

所有函数默认**返回新的** :class:`MidiFile`（``inplace=False``），
避免调用方被副作用惊到；需要原地修改时显式传 ``inplace=True``。
"""

from __future__ import annotations

import copy
import random
from typing import Iterable, List, Optional, Sequence, Set

from .errors import MidiValueError
from .events import (
    CHANNEL_AFTERTOUCH,
    CONTROL_CHANGE,
    META_END_OF_TRACK,
    META_LYRIC,
    META_MARKER,
    META_TEMPO,
    NOTE_OFF,
    NOTE_ON,
    PITCH_BEND,
    POLY_AFTERTOUCH,
    PROGRAM_CHANGE,
    ChannelEvent,
    MetaEvent,
    SysExEvent,
    bpm_to_tempo_bytes,
)
from .gm import DRUM_CHANNEL
from .midifile import MidiFile, Track

NOTE_TYPES = (NOTE_ON, NOTE_OFF)


def _prepare(midi: MidiFile, inplace: bool) -> MidiFile:
    return midi if inplace else copy.deepcopy(midi)


# ---------------------------------------------------------------- 移调


def transpose(
    midi: MidiFile,
    semitones: int,
    channels: Optional[Iterable[int]] = None,
    include_drums: bool = False,
    inplace: bool = False,
) -> MidiFile:
    """整体移调。

    Args:
        semitones: 移调半音数，正数升高。
        channels: 只处理这些通道；缺省处理全部。
        include_drums: 是否移调打击乐通道（默认 False，鼓组移调通常无意义）。
        inplace: 是否原地修改。

    Raises:
        MidiValueError: 移调后音高越界。
    """
    out = _prepare(midi, inplace)
    allowed = None if channels is None else set(channels)
    for track in out.tracks:
        for ev in track.channel_events():
            if ev.etype not in NOTE_TYPES:
                continue
            if allowed is not None and ev.channel not in allowed:
                continue
            if ev.channel == DRUM_CHANNEL and not include_drums:
                continue
            new_pitch = ev.data1 + semitones
            if not 0 <= new_pitch <= 127:
                raise MidiValueError(
                    "移调后音高越界: %d %+d = %d" % (ev.data1, semitones, new_pitch)
                )
            ev.data1 = new_pitch
    return out


# ---------------------------------------------------------------- 量化


def quantize(
    midi: MidiFile,
    grid: int,
    strength: float = 1.0,
    swing: float = 0.0,
    channels: Optional[Iterable[int]] = None,
    inplace: bool = False,
) -> MidiFile:
    """量化音符起始位置（保持时值不变）。

    Args:
        grid: 网格粒度（tick），如 ``division // 4`` 表示十六分音符。
        strength: 量化强度 0-1；1 为完全对齐，0 为不动。
        swing: 摇摆量 0-0.5；只作用于网格内的“后半拍”（奇数格）。
        channels: 只处理这些通道。
        inplace: 是否原地修改。

    Raises:
        MidiValueError: 参数越界。
    """
    if grid <= 0:
        raise MidiValueError("grid 必须为正整数")
    if not 0.0 <= strength <= 1.0:
        raise MidiValueError("strength 必须在 0-1 之间")
    if not 0.0 <= swing <= 0.5:
        raise MidiValueError("swing 必须在 0-0.5 之间")

    out = _prepare(midi, inplace)
    allowed = None if channels is None else set(channels)

    def target_for(tick: int) -> int:
        base = int(round(tick / float(grid))) * grid
        shifted = tick + (base - tick) * strength
        if swing and grid > 1:
            slot = int(round(shifted / grid))
            if slot % 2 == 1:
                shifted += swing * grid
        return int(round(shifted))

    for track in out.tracks:
        pending: dict = {}
        for ev in sorted(track.events, key=lambda e: e.tick):
            if not isinstance(ev, ChannelEvent) or ev.etype not in NOTE_TYPES:
                continue
            if allowed is not None and ev.channel not in allowed:
                continue
            key = (ev.channel, ev.data1)
            if ev.is_note_off:
                stack = pending.get(key)
                if not stack:
                    continue
                on = stack.pop(0)
                delta = target_for(on.tick) - on.tick
                on.tick += delta
                ev.tick += delta
            else:
                pending.setdefault(key, []).append(ev)
        track.sort()
    return out


# ---------------------------------------------------------------- 力度


def velocity(
    midi: MidiFile,
    scale: float = 1.0,
    offset: int = 0,
    ratio: float = 1.0,
    channels: Optional[Iterable[int]] = None,
    inplace: bool = False,
) -> MidiFile:
    """调整音符力度。

    运算顺序：先压缩（向 64 靠拢 ``ratio`` 倍），再乘 ``scale``，最后加 ``offset``。

    Args:
        scale: 缩放系数。
        offset: 平移量（可为负）。
        ratio: 动态压缩比；1 表示不压缩，>1 压缩，<1 扩张。
        channels: 只处理这些通道。
        inplace: 是否原地修改。
    """
    if ratio <= 0:
        raise MidiValueError("ratio 必须为正")
    out = _prepare(midi, inplace)
    allowed = None if channels is None else set(channels)
    for track in out.tracks:
        for ev in track.channel_events():
            if ev.etype != NOTE_ON or ev.data2 == 0:
                continue
            if allowed is not None and ev.channel not in allowed:
                continue
            value = 64 + (ev.data2 - 64) / ratio
            value = value * scale + offset
            ev.data2 = _clamp7(int(round(value)))
    return out


def humanize(
    midi: MidiFile,
    tick_jitter: int = 0,
    velocity_jitter: int = 0,
    seed: Optional[int] = 0,
    inplace: bool = False,
) -> MidiFile:
    """加入可控随机扰动（“人性化”），使用固定随机种子保证可复现。

    Args:
        tick_jitter: 起始 tick 抖动范围（±）。
        velocity_jitter: 力度抖动范围（±）。
        seed: 随机种子；相同种子结果完全一致。
        inplace: 是否原地修改。
    """
    out = _prepare(midi, inplace)
    rng = random.Random(seed)
    for track in out.tracks:
        pending: dict = {}
        for ev in sorted(track.events, key=lambda e: e.tick):
            if not isinstance(ev, ChannelEvent) or ev.etype not in NOTE_TYPES:
                continue
            key = (ev.channel, ev.data1)
            if ev.is_note_off:
                stack = pending.get(key)
                if not stack:
                    continue
                on = stack.pop(0)
                if tick_jitter:
                    delta = rng.randint(-abs(tick_jitter), abs(tick_jitter))
                    on.tick = max(0, on.tick + delta)
                    ev.tick = max(on.tick, ev.tick + delta)
                if velocity_jitter and on.data2:
                    on.data2 = _clamp7(
                        on.data2 + rng.randint(-abs(velocity_jitter), abs(velocity_jitter))
                    )
            else:
                pending.setdefault(key, []).append(ev)
        track.sort()
    return out


def _clamp7(value: int) -> int:
    return max(0, min(127, value))


# ---------------------------------------------------------------- 时间


def scale_ticks(midi: MidiFile, factor: float, inplace: bool = False) -> MidiFile:
    """按倍率缩放所有 tick（时间拉伸/压缩），速度标记不变。

    ``factor > 1`` 表示拉长（时长变长）。
    """
    if factor <= 0:
        raise MidiValueError("factor 必须为正")
    out = _prepare(midi, inplace)
    for track in out.tracks:
        for ev in track.events:
            ev.tick = int(round(ev.tick * factor))
        track.sort()
    return out


def scale_tempo(midi: MidiFile, factor: float, inplace: bool = False) -> MidiFile:
    """按倍率缩放速度（BPM × factor），tick 结构不变。

    ``factor > 1`` 表示更快（时长变短）。
    """
    if factor <= 0:
        raise MidiValueError("factor 必须为正")
    out = _prepare(midi, inplace)
    changed = False
    for track in out.tracks:
        for ev in track.events:
            if isinstance(ev, MetaEvent) and ev.mtype == META_TEMPO and len(ev.data) == 3:
                us = ev.tempo
                new_us = max(1, min(0xFFFFFF, int(round(us / factor))))
                ev.data = bytes(
                    [(new_us >> 16) & 0xFF, (new_us >> 8) & 0xFF, new_us & 0xFF]
                )
                changed = True
    if not changed:
        # 没有 tempo 事件时插入一条，以 120 BPM 为基准
        base = 500000
        new_us = max(1, min(0xFFFFFF, int(round(base / factor))))
        out.tracks[0].events.insert(
            0,
            MetaEvent(
                tick=0,
                mtype=META_TEMPO,
                data=bytes([(new_us >> 16) & 0xFF, (new_us >> 8) & 0xFF, new_us & 0xFF]),
            ),
        )
        out.tracks[0].sort()
    return out


def set_bpm(midi: MidiFile, bpm: float, inplace: bool = False) -> MidiFile:
    """把全曲设为固定 BPM（删除其它速度变化）。"""
    if bpm <= 0:
        raise MidiValueError("bpm 必须为正")
    out = _prepare(midi, inplace)
    for track in out.tracks:
        track.events = [
            e
            for e in track.events
            if not (isinstance(e, MetaEvent) and e.mtype == META_TEMPO)
        ]
    out.tracks[0].events.insert(0, MetaEvent(tick=0, mtype=META_TEMPO, data=bpm_to_tempo_bytes(bpm)))
    out.tracks[0].sort()
    return out


def trim(
    midi: MidiFile,
    start: int = 0,
    end: Optional[int] = None,
    inplace: bool = False,
) -> MidiFile:
    """裁剪到 ``[start, end)`` 区间，并把起点平移到 0。

    跨越 ``end`` 的未结束音符会被自动补上 note_off；
    跨越 ``start`` 的旧音符会被截断到 ``start``。
    """
    out = _prepare(midi, inplace)
    if end is None:
        end = out.end_tick
    if end < start:
        raise MidiValueError("end 不能小于 start")

    for track in out.tracks:
        kept: List = []
        rebased: List = []  # 区间之前的全局元事件，已对齐到 0，不再参与平移
        closing: List = []  # 需要补上的 note_off
        pending: dict = {}  # 区间内发出、尚未关闭的 note_on
        carry: dict = {}  # 起始早于 start、尚未关闭的音符 -> 力度

        for ev in sorted(track.events, key=lambda e: e.tick):
            if isinstance(ev, MetaEvent) and ev.mtype == META_END_OF_TRACK:
                continue

            # ---- 区间之前：只保留全局元事件，并记录仍在发声的音符
            if ev.tick < start:
                if isinstance(ev, MetaEvent) and ev.mtype in (META_TEMPO, 0x58, 0x59):
                    rebased.append(MetaEvent(tick=0, mtype=ev.mtype, data=ev.data))
                elif isinstance(ev, ChannelEvent) and ev.etype in NOTE_TYPES:
                    key = (ev.channel, ev.data1)
                    if ev.is_note_off:
                        carry.pop(key, None)
                    else:
                        carry[key] = ev.velocity
                continue

            # ---- 区间之后：丢弃（未关闭的音符稍后补 note_off）
            if ev.tick >= end:
                continue

            if isinstance(ev, ChannelEvent) and ev.etype in NOTE_TYPES:
                key = (ev.channel, ev.data1)
                if ev.is_note_off:
                    if key in carry:
                        # 起点在区间之前：补一个从 start 开始的 note_on
                        kept.append(
                            ChannelEvent(
                                tick=start,
                                channel=key[0],
                                etype=NOTE_ON,
                                data1=key[1],
                                data2=carry.pop(key),
                            )
                        )
                    elif key not in pending:
                        continue  # 孤儿音符关，丢弃
                    else:
                        pending.pop(key, None)
                    kept.append(ev)
                else:
                    carry.pop(key, None)  # 重新起音，覆盖跨起点状态
                    pending[key] = ev
                    kept.append(ev)
                continue

            kept.append(ev)

        # 跨过结尾仍未关闭的音符
        for (channel, pitch) in pending:
            closing.append(
                ChannelEvent(
                    tick=end, channel=channel, etype=NOTE_OFF, data1=pitch, data2=0
                )
            )
        # 起始在起点之前、且一直延续到结尾之后的音符：贯穿整个区间
        for (channel, pitch), vel in carry.items():
            kept.append(
                ChannelEvent(
                    tick=start, channel=channel, etype=NOTE_ON, data1=pitch, data2=vel
                )
            )
            closing.append(
                ChannelEvent(
                    tick=end, channel=channel, etype=NOTE_OFF, data1=pitch, data2=0
                )
            )

        for ev in kept:
            ev.tick -= start
        for ev in closing:
            ev.tick -= start
        track.events = rebased + kept + closing
        track.sort()
    return out


# ---------------------------------------------------------------- 结构


def merge_tracks(midi: MidiFile, inplace: bool = False) -> MidiFile:
    """把所有轨道合并成一条（用于转 Format 0 或简化结构）。"""
    out = _prepare(midi, inplace)
    merged = Track()
    names: List[str] = []
    for track in out.tracks:
        if track.name:
            names.append(track.name)
        merged.events.extend(track.events)
    # 合并后只保留一份 end_of_track
    merged.events = [
        e
        for e in merged.events
        if not (isinstance(e, MetaEvent) and e.mtype == META_END_OF_TRACK)
    ]
    merged.sort()
    if names:
        merged.events.insert(
            0, MetaEvent(tick=0, mtype=0x03, data=" + ".join(names).encode("utf-8"))
        )
    out.tracks = [merged]
    return out


def split_by_channel(midi: MidiFile, inplace: bool = False) -> MidiFile:
    """按通道拆分成多条轨道；元事件（速度/拍号）保留在第一条轨道。"""
    out = _prepare(midi, inplace)
    tracks: dict = {}
    global_events: List = []
    order: List[int] = []
    for track in out.tracks:
        for ev in track.events:
            if isinstance(ev, ChannelEvent):
                if ev.channel not in tracks:
                    tracks[ev.channel] = Track()
                    order.append(ev.channel)
                tracks[ev.channel].events.append(ev)
            elif isinstance(ev, MetaEvent) and ev.mtype in (META_TEMPO, 0x58, 0x59, 0x03):
                global_events.append(ev)
    if not tracks:
        return out
    result: List[Track] = []
    head = Track()
    head.events.extend(global_events)
    head.name = midi.tracks[0].name if midi.tracks and midi.tracks[0].name else "global"
    result.append(head)
    for channel in sorted(order):
        track = tracks[channel]
        track.name = "ch%d" % channel
        result.append(track)
    out.tracks = result
    if out.format == 0:
        out.format = 1
    return out


def to_format(midi: MidiFile, fmt: int, inplace: bool = False) -> MidiFile:
    """转换 SMF 格式（0 / 1 / 2）。转 0 时会自动合并轨道。"""
    if fmt not in (0, 1, 2):
        raise MidiValueError("MIDI 格式必须为 0 / 1 / 2")
    out = _prepare(midi, inplace)
    if fmt == 0 and len(out.tracks) > 1:
        out = merge_tracks(out, inplace=True)
    out.format = fmt
    return out


def strip(
    midi: MidiFile,
    sysex: bool = False,
    controllers: bool = False,
    keep_controllers: Optional[Sequence[int]] = None,
    program_change: bool = False,
    pitch_bend: bool = False,
    aftertouch: bool = False,
    lyrics: bool = False,
    markers: bool = False,
    inplace: bool = False,
) -> MidiFile:
    """按类别移除事件。

    Args:
        sysex: 移除 SysEx。
        controllers: 移除控制器事件；``keep_controllers`` 可保留指定编号。
        keep_controllers: 需要保留的控制器编号（仅在 ``controllers=True`` 时生效）。
        program_change: 移除音色切换。
        pitch_bend: 移除弯音。
        aftertouch: 移除触后。
        lyrics: 移除歌词元事件。
        markers: 移除标记元事件。
        inplace: 是否原地修改。
    """
    out = _prepare(midi, inplace)
    keep = set(keep_controllers or ())
    for track in out.tracks:
        events: List = []
        for ev in track.events:
            if isinstance(ev, SysExEvent):
                if sysex:
                    continue
            elif isinstance(ev, MetaEvent):
                if lyrics and ev.mtype == META_LYRIC:
                    continue
                if markers and ev.mtype == META_MARKER:
                    continue
            elif isinstance(ev, ChannelEvent):
                if controllers and ev.etype == CONTROL_CHANGE and ev.data1 not in keep:
                    continue
                if program_change and ev.etype == PROGRAM_CHANGE:
                    continue
                if pitch_bend and ev.etype == PITCH_BEND:
                    continue
                if aftertouch and ev.etype in (POLY_AFTERTOUCH, CHANNEL_AFTERTOUCH):
                    continue
            events.append(ev)
        track.events = events
    return out


def clean(midi: MidiFile, inplace: bool = False) -> MidiFile:
    """修复常见问题：孤儿音符关、未闭合音符、越界数据、重复 end_of_track。"""
    out = _prepare(midi, inplace)
    for track in out.tracks:
        events: List = []
        pending: dict = {}
        seen_end = False
        for ev in sorted(track.events, key=lambda e: e.tick):
            if isinstance(ev, MetaEvent) and ev.mtype == META_END_OF_TRACK:
                if seen_end:
                    continue
                seen_end = True
            if isinstance(ev, ChannelEvent):
                # 力度为 0 的 note_on 先规范化成 note_off，再参与配对
                if ev.etype == NOTE_ON and ev.data2 == 0:
                    ev.etype = NOTE_OFF
                if ev.etype in NOTE_TYPES:
                    key = (ev.channel, ev.data1)
                    if ev.is_note_off:
                        if key not in pending:
                            continue  # 孤儿音符关，丢弃
                        del pending[key]
                    else:
                        pending[key] = ev
            events.append(ev)
        end_tick = max((e.tick for e in events), default=0)
        for (channel, pitch), on in list(pending.items()):
            events.append(
                ChannelEvent(
                    tick=end_tick, channel=channel, etype=NOTE_OFF, data1=pitch, data2=0
                )
            )
        if not seen_end:
            events.append(MetaEvent(tick=end_tick, mtype=META_END_OF_TRACK, data=b""))
        track.events = events
        track.sort()
    return out


def remove_duplicate_notes(midi: MidiFile, inplace: bool = False) -> MidiFile:
    """移除完全重叠的重复音符（同通道、同音高、同起始）。"""
    out = _prepare(midi, inplace)
    for track in out.tracks:
        seen: Set = set()
        drop: Set = set()
        pending: dict = {}
        for ev in sorted(track.events, key=lambda e: e.tick):
            if not isinstance(ev, ChannelEvent) or ev.etype not in NOTE_TYPES:
                continue
            key = (ev.channel, ev.data1)
            if ev.is_note_off:
                pending.pop(key, None)
                continue
            slot = (ev.channel, ev.data1, ev.tick)
            if slot in seen or key in pending:
                drop.add(id(ev))
            else:
                seen.add(slot)
                pending[key] = ev
        track.events = [e for e in track.events if id(e) not in drop]
    return out


__all__ = [
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
]
