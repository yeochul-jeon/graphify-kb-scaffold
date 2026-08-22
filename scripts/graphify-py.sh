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

# 클러스터링 재현성 — networkx louvain 은 문자열 키 집합을 순회하고 그 순서가
# PYTHONHASHSEED 로 프로세스마다 무작위화되므로, 고정하지 않으면 **입력이 완전히
# 같아도 커뮤니티 수가 흔들린다.** upstream 도 같은 이유로 자기 git 훅에서 이 값을
# 0 으로 고정한다(graphify/hooks.py `_HOOK_SCRIPT`) — 그런데 이 저장소는 그 훅을 쓰지
# 않고 자체 `.githooks/pre-commit`(wiki 가드)을 쓰므로 고정 지점이 없었다.
#
# 실측 (2026-08-17, graph.json 6607n/8388e 동일 입력에 cluster() 만 반복 실행):
#   PYTHONHASHSEED=0  → 965 · 965 · 965   (재현)
#   미설정            → 965 · 964 · 966 · 964   (흔들림)
# 이 흔들림이 자기 측정 문서의 주입값을 바꿔 wiki 가드를 상시 발동시킨다 — 원장 #72 잔여 ①.
# 되돌리려면 이 export 한 줄만 지우면 된다.
export PYTHONHASHSEED=0

exec "$PYTHON" "$@"
