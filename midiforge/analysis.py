"""音乐内容分析：调性、和弦、节奏与力度分布、轨道概览。

全部为零依赖确定性算法（不联网、不随机），同一输入必得同一输出。
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict, List, Optional, Sequence, Tuple

from .events import PROGRAM_CHANGE, ChannelEvent
from .gm import (
    DRUM_CHANNEL,
    fifths_of_pitch_class,
    key_name,
    note_name,
    program_name,
    ticks_to_note_name,
)
from .notes import Note, max_polyphony
from .tempo import TempoMap

# Krumhansl-Kessler 调性轮廓（用于调性猜测）
_MAJOR_PROFILE = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
_MINOR_PROFILE = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

#: 和弦模板：名称 → 相对根音的半音集合
CHORD_TEMPLATES: List[Tuple[str, Tuple[int, ...]]] = [
    ("maj7", (0, 4, 7, 11)),
    ("maj9", (0, 2, 4, 7, 11)),
    ("min9", (0, 2, 3, 7, 10)),
    ("dom7", (0, 4, 7, 10)),
    ("min7", (0, 3, 7, 10)),
    ("dim7", (0, 3, 6, 9)),
    ("m7b5", (0, 3, 6, 10)),
    ("maj6", (0, 4, 7, 9)),
    ("min6", (0, 3, 7, 9)),
    ("add9", (0, 2, 4, 7)),
    ("sus4", (0, 5, 7)),
    ("sus2", (0, 2, 7)),
    ("aug", (0, 4, 8)),
    ("dim", (0, 3, 6)),
    ("maj", (0, 4, 7)),
    ("min", (0, 3, 7)),
    ("5", (0, 7)),
]


# ---------------------------------------------------------------- 调性


def pitch_class_histogram(notes: Sequence[Note]) -> List[float]:
    """按时值加权统计 12 个音级（返回长度 12 的列表，单位：tick）。"""
    hist = [0.0] * 12
    for n in notes:
        if n.is_drum:
            continue
        hist[n.pitch % 12] += max(1.0, float(n.duration))
    return hist


def guess_key(notes: Sequence[Note]) -> dict:
    """用 Krumhansl-Kessler 轮廓相关法猜测调性。

    Returns:
        ``{"key": "C", "scale": "major", "fifths": 0, "confidence": 0.83}``
        音符不足（少于 8 个非打击乐音符）时 confidence 为 0，key 为 ``"?"``。
    """
    melodic = [n for n in notes if not n.is_drum]
    if len(melodic) < 8:
        return {"key": "?", "scale": "major", "fifths": 0, "confidence": 0.0}
    hist = pitch_class_histogram(melodic)
    total = sum(hist) or 1.0
    norm = [h / total for h in hist]
    best = (-2.0, 0, False)
    for root in range(12):
        for minor, profile in ((False, _MAJOR_PROFILE), (True, _MINOR_PROFILE)):
            rotated = [profile[(pc - root) % 12] for pc in range(12)]
            score = _pearson(norm, rotated)
            if score > best[0]:
                best = (score, root, minor)
    score, root, minor = best
    # 调号 = 关系大调的五度圈位置（小调与其关系大调共用调号）
    major_root = (root + 3) % 12 if minor else root
    fifths = fifths_of_pitch_class(major_root)
    confidence = max(0.0, min(1.0, (score + 1) / 2))
    return {
        "key": note_name(root + 60)[:-1],
        "scale": "minor" if minor else "major",
        "fifths": fifths,
        "confidence": round(confidence, 3),
        "key_label": note_name(root + 60)[:-1] + ("m" if minor else ""),
    }


def _pearson(a: Sequence[float], b: Sequence[float]) -> float:
    n = len(a)
    ma = sum(a) / n
    mb = sum(b) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    da = sum((x - ma) ** 2 for x in a) ** 0.5
    db = sum((y - mb) ** 2 for y in b) ** 0.5
    if da == 0 or db == 0:
        return 0.0
    return num / (da * db)


# ---------------------------------------------------------------- 和弦


def chord_at(pitches: Sequence[int]) -> str:
    """给定同时发声的音高集合，识别和弦名称。

    Args:
        pitches: 音高（0-127），重复音高会被去重。

    Returns:
        形如 ``"Cmaj7"`` 的和弦名；无法匹配时返回 ``"?"``。
    """
    pcs = sorted({p % 12 for p in pitches})
    if len(pcs) < 2:
        return "?"
    for root in pcs:
        intervals = sorted({(pc - root) % 12 for pc in pcs})
        for name, template in CHORD_TEMPLATES:
            if tuple(intervals) == tuple(sorted(template)):
                return note_name(root + 60)[:-1] + name
    if len(pcs) == 2:
        return "%s+%s" % (note_name(pcs[0] + 60)[:-1], note_name(pcs[1] + 60)[:-1])
    return "?"


def chord_progression(
    notes: Sequence[Note], grid: Optional[int] = None
) -> List[dict]:
    """按时隙切片识别和弦进行。

    Args:
        notes: 音符列表。
        grid: 切片粒度（tick）。缺省取 ``division / 2``（八分音符）。

    Returns:
        ``[{"start", "end", "chord", "pitches"}, ...]``，无法识别的时隙会被跳过。
    """
    melodic = [n for n in notes if not n.is_drum]
    if not melodic:
        return []
    if grid is None:
        grid = 240
    if grid <= 0:
        raise ValueError("grid 必须为正")
    end_tick = max(n.end for n in melodic)
    slices: List[dict] = []
    for start in range(0, end_tick + 1, grid):
        active = [
            n.pitch
            for n in melodic
            if n.start <= start < n.end
        ]
        if len({p % 12 for p in active}) < 2:
            continue
        chord = chord_at(active)
        if chord == "?":
            continue
        slices.append(
            {
                "start": start,
                "end": start + grid,
                "chord": chord,
                "pitches": sorted(set(active)),
            }
        )
    return _collapse(slices)


def _collapse(slices: List[dict]) -> List[dict]:
    """合并相邻且和弦相同的切片。"""
    out: List[dict] = []
    for s in slices:
        if out and out[-1]["chord"] == s["chord"] and out[-1]["end"] == s["start"]:
            out[-1]["end"] = s["end"]
        else:
            out.append(dict(s))
    return out


# ---------------------------------------------------------------- 统计


def velocity_histogram(notes: Sequence[Note], bins: int = 8) -> Dict[str, int]:
    """力度直方图，键为 ``"0-15"`` 形式的区间名。"""
    size = 128 // bins
    out: Dict[str, int] = {}
    for n in notes:
        idx = min(bins - 1, n.velocity // size)
        key = "%d-%d" % (idx * size, idx * size + size - 1)
        out[key] = out.get(key, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: int(kv[0].split("-")[0])))


def rhythm_histogram(notes: Sequence[Note], division: int) -> Dict[str, int]:
    """时值分布，键为 ``"1/4"`` 形式的音符名。"""
    counter: Counter = Counter()
    for n in notes:
        counter[ticks_to_note_name(n.duration, division)] += 1
    return dict(counter.most_common())


def repeated_patterns(notes: Sequence[Note], n: int = 4, top: int = 5) -> List[dict]:
    """统计最常出现的音高-时值 n-gram（用于发现重复乐句 / 循环）。

    Args:
        notes: 音符列表（建议传入单轨旋律）。
        n: n-gram 长度。
        top: 返回前几名。

    Returns:
        ``[{"pattern": "C4:480 E4:240 ...", "count": 3}, ...]``
    """
    melodic = [x for x in notes if not x.is_drum]
    if len(melodic) < n:
        return []
    seq = ["%s:%s" % (x.label, ticks_to_note_name(x.duration, 480)) for x in melodic]
    counter: Counter = Counter(
        " ".join(seq[i : i + n]) for i in range(len(seq) - n + 1)
    )
    return [
        {"pattern": p, "count": c} for p, c in counter.most_common(top) if c > 1
    ]


def channel_programs(midi) -> Dict[int, int]:
    """统计每个通道最后使用的音色编号（无 program_change 时为 0）。"""
    programs: Dict[int, int] = {}
    for track in midi.tracks:
        for ev in sorted(track.channel_events(), key=lambda e: e.tick):
            if ev.etype == PROGRAM_CHANGE:
                programs[ev.channel] = ev.data1
    return programs


def track_summaries(midi, notes: Sequence[Note]) -> List[dict]:
    """逐轨道概览。"""
    by_track: Dict[int, List[Note]] = defaultdict(list)
    for n in notes:
        by_track[n.track].append(n)
    programs = channel_programs(midi)
    out: List[dict] = []
    for idx, track in enumerate(midi.tracks):
        items = by_track.get(idx, [])
        channels = sorted({n.channel for n in items})
        pitches = [n.pitch for n in items]
        out.append(
            {
                "index": idx,
                "name": track.name or "(unnamed)",
                "events": len(track.events),
                "notes": len(items),
                "channels": channels,
                "programs": {c: program_name(programs.get(c, 0)) for c in channels},
                "drum": any(n.is_drum for n in items),
                "pitch_low": note_name(min(pitches)) if pitches else None,
                "pitch_high": note_name(max(pitches)) if pitches else None,
                "end_tick": track.end_tick,
            }
        )
    return out


def stats(midi, notes: Optional[Sequence[Note]] = None, tempo_map=None) -> dict:
    """生成完整的统计报告字典。

    Args:
        midi: MIDI 对象。
        notes: 已抽取的音符（缺省内部自动抽取）。
        tempo_map: 时间映射（缺省内部构造）。
    """
    if tempo_map is None:
        tempo_map = TempoMap.from_midi(midi)
    if notes is None:
        from .notes import extract_notes

        notes = extract_notes(midi, tempo_map=tempo_map)
    melodic = [n for n in notes if not n.is_drum]
    pitches = [n.pitch for n in notes]
    durations = [n.duration for n in notes]
    velocities = [n.velocity for n in notes]
    total_sec = 0.0
    if notes:
        total_sec = tempo_map.tick_to_seconds(max(n.end for n in notes))
    return {
        "notes": len(notes),
        "melodic_notes": len(melodic),
        "drum_notes": len(notes) - len(melodic),
        "unique_pitches": len(set(pitches)),
        "pitch_range": (
            [note_name(min(pitches)), note_name(max(pitches))] if pitches else None
        ),
        "duration_seconds": round(total_sec, 3),
        "duration_ticks": max((n.end for n in notes), default=0),
        "avg_velocity": round(sum(velocities) / len(velocities), 2) if velocities else 0,
        "min_velocity": min(velocities) if velocities else 0,
        "max_velocity": max(velocities) if velocities else 0,
        "avg_duration_ticks": round(sum(durations) / len(durations), 1) if durations else 0,
        "notes_per_second": round(len(notes) / total_sec, 2) if total_sec > 0 else 0.0,
        "max_polyphony": max_polyphony(notes),
        "key": guess_key(notes),
        "chords": chord_progression(notes, grid=midi.ticks_per_quarter or 480)[:24],
        "rhythm_histogram": rhythm_histogram(notes, midi.ticks_per_quarter),
        "velocity_histogram": velocity_histogram(notes),
        "repeated_patterns": repeated_patterns(melodic),
        "tracks": track_summaries(midi, notes),
    }


__all__ = [
    "stats",
    "guess_key",
    "chord_at",
    "chord_progression",
    "rhythm_histogram",
    "velocity_histogram",
    "repeated_patterns",
    "track_summaries",
    "channel_programs",
    "pitch_class_histogram",
    "CHORD_TEMPLATES",
]
