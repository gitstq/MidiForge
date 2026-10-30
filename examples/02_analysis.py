#!/usr/bin/env python3
"""示例 2：音乐内容分析 —— 调性、和弦、直方图、重复乐句。

运行：
    python examples/02_analysis.py
"""

import midiforge
from midiforge import chord_at, chord_progression, extract_notes, guess_key, stats
from midiforge.analysis import (
    pitch_class_histogram,
    rhythm_histogram,
    velocity_histogram,
)
from midiforge.gm import NOTE_NAMES_SHARP


def main() -> None:
    midi = midiforge.demo_song(bpm=96, bars=4)
    notes = extract_notes(midi, include_drums=False)

    # ---- 调性
    key = guess_key(notes)
    print("── 调性 ──")
    print("  %s %s（置信度 %.2f）" % (key["key"], key["scale"], key["confidence"]))

    # ---- 和弦
    print("\n── 和弦进行 ──")
    for item in chord_progression(notes, grid=midi.ticks_per_quarter * 2):
        print(
            "  tick %-6d %-6s %s"
            % (item["start"], item["chord"], item["pitches"])
        )

    print("\n── 单个和弦识别 ──")
    for pitches in ([60, 64, 67], [60, 63, 67], [60, 64, 67, 70], [62, 65, 69]):
        print("  %-18s → %s" % (pitches, chord_at(pitches)))

    # ---- 直方图
    # 音级直方图以「时长加权」，返回长度 12 的列表（索引 = pitch class）
    print("\n── 音级直方图（时长加权） ──")
    hist = pitch_class_histogram(notes)
    total = sum(hist) or 1.0
    for pc, weight in sorted(enumerate(hist), key=lambda kv: -kv[1]):
        if weight <= 0:
            continue
        print(
            "  %-3s %8.0f tick  %5.1f%%"
            % (NOTE_NAMES_SHARP[pc], weight, weight / total * 100)
        )

    print("\n── 时值直方图 ──")
    for name, count in sorted(
        rhythm_histogram(notes, midi.ticks_per_quarter).items(), key=lambda kv: -kv[1]
    ):
        print("  %-8s %d" % (name, count))

    print("\n── 力度直方图 ──")
    for name, count in velocity_histogram(notes).items():
        print("  %-10s %d" % (name, count))

    # ---- 汇总
    print("\n── stats() 摘要 ──")
    s = stats(midi)
    for key in (
        "notes",
        "melodic_notes",
        "drum_notes",
        "duration_seconds",
        "notes_per_second",
        "pitch_range",
        "avg_velocity",
        "max_polyphony",
        "unique_pitches",
    ):
        print("  %-18s %s" % (key, s.get(key)))

    print("\n── 重复乐句 ──")
    for item in s.get("repeated_patterns", [])[:5]:
        print("  ×%-3d %s" % (item["count"], item["pattern"]))


if __name__ == "__main__":
    main()
