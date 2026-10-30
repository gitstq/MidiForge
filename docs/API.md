# 🐍 API 参考（API Reference）

> 本文档由 `inspect` 自动提取，覆盖 `midiforge` 包的全部公开 API（版本 `1.0.0`）。

所有 API 均可直接从顶层包导入：

```python
import midiforge
midiforge.<name>
```


## 读取与写入（reader） — `midiforge.reader`

| API | 签名 | 说明 |
|---|---|---|
| `parse` | `(data: 'bytes') -> 'MidiFile'` | 把 MIDI 字节流解析为 :class:`MidiFile`。 |
| `read_file` | `(path: 'str') -> 'MidiFile'` | 从磁盘读取 MIDI 文件。 |
| `peek_header` | `(data: 'bytes') -> 'Tuple[int, int, int]'` | 只读取头部，返回 ``(format, ntrks, division)``，用于快速探测。 |

## 写入（writer） — `midiforge.writer`

| API | 签名 | 说明 |
|---|---|---|
| `serialize` | `(midi: 'MidiFile', use_running_status: 'bool' = True) -> 'bytes'` | 把 :class:`MidiFile` 序列化为 SMF 字节流。 |
| `write_file` | `(midi: 'MidiFile', path: 'str', use_running_status: 'bool' = True) -> 'None'` | 序列化并写入磁盘文件。 |

## 文件与轨道模型 — `midiforge.midifile`

| API | 签名 | 说明 |
|---|---|---|
| `MidiFile` | `class` | Standard MIDI File 内存表示。 |
| `Track` | `class` | 一条 MIDI 轨道。 |
| `new_midi` | `(format: 'int' = 1, division: 'int' = 480, tracks: 'int' = 1) -> 'MidiFile'` | 创建一个空的 :class:`MidiFile`（自动补齐指定数量的空轨道）。 |

## 事件模型 — `midiforge.events`

| API | 签名 | 说明 |
|---|---|---|
| `ChannelEvent` | `class` | 通道语音事件。 |
| `MetaEvent` | `class` | 元事件（0xFF）。 |
| `SysExEvent` | `class` | 系统专有事件。 |
| `make_tempo` | `(tick: 'int', bpm: 'float') -> 'MetaEvent'` | 按 BPM 构造 tempo 元事件。 |
| `bpm_to_tempo_bytes` | `(bpm: 'float') -> 'bytes'` | BPM → 3 字节大端微秒数。 |

## 音符 — `midiforge.notes`

| API | 签名 | 说明 |
|---|---|---|
| `Note` | `class` | 一个已经配好对的音符。 |
| `extract_notes` | `(midi, tempo_map: 'Optional[TempoMap]' = None, include_drums: 'bool' = True, close_unterminated: 'bool' = True) -> 'List[Note]'` | 从 MIDI 中抽取全部音符。 |
| `note_density` | `(notes: 'List[Note]', window_ticks: 'int', end_tick: 'int') -> 'List[int]'` | 按固定窗口统计音符密度（每窗口的音符起始数）。 |
| `polyphony_profile` | `(notes: 'List[Note]') -> 'Dict[int, int]'` | 统计同时发声数分布：``{同时发声数: 出现的采样点数}``。 |
| `max_polyphony` | `(notes: 'List[Note]') -> 'int'` | 最大同时发声数。 |

## 时间轴 — `midiforge.tempo`

| API | 签名 | 说明 |
|---|---|---|
| `TempoMap` | `class` | 速度映射表。 |
| `TempoChange` | `class` | 一次速度变化。 |

## 音乐常量 — `midiforge.gm`

| API | 签名 | 说明 |
|---|---|---|
| `note_name` | `(pitch: 'int', prefer_flat: 'bool' = False) -> 'str'` | 音高（0-127）→ 科学音名，如 ``60 → C4``。 |
| `program_name` | `(program: 'int') -> 'str'` | 音色编号（0-127）→ GM 音色名。 |
| `drum_name` | `(pitch: 'int') -> 'str'` | 打击乐通道上的键位名。 |
| `key_name` | `(fifths: 'int', minor: 'bool' = False, prefer_flat: 'bool' = False) -> 'str'` | 由调号五度圈位置得到调名，如 ``(0, True) → Am``、``(-1, True) → Dm``。 |
| `ticks_to_note_name` | `(ticks: 'int', division: 'int') -> 'str'` | 把时值（tick）转成标准音符名，如 ``480/480`` → ``1/4``（四分音符）。 |
| `fifths_of_pitch_class` | `(pitch_class: 'int') -> 'int'` | 音级（0-11）→ 五度圈位置（-6..6）。如 C=0、G=1、F=-1。 |

## 分析 — `midiforge.analysis`

| API | 签名 | 说明 |
|---|---|---|
| `guess_key` | `(notes: 'Sequence[Note]') -> 'dict'` | 用 Krumhansl-Kessler 轮廓相关法猜测调性。 |
| `chord_at` | `(pitches: 'Sequence[int]') -> 'str'` | 给定同时发声的音高集合，识别和弦名称。 |
| `chord_progression` | `(notes: 'Sequence[Note]', grid: 'Optional[int]' = None) -> 'List[dict]'` | 按时隙切片识别和弦进行。 |
| `pitch_class_histogram` | `(notes: 'Sequence[Note]') -> 'List[float]'` | 按时值加权统计 12 个音级（返回长度 12 的列表，单位：tick）。 |
| `velocity_histogram` | `(notes: 'Sequence[Note]', bins: 'int' = 8) -> 'Dict[str, int]'` | 力度直方图，键为 ``"0-15"`` 形式的区间名。 |
| `rhythm_histogram` | `(notes: 'Sequence[Note]', division: 'int') -> 'Dict[str, int]'` | 时值分布，键为 ``"1/4"`` 形式的音符名。 |
| `repeated_patterns` | `(notes: 'Sequence[Note]', n: 'int' = 4, top: 'int' = 5) -> 'List[dict]'` | 统计最常出现的音高-时值 n-gram（用于发现重复乐句 / 循环）。 |
| `channel_programs` | `(midi) -> 'Dict[int, int]'` | 统计每个通道最后使用的音色编号（无 program_change 时为 0）。 |
| `track_summaries` | `(midi, notes: 'Sequence[Note]') -> 'List[dict]'` | 逐轨道概览。 |
| `stats` | `(midi, notes: 'Optional[Sequence[Note]]' = None, tempo_map=None) -> 'dict'` | 生成完整的统计报告字典。 |

## 变换 — `midiforge.transform`

| API | 签名 | 说明 |
|---|---|---|
| `transpose` | `(midi: 'MidiFile', semitones: 'int', channels: 'Optional[Iterable[int]]' = None, include_drums: 'bool' = False, inplace: 'bool' = False) -> 'MidiFile'` | 整体移调。 |
| `quantize` | `(midi: 'MidiFile', grid: 'int', strength: 'float' = 1.0, swing: 'float' = 0.0, channels: 'Optional[Iterable[int]]' = None, inplace: 'bool' = False) -> 'MidiFile'` | 量化音符起始位置（保持时值不变）。 |
| `velocity` | `(midi: 'MidiFile', scale: 'float' = 1.0, offset: 'int' = 0, ratio: 'float' = 1.0, channels: 'Optional[Iterable[int]]' = None, inplace: 'bool' = False) -> 'MidiFile'` | 调整音符力度。 |
| `humanize` | `(midi: 'MidiFile', tick_jitter: 'int' = 0, velocity_jitter: 'int' = 0, seed: 'Optional[int]' = 0, inplace: 'bool' = False) -> 'MidiFile'` | 加入可控随机扰动（“人性化”），使用固定随机种子保证可复现。 |
| `set_bpm` | `(midi: 'MidiFile', bpm: 'float', inplace: 'bool' = False) -> 'MidiFile'` | 把全曲设为固定 BPM（删除其它速度变化）。 |
| `scale_tempo` | `(midi: 'MidiFile', factor: 'float', inplace: 'bool' = False) -> 'MidiFile'` | 按倍率缩放速度（BPM × factor），tick 结构不变。 |
| `scale_ticks` | `(midi: 'MidiFile', factor: 'float', inplace: 'bool' = False) -> 'MidiFile'` | 按倍率缩放所有 tick（时间拉伸/压缩），速度标记不变。 |
| `trim` | `(midi: 'MidiFile', start: 'int' = 0, end: 'Optional[int]' = None, inplace: 'bool' = False) -> 'MidiFile'` | 裁剪到 ``[start, end)`` 区间，并把起点平移到 0。 |
| `merge_tracks` | `(midi: 'MidiFile', inplace: 'bool' = False) -> 'MidiFile'` | 把所有轨道合并成一条（用于转 Format 0 或简化结构）。 |
| `split_by_channel` | `(midi: 'MidiFile', inplace: 'bool' = False) -> 'MidiFile'` | 按通道拆分成多条轨道；元事件（速度/拍号）保留在第一条轨道。 |
| `to_format` | `(midi: 'MidiFile', fmt: 'int', inplace: 'bool' = False) -> 'MidiFile'` | 转换 SMF 格式（0 / 1 / 2）。转 0 时会自动合并轨道。 |
| `strip` | `(midi: 'MidiFile', sysex: 'bool' = False, controllers: 'bool' = False, keep_controllers: 'Optional[Sequence[int]]' = None, program_change: 'bool' = False, pitch_bend: 'bool' = False, aftertouch: 'bool' = False, lyrics: 'bool' = False, markers: 'bool' = False, inplace: 'bool' = False) -> 'MidiFile'` | 按类别移除事件。 |
| `clean` | `(midi: 'MidiFile', inplace: 'bool' = False) -> 'MidiFile'` | 修复常见问题：孤儿音符关、未闭合音符、越界数据、重复 end_of_track。 |
| `remove_duplicate_notes` | `(midi: 'MidiFile', inplace: 'bool' = False) -> 'MidiFile'` | 移除完全重叠的重复音符（同通道、同音高、同起始）。 |

## 校验 — `midiforge.validate`

| API | 签名 | 说明 |
|---|---|---|
| `validate` | `(midi: 'MidiFile', strict: 'bool' = False) -> 'List[Issue]'` | 校验 MIDI 结构。 |
| `summarize` | `(issues: 'Sequence[Issue]') -> 'dict'` | 统计各级问题数量。 |
| `is_healthy` | `(midi: 'MidiFile') -> 'bool'` | 是否没有 error 级问题。 |
| `Issue` | `class` | 一条校验问题。 |
| `RULE_TITLES` | `` | dict() -> new empty dictionary |

## 差异 — `midiforge.diff`

| API | 签名 | 说明 |
|---|---|---|
| `diff_midi` | `(before, after, tempo_map=None, tolerance: 'int' = 0) -> 'dict'` | 直接对比两个 :class:`MidiFile`（内部自动抽取音符）。 |
| `diff_notes` | `(before: 'Sequence[Note]', after: 'Sequence[Note]', tolerance: 'int' = 0) -> 'dict'` | 对比两组音符。 |
| `format_diff` | `(result: 'dict', limit: 'int' = 20) -> 'str'` | 把 diff 结果渲染成人类可读文本。 |

## 导出 — `midiforge.export`

| API | 签名 | 说明 |
|---|---|---|
| `notes_to_csv` | `(notes: 'Sequence[Note]') -> 'str'` | 音符列表 → CSV 文本（含表头，UTF-8，LF 换行）。 |
| `notes_to_json` | `(notes: 'Sequence[Note]', indent: 'Optional[int]' = 2) -> 'str'` | 音符列表 → JSON 文本。 |
| `notes_to_markdown` | `(notes: 'Sequence[Note]', limit: 'int' = 100) -> 'str'` | 音符列表 → Markdown 表格（超长时截断并注明）。 |
| `piano_roll` | `(notes: 'Sequence[Note]', width: 'int' = 72, max_rows: 'int' = 24, tick_span: 'Optional[int]' = None) -> 'str'` | 把音符画成 ASCII 钢琴卷帘（终端友好）。 |
| `midi_to_json` | `(midi: 'MidiFile', tempo_map: 'Optional[TempoMap]' = None, notes=None) -> 'str'` | 整份 MIDI 的完整 JSON 快照（概览 + 速度表 + 事件 + 音符）。 |

## 构造 — `midiforge.builder`

| API | 签名 | 说明 |
|---|---|---|
| `demo_song` | `(bpm: 'float' = 108.0, division: 'int' = 480, bars: 'int' = 4) -> 'MidiFile'` | 生成一段 4/4 拍的示例曲（钢琴旋律 + 弦乐和弦 + 鼓组）。 |
| `from_notes` | `(notes: 'Sequence[Tuple[int, int, int, int]]', bpm: 'float' = 120.0, division: 'int' = 480, channel: 'int' = 0, program: 'int' = 0, name: 'str' = 'track') -> 'MidiFile'` | 用 ``(pitch, start_tick, duration_tick, velocity)`` 元组快速构造单轨 MIDI。 |

## 异常 — `midiforge.errors`

| API | 签名 | 说明 |
|---|---|---|
| `MidiForgeError` | `class` | MidiForge 的异常基类。 |
| `MidiParseError` | `class` | MIDI 字节流不符合 Standard MIDI File 规范时抛出。 |
| `MidiWriteError` | `class` | 序列化 MIDI 文件失败时抛出（通常是事件数据越界）。 |
| `MidiValueError` | `class` | 用户输入的参数不合法时抛出（移调超出范围、网格值非法等）。 |
