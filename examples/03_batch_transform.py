#!/usr/bin/env python3
"""示例 3：批量变换流水线 —— 移调 → 量化 → 力度压缩 → 裁剪 → 校验 → 导出。

演示 MidiForge 的「默认返回新对象」设计：每一步都可独立回溯，互不污染。

运行：
    python examples/03_batch_transform.py
"""

import os
import tempfile

import midiforge
from midiforge import (
    clean,
    demo_song,
    notes_to_csv,
    quantize,
    read_file,
    trim,
    validate,
    velocity,
    write_file,
)


def pipeline(midi, division):
    """一条典型的处理流水线。"""
    step1 = midiforge.transpose(midi, semitones=+2)          # 升 2 个半音
    step2 = quantize(step1, grid=division // 4, strength=0.8)  # 量化到 16 分音符，80% 强度
    step3 = velocity(step2, scale=0.85, offset=-3)             # 力度压到 85% 并整体 -3
    step4 = trim(step3, start=0, end=division * 8)             # 只保留前 2 小节
    step5 = clean(step4)                                       # 收尾：修复孤儿/未闭合/重复
    return step5


def main() -> None:
    tmp = tempfile.mkdtemp(prefix="midiforge_batch_")
    src = os.path.join(tmp, "raw.mid")
    write_file(demo_song(bpm=120, bars=4), src)

    midi = read_file(src)
    division = midi.ticks_per_quarter
    print("源：%d 轨 / %d tick / BPM %.1f" % (len(midi.tracks), midi.end_tick, 120.0))

    out = pipeline(midi, division)
    dst = os.path.join(tmp, "processed.mid")
    write_file(out, dst)
    print("产物：%s（%d tick）" % (dst, out.end_tick))

    # ---- 校验：流水线每一步的产物都必须是「健康」的
    issues = validate(read_file(dst))
    errors = [i for i in issues if i.level == "error"]
    print("校验：%s" % ("✅ 健康" if not errors else "❌ %d 个 error" % len(errors)))
    for it in issues[:5]:
        print("  %s %-7s %s" % (it.code, it.level, it.message))

    # ---- 导出 CSV 供 Excel / pandas 使用
    csv_path = os.path.join(tmp, "processed.csv")
    notes = midiforge.extract_notes(out)
    with open(csv_path, "w", encoding="utf-8") as fh:
        fh.write(notes_to_csv(notes))
    print("音符表：%s（%d 行）" % (csv_path, len(notes)))

    # ---- 差异对比：源 vs 产物
    report = midiforge.diff_midi(midi, out)
    print("相似度：%.1f%%" % (report["similarity"] * 100))
    c = report["counts"]
    print(
        "新增 %(added)d / 删除 %(removed)d / 修改 %(modified)d / 不变 %(unchanged)d" % c
    )
    print(
        "变更明细：新增 %d 条 / 删除 %d 条 / 修改 %d 条（详见 report['added'] 等）"
        % (len(report["added"]), len(report["removed"]), len(report["modified"]))
    )
    print("\n临时目录：%s" % tmp)


if __name__ == "__main__":
    main()
