#!/bin/bash
# Git hooks 활성화 스크립트
# 실행: bash scripts/setup-hooks.sh

set -e

KB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== Knowledge Base Git Hooks 설정 ==="

# git hooks 경로를 .githooks/로 지정
git -C "$KB_DIR" config core.hooksPath .githooks

# 실행 권한 부여
chmod +x "$KB_DIR/.githooks/pre-commit"

echo "✅ Git hooks 활성화 완료"
echo ""
echo "설정된 훅:"
echo "  - pre-commit: wiki/ 오염 방지 경고"
echo ""
echo "우회 방법 (Claude Code 커밋 시):"
echo "  ALLOW_WIKI_EDIT=1 git commit -m '...'"
echo ""
echo "비활성화 방법:"
echo "  git config --unset core.hooksPath"
