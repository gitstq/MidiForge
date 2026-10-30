# 📚 文档（docs）

| 文档 | 内容 |
|---|---|
| [README.md](../README.md) | 项目主文档（简体中文 / 繁體中文 / English，顶部可切换） |
| [CLI.md](./CLI.md) | 命令行完整参考：18 个子命令的全部参数，自动生成 |
| [API.md](./API.md) | Python API 参考：全部公开函数/类的签名与说明，自动生成 |
| [SMF格式要点.md](./SMF格式要点.md) | Standard MIDI File 格式要点与常见坑位备忘 |
| [../CONTRIBUTING.md](../CONTRIBUTING.md) | 贡献指南、提交规范、PR 硬性要求 |
| [../CHANGELOG.md](../CHANGELOG.md) | 更新日志 |

## 🔄 重新生成自动文档

`CLI.md` 与 `API.md` 均从代码自动提取，改动 CLI 或公开 API 后请重新生成：

```bash
python - <<'PY' > docs/CLI.md
from midiforge.cli import build_parser
p = build_parser()
print(p.format_help())
for a in p._actions:
    if a.__class__.__name__ == "_SubParsersAction":
        for name, sub in sorted(a.choices.items()):
            print("\n### `%s`\n" % name)
            print(sub.format_help())
PY
```

（`API.md` 用 `inspect.signature` + `inspect.getdoc` 遍历各模块生成，见仓库脚本思路。）
