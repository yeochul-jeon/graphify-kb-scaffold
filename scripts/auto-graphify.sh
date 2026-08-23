#!/usr/bin/env bash
# Stop 훅: .work-log/.wiki-dirty 존재 시 그래프 자동 재빌드 (동기, 타임아웃 90초)
set -euo pipefail
cd "$(dirname "$0")/.."
DIRTY_FLAG=".work-log/.wiki-dirty"
FAIL_COUNT=".work-log/.graphify-fail-count"
MAX_FAILS=3
COOLDOWN=1800   # 초. MAX_FAILS 도달 후 재시도 간격
[ -f "$DIRTY_FLAG" ] || exit 0

# 연속 실패가 쌓이면 재시도를 늦춘다 — 매 Stop 마다 90초를 태우지 않기 위해서다.
# ⚠ 두 가지를 지킨다:
#   ① 멈추는 것은 "시도" 뿐이고 DIRTY_FLAG 는 남긴다. 지우면 상태 소실로 되돌아간다
#   ② 영구 정지가 아니라 쿨다운이다. 영구 래치는 사람이 손대야만 풀리는데,
#      그 안내 메시지가 훅의 2>/dev/null 로 사라지면 자동 재빌드가 조용히 죽는다
fails=$(cat "$FAIL_COUNT" 2>/dev/null || echo 0)
case "$fails" in ''|*[!0-9]*) fails=0 ;; esac
if [ "$fails" -ge "$MAX_FAILS" ]; then
  last=$(stat -f %m "$FAIL_COUNT" 2>/dev/null || stat -c %Y "$FAIL_COUNT" 2>/dev/null || echo 0)
  waited=$(( $(date +%s) - last ))
  if [ "$waited" -lt "$COOLDOWN" ]; then
    echo "⚠ graphify rebuild ${fails}회 연속 실패 — $(( (COOLDOWN - waited) / 60 ))분 후 재시도 (재빌드 필요 상태는 유지)" >&2
    echo "  즉시 진단: bash scripts/graphify-build.sh" >&2
    exit 0
  fi
fi

# timeout(GNU coreutils)이 없는 macOS 기본 환경 대응 — gtimeout(brew coreutils) 폴백,
# 둘 다 없으면 시간 제한 없이 실행하되 저하된 상태임을 stderr에 남긴다(침묵 금지).
if command -v timeout >/dev/null 2>&1; then
  TIMEOUT_CMD="timeout 90"
elif command -v gtimeout >/dev/null 2>&1; then
  TIMEOUT_CMD="gtimeout 90"
else
  TIMEOUT_CMD=""
  echo "⚠ timeout/gtimeout 명령 없음 — 90초 시간 제한 없이 실행 (brew install coreutils 권장)" >&2
fi

echo "▶ wiki 변경 감지 — 그래프 자동 재빌드 시작" >&2
if $TIMEOUT_CMD bash scripts/graphify-build.sh; then
  rm -f "$DIRTY_FLAG" "$FAIL_COUNT"   # 성공했을 때만 상태를 내린다
else
  rc=$?
  if [ "$rc" -eq 124 ]; then why="90초 타임아웃"; else why="빌드 실패(rc=$rc)"; fi
  # flag 를 유지해 다음 트리거에 재시도되게 한다. 삭제를 선행하면 실패가 영구화된다
  echo $((fails + 1)) > "$FAIL_COUNT"
  if [ $((fails + 1)) -ge "$MAX_FAILS" ]; then
    next="$((COOLDOWN / 60))분 후 재시도"
  else
    next="다음 트리거에 재시도"
  fi
  echo "⚠ graphify rebuild $why — 연속 $((fails + 1))회, $next" >&2
  # ⚠ 1 이지 2 가 아니다. Stop 훅에서 2 는 blocking — 정지를 막고 stderr 를 에이전트에
  #   되먹여 대화를 계속시키므로 재빌드 실패가 정지 루프가 된다. 1(그 외 비-2)은
  #   non-blocking error 라 정지는 진행되고 트랜스크립트에만 실패가 표시된다.
  #   출처: https://code.claude.com/docs/en/hooks
  # 이 줄이 없으면 마지막 명령이 echo(rc 0)라 실패가 rc 0 으로 새어나간다 — 훅에서
  # `|| true` 를 떼도 소용없는 이유가 이것이었다(fail-open 이 훅이 아니라 여기 있었다).
  exit 1
fi
