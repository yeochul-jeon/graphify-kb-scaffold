#!/usr/bin/env bash
# 업스트림 graphify 스킬이 업데이트되면 이 스크립트로 프로젝트 오버라이드를 재생성.
# 실행 후 Step 1 bootstrap 블록은 수동으로 확인해야 한다.
set -euo pipefail

SRC="$HOME/.claude/skills/graphify/SKILL.md"
DST=".claude/skills/graphify/SKILL.md"

if [ ! -f "$SRC" ]; then
  echo "ERROR: 글로벌 스킬 $SRC 를 찾을 수 없음." >&2
  exit 1
fi

mkdir -p "$(dirname "$DST")"

sed \
  -e 's|\$(cat graphify-out/\.graphify_python)|scripts/graphify-py.sh|g' \
  "$SRC" > "$DST"

echo "재생성 완료: $DST"
echo ""
echo "⚠️  수동 확인 필요:"
echo "  1. Step 1 (bootstrap) 블록이 'bash scripts/graphify-bootstrap.sh' 한 줄인지 확인"
echo "  2. 잔존 command_substitution 없는지: grep -c '\$(cat' $DST"
echo "  3. 업스트림에 새 \$(...) 패턴이 추가됐으면 scripts/graphify-bootstrap.sh도 업데이트"
