#!/usr/bin/env bash
# scripts/setup.sh — 첫 clone 온보딩: 의존성 점검 + git hooks 활성화 + graphify 설치
#
# 사용법: bash scripts/setup.sh
#
# 하는 일 (순서):
#   0. 저장소 루트 해석
#   1. 필수 의존성 점검 (git) — 없으면 즉시 종료
#   2. 권장/선택 의존성 점검 (python3>=3.10, claude CLI, uv/pipx/pip, uv(uvx), curl)
#      — 없으면 경고만 (graphify는 uv/pipx가 별도 관리하는 인터프리터로 실행되는
#        경우가 많아, 시스템 python3 버전만으로 실패를 단정할 수 없다)
#   3. scripts/setup-hooks.sh 호출 (git hooks 활성화)
#   4. scripts/graphify-bootstrap.sh 호출 (graphify 설치 + 인터프리터 경로 기록)
#   5. graphify 설치 결과 독립 재검증
#   6. 요약 체크리스트 출력
#
# 기존 두 스크립트(graphify-bootstrap.sh, setup-hooks.sh)의 내부 설치/설정
# 로직은 그대로 호출만 한다 — 재구현하지 않는다.
#
# 종료 코드:
#   0  성공 (선택 단계 경고 포함 가능)
#   2  필수 의존성 누락 (git)
#   3  git 저장소가 아님
set -euo pipefail

# ── 색상 (tty 시에만) ────────────────────────────────────────────────────────
if [ -t 2 ]; then
  CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; RESET='\033[0m'
else
  CYAN=''; GREEN=''; YELLOW=''; RED=''; RESET=''
fi

info() { echo -e "${CYAN}▶${RESET} $*" >&2; }
ok()   { echo -e "${GREEN}✓${RESET} $*" >&2; }
warn() { echo -e "${YELLOW}⚠${RESET} $*" >&2; }
die()  { echo -e "${RED}ERROR:${RESET} $*" >&2; exit "${2:-1}"; }

SUMMARY=()

# ── 0. 저장소 루트 해석 ───────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
[ -n "$ROOT" ] || die "git 저장소가 아닙니다: $SCRIPT_DIR" 3
cd "$ROOT"

info "graphify-kb 온보딩 시작 ($ROOT)"

# ── 1. 필수 의존성 점검 ───────────────────────────────────────────────────────
if command -v git >/dev/null 2>&1; then
  GIT_VERSION="$(git --version | awk '{print $3}')"
  ok "git 확인됨 ($GIT_VERSION)"
  SUMMARY+=("✓ git 확인됨 ($GIT_VERSION)")
else
  die "git이 필요합니다. https://git-scm.com/downloads 참고." 2
fi

if command -v python3 >/dev/null 2>&1; then
  PY_VERSION="$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')"
  if python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
    ok "python3 확인됨 ($PY_VERSION, >=3.10 충족)"
    SUMMARY+=("✓ python3 확인됨 ($PY_VERSION, >=3.10 충족)")
  else
    # 시스템 기본 python3가 낮아도, graphify는 대개 uv/pipx가 별도로 관리하는
    # 인터프리터(그래피파이 바이너리의 shebang)로 실행되므로 여기서 즉시
    # 실패시키지 않는다 — 실제 성공 여부는 5단계에서 `graphify` 커맨드로
    # 독립 재검증한다.
    warn "시스템 python3가 낮습니다 ($PY_VERSION < 3.10) — uv/pipx가 없으면 graphify 설치가 실패할 수 있습니다"
    SUMMARY+=("⚠ 시스템 python3 낮음 ($PY_VERSION < 3.10, brew install python 권장)")
  fi
else
  warn "python3 없음 — uv/pipx가 없으면 graphify 설치가 실패할 수 있습니다"
  SUMMARY+=("⚠ python3 없음 (brew install python 권장)")
fi

# ── 2. 권장/선택 의존성 점검 (없어도 계속 진행) ────────────────────────────────
if command -v claude >/dev/null 2>&1; then
  ok "claude CLI 확인됨"
  SUMMARY+=("✓ claude CLI 확인됨")
else
  warn "claude CLI 없음 — https://docs.anthropic.com/ko/docs/claude-code 참고 후 이 폴더에서 claude 실행하세요"
  SUMMARY+=("⚠ claude CLI 없음 — Claude Code 설치 필요")
fi

if command -v uv >/dev/null 2>&1 || command -v pipx >/dev/null 2>&1 \
    || command -v pip >/dev/null 2>&1 || command -v pip3 >/dev/null 2>&1; then
  ok "graphify 설치 경로(uv/pipx/pip) 확인됨"
  SUMMARY+=("✓ graphify 설치 경로(uv/pipx/pip) 확인됨")
else
  warn "uv/pipx/pip 모두 없음 — graphify 설치가 실패할 수 있습니다"
  SUMMARY+=("⚠ uv/pipx/pip 모두 없음 — graphify 설치 실패 가능")
fi

if command -v uv >/dev/null 2>&1; then
  SUMMARY+=("✓ uv(uvx) 확인됨")
else
  warn "uv(uvx) 없음 — scripts/ingest-youtube.sh(유튜브 자막 수집) 사용 불가"
  SUMMARY+=("⚠ uv(uvx) 없음 — 유튜브 자막 수집(ingest-youtube.sh) 사용 불가")
fi

if command -v curl >/dev/null 2>&1; then
  SUMMARY+=("✓ curl 확인됨")
else
  warn "curl 없음 — scripts/ingest-fetch.sh(URL 수집) 사용 불가"
  SUMMARY+=("⚠ curl 없음 — URL 수집(ingest-fetch.sh) 사용 불가")
fi

if command -v timeout >/dev/null 2>&1 || command -v gtimeout >/dev/null 2>&1; then
  SUMMARY+=("✓ timeout/gtimeout 확인됨")
else
  warn "timeout/gtimeout 없음 — graphify 자동 재빌드가 시간 제한 없이 실행됩니다 (brew install coreutils 권장)"
  SUMMARY+=("⚠ timeout/gtimeout 없음 (brew install coreutils 권장) — 자동 재빌드 90초 제한 무효화")
fi

# ── 3. git hooks 활성화 ───────────────────────────────────────────────────────
info "git hooks 설정 중..."
bash "$ROOT/scripts/setup-hooks.sh"

# setup-hooks.sh는 충돌 시 경고만 하고 계속하므로, 종료 코드가 아니라
# 실제 git config 값을 직접 재확인해 요약 줄을 판정한다.
FINAL_HOOKS_PATH="$(git -C "$ROOT" config --get core.hooksPath || true)"
if [ "$FINAL_HOOKS_PATH" = ".githooks" ]; then
  SUMMARY+=("✓ git hooks 활성화 (core.hooksPath=.githooks)")
else
  SUMMARY+=("⚠ git hooks 비활성 (core.hooksPath=${FINAL_HOOKS_PATH:-미설정})")
fi

# ── 4. graphify 설치 ──────────────────────────────────────────────────────────
info "graphify 설치 확인 중..."
bash "$ROOT/scripts/graphify-bootstrap.sh" "$ROOT"

# ── 5. graphify 설치 결과 독립 재검증 ─────────────────────────────────────────
# graphify-bootstrap.sh의 pip 폴백 파이프라인은 마지막 명령이 tail이라
# pip 실패와 무관하게 exit 0을 반환할 수 있다 — 그 종료 코드를 신뢰하지 않고
# 직접 확인한다.
if command -v graphify >/dev/null 2>&1; then
  ok "graphify 사용 가능"
  SUMMARY+=("✓ graphify 사용 가능")
else
  warn "graphify 설치 확인 실패 — 다음 /graphify 실행 시 스킬이 재시도합니다"
  SUMMARY+=("⚠ graphify 설치 확인 실패 (다음 /graphify 실행 시 재시도됨)")
fi

# ── 6. 요약 ───────────────────────────────────────────────────────────────────
echo "" >&2
echo "── setup 완료 ──────────────────────────" >&2
for line in "${SUMMARY[@]}"; do
  echo "$line" >&2
done
echo "" >&2
echo "다음 단계: 이 폴더에서 \`claude\` 실행 후 \`/graphify .\` 로 지식그래프 생성" >&2

exit 0
