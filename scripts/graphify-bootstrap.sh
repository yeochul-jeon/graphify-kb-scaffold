#!/usr/bin/env bash
# graphify python 인터프리터 탐지 & 설치 래퍼.
# SKILL.md Step 1 블록의 command_substitution을 Claude Code 밖에서 처리한다.
#
# 설치 우선순위 (graphify 미발견 시):
#   1. uv tool install graphifyy   (uv 있으면)
#   2. pipx install graphifyy      (pipx 있으면)
#   3. pip install graphifyy       (fallback)
set -euo pipefail

GRAPHIFY_BIN=$(which graphify 2>/dev/null || true)

if [ -z "$GRAPHIFY_BIN" ]; then
    # graphify 미설치 — uv tool / pipx / pip 순으로 시도
    if command -v uv >/dev/null 2>&1; then
        echo "graphify 미설치. uv tool로 설치 시도..." >&2
        uv tool install graphifyy --quiet 2>/dev/null || true
    elif command -v pipx >/dev/null 2>&1; then
        echo "graphify 미설치. pipx로 설치 시도..." >&2
        pipx install graphifyy --quiet 2>/dev/null || true
    fi
    # 재탐지
    GRAPHIFY_BIN=$(which graphify 2>/dev/null || true)
fi

if [ -n "$GRAPHIFY_BIN" ]; then
    PYTHON=$(head -1 "$GRAPHIFY_BIN" | tr -d '#!')
    case "$PYTHON" in
        *[!a-zA-Z0-9/_.-]*) PYTHON="python3" ;;
    esac
else
    # uv / pipx 모두 없거나 실패 시 pip fallback
    PYTHON="python3"
    "$PYTHON" -c "import graphify" 2>/dev/null || \
        "$PYTHON" -m pip install graphifyy -q 2>/dev/null || \
        "$PYTHON" -m pip install graphifyy -q --break-system-packages 2>&1 | tail -3
fi

mkdir -p graphify-out
"$PYTHON" -c "import sys; open('graphify-out/.graphify_python', 'w').write(sys.executable)"
echo "✓ Python 경로 기록 완료: $PYTHON" >&2
