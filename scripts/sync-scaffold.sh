#!/usr/bin/env bash
# sync-scaffold.sh — graphify-kb → graphify-kb-scaffold 단방향 템플릿 동기화
#
# 사용법:
#   scripts/sync-scaffold.sh [--apply] [--target <path>] [--force] [-v] [-h]
#
#   (기본) dry-run: 변경 없이 rsync 계획만 출력
#   --apply         실제 파일 복사/삭제 실행
#   --target <path> scaffold 경로 (없으면 $SCAFFOLD_DIR → ../graphify-kb-scaffold)
#   --force         target working tree가 dirty여도 진행
#   -v, --verbose   rsync 상세 출력
#   -h, --help      이 도움말 표시
#
# 에러 코드:
#   0  성공 (dry-run 포함)
#   2  target dirty + --force 없음
#   3  target 경로 부재 또는 git repo 아님
#   4  source 또는 rsync 실행 실패

set -euo pipefail

# ── 색상 (tty 시에만) ──────────────────────────────────────────────────────────
if [ -t 1 ]; then
  BOLD='\033[1m'; CYAN='\033[0;36m'; GREEN='\033[0;32m'
  YELLOW='\033[1;33m'; RED='\033[0;31m'; RESET='\033[0m'
else
  BOLD=''; CYAN=''; GREEN=''; YELLOW=''; RED=''; RESET=''
fi

info()    { echo -e "${CYAN}[sync]${RESET} $*"; }
ok()      { echo -e "${GREEN}[ok]${RESET}   $*"; }
warn()    { echo -e "${YELLOW}[warn]${RESET} $*"; }
die()     { echo -e "${RED}[err]${RESET}  $*" >&2; exit "${2:-1}"; }

# ── 상수 ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null \
               || die "source가 git repo가 아닙니다: $SCRIPT_DIR" 4)"

# ── allowlist ─────────────────────────────────────────────────────────────────
# [type]:[relative-path]
#   dir  → rsync -a --delete (하위 완전 미러링)
#   file → rsync -a          (단건 복사)
SYNC_ITEMS=(
  "dir:.claude/commands"
  "dir:.claude/rules"
  "dir:.claude/skills/graphify"
  "dir:docs/guide"
  "dir:raw/_templates"
  "file:.claude/settings.json"
  "file:.githooks/pre-commit"
  "file:.claudeignore"
  "file:.graphifyignore"
  "file:CLAUDE.md"
  # CLAUDE.md 는 본문 없이 `@AGENTS.md` 를 불러오기만 한다(2026-08-19 통합).
  # 둘은 반드시 같이 전파해야 한다 — CLAUDE.md 만 보내면 대상 저장소가 없는 파일을 불러온다.
  "file:AGENTS.md"
  "file:docs/architecture.md"
  "file:docs/tutorial.md"
  "file:docs/obsidian-setup.md"
  "file:scripts/kb.sh"
  "file:scripts/setup.sh"
  "file:scripts/setup-hooks.sh"
  "file:scripts/graphify-bootstrap.sh"
  "file:scripts/graphify-py.sh"
  # SKILL.md Step B3-a 가 부르는 스펙 준수 게이트. SKILL.md 가 이미 전파되므로
  # 이 스크립트가 없으면 전파된 스킬이 없는 파일을 부른다 (2026-08-23).
  "file:scripts/check-extraction-chunks.py"
  "file:scripts/sync-scaffold.sh"
  # scripts/check-mirrors.py 는 **의도적으로 넣지 않는다** (2026-08-19).
  #   그 검사는 `.agents/`·`.codex/` 아래 파일 전건이 매핑표에 청구되기를 요구하는데,
  #   scaffold 저장소에는 그 디렉터리가 없어 선언된 미러 루트 부재로 무조건 실패한다.
  #   전파하려면 「미러 자산 0건이면 통과」 분기가 필요하며 그것은 별건이다.
)

# ── 인자 파싱 ─────────────────────────────────────────────────────────────────
APPLY=false
FORCE=false
VERBOSE=false
TARGET=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply)        APPLY=true ;;
    --force)        FORCE=true ;;
    -v|--verbose)   VERBOSE=true ;;
    --target)       shift; TARGET="$1" ;;
    -h|--help)
      sed -n '2,18p' "${BASH_SOURCE[0]}" | sed 's/^# \?//'
      exit 0
      ;;
    *) die "알 수 없는 옵션: $1 (--help 참고)" ;;
  esac
  shift
done

# ── target 경로 해석 ─────────────────────────────────────────────────────────
if [[ -z "$TARGET" ]]; then
  TARGET="${SCAFFOLD_DIR:-$(cd "$SOURCE_ROOT/.." && pwd)/graphify-kb-scaffold}"
fi
TARGET="$(cd "$TARGET" 2>/dev/null && pwd || echo "$TARGET")"

# ── preflight ─────────────────────────────────────────────────────────────────
if [[ ! -d "$TARGET/.git" ]]; then
  die "target 경로가 존재하지 않거나 git repo가 아닙니다: $TARGET" 3
fi

SOURCE_SHA="$(git -C "$SOURCE_ROOT" rev-parse --short HEAD 2>/dev/null || echo "unknown")"

# source dirty 경고
if [[ -n "$(git -C "$SOURCE_ROOT" status --porcelain 2>/dev/null)" ]]; then
  warn "source에 미커밋 변경이 있습니다. WIP 상태로 동기화됩니다."
fi

# target dirty 검사
if [[ -n "$(git -C "$TARGET" status --porcelain 2>/dev/null)" ]]; then
  if [[ "$FORCE" == true ]]; then
    warn "target working tree가 dirty 상태입니다 (--force 로 진행)."
  else
    die "target working tree가 dirty 상태입니다.\n       scaffold에서 커밋 또는 stash 후 재실행하거나 --force 를 사용하세요." 2
  fi
fi

# ── rsync 실행 ────────────────────────────────────────────────────────────────
RSYNC_BASE_FLAGS="-a"
[[ "$VERBOSE" == true ]] && RSYNC_BASE_FLAGS+="v"

if [[ "$APPLY" == false ]]; then
  echo -e "\n${BOLD}── dry-run: 변경 예정 항목 ──────────────────────────────────────────────${RESET}"
  echo -e "  source  : $SOURCE_ROOT  @${SOURCE_SHA}"
  echo -e "  target  : $TARGET"
  echo ""

  CHANGED=0
  for item in "${SYNC_ITEMS[@]}"; do
    type="${item%%:*}"
    rel="${item#*:}"
    src="$SOURCE_ROOT/$rel"

    if [[ ! -e "$src" ]]; then
      warn "source 없음 (건너뜀): $rel"
      continue
    fi

    if [[ "$type" == "dir" ]]; then
      result=$(rsync -ain --delete --itemize-changes "$src/" "$TARGET/$rel/" 2>/dev/null || true)
    else
      result=$(rsync -ain --itemize-changes "$src" "$TARGET/$rel" 2>/dev/null || true)
    fi

    if [[ -n "$result" ]]; then
      echo -e "  ${CYAN}${rel}${RESET}"
      echo "$result" | sed 's/^/    /'
      CHANGED=$((CHANGED + $(echo "$result" | wc -l | tr -d ' ')))
    fi
  done

  if [[ $CHANGED -eq 0 ]]; then
    ok "변경 없음. 두 저장소가 동기화된 상태입니다."
  else
    echo ""
    info "변경 예정 라인: ${BOLD}${CHANGED}${RESET}  →  실제 적용하려면 ${BOLD}--apply${RESET} 를 추가하세요."
  fi
  exit 0
fi

# ── apply ─────────────────────────────────────────────────────────────────────
echo -e "\n${BOLD}── apply: 동기화 실행 ───────────────────────────────────────────────────${RESET}"
echo -e "  source  : $SOURCE_ROOT  @${SOURCE_SHA}"
echo -e "  target  : $TARGET"
echo ""

for item in "${SYNC_ITEMS[@]}"; do
  type="${item%%:*}"
  rel="${item#*:}"
  src="$SOURCE_ROOT/$rel"

  if [[ ! -e "$src" ]]; then
    warn "source 없음 (건너뜀): $rel"
    continue
  fi

  # target 부모 디렉토리 보장
  parent_dir="$TARGET/$(dirname "$rel")"
  mkdir -p "$parent_dir"

  if [[ "$type" == "dir" ]]; then
    mkdir -p "$TARGET/$rel"
    rsync $RSYNC_BASE_FLAGS --delete "$src/" "$TARGET/$rel/" \
      && ok "$rel/"
  else
    rsync $RSYNC_BASE_FLAGS "$src" "$TARGET/$rel" \
      && ok "$rel"
  fi
done

# ── post-report ───────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}── scaffold git status ──────────────────────────────────────────────────${RESET}"
git -C "$TARGET" status --short

echo ""
echo -e "${BOLD}── scaffold git diff --stat ─────────────────────────────────────────────${RESET}"
git -C "$TARGET" diff --stat 2>/dev/null || true
git -C "$TARGET" diff --cached --stat 2>/dev/null || true

echo ""
info "synced from graphify-kb@${SOURCE_SHA}"
echo -e "  제안 커밋 메시지: ${BOLD}chore: sync templates from graphify-kb@${SOURCE_SHA}${RESET}"
