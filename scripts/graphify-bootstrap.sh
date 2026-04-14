#!/usr/bin/env bash
# graphify python 인터프리터 탐지 & 설치 래퍼.
# SKILL.md Step 1 블록의 command_substitution을 Claude Code 밖에서 처리한다.
set -euo pipefail

GRAPHIFY_BIN=$(which graphify 2>/dev/null || true)
if [ -n "$GRAPHIFY_BIN" ]; then
    PYTHON=$(head -1 "$GRAPHIFY_BIN" | tr -d '#!')
    case "$PYTHON" in
        *[!a-zA-Z0-9/_.-]*) PYTHON="python3" ;;
    esac
else
    PYTHON="python3"
fi

"$PYTHON" -c "import graphify" 2>/dev/null || \
    "$PYTHON" -m pip install graphifyy -q 2>/dev/null || \
    "$PYTHON" -m pip install graphifyy -q --break-system-packages 2>&1 | tail -3

mkdir -p graphify-out
"$PYTHON" -c "import sys; open('graphify-out/.graphify_python', 'w').write(sys.executable)"
