<div align="center">

# 🎼 MidiForge

**零依赖的 MIDI（Standard MIDI File）解析 · 分析 · 变换 · 校验工具箱**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Dependencies](https://img.shields.io/badge/dependencies-0-brightgreen.svg)](https://github.com/gitstq/MidiForge/blob/main/pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Tests](https://img.shields.io/badge/tests-380%20passed-brightgreen.svg)](./tests)
[![Offline](https://img.shields.io/badge/network-not%20required-orange.svg)](#-核心特性)

**🌐 语言切换 / Language Switcher：**

[简体中文](./README.md) · [繁體中文](./README.zh-TW.md) · [English](./README.en.md)

</div>

---

## 🎉 项目介绍

MIDI 文件（`.mid`，Standard MIDI File，简称 SMF）是音乐制作、游戏音频、乐谱软件、硬件音源之间最通用的交换格式。它结构紧凑、信息密度高，但同时也是出了名的「难读」：变长量（VLQ）编码、running status 省略、SMPTE 时基、多轨 tempo map、力度为 0 的 note-on 等价于 note-off……任何一处细节理解偏差，读出来的结果就会错得悄无声息。

现实中的痛点通常是这样的：

- 🎹 想统计一首曲子的调性、和弦进行、力度分布，却要先装 `mido` / `pretty_midi` / `music21`，再拉一堆传递依赖；
- 🐛 手上有一个损坏的 `.mid`，播放器直接拒绝打开，却不知道到底坏在第几个字节；
- 🔁 想把几百个 MIDI 批量移调、量化、裁剪，只能打开 DAW 手工点；
- 📊 想做音乐信息检索（MIR）的原型，但现有库要么太重、要么 API 不透明、要么输出不可复现。

**MidiForge 就是为了解决这些问题而生的。** 它是一个**纯 Python 标准库实现**、**零第三方依赖**、**完全离线**的 MIDI 处理工具箱，同时提供 **Python 库 API** 与 **命令行工具**两种使用姿势：

```python
import midiforge
midi = midiforge.read_file("song.mid")
print(midi.summary()["duration_seconds"])   # 8.0
```

```bash
midiforge info song.mid
```

它不追求「成为一个 DAW」，而是追求成为一把**趁手、可靠、可嵌入任何流水线**的瑞士军刀：读得懂、改得动、查得清、验得准。

> **为什么是「零依赖」？**
> 音频/MIR 场景的依赖树 notoriously 脆弱（`numpy` 版本冲突、`pybind11` 编译失败、系统缺 `libsndfile`……）。MidiForge 只使用 `argparse` / `struct` / `dataclasses` / `math` / `random` / `json` / `csv` 这类标准库模块，因此它可以在**受限环境**（离线内网、CI 容器、嵌入式 Python、教学机房）里直接 `pip install` 后开箱即用，也永远不用担心某天被上游依赖的 breaking change 拖垮。

---

## ✨ 核心特性

### 🔍 解析与写入：把规范吃透

| 能力 | 说明 |
|---|---|
| 📄 Format 0 / 1 / 2 | 单轨合并、多轨同步、多曲集三种结构全部支持 |
| 🧩 MThd / MTrk 块 | 未知块（如 `XFIH`、厂商私有块）安全跳过，不会误报失败 |
| ⚡ Running status | 完整还原省略状态字节的事件流 |
| 🎛 通道事件 | Note On/Off、Poly Aftertouch、CC、Program Change、Channel Aftertouch、Pitch Bend |
| 🏷 元事件 | Tempo、拍号、调号、轨道名、歌词、标记、音轨文本、SMPTE Offset 等 |
| 📡 SysEx | `0xF0` / `0xF7` 分段系统独占消息 |
| ⏱ SMPTE 时基 | division 为负时的帧率（24/25/29/30 fps）与每帧 tick 数正确还原 |
| 🚨 偏移级报错 | 解析失败时给出**出错字节偏移**与人类可读原因，而不是一句 `struct.error` |

### 🧠 音乐内容分析：不只是「读出来」

- **🎯 调性识别**：基于 Krumhansl-Kessler 音级轮廓 + 皮尔逊相关系数，输出调性、大小调与置信度（如 `C major（置信度 0.97）`）
- **🎸 和弦识别**：按同时发声的音集合匹配模板，覆盖 `maj / min / dim / aug / sus4 / maj7 / min7 / dom7 / m7b5 / dim7 / add9 / 6` 等
- **📈 分布统计**：音级直方图、力度直方图、时值（节奏）直方图、音符密度、复音数曲线、最大同时发声数
- **🔁 重复乐句检测**：自动找出反复出现的旋律片段及其出现次数
- **🎼 音色盘点**：每个通道的 Program（GM 音色名）、鼓组通道（ch 9）按 GM 鼓图映射为军鼓/底鼓/踩镲等名称

### 🛠 变换与生成：批量处理的主力

`transpose` 移调 · `quantize` 量化（带强度与 swing） · `velocity` 力度缩放/平移/动态压缩 · `humanize` 人性化扰动（固定 seed，结果可复现） · `set_bpm` / `scale_tempo` 速度处理 · `trim` 区间裁剪（自动修补跨越边界的音符） · `merge_tracks` / `split_by_channel` 轨道重组 · `to_format` 格式转换 · `strip` 按类别剔除事件 · `clean` 一键修复常见损坏。

所有变换函数默认 **返回新对象**（`inplace=False`），不会偷偷修改你的原始数据。

### ✅ 结构校验：20 条规则的「体检报告」

内置 **MF001–MF020** 共 20 条规则，覆盖 `error / warning / info` 三级：缺少 `end_of_track`、孤儿音符关、未闭合音符开、零时长音符、同音高重叠、tempo 缺失或异常、拍号缺失、`end_of_track` 之后仍有事件、力度越界、时基为 0、未知元事件……

```bash
$ midiforge validate broken.mid
MF004  error   音符关 ch1 60 没有对应的音符开 [track=2] @1430
MF005  warning 音符开 ch0 72 未闭合 [track=1] @960
── 合计 2 条（error 1 / warning 1 / info 0）
```

### 🖥 命令行：18 个开箱即用的子命令

`info` · `validate`（别名 `lint`） · `notes` · `stats`（别名 `analyze`） · `roll` · `diff` · `demo` · `transpose` · `quantize` · `velocity` · `humanize` · `tempo` · `trim` · `merge` · `split` · `convert` · `strip` · `clean`

> 🎁 **没有 MIDI 素材？** `midiforge demo -o song.mid` 会直接生成一首 4 轨道（指挥轨 / 旋律 / 和声 / 鼓）的示例曲，方便立刻试玩全部功能。

### 📤 导出与可视化

- `notes_to_csv` / `notes_to_json` / `notes_to_markdown`：把音符表直接喂给 Excel、pandas 或文档
- `piano_roll`：**终端 ASCII 钢琴卷帘**，无需图形界面即可肉眼看出旋律轮廓
- `diff_midi`：两个文件的音符级差异对比（新增 / 删除 / 修改 / 不变 + 相似度百分比）

### 🔒 工程属性

| 属性 | 说明 |
|---|---|
| 零依赖 | 只用 Python 标准库，`pip install` 后无任何传递依赖 |
| 离线 | 运行期不发起任何网络请求 |
| 确定性 | 除 `humanize` 外全部为纯函数；`humanize` 支持固定 `seed` 复现 |
| 类型友好 | 全部使用 `dataclasses` + type hints，附带 `py.typed` |
| 测试充分 | 380 项单元测试，覆盖 VLQ、解析、写入、时值、分析、变换、校验、CLI |
| 跨平台 | 纯 Python，Windows / macOS / Linux 行为一致 |

---

## 🚀 快速开始

### 📦 安装

```bash
# 方式一：从 PyPI 安装（推荐）
pip install midiforge

# 方式二：从源码安装（无需联网依赖）
git clone https://github.com/gitstq/MidiForge.git
cd MidiForge
pip install .

# 方式三：零安装，直接以模块方式运行
python -m midiforge --help
```

> **要求**：Python ≥ 3.8。无其它运行时依赖。

### ⚡ 60 秒上手

```bash
# 1) 生成一首内置示例曲（没有任何素材也能玩）
midiforge demo -o song.mid

# 2) 看一眼它长什么样
midiforge info song.mid

# 3) 做一次结构体检
midiforge validate song.mid

# 4) 分析音乐内容：调性、和弦、节奏、力度
midiforge stats song.mid

# 5) 在终端画出钢琴卷帘
midiforge roll song.mid --width 72

# 6) 整体移调 +3 半音并另存
midiforge transpose song.mid -s 3 -o song_up.mid
```

### 🐍 Python API 最小示例

```python
import midiforge

midi = midiforge.read_file("song.mid")

print(midi.format, midi.division, len(midi.tracks))   # 1 480 4
print(midi.duration_seconds())                         # 8.88

notes = midiforge.extract_notes(midi)
for n in notes[:5]:
    print(n.label, n.start, n.duration, n.velocity)

# 音乐分析
print(midiforge.guess_key(notes))        # {'key': 'C', 'scale': 'major', ...}
print(midiforge.chord_progression(notes))

# 变换后写回
up = midiforge.transpose(midi, semitones=3)
midiforge.write_file(up, "song_up.mid")
```

---

## 📖 详细使用指南

### 🖥 命令行全览

```bash
midiforge --help          # 总帮助
midiforge <command> --help  # 子命令帮助
midiforge --version
```

| 命令 | 用途 | 常用参数 |
|---|---|---|
| `info` | 文件概览 | `--json` |
| `validate` / `lint` | 结构校验 | `--json`、`--strict` |
| `notes` | 列出音符 | `--json`、`--no-drums`、`--limit N` |
| `stats` / `analyze` | 音乐内容分析 | `--json` |
| `roll` | ASCII 钢琴卷帘 | `--width N`、`--rows N` |
| `diff` | 两文件音符差异 | `--json`、`--tolerance N` |
| `demo` | 生成内置示例曲 | `--bpm`、`--bars`、`-o` |
| `transpose` | 移调 | `-s/--semitones N`、`--channels 0,1` |
| `quantize` | 量化 | `-g/--grid`（`16`、`1/16` 或 tick）、`--strength`、`--swing` |
| `velocity` | 力度调整 | `--scale`、`--offset`、`--ratio` |
| `humanize` | 人性化扰动 | `--tick N`、`--velocity N`、`--seed N` |
| `tempo` | 速度处理 | `--set BPM`、`--scale F`、`--stretch F` |
| `trim` | 区间裁剪 | `--start`、`--end` |
| `merge` | 合并所有轨道 | `-o` |
| `split` | 按通道拆分 | `-o` |
| `convert` | 格式转换 / 导出 | `--format 0\|1\|2`、`--to csv\|json\|md` |
| `strip` | 按类别剔除 | `--sysex`、`--cc`、`--program`、`--pitch-bend`、`--aftertouch`、`--lyrics`、`--markers` |
| `clean` | 修复常见损坏 | `-o` |

#### 典型组合

```bash
# 批量把一批 MIDI 统一成 120 BPM、量化到 16 分音符、力度压到 80%
for f in raw/*.mid; do
  midiforge tempo "$f" --set 120 -o "tmp1.mid" &&
  midiforge quantize tmp1.mid -g 16 -o "tmp2.mid" &&
  midiforge velocity tmp2.mid --scale 0.8 -o "out/$(basename "$f")"
done

# 导出音符表给 Excel / pandas
midiforge convert song.mid --to csv -o notes.csv

# 导出完整结构（含 tempo map）为 JSON
midiforge convert song.mid --to json -o song.json

# 裁剪第 2~4 小节（480 tpq 下每小节 1920 tick）
midiforge trim song.mid --start 1920 --end 7680 -o clip.mid

# 对比「原曲」与「人工改编版」的差异
midiforge diff original.mid arranged.mid
```

退出码约定：`0` 正常；`1` 校验发现 error；`2` 解析/写入/参数错误。可直接在 CI 中使用。

### 🐍 Python API 指南

#### 1️⃣ 读取与写入

```python
from midiforge import read_file, write_file, parse, serialize

midi = read_file("song.mid")          # 从磁盘
blob = open("song.mid", "rb").read()
midi = parse(blob)                    # 从字节流

data = serialize(midi)                # → bytes
write_file(midi, "out.mid")           # 写盘
```

#### 2️⃣ 文件模型

```python
midi.format          # 0 / 1 / 2
midi.division        # 480 表示 480 tpq；负数表示 SMPTE
midi.is_smpte        # bool
midi.ticks_per_quarter
midi.tracks          # List[Track]
midi.all_events()    # 所有轨道展开后的事件（按 tick 排序）
midi.tempo_events()  # 所有 tempo 元事件
midi.time_signatures()
midi.end_tick
midi.duration_seconds()
midi.track_by_name("melody")
midi.summary()       # → dict，一行概览
```

#### 3️⃣ 事件模型

```python
from midiforge import ChannelEvent, MetaEvent, SysExEvent

ev = ChannelEvent(tick=0, channel=0, etype=0x9, data1=60, data2=88)
ev.status            # 0x90
ev.type_name         # 'note_on'
ev.is_note_on        # True（力度 0 时为 False）
ev.is_note_off       # False（含「力度 0 的 note_on」）
ev.pitch             # 60
ev.velocity          # 88
ev.controller_name   # 'Sustain'（CC 事件）
ev.pitch_bend        # -8192 ~ 8191（弯音事件）

meta = MetaEvent(tick=0, mtype=0x51, data=b"\x07\xa1\x20")
meta.tempo           # 500000（微秒/四分音符）
meta.bpm             # 120.0

track_name = MetaEvent(tick=0, mtype=0x03, data="主旋律".encode())
track_name.text      # '主旋律'
```

#### 4️⃣ 音符提取

```python
from midiforge import extract_notes, max_polyphony, note_density

notes = extract_notes(midi, include_drums=False, close_unterminated=True)
n = notes[0]
n.pitch, n.label      # 60, 'C4'
n.start, n.end        # 起始/结束 tick
n.duration            # 时值 tick
n.start_sec           # 起始秒（依赖 tempo map）
n.is_drum             # 是否打击乐通道
n.unterminated        # 是否未闭合（已被修补为 False）
n.to_dict()           # → dict，便于 JSON 序列化

max_polyphony(midi)   # 最大同时发声数
```

#### 5️⃣ 时间轴：Tempo Map

```python
from midiforge import TempoMap

tm = TempoMap.from_midi(midi)
tm.bpm_at(1920)              # 指定 tick 处的 BPM
tm.tick_to_seconds(1920)     # tick → 秒（分段积分，正确处理变速）
tm.seconds_to_tick(4.0)      # 秒 → tick
tm.tick_to_mbt(1920)         # → (bar, beat, tick)（小节/拍/刻度）
tm.to_list()                 # [(tick, 微秒每拍), ...]
```

> ⚠️ 处理变速（ritardando / accelerando）乐曲时，请务必用 `TempoMap` 做时间换算，不要用「单一 BPM × tick」的线性近似。

#### 6️⃣ 音乐分析

```python
from midiforge import guess_key, chord_at, chord_progression, stats
from midiforge.analysis import pitch_class_histogram, velocity_histogram, rhythm_histogram

guess_key(notes)             # {'key': 'A', 'scale': 'minor', 'confidence': 0.93, ...}
chord_at([60, 64, 67, 71])   # 'Cmaj7'
chord_progression(notes, grid=480)
stats(midi)                  # 汇总字典：音符数、音域、密度、力度、复音、调性、直方图…
```

#### 7️⃣ 变换（默认返回新对象）

```python
from midiforge import transpose, quantize, velocity, humanize
from midiforge import set_bpm, scale_tempo, trim, merge_tracks, split_by_channel
from midiforge import to_format, strip, clean, remove_duplicate_notes

up      = transpose(midi, semitones=3, include_drums=False)
tight   = quantize(midi, grid=120, strength=0.8, swing=0.15)
soft    = velocity(midi, scale=0.8, offset=-5, ratio=0.9)
alive   = humanize(midi, tick_jitter=8, velocity_jitter=6, seed=42)  # 可复现
fast    = set_bpm(midi, 140)
clip    = trim(midi, start=1920, end=7680)      # 自动修补跨界音符
merged  = merge_tracks(midi)
split   = split_by_channel(midi)
fmt0    = to_format(midi, 0)
lean    = strip(midi, sysex=True, cc=True, lyrics=True)
fixed   = clean(midi)                            # 去孤儿/补闭合/去重
```

需要原地修改时统一传 `inplace=True`。

#### 8️⃣ 校验

```python
from midiforge import validate
from midiforge.validate import summarize, is_healthy, RULE_TITLES

issues = validate(midi, strict=False)
for it in issues:
    print(it.code, it.level, it.message, it.track, it.tick)

summarize(issues)     # {'error': 1, 'warning': 1, 'info': 0}
is_healthy(midi)      # 是否没有 error
```

规则速查表：

| 编号 | 含义 | 编号 | 含义 |
|---|---|---|---|
| MF001 | 缺少 end_of_track | MF011 | 缺少拍号标记 |
| MF002 | 轨道缺少名称 | MF012 | end_of_track 之后仍有事件 |
| MF003 | 空轨道 | MF013 | 重复的 end_of_track |
| MF004 | 孤儿音符关事件 | MF014 | tempo 出现在非首轨 |
| MF005 | 未闭合的音符开 | MF015 | 文件没有任何音符 |
| MF006 | 零时长音符 | MF016 | 力度超过 127 |
| MF007 | 力度为 0 的音符开 | MF017 | MIDI 格式值异常 |
| MF008 | 同音高音符重叠 | MF018 | 轨道数超过 65535 |
| MF009 | 缺少速度标记 | MF019 | 时基为 0 |
| MF010 | 速度值异常 | MF020 | 未知元事件类型 |

#### 9️⃣ 差异对比

```python
from midiforge import diff_midi, diff_notes
from midiforge.diff import format_diff

report = diff_midi(before, after)
report["similarity"]     # 相似度，0.0 ~ 1.0
report["counts"]          # {"added": n, "removed": n, "modified": n, "unchanged": n}
report["added"]           # 新增音符明细列表（removed / modified 同理）
print(format_diff(report))
```

#### 🔟 导出与可视化

```python
from midiforge import notes_to_csv, notes_to_json, notes_to_markdown, piano_roll
from midiforge.export import midi_to_json

open("notes.csv", "w").write(notes_to_csv(notes))
print(piano_roll(notes, width=72, max_rows=24))
```

```
C4    │▏████████████████▏█████████████████▏█████████████████▏██████████████████
E4    │▏███▏█▏██████████▏████▏█▏███████████···▏██▏██············▏█▏███·········
G4    │▏███████▏█████████········▏██···············▏██···············▏██·······
      └────────────────────────────────────────────────────────────────────────
```

#### 1️⃣1️⃣ 从零构造 MIDI

```python
from midiforge import new_midi, Track, write_file
from midiforge.events import make_tempo
from midiforge import MetaEvent, ChannelEvent

midi = new_midi(format=1, division=480, tracks=1)
t = midi.tracks[0]
t.name = "我的旋律"
t.add(make_tempo(0, 120))                                      # tempo 120 BPM
t.add(MetaEvent(tick=0, mtype=0x58, data=bytes([4, 2, 24, 8]))) # 4/4
t.add(ChannelEvent(tick=0,   channel=0, etype=0xC, data1=0))    # Program 0
t.add(ChannelEvent(tick=0,   channel=0, etype=0x9, data1=60, data2=90))
t.add(ChannelEvent(tick=480, channel=0, etype=0x8, data1=60, data2=0))
t.add(MetaEvent(tick=480, mtype=0x2F, data=b""))                # end_of_track
write_file(midi, "mine.mid")
```

也可以用 `from_notes([(pitch, start, duration, velocity), ...])` 一行生成。

### 🧪 错误处理

```python
from midiforge import MidiParseError, MidiWriteError, MidiValueError, MidiForgeError

try:
    midi = read_file("maybe_broken.mid")
except MidiParseError as exc:
    print(exc.message)   # 人类可读原因
    print(exc.offset)    # 出错字节偏移（-1 表示未知）
```

---

## 💡 设计思路与迭代规划

### 🏛 架构分层

```
┌─────────────────────────────────────────────────────────────┐
│  CLI 层        cli.py（18 个子命令，argparse）                │
├─────────────────────────────────────────────────────────────┤
│  能力层   analysis · transform · validate · diff · export     │
│          builder（构造）                                      │
├─────────────────────────────────────────────────────────────┤
│  语义层   notes（音符配对） · tempo（时间轴） · gm（音乐常量） │
├─────────────────────────────────────────────────────────────┤
│  模型层   midifile（MidiFile/Track） · events（事件）         │
├─────────────────────────────────────────────────────────────┤
│  编解码层 reader（解析） · writer（序列化） · vlq（变长量）    │
└─────────────────────────────────────────────────────────────┘
```

每一层只依赖下层，**不允许反向依赖**；能力层之间也尽量解耦（`analysis` 只依赖 `notes` + `gm`，不认识 `cli`）。这样新增一个分析能力时，不会牵动解析器。

### 🎯 关键设计决策

| 决策 | 取舍理由 |
|---|---|
| **零第三方依赖** | 牺牲部分性能（纯 Python 位运算）换取极致的部署可靠性与可嵌入性；MIDI 文件通常只有几十 KB，性能完全够用 |
| **dataclasses 而非裸 tuple** | 事件字段语义（tick / channel / etype / data1 / data2）一旦用 tuple 就会满天飞魔法数字；dataclass 自带可读 repr、可 `to_dict()`、IDE 友好 |
| **默认不可变（inplace=False）** | 音频批处理脚本最怕「改了一半又改回不去」；返回新对象让 `a → b → c` 的流水线天然可回溯，代价只是一次 `deepcopy` |
| **损坏文件「读出来 + 报告」而非直接抛错** | 真实世界的 MIDI 有大量残缺文件；能读多少读多少，再由 `validate` 给出体检报告，比一句 `invalid file` 有用得多 |
| **确定性优先** | 除 `humanize` 外所有算法都是纯函数，同一输入永远同一输出，方便做快照测试与 diff |
| **humanize 支持 seed** | 随机性必须可控、可复现，否则无法回归测试 |
| **时值命名采用标准记谱法** | 分母以全音符为 1（`1/4` = 四分音符），避免「以拍为单位」造成的二义性 |
| **end_of_track 永远排在轨道末尾** | 序列化时强制后置，否则解析器会提前终止、静默吞掉后面的事件 |

### 🗺 迭代路线

**v1.0.0（当前）** — 完整的 SMF 读写、音符提取、调性/和弦/节奏分析、11 类变换、20 条校验规则、18 个 CLI 命令、380 项测试。

**v1.1.0（规划）**
- 🎵 MusicXML 导入 / 导出（与乐谱软件互通）
- 🥁 更细粒度的鼓组映射与自定义鼓图
- 📐 小节线对齐的量化（`--align-bars`）
- 🧹 CLI 支持批量目录处理与并行

**v1.2.0（规划）**
- 🎹 类型 0/1 之外：支持 RMID（内嵌资源的 MIDI）
- 🔊 导出为 WAV（需可选依赖，保持核心零依赖）
- 🧬 风格化变换：琶音器、和声生成器
- 📊 HTML 可视化报告（内置模板，离线可用）

**v2.0.0（远期）**
- 🤖 简易旋律补全 / 续写（基于统计 n-gram，仍保持零依赖）
- 🌐 WebAssembly 构建，浏览器端直接解析
- 🔌 插件机制：允许用户注册自定义校验规则

> 我们始终守住两条底线：**核心包永远零依赖**、**核心包永远离线可用**。任何需要外部库的能力都会以「可选扩展」的形式提供。

---

## 📦 打包与部署指南

### 🧑‍💻 本地开发

```bash
git clone https://github.com/gitstq/MidiForge.git
cd MidiForge

# 运行全部测试（无需安装任何依赖）
python -m unittest discover -s tests -t .

# 以模块方式试跑 CLI
python -m midiforge demo -o /tmp/demo.mid
python -m midiforge info /tmp/demo.mid
```

### 📦 构建分发包

```bash
# 安装构建工具（仅构建时需要）
pip install build twine

# 构建 sdist + wheel
python -m build

# 产物位于 dist/
#   midiforge-1.0.0.tar.gz
#   midiforge-1.0.0-py3-none-any.whl

# 校验元数据
twine check dist/*
```

也可使用仓库内置脚本：

```bash
bash scripts/build.sh        # 构建
bash scripts/release.sh      # 构建 + 校验 + 打印上传命令
```

### 🚀 发布到 PyPI

```bash
# 先传到 TestPyPI 验证
twine upload --repository testpypi dist/*

# 正式发布
twine upload dist/*
```

### 🐳 单文件 / 二进制分发

MidiForge 是纯 Python 包，可以按需打包为独立可执行文件（**可选**，不影响核心的零依赖属性）：

```bash
pip install pyinstaller
pyinstaller --onefile --name midiforge midiforge/__main__.py
# 产物：dist/midiforge（Windows 下为 dist/midiforge.exe）
```

### 🔧 作为库嵌入你的项目

```python
# 直接复制 midiforge/ 目录到你的工程即可（零依赖的好处）
from midiforge import read_file, extract_notes
```

或正常声明依赖：

```toml
# pyproject.toml
dependencies = ["midiforge>=1.0.0"]
```

### 🤖 在 CI 中使用

```yaml
- name: 校验所有 MIDI 文件
  run: |
    pip install midiforge
    for f in assets/**/*.mid; do midiforge validate "$f" || exit 1; done
```

`validate` 发现 error 时退出码为 `1`，可直接作为流水线门禁。

### 📁 目录结构

```
MidiForge/
├── midiforge/            # 核心包（零依赖）
│   ├── __init__.py       # 公开 API 汇总 + __version__
│   ├── __main__.py       # python -m midiforge
│   ├── cli.py            # 命令行（18 个子命令）
│   ├── reader.py         # SMF 解析
│   ├── writer.py         # SMF 序列化
│   ├── vlq.py            # 变长量编解码
│   ├── midifile.py       # MidiFile / Track 模型
│   ├── events.py         # 事件模型与常量表
│   ├── notes.py          # 音符配对与复音分析
│   ├── tempo.py          # TempoMap（tick ↔ 秒 ↔ MBT）
│   ├── gm.py             # GM 音色 / 鼓图 / 音名 / 时值命名
│   ├── analysis.py       # 调性、和弦、直方图、统计
│   ├── transform.py      # 移调、量化、力度、裁剪……
│   ├── validate.py       # MF001–MF020 校验规则
│   ├── diff.py           # 音符级差异对比
│   ├── export.py         # CSV / JSON / Markdown / 钢琴卷帘
│   ├── builder.py        # 从零构造 MIDI
│   ├── errors.py         # 异常体系
│   └── py.typed          # PEP 561 类型标记
├── tests/                # 380 项单元测试
├── examples/             # 可运行示例
├── scripts/              # 构建 / 发布脚本
├── docs/                 # 补充文档
├── .github/workflows/    # CI
├── pyproject.toml
├── LICENSE               # MIT
├── CHANGELOG.md
└── README.md             # 简体中文 / 繁體中文 / English
```

---

## 🤝 贡献指南

欢迎任何形式的贡献：🐛 报 bug、💡 提需求、📝 改文档、🔧 提代码。

### 🏁 快速流程

```bash
# 1. Fork 本仓库并克隆
git clone https://github.com/<你的用户名>/MidiForge.git
cd MidiForge

# 2. 创建特性分支
git checkout -b feat/your-feature

# 3. 编码 + 补测试
#    新增能力请务必同步补充 tests/ 下的用例

# 4. 本地全量自测
python -m unittest discover -s tests -t .

# 5. 提交（遵循 Angular 提交规范）
git commit -m "feat: 新增 XXX 能力"

# 6. 推送并发起 Pull Request
git push origin feat/your-feature
```

### 📜 提交信息规范（Angular Convention）

| 前缀 | 用途 | 示例 |
|---|---|---|
| `feat:` | 新功能 | `feat: 支持 RMID 解析` |
| `fix:` | 修复缺陷 | `fix: 修正 SMPTE 帧率解析` |
| `docs:` | 文档变更 | `docs: 补充 CLI 示例` |
| `refactor:` | 重构（不改变外部行为） | `refactor: 拆分 _parse_track` |
| `test:` | 测试相关 | `test: 补充 trim 边界用例` |
| `perf:` | 性能优化 | `perf: 复用 TempoMap 缓存` |
| `chore:` | 构建/工具/杂项 | `chore: 升级 CI Python 版本` |
| `style:` | 格式调整 | `style: 统一引号风格` |

### ✅ 提交的硬性要求

1. **测试必须通过**：`python -m unittest discover -s tests -t .` 全绿；
2. **新增代码要有测试**：核心逻辑要求覆盖正常路径 + 边界 + 异常；
3. **保持零依赖**：不得在 `midiforge/` 中引入任何第三方 import（标准库除外）；
4. **保持离线**：不得引入任何网络请求；
5. **类型注解**：新增公开函数请附带 type hints 与中文 docstring；
6. **兼容 Python 3.8+**：不要使用 3.9+ 专属语法（如 `list[str]` 字面量，请用 `List[str]`）；
7. **提交前自查**：不要提交 `__pycache__`、虚拟环境、构建产物（已由 `.gitignore` 覆盖）。

### 🐛 报告 Bug

请附上：

- MidiForge 版本（`python -m midiforge --version`）与 Python 版本；
- 完整报错堆栈（含 `offset` 与错误信息）；
- 能复现问题的最小 MIDI 文件（或 `midiforge demo` 的输出 + 复现命令）；
- 期望行为 vs 实际行为。

### 💬 行为准则

请保持友善、就事论事。讨论技术方案时请给出理由与场景，而不是结论。

---

## 📄 开源协议说明

本项目基于 **MIT License** 开源，详见 [LICENSE](./LICENSE)。

### 📝 你可以做什么

- ✅ 免费用于**个人、教育、商业**项目；
- ✅ 修改、二次分发、再授权；
- ✅ 作为闭源产品的一部分发布（**无需开源你的产品**）；
- ✅ 私下使用，无需告知作者。

### ⚠️ 你需要做什么

- 在软件的所有副本或重要组成部分中**保留版权声明与许可声明**；
- 即：`LICENSE` 文件全文（含 `Copyright (c) 2026 MidiForge Contributors`）需随分发物一同提供。

### 🚫 免责声明

本软件按「**原样**」（AS IS）提供，**不附任何明示或暗示的担保**，包括但不限于适销性、特定用途适用性与非侵权性。在任何情况下，作者或版权持有人均不对因使用本软件而产生的任何索赔、损害或其它责任负责。

### 🔗 第三方说明

- MidiForge **不包含、不复制**任何第三方源码；实现参考的是公开的 **Standard MIDI Files 1.0 规范**（MIDI Manufacturers Association）与公开的音乐理论知识（Krumhansl-Kessler 音级轮廓、General MIDI 音色表等）。
- 运行期**零第三方依赖**，无传递依赖的许可证合规负担。
- 仓库中 `examples/`、`tests/` 生成的 MIDI 数据均由程序内置算法合成，不含受版权保护的音乐作品。

---

<div align="center">

如果 MidiForge 帮到了你，欢迎 ⭐ **Star** 一下，也欢迎把你的使用场景分享到 Issues！

Made with ❤️ and zero dependencies.

[简体中文](./README.md) · [繁體中文](./README.zh-TW.md) · [English](./README.en.md)

</div>
