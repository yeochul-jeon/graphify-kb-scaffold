#!/bin/bash
# Git hooks 활성화 스크립트
# 실행: bash scripts/setup-hooks.sh

set -e

KB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== Knowledge Base Git Hooks 설정 ==="

# git hooks 경로를 .githooks/로 지정 — 이미 다른 값이면 덮어쓰지 않고 경고만 한다
# (pre-commit/lefthook의 "cowardly refuse when core.hooksPath already set" 관례)
CURRENT_HOOKS_PATH="$(git -C "$KB_DIR" config --get core.hooksPath || true)"
HOOKS_ACTIVE=true
case "$CURRENT_HOOKS_PATH" in
  "")
    git -C "$KB_DIR" config core.hooksPath .githooks
    echo "✓ hooksPath 설정 완료 (.githooks)"
    ;;
  .githooks)
    echo "− hooksPath 이미 설정됨 (건너뜀)"
    ;;
  *)
    echo "⚠ core.hooksPath가 이미 '${CURRENT_HOOKS_PATH}'로 설정되어 있습니다. 덮어쓰지 않습니다." >&2
    echo "  수동 확인 후 필요 시: git config core.hooksPath .githooks" >&2
    HOOKS_ACTIVE=false
    ;;
esac

# 실행 권한 부여
chmod +x "$KB_DIR/.githooks/pre-commit"

if [ "$HOOKS_ACTIVE" = true ]; then
  echo "✅ Git hooks 활성화 완료"
  echo ""
  echo "설정된 훅:"
  echo "  - pre-commit: wiki/ 오염 방지 경고"
  echo ""
  echo "우회 방법 (Claude Code 커밋 시 — 사유는 의무):"
  echo "  ALLOW_WIKI_EDIT=1 ALLOW_WIKI_EDIT_REASON='<사유>' git commit -m '...'"
  echo "  사유 문구와 판별 기준: .claude/rules/wiki-concepts.md §우회 사유의 두 갈래"
  echo "  (그래프 재빌드가 자동 생성한 diff 는 별도 사유를 씁니다)"
  echo ""
  echo "비활성화 방법:"
  echo "  git config --unset core.hooksPath"
else
  echo "⚠ 기존 core.hooksPath 설정을 유지합니다 — .githooks/pre-commit(wiki/ 오염 방지 경고)이 활성화되지 않았습니다."
fi
