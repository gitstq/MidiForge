"""MIDI 结构校验（lint）。

按 SMF 规范与工程实践给出 error / warning / info 三级问题，
每条问题带唯一编号（``MF0xx``），便于在 CI 中按编号过滤。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from .events import (
    META_END_OF_TRACK,
    META_TEMPO,
    META_TIME_SIGNATURE,
    NOTE_OFF,
    NOTE_ON,
    ChannelEvent,
    Event,
    MetaEvent,
)
from .midifile import MidiFile

ERROR = "error"
WARNING = "warning"
INFO = "info"

#: 编号 → 简短标题
RULE_TITLES: Dict[str, str] = {
    "MF001": "缺少 end_of_track 元事件",
    "MF002": "轨道缺少名称",
    "MF003": "空轨道",
    "MF004": "孤儿音符关事件",
    "MF005": "未闭合的音符开事件",
    "MF006": "零时长音符",
    "MF007": "力度为 0 的音符开（应写作音符关）",
    "MF008": "同音高音符重叠",
    "MF009": "缺少速度（tempo）标记",
    "MF010": "速度值异常",
    "MF011": "缺少拍号标记",
    "MF012": "end_of_track 之后仍有事件",
    "MF013": "重复的 end_of_track",
    "MF014": "tempo 出现在非首轨",
    "MF015": "文件没有任何音符",
    "MF016": "力度超过 127",
    "MF017": "MIDI 格式值异常",
    "MF018": "轨道数超过 65535",
    "MF019": "时基（division）为 0",
    "MF020": "未知元事件类型",
}


@dataclass
class Issue:
    """一条校验问题。"""

    code: str
    level: str
    message: str
    track: Optional[int] = None
    tick: Optional[int] = None

    @property
    def title(self) -> str:
        """问题标题。"""
        return RULE_TITLES.get(self.code, "")

    def to_dict(self) -> dict:
        """转成 JSON 友好字典。"""
        return {
            "code": self.code,
            "level": self.level,
            "title": self.title,
            "message": self.message,
            "track": self.track,
            "tick": self.tick,
        }

    def __str__(self) -> str:
        where = ""
        if self.track is not None:
            where = " [track=%d]" % self.track
        if self.tick is not None:
            where += " @%d" % self.tick
        return "%-6s %-7s %s%s" % (self.code, self.level, self.message, where)


def validate(midi: MidiFile, strict: bool = False) -> List[Issue]:
    """校验 MIDI 结构。

    Args:
        midi: 待校验对象。
        strict: 是否把 info 级问题也纳入（默认 info 不返回）。

    Returns:
        :class:`Issue` 列表，按 ``(level, code, track, tick)`` 排序。
    """
    issues: List[Issue] = []

    if midi.format not in (0, 1, 2):
        issues.append(Issue("MF017", ERROR, "MIDI 格式字段为 %d，应为 0/1/2" % midi.format))
    if not midi.tracks:
        issues.append(Issue("MF003", ERROR, "文件不包含任何轨道"))
        return _sorted(issues)
    if len(midi.tracks) > 0xFFFF:
        issues.append(Issue("MF018", ERROR, "轨道数 %d 超过上限" % len(midi.tracks)))
    if not midi.is_smpte and (midi.division & 0x7FFF) == 0:
        issues.append(Issue("MF019", ERROR, "时基为 0，无法换算时间"))

    for index, track in enumerate(midi.tracks):
        issues.extend(_validate_track(index, track, strict))

    if not midi.tempo_events() and not midi.is_smpte:
        issues.append(Issue("MF009", WARNING, "全曲没有 tempo 标记，将按 120 BPM 计算"))
    if not midi.time_signatures():
        issues.append(Issue("MF011", INFO, "全曲没有拍号标记，将按 4/4 计算"))
    if midi.format != 0:
        for index in range(1, len(midi.tracks)):
            for ev in midi.tracks[index].meta_events(META_TEMPO):
                issues.append(
                    Issue(
                        "MF014",
                        WARNING,
                        "tempo 事件应只出现在第一条轨道",
                        track=index,
                        tick=ev.tick,
                    )
                )
    total_notes = sum(
        1
        for t in midi.tracks
        for e in t.events
        if isinstance(e, ChannelEvent) and e.etype == NOTE_ON and e.data2 > 0
    )
    if total_notes == 0:
        issues.append(Issue("MF015", WARNING, "文件中没有任何音符开事件"))

    return _sorted(issues, strict)


def _validate_track(index: int, track, strict: bool) -> List[Issue]:
    issues: List[Issue] = []
    if not track.events:
        issues.append(Issue("MF003", WARNING, "轨道为空", track=index))
        return issues
    if not track.name and strict:
        issues.append(Issue("MF002", INFO, "轨道没有名称", track=index))

    end_ticks = [
        e.tick
        for e in track.events
        if isinstance(e, MetaEvent) and e.mtype == META_END_OF_TRACK
    ]
    if not end_ticks:
        issues.append(Issue("MF001", ERROR, "轨道缺少 end_of_track 元事件", track=index))
    elif len(end_ticks) > 1:
        issues.append(
            Issue("MF013", WARNING, "存在 %d 个 end_of_track" % len(end_ticks), track=index)
        )
    else:
        after = [e for e in track.events if e.tick > end_ticks[0]]
        if after:
            issues.append(
                Issue(
                    "MF012",
                    WARNING,
                    "end_of_track 之后仍有 %d 个事件" % len(after),
                    track=index,
                    tick=after[0].tick,
                )
            )

    pending: Dict[tuple, int] = {}
    active: Dict[tuple, int] = {}
    for ev in sorted(track.events, key=lambda e: e.tick):
        if isinstance(ev, MetaEvent):
            if ev.mtype == META_TEMPO:
                try:
                    value = ev.tempo
                    if value <= 0 or value > 0xFFFFFF:
                        raise ValueError
                    if value < 10000 or value > 4000000:
                        issues.append(
                            Issue(
                                "MF010",
                                WARNING,
                                "速度 %.1f BPM 超出常规范围" % ev.bpm,
                                track=index,
                                tick=ev.tick,
                            )
                        )
                except ValueError:
                    issues.append(
                        Issue(
                            "MF010",
                            ERROR,
                            "tempo 事件负载不是合法的 3 字节值",
                            track=index,
                            tick=ev.tick,
                        )
                    )
            elif ev.mtype not in (0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08,
                                  0x09, 0x20, 0x2F, 0x51, 0x54, 0x58, 0x59, 0x7F):
                issues.append(
                    Issue(
                        "MF020",
                        INFO,
                        "未知元事件类型 0x%02X" % ev.mtype,
                        track=index,
                        tick=ev.tick,
                    )
                )
            continue
        if not isinstance(ev, ChannelEvent) or ev.etype not in (NOTE_ON, NOTE_OFF):
            continue
        if ev.data1 > 127 or ev.data2 > 127:  # pragma: no cover - 构造时已校验
            issues.append(
                Issue("MF016", ERROR, "事件数据字节超过 127", track=index, tick=ev.tick)
            )
        key = (ev.channel, ev.data1)
        if ev.etype == NOTE_ON and ev.data2 == 0:
            # 力度为 0 的 note_on：规范写法应为 note_off
            issues.append(
                Issue(
                    "MF007",
                    WARNING,
                    "力度为 0 的音符开，建议写成 note_off",
                    track=index,
                    tick=ev.tick,
                )
            )
            pending.pop(key, None)
            continue
        if ev.is_note_off:
            if key not in pending:
                issues.append(
                    Issue(
                        "MF004",
                        ERROR,
                        "音符关 ch%d %d 没有对应的音符开" % (ev.channel, ev.data1),
                        track=index,
                        tick=ev.tick,
                    )
                )
            else:
                start = pending.pop(key)
                if ev.tick == start:
                    issues.append(
                        Issue(
                            "MF006",
                            WARNING,
                            "零时长音符 ch%d pitch=%d" % (ev.channel, ev.data1),
                            track=index,
                            tick=ev.tick,
                        )
                    )
            active.pop(key, None)
        else:
            if ev.data2 == 0:
                issues.append(
                    Issue(
                        "MF007",
                        WARNING,
                        "力度为 0 的音符开，建议写成 note_off",
                        track=index,
                        tick=ev.tick,
                    )
                )
                continue
            if key in pending:
                issues.append(
                    Issue(
                        "MF008",
                        WARNING,
                        "同音高音符重叠 ch%d pitch=%d" % (ev.channel, ev.data1),
                        track=index,
                        tick=ev.tick,
                    )
                )
            pending[key] = ev.tick
            active[key] = ev.tick  # noqa: F841 - 供未来扩展（重叠时长统计）

    for (channel, pitch), tick in pending.items():
        issues.append(
            Issue(
                "MF005",
                ERROR,
                "音符开 ch%d pitch=%d 未闭合" % (channel, pitch),
                track=index,
                tick=tick,
            )
        )
    return issues


def _sorted(issues: List[Issue], strict: bool = True) -> List[Issue]:
    level_order = {ERROR: 0, WARNING: 1, INFO: 2}
    if not strict:
        issues = [i for i in issues if i.level != INFO]
    issues.sort(key=lambda i: (level_order.get(i.level, 3), i.code, i.track or -1, i.tick or -1))
    return issues


def summarize(issues: Sequence[Issue]) -> dict:
    """统计各级问题数量。"""
    levels = {ERROR: 0, WARNING: 0, INFO: 0}
    for issue in issues:
        levels[issue.level] = levels.get(issue.level, 0) + 1
    return {
        "total": len(issues),
        "errors": levels[ERROR],
        "warnings": levels[WARNING],
        "infos": levels[INFO],
    }


def is_healthy(midi: MidiFile) -> bool:
    """是否没有 error 级问题。"""
    return not any(i.level == ERROR for i in validate(midi))


__all__ = ["validate", "Issue", "summarize", "is_healthy", "ERROR", "WARNING", "INFO"]
