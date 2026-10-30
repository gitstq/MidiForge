#!/usr/bin/env bash
# 构建 MidiForge 分发包（sdist + wheel）
#
# 用法：
#   bash scripts/build.sh
#
# 产物位于 dist/：
#   midiforge-1.0.0.tar.gz
#   midiforge-1.0.0-py3-none-any.whl
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"

echo "==> 运行全量测试"
"$PYTHON" -m unittest discover -s tests -t . >/dev/null
echo "    测试通过"

echo "==> 清理历史产物"
rm -rf dist build ./*.egg-info

echo "==> 安装构建工具（仅构建时需要）"
"$PYTHON" -m pip install --quiet --upgrade build twine

echo "==> 构建 sdist + wheel"
"$PYTHON" -m build

echo "==> 校验元数据"
"$PYTHON" -m twine check dist/*

echo "==> 完成，产物："
ls -1 dist/
