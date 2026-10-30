# 📝 更新日志（Changelog）

本项目遵循 [Keep a Changelog](https://keepachangelog.com/) 格式，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。
所有提交信息遵循 [Angular Commit Convention](https://github.com/angular/angular/blob/main/CONTRIBUTING.md#commit)。

---

## [1.0.0] - 2026-10-31

首个正式版本：零依赖的 MIDI（SMF）解析 / 分析 / 变换 / 校验工具箱。

### ✨ 新增（feat）

**编解码层**
- `reader.py`：SMF 解析器，支持 Format 0/1/2、MThd/MTrk 块、未知块安全跳过、running status、元事件、SysEx、SMPTE 时基；解析失败给出字节级偏移
- `writer.py`：SMF 序列化器，自动补齐 `end_of_track`（强制置于轨道末尾）、支持 running status 压缩
- `vlq.py`：变长量（VLQ）编解码，最大 4 字节 / 0x0FFFFFFF
- `peek_header()`：只读取头部，用于快速探测

**模型层**
- `midifile.py`：`MidiFile` / `Track`，提供 `all_events()`、`tempo_events()`、`time_signatures()`、`end_tick`、`duration_seconds`、`track_by_name()`、`summary()`、`new_midi()`
- `events.py`：`ChannelEvent` / `MetaEvent` / `SysExEvent`，含状态名、控制器名、文本解码、tempo ↔ BPM 换算

**语义层**
- `notes.py`：音符配对（FIFO + 力度 0 等价 note-off + 未闭合修补）、`note_density()`、`polyphony_profile()`、`max_polyphony()`
- `tempo.py`：`TempoMap`，支持 tick ↔ 秒（分段积分，正确处理变速）、tick ↔ 拍、MBT（小节/拍/刻度）
- `gm.py`：128 个 GM 音色名、GM 鼓图、音名（升号/降号两种记法）、调号五度圈、标准记谱时值命名

**能力层**
- `analysis.py`：Krumhansl-Kessler 调性识别（含置信度）、和弦模板识别、和弦进行、音级/力度/时值直方图、重复乐句检测、通道音色盘点、`stats()`
- `transform.py`：`transpose` / `quantize`（强度 + swing）/ `velocity`（缩放+平移+压缩）/ `humanize`（固定 seed）/ `set_bpm` / `scale_tempo` / `scale_ticks` / `trim`（自动修补跨界音符）/ `merge_tracks` / `split_by_channel` / `to_format` / `strip` / `clean` / `remove_duplicate_notes`；默认 `inplace=False`
- `validate.py`：**MF001–MF020** 共 20 条校验规则，三级（error / warning / info）
- `diff.py`：音符级差异对比（新增 / 删除 / 修改 / 不变 + 相似度）
- `export.py`：CSV / JSON / Markdown 导出 + 终端 ASCII 钢琴卷帘
- `builder.py`：`demo_song()` 生成 4 轨道示例曲、`from_notes()` 从音符表构造 MIDI
- `errors.py`：`MidiForgeError` / `MidiParseError`（带 offset）/ `MidiWriteError` / `MidiValueError`

**命令行**
- 18 个子命令：`info` · `validate`（`lint`） · `notes` · `stats`（`analyze`） · `roll` · `diff` · `demo` · `transpose` · `quantize` · `velocity` · `humanize` · `tempo` · `trim` · `merge` · `split` · `convert` · `strip` · `clean`
- 退出码约定：`0` 正常 / `1` 校验发现 error / `2` 解析·写入·参数错误

**工程**
- `pyproject.toml`（setuptools，Python ≥ 3.8，零运行时依赖）
- `py.typed`（PEP 561 类型标记）
- MIT 协议
- 三语文档：简体中文 / 繁體中文 / English（顶部可点击切换）

### 🐛 修复（fix）

- 序列化时 `end_of_track` 未按轨道末尾处理，导致同 tick 的通道事件被解析器提前截断丢弃
- SMPTE 时基往返丢失帧率高字节（`0xE728` → `0x6728`）
- `trim` 会把区间之前的全局元事件（tempo）再次向左平移，产生负 tick
- `trim` 未修补「起始早于 start、结束于区间内」的音符，产生孤儿 note-off
- `_parse_track` 控制流缺陷导致 delta time 未读取、事件解析错位
- 时值命名与标准记谱法不一致（分母基准应为全音符）
- 调号别名与关系小调换算错误（A minor 被判为 D minor）

### ✅ 测试

- 380 项单元测试，覆盖 VLQ、事件模型、解析、写入、TempoMap、音符提取、分析、变换、校验、导出、GM 常量与 CLI
