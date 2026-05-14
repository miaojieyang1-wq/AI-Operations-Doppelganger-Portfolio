#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "未检测到 Python。此源代码分发包需要先安装 Python 3.10 或更高版本。"
  exit 1
fi

python3 - <<'PY'
import sys
if sys.version_info < (3, 10):
    raise SystemExit(1)
PY
if [ $? -ne 0 ]; then
  echo "当前 Python 版本低于 3.10，无法启动 AI 运营分身。"
  exit 1
fi

python3 -m streamlit run app.py
