# 📐 SMF（Standard MIDI File）格式要点

本文是 MidiForge 实现时所依据的格式要点备忘，也是「为什么这些坑值得单独处理」的说明。规范原文见 MIDI Manufacturers Association 发布的 *Standard MIDI Files 1.0*。

## 1. 整体结构

```
MThd <len:4> <format:2> <ntrks:2> <division:2>     ← 文件头，len 通常为 6
MTrk <len:4> <事件流…>                              ← 轨道，重复 ntrks 次
（其它块，如 XFIH / 厂商私有块）                     ← 按 len 安全跳过
```

- **format**：`0` 单轨合并；`1` 多轨同步播放；`2` 多轨各自独立。
- **ntrks**：声明的轨道数。现实文件里它常常与真实块数不一致，MidiForge 以**实际读到的块为准**，不一致不报错（交由 `validate` 提示）。
- **division**：
  - 最高位为 `0` → 正值，表示「每四分音符的 tick 数」（常见 480、960）。
  - 最高位为 `1` → SMPTE，高字节是帧率的**负数补码**（`0xE8`=-24 → 24fps，`0xE7`=-25 → 25fps，`0xE3`=29.97，`0xE2`=30），低字节是每帧的 tick 数。
  - ⚠️ 坑点：SMPTE 的帧率字节必须原样保存。若只做 `raw & 0x7FFF` 掩码，帧率高字节的最高位会被吃掉（`0xE728 → 0x6728`），往返一次文件就废了。MidiForge 内部用**负数 division** 表示 SMPTE，写回时还原为 `0x8000 | (raw & 0x7F00) | (raw & 0x00FF)`。

## 2. 变长量（VLQ）

delta time 与部分长度字段使用 VLQ：每字节低 7 位为数据，最高位为「还有后续字节」标志，**大端**（先高后低）。

```
0x81 0x00 → 128        （(0x01 << 7) | 0x00）
0xFF 0x7F → 16383
```

- 最多 4 字节，上限 `0x0FFFFFFF`；
- **坑点**：VLQ 不是「小端 7 位」，顺序写反会得到完全错误的时间轴。

## 3. 事件

```
<delta time: VLQ> <事件…>
```

### 3.1 通道事件（0x80–0xEF）

| 高 4 位 | 类型 | 数据字节数 |
|---|---|---|
| `0x8` | Note Off | 2（音高、力度） |
| `0x9` | Note On | 2（音高、力度） |
| `0xA` | Polyphonic Aftertouch | 2 |
| `0xB` | Control Change | 2（控制器号、值） |
| `0xC` | Program Change | 1 |
| `0xD` | Channel Aftertouch | 1 |
| `0xE` | Pitch Bend | 2（14 位，中心 0x2000） |

低 4 位是通道号（0–15），**通道 9 在 General MIDI 中固定为打击乐**。

**坑点 1：力度为 0 的 Note On 等价于 Note Off。** 这是为了配合 running status 的压缩技巧，写代码时必须统一判断，否则音符会「无限延长」。MidiForge 的 `ChannelEvent.is_note_off` 已封装该规则。

**坑点 2：running status。** 若当前事件的状态字节与上一个相同，可以省略状态字节，只写数据字节。但**元事件与 SysEx 会清除 running status**，不是「全局记住上一个」这么简单。

### 3.2 元事件（0xFF）

```
FF <type:1> <len:VLQ> <data…>
```

常用类型：

| 类型 | 含义 | 数据 |
|---|---|---|
| `0x00` | 序列号 | 2 字节 |
| `0x01`–`0x09` | 文本 / 版权 / 轨道名 / 乐器名 / 歌词 / 标记 / 提示点 | 文本 |
| `0x20` | MIDI 通道前缀 | 1 字节 |
| `0x2F` | **end_of_track** | 空（必须存在，且必须是轨道最后一个事件） |
| `0x51` | tempo | 3 字节大端，**微秒/四分音符**（`BPM = 60000000 / us`） |
| `0x54` | SMPTE offset | 5 字节 |
| `0x58` | 拍号 | 4 字节：分子、分母指数（2=四分音符）、每拍 tick 数（通常 24）、每 24 个 MIDI 时钟的标准音符数（通常 8） |
| `0x59` | 调号 | 2 字节：**升降号数量（有符号）**、大小调（0=大调，1=小调） |
| `0x7F` | 音序器特有 | 任意 |

### 3.3 SysEx（0xF0 / 0xF7）

```
F0 <len:VLQ> <data…>    完整 SysEx
F7 <len:VLQ> <data…>    分段 / 转义
```

长度字段把 `F0 … F7` 之间的内容整体包住；`0xF7` 也常用于分段续传。

## 4. 时间轴：为什么必须做分段积分

tick 是「音乐时间」，秒是「真实时间」，两者由 tempo map 连接：

- 全曲无变速时：`seconds = ticks / division * 60 / BPM`，简单线性；
- 有变速时：必须**按 tempo 变化点分段累加**，每一段用该段的 tempo 换算，再求和。

MidiForge 的 `TempoMap` 就是做这件事（`tick_to_seconds` / `seconds_to_tick` / `tick_to_mbt`）。用线性近似处理变速乐曲，几分钟的曲子能偏出好几秒。

## 5. 必须避开的实践坑（MidiForge 的处理方式）

| 坑 | 后果 | MidiForge 的处理 |
|---|---|---|
| `end_of_track` 没排到最后 | 解析器提前终止，后面的事件被静默吞掉 | 序列化时把 `end_of_track` 强制后置 |
| 把 SMPTE 帧率当普通掩码处理 | 往返后时基被破坏 | 负数内部表示 + 原样还原高字节 |
| 遗漏「力度 0 = Note Off」 | 音符永不结束，复音数爆表 | `is_note_off` 统一封装 |
| running status 跨元事件沿用 | 解析错位，读出乱码事件 | 元事件 / SysEx 后重置 running status |
| 直接用 `tick × BPM` 线性换算 | 变速乐曲时间轴漂移 | `TempoMap` 分段积分 |
| 损坏文件直接抛 `struct.error` | 无法定位问题 | 抛出带 `offset` 的 `MidiParseError` |
| 时间单位混淆（tick / beat / bar） | 小节位置算错 | `tick_to_mbt()` 统一换算 |

## 6. 音乐理论部分

- **音名**：MIDI 音高 60 = C4（科学音高记法，中央 C）。MidiForge 同时提供升号（`C#4`）与降号（`Db4`）两种记法。
- **调性识别**：Krumhansl-Kessler 音级轮廓给出 12 个音级的「典型权重」，把曲子的音级直方图（时长加权）与 24 个候选调（12 大调 + 12 小调）做**皮尔逊相关**，取最高者。缺点是对只有音阶、没有和声与重音的素材会存在歧义，因此 MidiForge 同时返回置信度。
- **和弦识别**：把同时发声的音高集合归一到 pitch class，与各和弦模板（音程集合）比对。
- **调号 ↔ 五度圈**：调号字节的升降号数量即五度圈位置（正数=升号方向）。

---

> 以上每一条都对应 `tests/` 中的至少一个用例。改动解析/写入逻辑时，请同步维护这些用例。
