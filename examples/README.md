# 📚 示例（Examples）

所有示例都是**可直接运行**的独立脚本，且不依赖任何外部 MIDI 素材（无素材时用 `demo_song()` 现场生成）。

## ▶️ 运行方式

```bash
# 在项目根目录
python examples/01_quickstart.py

# 若未安装 midiforge，加上 PYTHONPATH
PYTHONPATH=. python examples/01_quickstart.py
```

## 📖 示例清单

| 文件 | 主题 | 你会学到 |
|---|---|---|
| `01_quickstart.py` | 快速上手 | 生成/读取 MIDI、`summary()`、`extract_notes()`、写回与自检 |
| `02_analysis.py` | 音乐内容分析 | 调性识别、和弦进行、音级/力度/时值直方图、重复乐句、`stats()` |
| `03_batch_transform.py` | 批量变换流水线 | 移调 → 量化 → 力度 → 裁剪 → 修复，以及校验与差异对比 |
| `04_build_from_scratch.py` | 从零构造 MIDI | 手工组装事件（tempo/拍号/调号/音符/鼓点）与 `from_notes()` 生成 |

## 💡 小提示

- 所有变换函数默认 **返回新对象**，因此流水线每一步都能独立回溯（见 `03_batch_transform.py`）。
- 处理完记得跑一次 `validate()`：发现 error 就是流水线出了问题。
- 想把结果交给 Excel / pandas，用 `notes_to_csv()`（见 `03_batch_transform.py`）。
- 想肉眼确认旋律轮廓，用 `piano_roll()`（见 `04_build_from_scratch.py`）。
