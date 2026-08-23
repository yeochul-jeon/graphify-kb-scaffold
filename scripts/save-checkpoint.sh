#!/usr/bin/env bash
# .work-log/last-session.md 에 세션 상태 체크포인트를 기록한다.
# Usage:
#   scripts/save-checkpoint.sh <trigger> [note]
#     trigger: pre-compact | session-end | manual
#     note   : optional free-form note
#
# PreCompact hook 에서 자동 호출되며, SessionStart 에서 이 파일을 읽어 컨텍스트를 복원한다.
set -euo pipefail

# 저장소 루트를 고정한다 (원장 #37). 없으면 `.work-log/` 와 아래 git 조회가
# **호출 시점 cwd 기준**이 되어, 하위 디렉터리에서 부르면 체크포인트가
# `<subdir>/.work-log/last-session.md` 에 생기고 SessionStart 는 루트만 읽으므로
# 낡은 체크포인트가 계속 주입된다. `wiki-dirty-flag.sh:4` 와 같은 처리다.
cd "$(dirname "$0")/.."

TRIGGER="${1:-manual}"
NOTE="${2:-}"

LOG_DIR=".work-log"
LOG_FILE="$LOG_DIR/last-session.md"

mkdir -p "$LOG_DIR"

TIMESTAMP="$(date +%Y-%m-%d\ %H:%M:%S\ %Z)"
HEAD_SHA="$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')"
BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')"

# 최근 수정 파일 상위 10개 (staged + unstaged)
CHANGED_FILES="$(git status --porcelain 2>/dev/null | head -10 || echo '  (git 상태 조회 실패)')"
if [ -z "$CHANGED_FILES" ]; then
  CHANGED_FILES="  (변경 없음)"
fi

{
  echo "# Last Session Checkpoint"
  echo ""
  echo "- **Trigger**: \`$TRIGGER\`"
  echo "- **Timestamp**: $TIMESTAMP"
  echo "- **Branch**: \`$BRANCH\`"
  echo "- **HEAD**: \`$HEAD_SHA\`"
  echo ""
  echo "## 변경 중인 파일 (git status)"
  echo ""
  echo '```'
  printf '%s\n' "$CHANGED_FILES"
  echo '```'
  if [ -n "$NOTE" ]; then
    echo ""
    echo "## Note"
    echo ""
    printf '%s\n' "$NOTE"
  fi
  echo ""
  echo "---"
  echo "> 다음 세션 시작 시 이 파일이 SessionStart hook 으로 컨텍스트에 주입된다."
} > "$LOG_FILE"

# stdout 은 PreCompact hook 이 additionalContext 로 사용하지 않도록 조용히 처리
echo "[checkpoint] saved to $LOG_FILE (trigger=$TRIGGER)" >&2
