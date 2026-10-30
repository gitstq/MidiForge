"""MIDI 事件对象模型。

对应 Standard MIDI Files 1.0（SMF）规范中的三类事件：

* :class:`ChannelEvent` —— 通道语音事件（音符、控制器、弯音……）
* :class:`MetaEvent`    —— 元事件（速度、拍号、轨道名……）
* :class:`SysExEvent`   —— 系统专有事件（0xF0 / 0xF7）

所有事件都带有 ``tick``（绝对 tick 位置，非 delta），
排序与写入时再按需换算成 delta time。
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Dict

# ---------------------------------------------------------------- 常量表

#: 通道事件高 4 位 → 名称
CHANNEL_TYPE_NAMES: Dict[int, str] = {
    0x8: "note_off",
    0x9: "note_on",
    0xA: "poly_aftertouch",
    0xB: "control_change",
    0xC: "program_change",
    0xD: "channel_aftertouch",
    0xE: "pitch_bend",
}

NOTE_OFF = 0x8
NOTE_ON = 0x9
POLY_AFTERTOUCH = 0xA
CONTROL_CHANGE = 0xB
PROGRAM_CHANGE = 0xC
CHANNEL_AFTERTOUCH = 0xD
PITCH_BEND = 0xE

#: 常用元事件类型
META_SEQUENCE_NUMBER = 0x00
META_TEXT = 0x01
META_COPYRIGHT = 0x02
META_TRACK_NAME = 0x03
META_INSTRUMENT = 0x04
META_LYRIC = 0x05
META_MARKER = 0x06
META_CUE = 0x07
META_CHANNEL_PREFIX = 0x20
META_END_OF_TRACK = 0x2F
META_TEMPO = 0x51
META_SMPTE_OFFSET = 0x54
META_TIME_SIGNATURE = 0x58
META_KEY_SIGNATURE = 0x59
META_SEQUENCER_SPECIFIC = 0x7F

META_NAMES: Dict[int, str] = {
    META_SEQUENCE_NUMBER: "sequence_number",
    META_TEXT: "text",
    META_COPYRIGHT: "copyright",
    META_TRACK_NAME: "track_name",
    META_INSTRUMENT: "instrument",
    META_LYRIC: "lyric",
    META_MARKER: "marker",
    META_CUE: "cue",
    META_CHANNEL_PREFIX: "channel_prefix",
    META_END_OF_TRACK: "end_of_track",
    META_TEMPO: "tempo",
    META_SMPTE_OFFSET: "smpte_offset",
    META_TIME_SIGNATURE: "time_signature",
    META_KEY_SIGNATURE: "key_signature",
    META_SEQUENCER_SPECIFIC: "sequencer_specific",
}

#: 常用控制器编号 → 名称（仅收录分析/清理高频使用的若干项）
CONTROLLER_NAMES: Dict[int, str] = {
    0: "bank_select",
    1: "modulation",
    6: "data_entry_msb",
    7: "volume",
    10: "pan",
    11: "expression",
    32: "bank_select_lsb",
    64: "sustain",
    65: "portamento",
    71: "resonance",
    72: "release",
    73: "attack",
    74: "brightness",
    91: "reverb",
    93: "chorus",
    120: "all_sound_off",
    121: "reset_all_controllers",
    123: "all_notes_off",
}


# ---------------------------------------------------------------- 基类


@dataclass
class Event:
    """事件基类。

    Attributes:
        tick: 绝对 tick 位置（从曲目开头算起）。
    """

    tick: int = 0

    #: 事件种类：``channel`` / ``meta`` / ``sysex``
    kind: str = "channel"

    def with_tick(self, tick: int) -> "Event":
        """返回 tick 被替换为 ``tick`` 的新事件（原事件不变）。"""
        return replace(self, tick=tick)

    def to_dict(self) -> Dict[str, Any]:
        """转成可 JSON 序列化的字典。"""
        raise NotImplementedError

    def __str__(self) -> str:  # pragma: no cover - 调试用途
        return "%s(tick=%d)" % (self.__class__.__name__, self.tick)


# ---------------------------------------------------------------- 通道事件


@dataclass
class ChannelEvent(Event):
    """通道语音事件。

    Attributes:
        channel: 0-15。
        etype: 事件类型高 4 位（0x8-0xE）。
        data1: 第一个数据字节；音符事件为音高（0-127）。
        data2: 第二个数据字节；音符事件为力度（0-127），
            program_change / channel_aftertouch 事件该字节无意义，固定为 0。
    """

    channel: int = 0
    etype: int = NOTE_ON
    data1: int = 60
    data2: int = 64

    kind: str = "channel"

    def __post_init__(self) -> None:
        if self.etype not in CHANNEL_TYPE_NAMES:
            raise ValueError("非法通道事件类型: 0x%X" % self.etype)
        if not 0 <= self.channel <= 15:
            raise ValueError("通道号必须在 0-15: %r" % self.channel)
        for name in ("data1", "data2"):
            value = getattr(self, name)
            if not 0 <= value <= 127:
                raise ValueError("%s 必须在 0-127: %r" % (name, value))

    # -- 便捷判定 --------------------------------------------------

    @property
    def type_name(self) -> str:
        """事件类型名，如 ``note_on``。"""
        return CHANNEL_TYPE_NAMES[self.etype]

    @property
    def status(self) -> int:
        """完整状态字节，如 0x93。"""
        return (self.etype << 4) | self.channel

    @property
    def is_note_on(self) -> bool:
        """是否为“真”音符开（力度 0 的音符开等价于音符关）。"""
        return self.etype == NOTE_ON and self.data2 > 0

    @property
    def is_note_off(self) -> bool:
        """是否为音符关（含力度为 0 的音符开）。"""
        return self.etype == NOTE_OFF or (self.etype == NOTE_ON and self.data2 == 0)

    @property
    def pitch(self) -> int:
        """音符事件的音高。"""
        return self.data1

    @property
    def velocity(self) -> int:
        """音符事件的力度。"""
        return self.data2

    @property
    def controller(self) -> int:
        """控制器事件的编号。"""
        return self.data1

    @property
    def controller_name(self) -> str:
        """控制器名称，未知编号返回 ``cc<num>``。"""
        return CONTROLLER_NAMES.get(self.data1, "cc%d" % self.data1)

    @property
    def value(self) -> int:
        """控制器 / 弯音等事件的数值。"""
        return self.data2

    @property
    def pitch_bend(self) -> int:
        """弯音值，范围 -8192..8191（0 为中心）。"""
        return ((self.data2 << 7) | self.data1) - 8192

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "kind": "channel",
            "tick": self.tick,
            "channel": self.channel,
            "type": self.type_name,
            "data1": self.data1,
            "data2": self.data2,
        }
        if self.etype in (NOTE_ON, NOTE_OFF):
            out["pitch"] = self.data1
            out["velocity"] = self.data2
        elif self.etype == CONTROL_CHANGE:
            out["controller"] = self.data1
            out["controller_name"] = self.controller_name
            out["value"] = self.data2
        elif self.etype == PITCH_BEND:
            out["pitch_bend"] = self.pitch_bend
        return out

    def __str__(self) -> str:
        if self.etype in (NOTE_ON, NOTE_OFF):
            return "tick=%-7d %-8s ch=%-2d note=%-3s vel=%d" % (
                self.tick,
                self.type_name,
                self.channel,
                self.data1,
                self.data2,
            )
        return "tick=%-7d %-16s ch=%-2d %d/%d" % (
            self.tick,
            self.type_name,
            self.channel,
            self.data1,
            self.data2,
        )


# ---------------------------------------------------------------- 元事件


@dataclass
class MetaEvent(Event):
    """元事件（0xFF）。"""

    mtype: int = META_TEXT
    data: bytes = b""

    kind: str = "meta"

    def __post_init__(self) -> None:
        if not 0 <= self.mtype <= 127:
            raise ValueError("元事件类型必须在 0-127: %r" % self.mtype)

    @property
    def type_name(self) -> str:
        """元事件名称。"""
        return META_NAMES.get(self.mtype, "meta_0x%02X" % self.mtype)

    @property
    def text(self) -> str:
        """文本类元事件解码后的字符串（非法 UTF-8 回退 Latin-1）。"""
        return decode_text(self.data)

    @property
    def tempo(self) -> int:
        """tempo 元事件的“每四分音符微秒数”。非 tempo 事件抛 ValueError。"""
        if self.mtype != META_TEMPO or len(self.data) != 3:
            raise ValueError("该元事件不是合法的 tempo 事件")
        return (self.data[0] << 16) | (self.data[1] << 8) | self.data[2]

    @property
    def bpm(self) -> float:
        """tempo 事件换算出的 BPM。"""
        return 60000000.0 / self.tempo

    @property
    def time_signature(self):
        """返回 ``(numerator, denominator, clocks_per_click, 32nds)``。"""
        if self.mtype != META_TIME_SIGNATURE or len(self.data) < 4:
            raise ValueError("该元事件不是合法的拍号事件")
        return (self.data[0], 2 ** self.data[1], self.data[2], self.data[3])

    @property
    def key_signature(self):
        """返回 ``(fifths, minor)``，``fifths`` 为 -7..7。"""
        if self.mtype != META_KEY_SIGNATURE or len(self.data) < 2:
            raise ValueError("该元事件不是合法的调号事件")
        sf = self.data[0]
        if sf > 127:
            sf -= 256
        return (sf, bool(self.data[1]))

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "kind": "meta",
            "tick": self.tick,
            "type": self.type_name,
        }
        if self.mtype == META_TEMPO and len(self.data) == 3:
            out["tempo"] = self.tempo
            out["bpm"] = round(self.bpm, 3)
        elif self.mtype == META_TIME_SIGNATURE and len(self.data) >= 4:
            out["time_signature"] = "%d/%d" % self.time_signature[:2]
        elif self.mtype == META_KEY_SIGNATURE and len(self.data) >= 2:
            out["key_signature"] = self.key_signature
        elif self.mtype in (
            META_TEXT,
            META_TRACK_NAME,
            META_INSTRUMENT,
            META_LYRIC,
            META_MARKER,
            META_CUE,
            META_COPYRIGHT,
        ):
            out["text"] = self.text
        else:
            out["data_hex"] = self.data.hex()
        return out

    def __str__(self) -> str:
        extra = ""
        if self.mtype == META_TEMPO and len(self.data) == 3:
            extra = " %.2f BPM" % self.bpm
        elif self.mtype == META_TRACK_NAME:
            extra = " " + self.text
        return "tick=%-7d meta %-20s%s" % (self.tick, self.type_name, extra)


# ---------------------------------------------------------------- SysEx


@dataclass
class SysExEvent(Event):
    """系统专有事件。

    Attributes:
        stype: 0xF0（完整 SysEx）或 0xF7（分段 / 转义）。
        data: 负载字节（不含 0xF0 起始与 0xF7 结束标志）。
    """

    stype: int = 0xF0
    data: bytes = b""

    kind: str = "sysex"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": "sysex",
            "tick": self.tick,
            "stype": "0x%02X" % self.stype,
            "length": len(self.data),
            "data_hex": self.data.hex(),
        }

    def __str__(self) -> str:
        return "tick=%-7d sysex 0x%02X len=%d" % (self.tick, self.stype, len(self.data))


# ---------------------------------------------------------------- 工具函数


def decode_text(data: bytes) -> str:
    """把元事件负载解码为文本，UTF-8 失败时回退 Latin-1（永不抛异常）。"""
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1")


def make_tempo(tick: int, bpm: float) -> MetaEvent:
    """按 BPM 构造 tempo 元事件。"""
    return MetaEvent(tick=tick, mtype=META_TEMPO, data=bpm_to_tempo_bytes(bpm))


def bpm_to_tempo_bytes(bpm: float) -> bytes:
    """BPM → 3 字节大端微秒数。"""
    us = int(round(60000000.0 / bpm))
    us = max(1, min(0xFFFFFF, us))
    return bytes([(us >> 16) & 0xFF, (us >> 8) & 0xFF, us & 0xFF])
