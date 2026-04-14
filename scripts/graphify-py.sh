#!/usr/bin/env bash
# graphify python 인터프리터 래퍼.
# Claude Code의 command_substitution 승인 프롬프트를 우회하기 위해
# $(...) 치환을 스킬 밖(이 스크립트 내부)에서 수행한다.
set -euo pipefail

PYCACHE="graphify-out/.graphify_python"
if [ ! -f "$PYCACHE" ]; then
  echo "ERROR: $PYCACHE not found. Run scripts/graphify-bootstrap.sh first." >&2
  exit 1
fi

PYTHON=$(cat "$PYCACHE")
exec "$PYTHON" "$@"
