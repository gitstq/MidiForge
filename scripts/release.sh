#!/usr/bin/env bash
# 构建并（可选）上传 MidiForge 到 PyPI
#
# 用法：
#   bash scripts/release.sh            # 仅构建 + 校验，并打印上传命令
#   bash scripts/release.sh testpypi   # 上传到 TestPyPI
#   bash scripts/release.sh pypi       # 上传到正式 PyPI
#
# 注意：真实上传需要 ~/.pypirc 或环境变量 TWINE_USERNAME / TWINE_PASSWORD（推荐 __token__）。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TARGET="${1:-none}"

bash scripts/build.sh

case "$TARGET" in
  testpypi)
    echo "==> 上传到 TestPyPI"
    python3 -m twine upload --repository testpypi dist/*
    ;;
  pypi)
    echo "==> 上传到 PyPI"
    python3 -m twine upload dist/*
    ;;
  *)
    echo "==> 构建完成，未执行上传。"
    echo "    上传到 TestPyPI：bash scripts/release.sh testpypi"
    echo "    上传到正式 PyPI：bash scripts/release.sh pypi"
    ;;
esac
