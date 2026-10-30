# 🖥 命令行参考（CLI Reference）

> 本文档由 `midiforge.cli.build_parser()` 自动生成，覆盖全部 18 个子命令。

安装后使用 `midiforge`，未安装时可用 `python -m midiforge`，两者参数完全一致。

```bash
midiforge --help
midiforge <command> --help
midiforge --version
```

## 📌 退出码

| 退出码 | 含义 |
|---|---|
| `0` | 正常完成 |
| `1` | `validate` 发现 error 级问题 |
| `2` | 解析 / 写入 / 参数错误（含文件不存在、MIDI 结构损坏） |

---

### 顶层

```
usage: midiforge [-h] [--version] <command> ...

MidiForge —— 零依赖 MIDI 文件处理与分析工具箱

positional arguments:
  <command>
    info           显示 MIDI 文件概览
    validate (lint)
                   校验结构并给出问题清单
    notes          列出所有音符
    stats (analyze)
                   音乐内容分析：调性、和弦、节奏与力度分布
    roll           终端 ASCII 钢琴卷帘
    diff           对比两个 MIDI 文件的音符差异
    demo           生成内置示例曲（无需外部素材）
    transpose      整体移调
    quantize       量化音符起始位置
    velocity       调整力度（缩放 / 平移 / 动态压缩）
    humanize       加入可控随机扰动（固定种子可复现）
    tempo          设置或缩放速度（BPM）
    trim           裁剪到指定区间
    merge          把所有轨道合并为一条
    split          按通道拆分为多条轨道
    convert        转换格式 / 导出为 CSV、JSON、Markdown
    strip          按类别移除事件
    clean          修复孤儿音符关 / 未闭合音符 / 重复事件

options:
  -h, --help       show this help message and exit
  --version        show program's version number and exit

示例:
  midiforge info song.mid
  midiforge stats song.mid --json
  midiforge notes song.mid --csv -o notes.csv
  midiforge transpose song.mid -s 3 -o out.mid
  midiforge quantize song.mid --grid 16 --swing 0.2 -o out.mid

```

### `analyze`

```
usage: midiforge stats [-h] [--json] file

positional arguments:
  file

options:
  -h, --help  show this help message and exit
  --json
```

### `clean`

```
usage: midiforge clean [-h] [--dedupe] -o OUTPUT file

positional arguments:
  file

options:
  -h, --help            show this help message and exit
  --dedupe              同时移除完全重叠的重复音符
  -o OUTPUT, --output OUTPUT
```

### `convert`

```
usage: midiforge convert [-h] [--format {0,1,2}] [--to {csv,json,md}] -o
                         OUTPUT
                         file

positional arguments:
  file

options:
  -h, --help            show this help message and exit
  --format {0,1,2}      目标 MIDI 格式
  --to {csv,json,md}    导出为文本格式
  -o OUTPUT, --output OUTPUT
```

### `demo`

```
usage: midiforge demo [-h] [--bpm BPM] [--bars BARS] [-o OUTPUT]

options:
  -h, --help            show this help message and exit
  --bpm BPM
  --bars BARS
  -o OUTPUT, --output OUTPUT
```

### `diff`

```
usage: midiforge diff [-h] [--json] [--tolerance TOLERANCE] a b

positional arguments:
  a
  b

options:
  -h, --help            show this help message and exit
  --json
  --tolerance TOLERANCE
                        起始时间容差（tick）
```

### `humanize`

```
usage: midiforge humanize [-h] [--tick-jitter TICK_JITTER]
                          [--velocity-jitter VELOCITY_JITTER] [--seed SEED] -o
                          OUTPUT
                          file

positional arguments:
  file

options:
  -h, --help            show this help message and exit
  --tick-jitter TICK_JITTER
  --velocity-jitter VELOCITY_JITTER
  --seed SEED
  -o OUTPUT, --output OUTPUT
```

### `info`

```
usage: midiforge info [-h] [--json] file

positional arguments:
  file

options:
  -h, --help  show this help message and exit
  --json      以 JSON 输出
```

### `lint`

```
usage: midiforge validate [-h] [--json] [--strict] file

positional arguments:
  file

options:
  -h, --help  show this help message and exit
  --json
  --strict    同时输出 info 级问题
```

### `merge`

```
usage: midiforge merge [-h] -o OUTPUT file

positional arguments:
  file

options:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
```

### `notes`

```
usage: midiforge notes [-h] [--json] [--csv] [--md] [--no-drums]
                       [--limit LIMIT] [-o OUTPUT]
                       file

positional arguments:
  file

options:
  -h, --help            show this help message and exit
  --json
  --csv                 以 CSV 输出
  --md                  以 Markdown 表格输出
  --no-drums            排除打击乐通道
  --limit LIMIT         只显示前 N 个音符
  -o OUTPUT, --output OUTPUT
                        写入文件（默认 stdout）
```

### `quantize`

```
usage: midiforge quantize [-h] [-g GRID] [--strength STRENGTH] [--swing SWING]
                          [--channels CHANNELS] -o OUTPUT
                          file

positional arguments:
  file

options:
  -h, --help            show this help message and exit
  -g GRID, --grid GRID  网格：tick 数或 4/8/16 等音符分母
  --strength STRENGTH
  --swing SWING
  --channels CHANNELS   只处理这些通道
  -o OUTPUT, --output OUTPUT
```

### `roll`

```
usage: midiforge roll [-h] [--width WIDTH] [--rows ROWS] file

positional arguments:
  file

options:
  -h, --help     show this help message and exit
  --width WIDTH
  --rows ROWS
```

### `split`

```
usage: midiforge split [-h] -o OUTPUT file

positional arguments:
  file

options:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
```

### `stats`

```
usage: midiforge stats [-h] [--json] file

positional arguments:
  file

options:
  -h, --help  show this help message and exit
  --json
```

### `strip`

```
usage: midiforge strip [-h] [--sysex] [--cc] [--keep-cc KEEP_CC] [--program]
                       [--pitch-bend] [--aftertouch] [--lyrics] [--markers] -o
                       OUTPUT
                       file

positional arguments:
  file

options:
  -h, --help            show this help message and exit
  --sysex
  --cc                  移除控制器事件
  --keep-cc KEEP_CC     保留的控制器编号，如 7,10,64
  --program
  --pitch-bend
  --aftertouch
  --lyrics
  --markers
  -o OUTPUT, --output OUTPUT
```

### `tempo`

```
usage: midiforge tempo [-h] [--set SET_BPM] [--scale SCALE]
                       [--stretch STRETCH] -o OUTPUT
                       file

positional arguments:
  file

options:
  -h, --help            show this help message and exit
  --set SET_BPM         设为固定 BPM
  --scale SCALE         按倍率缩放 BPM（>1 更快）
  --stretch STRETCH     按倍率缩放时间轴（>1 更长）
  -o OUTPUT, --output OUTPUT
```

### `transpose`

```
usage: midiforge transpose [-h] -s SEMITONES [--channels CHANNELS]
                           [--include-drums] -o OUTPUT
                           file

positional arguments:
  file

options:
  -h, --help            show this help message and exit
  -s SEMITONES, --semitones SEMITONES
  --channels CHANNELS   只处理这些通道，如 0,1,2
  --include-drums
  -o OUTPUT, --output OUTPUT
```

### `trim`

```
usage: midiforge trim [-h] [--start START] [--end END] -o OUTPUT file

positional arguments:
  file

options:
  -h, --help            show this help message and exit
  --start START         起始 tick
  --end END             结束 tick（缺省到结尾）
  -o OUTPUT, --output OUTPUT
```

### `validate`

```
usage: midiforge validate [-h] [--json] [--strict] file

positional arguments:
  file

options:
  -h, --help  show this help message and exit
  --json
  --strict    同时输出 info 级问题
```

### `velocity`

```
usage: midiforge velocity [-h] [--scale SCALE] [--offset OFFSET]
                          [--ratio RATIO] [--channels CHANNELS] -o OUTPUT
                          file

positional arguments:
  file

options:
  -h, --help            show this help message and exit
  --scale SCALE
  --offset OFFSET
  --ratio RATIO         动态压缩比，>1 压缩
  --channels CHANNELS   只处理这些通道
  -o OUTPUT, --output OUTPUT
```
