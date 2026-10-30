"""导出：CSV / JSON / Markdown 表格 / ASCII 钢琴卷帘。"""

from __future__ import annotations

import csv
import io
import json
from typing import List, Optional, Sequence

from .gm import note_name
from .midifile import MidiFile
from .notes import Note
from .tempo import TempoMap

CSV_HEADER = [
    "track",
    "channel",
    "pitch",
    "note",
    "velocity",
    "start_tick",
    "end_tick",
    "duration_ticks",
    "start_sec",
    "duration_sec",
    "drum",
]


def notes_to_csv(notes: Sequence[Note]) -> str:
    """音符列表 → CSV 文本（含表头，UTF-8，LF 换行）。"""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(CSV_HEADER)
    for n in notes:
        writer.writerow(
            [
                n.track,
                n.channel,
                n.pitch,
                n.label,
                n.velocity,
                n.start,
                n.end,
                n.duration,
                round(n.start_sec, 4),
                round(n.duration_sec, 4),
                int(n.is_drum),
            ]
        )
    return buf.getvalue()


def notes_to_json(notes: Sequence[Note], indent: Optional[int] = 2) -> str:
    """音符列表 → JSON 文本。"""
    return json.dumps(
        [n.to_dict() for n in notes], ensure_ascii=False, indent=indent
    )


def notes_to_markdown(notes: Sequence[Note], limit: int = 100) -> str:
    """音符列表 → Markdown 表格（超长时截断并注明）。"""
    lines: List[str] = []
    lines.append("| # | 轨道 | 通道 | 音高 | 力度 | 起始 tick | 时值 | 起始秒 |")
    lines.append("|---:|---:|---:|:---|---:|---:|---:|---:|")
    for i, n in enumerate(notes[:limit], 1):
        lines.append(
            "| %d | %d | %d | %s | %d | %d | %d | %.3f |"
            % (
                i,
                n.track,
                n.channel,
                n.label,
                n.velocity,
                n.start,
                n.duration,
                n.start_sec,
            )
        )
    if len(notes) > limit:
        lines.append("")
        lines.append("> 共 %d 个音符，此处仅列出前 %d 个。" % (len(notes), limit))
    return "\n".join(lines)


def piano_roll(
    notes: Sequence[Note],
    width: int = 72,
    max_rows: int = 24,
    tick_span: Optional[int] = None,
) -> str:
    """把音符画成 ASCII 钢琴卷帘（终端友好）。

    Args:
        notes: 音符列表。
        width: 字符宽度（时间轴分辨率）。
        max_rows: 最多显示多少个音高行（取音域内均匀采样）。
        tick_span: 时间跨度；缺省取最后一个音符的结束位置。

    Returns:
        多行字符串；无音符时返回提示文本。
    """
    if not notes:
        return "(没有音符)"
    width = max(8, min(width, 400))
    end = tick_span or max(n.end for n in notes)
    start = min(n.start for n in notes)
    span = max(1, end - start)
    pitches = sorted({n.pitch for n in notes})
    lo = min(pitches)
    hi = max(pitches)
    if hi - lo + 1 > max_rows:
        step = (hi - lo) / float(max_rows - 1)
        sampled = sorted({lo + int(round(i * step)) for i in range(max_rows)})
        row_of = lambda p: min(  # noqa: E731
            range(len(sampled)), key=lambda i: abs(sampled[i] - p)
        )
    else:
        sampled = list(range(lo, hi + 1))
        row_of = lambda p: max(0, min(len(sampled) - 1, p - lo))  # noqa: E731

    grid: List[List[str]] = [["·"] * width for _ in sampled]
    bucket: List[set] = [set() for _ in sampled]
    for n in notes:
        row = row_of(n.pitch)
        bucket[row].add(n.pitch)
        col_start = int((n.start - start) * (width - 1) / span)
        col_end = int((n.end - start) * (width - 1) / span)
        col_end = max(col_start, min(width - 1, col_end))
        for col in range(col_start, col_end + 1):
            grid[row][col] = "█"
        grid[row][col_start] = "▏" if col_end > col_start else "▏"

    lines: List[str] = []
    for i, row in enumerate(grid):
        # 采样模式下每row是一个「音高桶」，用桶内最低音标注，避免标签与实际音高错位
        label = note_name(min(bucket[i])) if bucket[i] else note_name(sampled[i])
        lines.append("%-5s │%s" % (label, "".join(row)))
    lines.append("      └" + "─" * width)
    lines.append(
        "       %d → %d tick（%d 个音高，%d 个音符）" % (start, end, len(sampled), len(notes))
    )
    return "\n".join(lines)


def midi_to_json(midi: MidiFile, tempo_map: Optional[TempoMap] = None, notes=None) -> str:
    """整份 MIDI 的完整 JSON 快照（概览 + 速度表 + 事件 + 音符）。"""
    if tempo_map is None:
        tempo_map = TempoMap.from_midi(midi)
    if notes is None:
        from .notes import extract_notes

        notes = extract_notes(midi, tempo_map=tempo_map)
    payload = {
        "summary": midi.summary(),
        "tempo_map": tempo_map.to_list(),
        "tracks": [
            {
                "index": i,
                "name": t.name,
                "events": [e.to_dict() for e in sorted(t.events, key=lambda e: e.tick)[:2000]],
            }
            for i, t in enumerate(midi.tracks)
        ],
        "notes": [n.to_dict() for n in notes],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def write_text(path: str, text: str) -> None:
    """把文本写入文件（UTF-8）。"""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


__all__ = [
    "notes_to_csv",
    "notes_to_json",
    "notes_to_markdown",
    "piano_roll",
    "midi_to_json",
    "write_text",
    "CSV_HEADER",
]
