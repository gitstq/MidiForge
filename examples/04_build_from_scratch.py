#!/usr/bin/env python3
"""示例 4：从零构造 MIDI —— 手写事件 vs 音符表生成。

演示两种构造方式：
  1. 手工组装事件（完全掌控每一个字节）
  2. from_notes() 一行生成（适合程序化作曲 / 算法生成）

运行：
    python examples/04_build_from_scratch.py
"""

import os
import tempfile

import midiforge
from midiforge import ChannelEvent, MetaEvent, from_notes, new_midi, write_file
from midiforge.events import make_tempo
from midiforge.gm import DRUM_CHANNEL


def by_hand(path: str) -> None:
    """手工组装：C 大调音阶上行 + 简单鼓点。"""
    midi = new_midi(format=1, division=480, tracks=2)

    # ---- 轨道 0：指挥轨（tempo + 拍号 + 调号）
    conductor = midi.tracks[0]
    conductor.name = "conductor"
    conductor.add(make_tempo(0, 100))                                    # 100 BPM
    conductor.add(MetaEvent(tick=0, mtype=0x58, data=bytes([4, 2, 24, 8])))  # 4/4
    conductor.add(MetaEvent(tick=0, mtype=0x59, data=bytes([0, 0])))     # C major
    conductor.add(MetaEvent(tick=3840, mtype=0x2F, data=b""))            # end_of_track

    # ---- 轨道 1：旋律 + 鼓
    music = midi.tracks[1]
    music.name = "scale & drums"
    music.add(MetaEvent(tick=0, mtype=0x03, data="scale & drums".encode()))
    music.add(ChannelEvent(tick=0, channel=0, etype=0xC, data1=0))       # Acoustic Grand

    scale = [60, 62, 64, 65, 67, 69, 71, 72]                            # C major scale
    for i, pitch in enumerate(scale):
        start = i * 240                                                  # 每音 1/8 音符
        music.add(ChannelEvent(tick=start, channel=0, etype=0x9, data1=pitch, data2=90))
        music.add(ChannelEvent(tick=start + 200, channel=0, etype=0x8, data1=pitch, data2=0))

    for i in range(4):                                                    # 四分音符上的底鼓
        music.add(ChannelEvent(tick=i * 480, channel=DRUM_CHANNEL, etype=0x9, data1=36, data2=100))
        music.add(ChannelEvent(tick=i * 480 + 60, channel=DRUM_CHANNEL, etype=0x8, data1=36, data2=0))

    music.add(MetaEvent(tick=music.end_tick, mtype=0x2F, data=b""))       # end_of_track

    write_file(midi, path)
    print("手工构造 → %s" % path)


def by_notes(path: str) -> None:
    """用音符表生成：一个琶音循环。"""
    notes = []
    arp = [60, 64, 67, 72, 67, 64]
    for bar in range(4):
        for i, pitch in enumerate(arp):
            notes.append((pitch, bar * 1920 + i * 320, 300, 80))
    midi = from_notes(notes, bpm=132, division=480, channel=1, program=25, name="arp")
    write_file(midi, path)
    print("音符表生成 → %s" % path)


def main() -> None:
    tmp = tempfile.mkdtemp(prefix="midiforge_build_")
    hand = os.path.join(tmp, "hand.mid")
    gen = os.path.join(tmp, "generated.mid")
    by_hand(hand)
    by_notes(gen)

    for path in (hand, gen):
        midi = midiforge.read_file(path)
        issues = [i for i in midiforge.validate(midi) if i.level == "error"]
        print(
            "\n%s：%d 轨 / %.2f 秒 / %d 音符 / 校验 %s"
            % (
                os.path.basename(path),
                len(midi.tracks),
                midi.duration_seconds(),
                len(midiforge.extract_notes(midi)),
                "✅ 无 error" if not issues else "❌ %d 个 error" % len(issues),
            )
        )

    print("\n── 手工构造曲的钢琴卷帘 ──")
    print(midiforge.piano_roll(midiforge.extract_notes(midiforge.read_file(hand)), width=64, max_rows=14))
    print("临时目录：%s" % tmp)


if __name__ == "__main__":
    main()
