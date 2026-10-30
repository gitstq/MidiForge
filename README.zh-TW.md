<div align="center">

# 🎼 MidiForge

**零依賴的 MIDI（Standard MIDI File）解析 · 分析 · 變換 · 校驗工具箱**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Dependencies](https://img.shields.io/badge/dependencies-0-brightgreen.svg)](https://github.com/gitstq/MidiForge/blob/main/pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Tests](https://img.shields.io/badge/tests-380%20passed-brightgreen.svg)](./tests)
[![Offline](https://img.shields.io/badge/network-not%20required-orange.svg)](#-核心特性)

**🌐 語言切換 / Language Switcher：**

[简体中文](./README.md) · [繁體中文](./README.zh-TW.md) · [English](./README.en.md)

</div>

---

## 🎉 專案介紹

MIDI 檔案（`.mid`，Standard MIDI File，簡稱 SMF）是音樂製作、遊戲音訊、樂譜軟體與硬體音源之間最通用的交換格式。它結構緊湊、資訊密度極高，但同時也是出了名的「難讀」：變長量（VLQ）編碼、running status 省略、SMPTE 時基、多軌 tempo map、力度為 0 的 note-on 等同於 note-off……任何一處細節理解偏差，讀出來的結果就會錯得悄無聲息。

實務上常見的痛點大概是這樣：

- 🎹 想統計一首曲子的調性、和弦進行、力度分佈，卻得先裝 `mido`／`pretty_midi`／`music21`，再拉一整串傳遞依賴；
- 🐛 手上有一個損壞的 `.mid`，播放器直接拒絕開啟，卻不知道到底壞在第幾個位元組；
- 🔁 想把幾百個 MIDI 批次移調、量化、裁剪，只能打開 DAW 手動點；
- 📊 想做音樂資訊檢索（MIR）的原型，但現有函式庫不是太重、就是 API 不透明、或是輸出無法重現。

**MidiForge 就是為了解決這些問題而生的。** 它是一個**純 Python 標準函式庫實作**、**零第三方依賴**、**完全離線**的 MIDI 處理工具箱，同時提供 **Python 函式庫 API** 與**命令行工具**兩種使用方式：

```python
import midiforge
midi = midiforge.read_file("song.mid")
print(midi.summary()["duration_seconds"])   # 8.0
```

```bash
midiforge info song.mid
```

它不追求「成為一套 DAW」，而是追求成為一把**趁手、可靠、能嵌入任何管線**的瑞士刀：讀得懂、改得動、查得清、驗得準。

> **為什麼堅持「零依賴」？**
> 音訊／MIR 場景的依賴樹向來脆弱（`numpy` 版本衝突、`pybind11` 編譯失敗、系統缺少 `libsndfile`……）。MidiForge 只使用 `argparse`／`struct`／`dataclasses`／`math`／`random`／`json`／`csv` 這類標準模組，因此它能在**受限環境**（離線內網、CI 容器、嵌入式 Python、教學機房）中 `pip install` 後立即開箱可用，也永遠不必擔心哪天被上游依賴的 breaking change 拖垮。

---

## ✨ 核心特性

### 🔍 解析與寫入：把規範吃透

| 能力 | 說明 |
|---|---|
| 📄 Format 0 / 1 / 2 | 單軌合併、多軌同步、多曲集三種結構完整支援 |
| 🧩 MThd / MTrk 區塊 | 未知區塊（如 `XFIH`、廠商私有區塊）安全跳過，不會誤判為失敗 |
| ⚡ Running status | 完整還原省略狀態位元組的事件流 |
| 🎛 通道事件 | Note On/Off、Poly Aftertouch、CC、Program Change、Channel Aftertouch、Pitch Bend |
| 🏷 中繼事件 | Tempo、拍號、調號、軌道名稱、歌詞、標記、SMPTE Offset 等 |
| 📡 SysEx | `0xF0`／`0xF7` 分段系統專屬訊息 |
| ⏱ SMPTE 時基 | division 為負時的幀率（24/25/29/30 fps）與每幀 tick 數正確還原 |
| 🚨 偏移級錯誤 | 解析失敗時回報**出錯位元組偏移**與可讀原因，而不是一句 `struct.error` |

### 🧠 音樂內容分析：不只是「讀出來」

- **🎯 調性辨識**：以 Krumhansl-Kessler 音級輪廓搭配皮爾遜相關係數，輸出調性、大小調與信心指數（如 `C major（置信度 0.97）`）
- **🎸 和弦辨識**：依同時發聲的音集合比對樣板，涵蓋 `maj / min / dim / aug / sus4 / maj7 / min7 / dom7 / m7b5 / dim7 / add9 / 6` 等
- **📈 分佈統計**：音級直方圖、力度直方圖、時值（節奏）直方圖、音符密度、複音曲線、最大同時發聲數
- **🔁 重複樂句偵測**：自動找出反覆出現的旋律片段與其出現次數
- **🎼 音色盤點**：每個通道的 Program（GM 音色名）、鼓組通道（ch 9）依 GM 鼓圖對應為軍鼓／大鼓／腳踏鈸等名稱

### 🛠 變換與生成：批次處理的主力

`transpose` 移調 · `quantize` 量化（含強度與 swing） · `velocity` 力度縮放／平移／動態壓縮 · `humanize` 人性化擾動（固定 seed，結果可重現） · `set_bpm`／`scale_tempo` 速度處理 · `trim` 區間裁剪（自動修補跨越邊界的音符） · `merge_tracks`／`split_by_channel` 軌道重組 · `to_format` 格式轉換 · `strip` 依類別剔除事件 · `clean` 一鍵修復常見損壞。

所有變換函式預設 **回傳新物件**（`inplace=False`），不會偷偷改動你的原始資料。

### ✅ 結構校驗：20 條規則的「健康檢查報告」

內建 **MF001–MF020** 共 20 條規則，涵蓋 `error / warning / info` 三級：缺少 `end_of_track`、孤兒音符關、未閉合音符開、零時值音符、同音高重疊、tempo 缺失或異常、拍號缺失、`end_of_track` 之後仍有事件、力度越界、時基為 0、未知中繼事件……

```bash
$ midiforge validate broken.mid
MF004  error   音符關 ch1 60 沒有對應的音符開 [track=2] @1430
MF005  warning 音符開 ch0 72 未閉合 [track=1] @960
── 合計 2 條（error 1 / warning 1 / info 0）
```

### 🖥 命令行：18 個開箱即用的子命令

`info` · `validate`（別名 `lint`） · `notes` · `stats`（別名 `analyze`） · `roll` · `diff` · `demo` · `transpose` · `quantize` · `velocity` · `humanize` · `tempo` · `trim` · `merge` · `split` · `convert` · `strip` · `clean`

> 🎁 **手上沒有 MIDI 素材？** `midiforge demo -o song.mid` 會直接產生一首 4 軌道（指揮軌／旋律／和聲／鼓）的範例曲，讓你立刻試玩全部功能。

### 📤 匯出與視覺化

- `notes_to_csv`／`notes_to_json`／`notes_to_markdown`：把音符表直接餵給 Excel、pandas 或文件
- `piano_roll`：**終端機 ASCII 鋼琴捲簾**，不需要圖形介面就能用肉眼看出旋律輪廓
- `diff_midi`：兩個檔案的音符級差異比對（新增／刪除／修改／不變 ＋ 相似度百分比）

### 🔒 工程屬性

| 屬性 | 說明 |
|---|---|
| 零依賴 | 只用 Python 標準函式庫，安裝後沒有任何傳遞依賴 |
| 離線 | 執行期間不發出任何網路請求 |
| 確定性 | 除 `humanize` 外皆為純函式；`humanize` 支援固定 `seed` 重現 |
| 型別友善 | 全面使用 `dataclasses` ＋ type hints，並附上 `py.typed` |
| 測試充分 | 380 項單元測試，涵蓋 VLQ、解析、寫入、時值、分析、變換、校驗、CLI |
| 跨平台 | 純 Python，Windows／macOS／Linux 行為一致 |

---

## 🚀 快速開始

### 📦 安裝

```bash
# 方式一：從 PyPI 安裝（推薦）
pip install midiforge

# 方式二：從原始碼安裝（不需任何網路依賴）
git clone https://github.com/gitstq/MidiForge.git
cd MidiForge
pip install .

# 方式三：免安裝，直接以模組方式執行
python -m midiforge --help
```

> **需求**：Python ≥ 3.8，除此之外沒有其它執行期依賴。

### ⚡ 60 秒上手

```bash
# 1) 產生一首內建範例曲（沒有素材也能玩）
midiforge demo -o song.mid

# 2) 看一眼它長什麼樣
midiforge info song.mid

# 3) 做一次結構健康檢查
midiforge validate song.mid

# 4) 分析音樂內容：調性、和弦、節奏、力度
midiforge stats song.mid

# 5) 在終端機畫出鋼琴捲簾
midiforge roll song.mid --width 72

# 6) 整體移調 +3 個半音並另存
midiforge transpose song.mid -s 3 -o song_up.mid
```

### 🐍 Python API 最小範例

```python
import midiforge

midi = midiforge.read_file("song.mid")

print(midi.format, midi.division, len(midi.tracks))   # 1 480 4
print(midi.duration_seconds())                         # 8.88

notes = midiforge.extract_notes(midi)
for n in notes[:5]:
    print(n.label, n.start, n.duration, n.velocity)

# 音樂分析
print(midiforge.guess_key(notes))        # {'key': 'C', 'scale': 'major', ...}
print(midiforge.chord_progression(notes))

# 變換後寫回
up = midiforge.transpose(midi, semitones=3)
midiforge.write_file(up, "song_up.mid")
```

---

## 📖 詳細使用指南

### 🖥 命令行總覽

```bash
midiforge --help            # 總說明
midiforge <command> --help  # 子命令說明
midiforge --version
```

| 命令 | 用途 | 常用參數 |
|---|---|---|
| `info` | 檔案概覽 | `--json` |
| `validate` / `lint` | 結構校驗 | `--json`、`--strict` |
| `notes` | 列出音符 | `--json`、`--no-drums`、`--limit N` |
| `stats` / `analyze` | 音樂內容分析 | `--json` |
| `roll` | ASCII 鋼琴捲簾 | `--width N`、`--rows N` |
| `diff` | 兩檔案音符差異 | `--json`、`--tolerance N` |
| `demo` | 產生內建範例曲 | `--bpm`、`--bars`、`-o` |
| `transpose` | 移調 | `-s/--semitones N`、`--channels 0,1` |
| `quantize` | 量化 | `-g/--grid`（`16`、`1/16` 或 tick）、`--strength`、`--swing` |
| `velocity` | 力度調整 | `--scale`、`--offset`、`--ratio` |
| `humanize` | 人性化擾動 | `--tick N`、`--velocity N`、`--seed N` |
| `tempo` | 速度處理 | `--set BPM`、`--scale F`、`--stretch F` |
| `trim` | 區間裁剪 | `--start`、`--end` |
| `merge` | 合併所有軌道 | `-o` |
| `split` | 依通道拆分 | `-o` |
| `convert` | 格式轉換／匯出 | `--format 0\|1\|2`、`--to csv\|json\|md` |
| `strip` | 依類別剔除 | `--sysex`、`--cc`、`--program`、`--pitch-bend`、`--aftertouch`、`--lyrics`、`--markers` |
| `clean` | 修復常見損壞 | `-o` |

#### 典型組合

```bash
# 批次把一批 MIDI 統一成 120 BPM、量化到 16 分音符、力度壓到 80%
for f in raw/*.mid; do
  midiforge tempo "$f" --set 120 -o "tmp1.mid" &&
  midiforge quantize tmp1.mid -g 16 -o "tmp2.mid" &&
  midiforge velocity tmp2.mid --scale 0.8 -o "out/$(basename "$f")"
done

# 匯出音符表給 Excel / pandas
midiforge convert song.mid --to csv -o notes.csv

# 匯出完整結構（含 tempo map）為 JSON
midiforge convert song.mid --to json -o song.json

# 裁剪第 2~4 小節（480 tpq 下每小節 1920 tick）
midiforge trim song.mid --start 1920 --end 7680 -o clip.mid

# 比對「原曲」與「人工改編版」的差異
midiforge diff original.mid arranged.mid
```

結束碼約定：`0` 正常；`1` 校驗發現 error；`2` 解析／寫入／參數錯誤。可直接在 CI 中使用。

### 🐍 Python API 指南

#### 1️⃣ 讀取與寫入

```python
from midiforge import read_file, write_file, parse, serialize

midi = read_file("song.mid")          # 從磁碟
blob = open("song.mid", "rb").read()
midi = parse(blob)                    # 從位元組串流

data = serialize(midi)                # → bytes
write_file(midi, "out.mid")           # 寫入磁碟
```

#### 2️⃣ 檔案模型

```python
midi.format          # 0 / 1 / 2
midi.division        # 480 表示 480 tpq；負值表示 SMPTE
midi.is_smpte        # bool
midi.ticks_per_quarter
midi.tracks          # List[Track]
midi.all_events()    # 所有軌道展開後的事件（依 tick 排序）
midi.tempo_events()  # 所有 tempo 中繼事件
midi.time_signatures()
midi.end_tick
midi.duration_seconds()
midi.track_by_name("melody")
midi.summary()       # → dict，一行概覽
```

#### 3️⃣ 事件模型

```python
from midiforge import ChannelEvent, MetaEvent, SysExEvent

ev = ChannelEvent(tick=0, channel=0, etype=0x9, data1=60, data2=88)
ev.status            # 0x90
ev.type_name         # 'note_on'
ev.is_note_on        # True（力度為 0 時為 False）
ev.is_note_off       # False（包含「力度為 0 的 note_on」）
ev.pitch             # 60
ev.velocity          # 88
ev.controller_name   # 'Sustain'（CC 事件）
ev.pitch_bend        # -8192 ～ 8191（彎音事件）

meta = MetaEvent(tick=0, mtype=0x51, data=b"\x07\xa1\x20")
meta.tempo           # 500000（微秒／四分音符）
meta.bpm             # 120.0

track_name = MetaEvent(tick=0, mtype=0x03, data="主旋律".encode())
track_name.text      # '主旋律'
```

#### 4️⃣ 音符擷取

```python
from midiforge import extract_notes, max_polyphony, note_density

notes = extract_notes(midi, include_drums=False, close_unterminated=True)
n = notes[0]
n.pitch, n.label      # 60, 'C4'
n.start, n.end        # 起始／結束 tick
n.duration            # 時值 tick
n.start_sec           # 起始秒數（依賴 tempo map）
n.is_drum             # 是否為打擊樂通道
n.unterminated        # 是否未閉合（修補後為 False）
n.to_dict()           # → dict，方便 JSON 序列化

max_polyphony(midi)   # 最大同時發聲數
```

#### 5️⃣ 時間軸：Tempo Map

```python
from midiforge import TempoMap

tm = TempoMap.from_midi(midi)
tm.bpm_at(1920)              # 指定 tick 處的 BPM
tm.tick_to_seconds(1920)     # tick → 秒（分段積分，正確處理變速）
tm.seconds_to_tick(4.0)      # 秒 → tick
tm.tick_to_mbt(1920)         # → (小節, 拍, tick)
tm.to_list()                 # [(tick, 每拍微秒數), ...]
```

> ⚠️ 處理變速（ritardando／accelerando）樂曲時，請務必用 `TempoMap` 換算時間，不要用「單一 BPM × tick」的線性近似。

#### 6️⃣ 音樂分析

```python
from midiforge import guess_key, chord_at, chord_progression, stats
from midiforge.analysis import pitch_class_histogram, velocity_histogram, rhythm_histogram

guess_key(notes)             # {'key': 'A', 'scale': 'minor', 'confidence': 0.93, ...}
chord_at([60, 64, 67, 71])   # 'Cmaj7'
chord_progression(notes, grid=480)
stats(midi)                  # 彙總字典：音符數、音域、密度、力度、複音、調性、直方圖…
```

#### 7️⃣ 變換（預設回傳新物件）

```python
from midiforge import transpose, quantize, velocity, humanize
from midiforge import set_bpm, scale_tempo, trim, merge_tracks, split_by_channel
from midiforge import to_format, strip, clean, remove_duplicate_notes

up      = transpose(midi, semitones=3, include_drums=False)
tight   = quantize(midi, grid=120, strength=0.8, swing=0.15)
soft    = velocity(midi, scale=0.8, offset=-5, ratio=0.9)
alive   = humanize(midi, tick_jitter=8, velocity_jitter=6, seed=42)  # 可重現
fast    = set_bpm(midi, 140)
clip    = trim(midi, start=1920, end=7680)      # 自動修補跨界音符
merged  = merge_tracks(midi)
split   = split_by_channel(midi)
fmt0    = to_format(midi, 0)
lean    = strip(midi, sysex=True, cc=True, lyrics=True)
fixed   = clean(midi)                            # 去孤兒／補閉合／去重
```

需要原地修改時統一傳入 `inplace=True`。

#### 8️⃣ 校驗

```python
from midiforge import validate
from midiforge.validate import summarize, is_healthy, RULE_TITLES

issues = validate(midi, strict=False)
for it in issues:
    print(it.code, it.level, it.message, it.track, it.tick)

summarize(issues)     # {'error': 1, 'warning': 1, 'info': 0}
is_healthy(midi)      # 是否沒有 error
```

規則速查表：

| 編號 | 意義 | 編號 | 意義 |
|---|---|---|---|
| MF001 | 缺少 end_of_track | MF011 | 缺少拍號標記 |
| MF002 | 軌道缺少名稱 | MF012 | end_of_track 之後仍有事件 |
| MF003 | 空軌道 | MF013 | 重複的 end_of_track |
| MF004 | 孤兒音符關事件 | MF014 | tempo 出現在非首軌 |
| MF005 | 未閉合的音符開 | MF015 | 檔案沒有任何音符 |
| MF006 | 零時值音符 | MF016 | 力度超過 127 |
| MF007 | 力度為 0 的音符開 | MF017 | MIDI 格式值異常 |
| MF008 | 同音高音符重疊 | MF018 | 軌道數超過 65535 |
| MF009 | 缺少速度標記 | MF019 | 時基為 0 |
| MF010 | 速度值異常 | MF020 | 未知中繼事件類型 |

#### 9️⃣ 差異比對

```python
from midiforge import diff_midi, diff_notes
from midiforge.diff import format_diff

report = diff_midi(before, after)
report["similarity"]     # 相似度，0.0 ~ 1.0
report["counts"]          # {"added": n, "removed": n, "modified": n, "unchanged": n}
report["added"]           # 新增音符明細清單（removed / modified 同理）
print(format_diff(report))
```

#### 🔟 匯出與視覺化

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

#### 1️⃣1️⃣ 從零建構 MIDI

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

也可以用 `from_notes([(音高, 起始, 時值, 力度), ...])` 一行產生。

### 🧪 錯誤處理

```python
from midiforge import MidiParseError, MidiWriteError, MidiValueError, MidiForgeError

try:
    midi = read_file("maybe_broken.mid")
except MidiParseError as exc:
    print(exc.message)   # 可讀的原因說明
    print(exc.offset)    # 出錯位元組偏移（-1 表示未知）
```

---

## 💡 設計思路與迭代規劃

### 🏛 架構分層

```
┌─────────────────────────────────────────────────────────────┐
│  CLI 層        cli.py（18 個子命令，argparse）                │
├─────────────────────────────────────────────────────────────┤
│  能力層   analysis · transform · validate · diff · export     │
│          builder（建構）                                      │
├─────────────────────────────────────────────────────────────┤
│  語意層   notes（音符配對） · tempo（時間軸） · gm（音樂常數） │
├─────────────────────────────────────────────────────────────┤
│  模型層   midifile（MidiFile/Track） · events（事件）         │
├─────────────────────────────────────────────────────────────┤
│  編解碼層 reader（解析） · writer（序列化） · vlq（變長量）    │
└─────────────────────────────────────────────────────────────┘
```

每一層只依賴下層，**不允許反向依賴**；能力層之間也盡量解耦（`analysis` 只依賴 `notes` 與 `gm`，不認識 `cli`）。如此一來，新增一項分析能力時不會牽動解析器。

### 🎯 關鍵設計決策

| 決策 | 取捨理由 |
|---|---|
| **零第三方依賴** | 犧牲部分效能（純 Python 位元運算）換取極致的部署可靠性與可嵌入性；MIDI 檔案通常只有數十 KB，效能完全足夠 |
| **dataclasses 而非裸 tuple** | 事件欄位語意（tick／channel／etype／data1／data2）一旦用 tuple 就會滿天飛魔術數字；dataclass 自帶可讀 repr、可 `to_dict()`、IDE 友善 |
| **預設不可變（inplace=False）** | 音訊批次腳本最怕「改了一半又改不回來」；回傳新物件讓 `a → b → c` 的管線天然可回溯，代價只是一次 `deepcopy` |
| **損壞檔案「讀出來 ＋ 回報」而非直接丟錯** | 真實世界的 MIDI 有大量殘缺檔案；能讀多少讀多少，再由 `validate` 給出健康檢查報告，比一句 `invalid file` 有用得多 |
| **確定性優先** | 除 `humanize` 外所有演算法都是純函式，同一輸入永遠同一輸出，方便做快照測試與 diff |
| **humanize 支援 seed** | 隨機性必須可控、可重現，否則無法做回歸測試 |
| **時值命名採用標準記譜法** | 分母以全音符為 1（`1/4` ＝ 四分音符），避免「以拍為單位」造成的二義性 |
| **end_of_track 永遠排在軌道末尾** | 序列化時強制後置，否則解析器會提前終止、靜默吞掉後面的事件 |

### 🗺 迭代路線

**v1.0.0（目前）** — 完整的 SMF 讀寫、音符擷取、調性／和弦／節奏分析、11 類變換、20 條校驗規則、18 個 CLI 命令、380 項測試。

**v1.1.0（規劃）**
- 🎵 MusicXML 匯入／匯出（與樂譜軟體互通）
- 🥁 更細緻的鼓組對應與自訂鼓圖
- 📐 對齊小節線的量化（`--align-bars`）
- 🧹 CLI 支援批次目錄處理與平行運算

**v1.2.0（規劃）**
- 🎹 除類型 0/1 之外：支援 RMID（內嵌資源的 MIDI）
- 🔊 匯出為 WAV（採可選依賴，核心仍維持零依賴）
- 🧬 風格化變換：琶音器、和聲產生器
- 📊 HTML 視覺化報告（內建樣板，離線可用）

**v2.0.0（遠期）**
- 🤖 簡易旋律補全／續寫（以統計 n-gram 為基礎，仍保持零依賴）
- 🌐 WebAssembly 建置，瀏覽器端直接解析
- 🔌 外掛機制：允許使用者註冊自訂校驗規則

> 我們始終守住兩條底線：**核心套件永遠零依賴**、**核心套件永遠離線可用**。任何需要外部函式庫的能力都會以「可選擴充」的形式提供。

---

## 📦 打包與部署指南

### 🧑‍💻 本機開發

```bash
git clone https://github.com/gitstq/MidiForge.git
cd MidiForge

# 執行全部測試（不需安裝任何依賴）
python -m unittest discover -s tests -t .

# 以模組方式試跑 CLI
python -m midiforge demo -o /tmp/demo.mid
python -m midiforge info /tmp/demo.mid
```

### 📦 建置發行套件

```bash
# 安裝建置工具（僅建置時需要）
pip install build twine

# 建置 sdist + wheel
python -m build

# 產物位於 dist/
#   midiforge-1.0.0.tar.gz
#   midiforge-1.0.0-py3-none-any.whl

# 校驗中繼資料
twine check dist/*
```

也可以使用倉庫內建腳本：

```bash
bash scripts/build.sh        # 建置
bash scripts/release.sh      # 建置 ＋ 校驗 ＋ 列印上傳命令
```

### 🚀 發佈到 PyPI

```bash
# 先上傳到 TestPyPI 驗證
twine upload --repository testpypi dist/*

# 正式發佈
twine upload dist/*
```

### 🐳 單檔／二進位發行

MidiForge 是純 Python 套件，可依需求打包成獨立執行檔（**選用**，不影響核心的零依賴特性）：

```bash
pip install pyinstaller
pyinstaller --onefile --name midiforge midiforge/__main__.py
# 產物：dist/midiforge（Windows 下為 dist/midiforge.exe）
```

### 🔧 嵌入你的專案

```python
# 直接把 midiforge/ 目錄複製到你的專案即可（零依賴的好處）
from midiforge import read_file, extract_notes
```

或正常宣告依賴：

```toml
# pyproject.toml
dependencies = ["midiforge>=1.0.0"]
```

### 🤖 在 CI 中使用

```yaml
- name: 校驗所有 MIDI 檔案
  run: |
    pip install midiforge
    for f in assets/**/*.mid; do midiforge validate "$f" || exit 1; done
```

`validate` 發現 error 時結束碼為 `1`，可直接作為管線閘門。

### 📁 目錄結構

```
MidiForge/
├── midiforge/            # 核心套件（零依賴）
│   ├── __init__.py       # 公開 API 彙總 + __version__
│   ├── __main__.py       # python -m midiforge
│   ├── cli.py            # 命令行（18 個子命令）
│   ├── reader.py         # SMF 解析
│   ├── writer.py         # SMF 序列化
│   ├── vlq.py            # 變長量編解碼
│   ├── midifile.py       # MidiFile / Track 模型
│   ├── events.py         # 事件模型與常數表
│   ├── notes.py          # 音符配對與複音分析
│   ├── tempo.py          # TempoMap（tick ↔ 秒 ↔ 小節/拍/tick）
│   ├── gm.py             # GM 音色／鼓圖／音名／時值命名
│   ├── analysis.py       # 調性、和弦、直方圖、統計
│   ├── transform.py      # 移調、量化、力度、裁剪……
│   ├── validate.py       # MF001–MF020 校驗規則
│   ├── diff.py           # 音符級差異比對
│   ├── export.py         # CSV / JSON / Markdown / 鋼琴捲簾
│   ├── builder.py        # 從零建構 MIDI
│   ├── errors.py         # 例外體系
│   └── py.typed          # PEP 561 型別標記
├── tests/                # 380 項單元測試
├── examples/             # 可執行範例
├── scripts/              # 建置／發佈腳本
├── docs/                 # 補充文件
├── .github/workflows/    # CI
├── pyproject.toml
├── LICENSE               # MIT
├── CHANGELOG.md
└── README.md             # 简体中文 / 繁體中文 / English
```

---

## 🤝 貢獻指南

歡迎任何形式的貢獻：🐛 回報 bug、💡 提出需求、📝 修改文件、🔧 提交程式碼。

### 🏁 快速流程

```bash
# 1. Fork 本倉庫並複製
git clone https://github.com/<你的帳號>/MidiForge.git
cd MidiForge

# 2. 建立特性分支
git checkout -b feat/your-feature

# 3. 撰寫程式碼 ＋ 補測試
#    新增能力請務必同步補上 tests/ 下的案例

# 4. 本機完整自測
python -m unittest discover -s tests -t .

# 5. 提交（遵循 Angular 提交規範）
git commit -m "feat: 新增 XXX 能力"

# 6. 推送並發起 Pull Request
git push origin feat/your-feature
```

### 📜 提交訊息規範（Angular Convention）

| 前綴 | 用途 | 範例 |
|---|---|---|
| `feat:` | 新功能 | `feat: 支援 RMID 解析` |
| `fix:` | 修復缺陷 | `fix: 修正 SMPTE 幀率解析` |
| `docs:` | 文件變更 | `docs: 補充 CLI 範例` |
| `refactor:` | 重構（不改變外部行為） | `refactor: 拆分 _parse_track` |
| `test:` | 測試相關 | `test: 補充 trim 邊界案例` |
| `perf:` | 效能優化 | `perf: 重複使用 TempoMap 快取` |
| `chore:` | 建置／工具／雜項 | `chore: 升級 CI Python 版本` |
| `style:` | 格式調整 | `style: 統一引號風格` |

### ✅ 提交的硬性要求

1. **測試必須通過**：`python -m unittest discover -s tests -t .` 全綠；
2. **新增程式碼要有測試**：核心邏輯需涵蓋正常路徑 ＋ 邊界 ＋ 例外；
3. **保持零依賴**：不得在 `midiforge/` 中引入任何第三方 import（標準函式庫除外）；
4. **保持離線**：不得引入任何網路請求；
5. **型別註解**：新增公開函式請附上 type hints 與中文 docstring；
6. **相容 Python 3.8+**：不要使用 3.9+ 專屬語法（例如 `list[str]` 字面量，請用 `List[str]`）；
7. **提交前自查**：不要提交 `__pycache__`、虛擬環境、建置產物（已由 `.gitignore` 涵蓋）。

### 🐛 回報 Bug

請附上：

- MidiForge 版本（`python -m midiforge --version`）與 Python 版本；
- 完整的錯誤堆疊（含 `offset` 與錯誤訊息）；
- 能重現問題的最小 MIDI 檔案（或 `midiforge demo` 的輸出 ＋ 重現命令）；
- 期望行為 vs 實際行為。

### 💬 行為準則

請保持友善、就事論事。討論技術方案時請提出理由與場景，而不只是丟出結論。

---

## 📄 開源協議說明

本專案以 **MIT License** 開源，詳見 [LICENSE](./LICENSE)。

### 📝 你可以做什麼

- ✅ 免費用於**個人、教育、商業**專案；
- ✅ 修改、二次散布、再授權；
- ✅ 作為閉源產品的一部分發佈（**無需開源你的產品**）；
- ✅ 私下使用，無須告知作者。

### ⚠️ 你需要做什麼

- 在軟體的所有副本或重要組成部分中**保留著作權聲明與授權聲明**；
- 也就是：`LICENSE` 全文（含 `Copyright (c) 2026 MidiForge Contributors`）需隨散布物一併提供。

### 🚫 免責聲明

本軟體依「**現狀**」（AS IS）提供，**不附任何明示或暗示的擔保**，包括但不限於可商用性、特定用途適用性與不侵權性。在任何情況下，作者或著作權持有人均不對因使用本軟體所產生的任何求償、損害或其它責任負責。

### 🔗 第三方說明

- MidiForge **不包含、不複製**任何第三方原始碼；實作參考的是公開的 **Standard MIDI Files 1.0 規範**（MIDI Manufacturers Association）與公開的音樂理論知識（Krumhansl-Kessler 音級輪廓、General MIDI 音色表等）。
- 執行期**零第三方依賴**，沒有傳遞依賴的授權合規負擔。
- 倉庫中 `examples/`、`tests/` 產生的 MIDI 資料皆由程式內建演算法合成，不含受著作權保護的音樂作品。

---

<div align="center">

如果 MidiForge 幫助到你，歡迎 ⭐ **Star** 一下，也歡迎把你的使用場景分享到 Issues！

Made with ❤️ and zero dependencies.

[简体中文](./README.md) · [繁體中文](./README.zh-TW.md) · [English](./README.en.md)

</div>
