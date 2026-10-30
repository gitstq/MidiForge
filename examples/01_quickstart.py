#!/usr/bin/env python3
"""示例 1：快速上手 —— 读取、概览、提取音符、写回。

运行：
    python examples/01_quickstart.py
"""

import os
import tempfile

import midiforge
from midiforge import extract_notes, write_file


def main() -> None:
    # 没有任何素材？先生成一首内置示例曲
    midi = midiforge.demo_song(bpm=108, bars=2)
    path = os.path.join(tempfile.gettempdir(), "midiforge_quickstart.mid")
    write_file(midi, path)
    print("已生成：%s" % path)

    # ---- 概览
    print("\n── 概览 ──")
    for key, value in midi.summary().items():
        print("  %-16s %s" % (key, value))

    # ---- 音符
    print("\n── 前 8 个音符 ──")
    notes = extract_notes(midi, include_drums=False)
    for n in notes[:8]:
        print(
            "  %-4s 力度=%-3d tick %d→%d (%.3fs)"
            % (n.label, n.velocity, n.start, n.end, n.start_sec)
        )

    # ---- 写回
    out = os.path.join(tempfile.gettempdir(), "midiforge_quickstart_out.mid")
    write_file(midi, out)
    print("\n已写出：%s" % out)

    # ---- 自检：写回的文件必须能通过校验
    issues = midiforge.validate(midiforge.read_file(out))
    print("校验结果：%s" % ("✅ 无问题" if not issues else "❌ %d 条" % len(issues)))


if __name__ == "__main__":
    main()
