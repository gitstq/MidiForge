"""两个 MIDI 文件的音符级对比。"""

from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

from .notes import Note

Key = Tuple[int, int, int]


def _key(note: Note, tolerance: int) -> Key:
    """把音符映射到对比键：``(channel, pitch, 量化后的起始 tick)``。"""
    if tolerance <= 0:
        return (note.channel, note.pitch, note.start)
    return (note.channel, note.pitch, round(note.start / tolerance) * tolerance)


def diff_notes(
    before: Sequence[Note], after: Sequence[Note], tolerance: int = 0
) -> dict:
    """对比两组音符。

    Args:
        before: 原音符列表。
        after: 新音符列表。
        tolerance: 起始时间容差（tick）；0 表示必须完全一致。

    Returns:
        含 ``added`` / ``removed`` / ``modified`` / ``unchanged`` / ``similarity`` 的字典。
    """
    a_map: Dict[Key, Note] = {}
    for n in before:
        a_map.setdefault(_key(n, tolerance), n)
    b_map: Dict[Key, Note] = {}
    for n in after:
        b_map.setdefault(_key(n, tolerance), n)

    added: List[dict] = []
    removed: List[dict] = []
    modified: List[dict] = []
    unchanged = 0

    for key, note in b_map.items():
        old = a_map.get(key)
        if old is None:
            added.append({"note": note.to_dict(), "reason": "new"})
            continue
        changes = {}
        if old.duration != note.duration:
            changes["duration"] = {"before": old.duration, "after": note.duration}
        if old.velocity != note.velocity:
            changes["velocity"] = {"before": old.velocity, "after": note.velocity}
        if old.track != note.track:
            changes["track"] = {"before": old.track, "after": note.track}
        if changes:
            item = note.to_dict()
            item["changes"] = changes
            modified.append(item)
        else:
            unchanged += 1

    for key, note in a_map.items():
        if key not in b_map:
            removed.append({"note": note.to_dict(), "reason": "missing"})

    total = len(a_map) + len(b_map)
    similarity = (2.0 * unchanged / total) if total else 1.0
    return {
        "added": added,
        "removed": removed,
        "modified": modified,
        "unchanged": unchanged,
        "similarity": round(similarity, 4),
        "counts": {
            "added": len(added),
            "removed": len(removed),
            "modified": len(modified),
            "unchanged": unchanged,
        },
    }


def diff_midi(before, after, tempo_map=None, tolerance: int = 0) -> dict:
    """直接对比两个 :class:`MidiFile`（内部自动抽取音符）。"""
    from .notes import extract_notes

    a_notes = extract_notes(before, tempo_map=tempo_map)
    b_notes = extract_notes(after, tempo_map=tempo_map)
    result = diff_notes(a_notes, b_notes, tolerance=tolerance)
    result["before"] = {
        "notes": len(a_notes),
        "tracks": len(before.tracks),
        "end_tick": before.end_tick,
    }
    result["after"] = {
        "notes": len(b_notes),
        "tracks": len(after.tracks),
        "end_tick": after.end_tick,
    }
    return result


def format_diff(result: dict, limit: int = 20) -> str:
    """把 diff 结果渲染成人类可读文本。"""
    counts = result["counts"]
    lines: List[str] = []
    lines.append("相似度: %.1f%%" % (result["similarity"] * 100))
    lines.append(
        "新增 %d / 删除 %d / 修改 %d / 不变 %d"
        % (counts["added"], counts["removed"], counts["modified"], counts["unchanged"])
    )
    for label, items in (
        ("新增", result["added"]),
        ("删除", result["removed"]),
        ("修改", result["modified"]),
    ):
        if not items:
            continue
        lines.append("")
        lines.append("── %s（最多显示 %d 条）" % (label, limit))
        for item in items[:limit]:
            note = item["note"]
            base = "  %-4s ch%-2d tick=%-6d vel=%-3d dur=%d" % (
                note["note"],
                note["channel"],
                note["start_tick"],
                note["velocity"],
                note["duration_ticks"],
            )
            if "changes" in item:
                detail = ", ".join(
                    "%s: %s→%s" % (k, v["before"], v["after"])
                    for k, v in item["changes"].items()
                )
                base += "  [%s]" % detail
            lines.append(base)
        if len(items) > limit:
            lines.append("  ... 其余 %d 条已省略" % (len(items) - limit))
    return "\n".join(lines)


__all__ = ["diff_notes", "diff_midi", "format_diff"]
