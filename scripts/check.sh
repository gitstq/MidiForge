#!/usr/bin/env bash
# 本地一键自检：单元测试 + CLI 冒烟 + 零依赖检查
#
# 用法：
#   bash scripts/check.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "==> 1/4 单元测试"
"$PYTHON" -m unittest discover -s tests -t . 2>&1 | tail -3

echo "==> 2/4 CLI 冒烟"
"$PYTHON" -m midiforge --version
"$PYTHON" -m midiforge demo -o "$TMP/demo.mid"
"$PYTHON" -m midiforge info "$TMP/demo.mid" >/dev/null
"$PYTHON" -m midiforge stats "$TMP/demo.mid" >/dev/null
"$PYTHON" -m midiforge validate "$TMP/demo.mid"
"$PYTHON" -m midiforge transpose "$TMP/demo.mid" -s 3 -o "$TMP/up.mid"
"$PYTHON" -m midiforge quantize "$TMP/demo.mid" -g 1/8 -o "$TMP/q.mid"
"$PYTHON" -m midiforge trim "$TMP/demo.mid" --start 0 --end 1920 -o "$TMP/cut.mid"
"$PYTHON" -m midiforge convert "$TMP/demo.mid" --to csv -o "$TMP/notes.csv"
for f in "$TMP"/*.mid; do "$PYTHON" -m midiforge validate "$f" >/dev/null; done
echo "    所有产物校验通过"

echo "==> 3/4 示例脚本"
for ex in examples/*.py; do
  printf "    %-32s" "$ex"
  PYTHONPATH=. "$PYTHON" "$ex" >/dev/null && echo "OK"
done

echo "==> 4/4 零依赖检查"
"$PYTHON" - <<'PY'
import ast, pathlib, sys

STDLIB_HINT = {
    "__future__", "argparse", "bisect", "collections", "copy", "csv",
    "dataclasses", "io", "itertools", "json", "math", "os", "random", "re",
    "statistics", "struct", "sys", "tempfile", "textwrap", "typing",
    "unicodedata", "unittest",
}
bad = []
for path in pathlib.Path("midiforge").rglob("*.py"):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] not in STDLIB_HINT | {"midiforge"}:
                    bad.append("%s: import %s" % (path, alias.name))
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            if node.module.split(".")[0] not in STDLIB_HINT | {"midiforge"}:
                bad.append("%s: from %s import ..." % (path, node.module))
if bad:
    print("发现非标准库依赖：")
    for line in bad:
        print("  " + line)
    sys.exit(1)
print("    midiforge/ 内无第三方依赖")
PY

echo "==> 全部通过 ✅"
