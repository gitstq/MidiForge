# 🤝 贡献指南（Contributing）

感谢你愿意为 MidiForge 做出贡献！这份文档说明如何参与开发、我们遵守哪些规范，以及提交 PR 前需要满足哪些硬性条件。

## 🏁 快速流程

```bash
# 1. Fork 并克隆
git clone https://github.com/<你的用户名>/MidiForge.git
cd MidiForge

# 2. 建分支
git checkout -b feat/your-feature

# 3. 编码 + 补测试
# 4. 全量自测
python -m unittest discover -s tests -t .

# 5. 按 Angular 规范提交
git commit -m "feat: 新增 XXX 能力"

# 6. 推送并发 PR
git push origin feat/your-feature
```

## 🧪 本地自测

```bash
# 全量
python -m unittest discover -s tests -t .

# 单个文件
python -m unittest tests.test_reader -v

# 单个用例
python -m unittest tests.test_reader.TestTrackParsing.test_roundtrip_demo

# 免安装试跑 CLI
python -m midiforge demo -o /tmp/demo.mid
python -m midiforge info /tmp/demo.mid
```

> ✅ **本项目的测试不需要安装任何依赖** —— 这是「零依赖」设计的直接收益。

## 📜 提交信息规范（Angular Convention）

格式：`<type>: <subject>`

| 前缀 | 用途 | 示例 |
|---|---|---|
| `feat:` | 新功能 | `feat: 支持 RMID 解析` |
| `fix:` | 修复缺陷 | `fix: 修正 SMPTE 帧率解析` |
| `docs:` | 文档变更 | `docs: 补充 CLI 示例` |
| `refactor:` | 重构（外部行为不变） | `refactor: 拆分 _parse_track` |
| `test:` | 测试相关 | `test: 补充 trim 边界用例` |
| `perf:` | 性能优化 | `perf: 复用 TempoMap 缓存` |
| `chore:` | 构建 / 工具 / 杂项 | `chore: 升级 CI Python 版本` |
| `style:` | 格式调整 | `style: 统一引号风格` |

**subject 书写要求**：使用中文（或英文）祈使句，首字母不大写，结尾不加句号，长度控制在 72 字符内。

## ✅ PR 的硬性要求

1. **测试全绿**：`python -m unittest discover -s tests -t .` 必须通过；
2. **新增代码必须带测试**：核心逻辑需覆盖正常路径、边界条件与异常路径；
3. **保持零依赖**：`midiforge/` 内不允许引入任何第三方 import（标准库除外）；
4. **保持离线**：不得引入任何网络请求；
5. **类型注解与文档**：新增公开函数需附带 type hints 与中文 docstring；
6. **兼容 Python 3.8+**：不要使用 3.9+ 专属语法（如 `list[str]` 字面量，请写 `List[str]`）；
7. **提交前自查**：不要提交 `__pycache__`、虚拟环境、构建产物（`.gitignore` 已覆盖）；
8. **README 三语同步**：若改动了对外行为，需同步更新 `README.md`、`README.zh-TW.md`、`README.en.md` 与 `CHANGELOG.md`。

## 🏛 架构约定

```
CLI 层 (cli.py)
   ↓
能力层 (analysis / transform / validate / diff / export / builder)
   ↓
语义层 (notes / tempo / gm)
   ↓
模型层 (midifile / events)
   ↓
编解码层 (reader / writer / vlq)
```

- **只允许向下依赖**，禁止反向依赖；
- 能力层之间尽量解耦（例如 `analysis` 不应 import `cli`）；
- 新增校验规则请同时补充 `RULE_TITLES` 与对应测试；
- 新增 CLI 命令请同步更新三语 README 的命令表。

## 🎨 代码风格

- 缩进 4 空格，行宽不超过 100 字符；
- 模块、函数、类均需 docstring（中文）；
- 常量集中放在模块顶部或 `gm.py` / `events.py` 的常量表中，不要在函数体内散落魔法数字；
- 对外 API 请同步加入 `midiforge/__init__.py` 的 `__all__`。

## 🐛 报告 Bug

请在 Issue 中附上：

- MidiForge 版本（`python -m midiforge --version`）与 Python 版本；
- 完整报错堆栈（含 `offset` 与错误信息）；
- 最小复现 MIDI 文件，或 `midiforge demo` 的输出 + 复现命令；
- 期望行为 vs 实际行为。

## 💬 行为准则

保持友善、就事论事。讨论技术方案时请给出理由与场景，而不是只给结论。

感谢你的时间与热情 🙏
