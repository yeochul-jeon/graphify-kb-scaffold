#!/usr/bin/env bash
# 범용 URL 콘텐츠 수집 래퍼 (Jina Reader 1차 → raw HTML 폴백).
# WebFetch는 (1) SPA/JS 렌더 페이지에서 빈 셸만 반환하고 (2) 결과를 소형 모델로
# 요약해버려 아카이브용 원문 보존이 불가 — 이 스크립트가 두 문제를 모두 해결한다.
set -euo pipefail

URL="${1:?Usage: ingest-fetch.sh <URL>}"
MIN_LEN=200  # 빈 응답만 걸러내는 최소 안전선 (Jina 성공=text/plain·오류=422+application/json이 이미 상태코드로 구분됨 — 길이로 짧은 정상 글을 오탐하지 않도록 낮게 유지)

TMP=$(mktemp)
trap 'rm -f "$TMP"' EXIT

UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

# --- Tier 1: Jina AI Reader (헤드리스 렌더링 + Markdown 변환, SPA/JS 대응, API 키 불필요) ---
# 성공은 text/plain, 오류는 422+application/json으로 이미 명확히 구분되므로 길이는 빈 응답 방지용 보조 체크만.
CODE=$(curl -sL --max-time 30 -o "$TMP" -w '%{http_code}' "https://r.jina.ai/${URL}" 2>/dev/null || echo "000")
LEN=$(wc -c < "$TMP" | tr -d ' ')

if [ "$CODE" = "200" ] && [ "$LEN" -ge "$MIN_LEN" ]; then
  echo "tier=1 (jina-reader) http=${CODE} len=${LEN}" >&2
  cat "$TMP"
  exit 0
fi
echo "tier1 실패 (http=${CODE} len=${LEN}) — tier2(raw HTML)로 폴백" >&2

# --- Tier 2: 직접 curl + 브라우저 UA (raw HTML — 호출자가 마크다운 변환 책임) ---
# Content-Type이 text/* 계열이 아니면(PDF·이미지 등 바이너리) 실패 처리 — 바이너리가 "성공"으로 오인되는 것을 방지.
RESPONSE=$(curl -sL --max-time 30 -A "$UA" -o "$TMP" -w '%{http_code} %{content_type}' "$URL" 2>/dev/null || echo "000 ")
CODE=$(echo "$RESPONSE" | awk '{print $1}')
CTYPE=$(echo "$RESPONSE" | cut -d' ' -f2-)
LEN=$(wc -c < "$TMP" | tr -d ' ')

if [ "$CODE" = "200" ] && [ "$LEN" -ge "$MIN_LEN" ] && echo "$CTYPE" | grep -qiE '^(text/|application/xhtml)'; then
  echo "tier=2 (raw-html, HTML→마크다운 변환은 호출자 책임) http=${CODE} content-type=${CTYPE} len=${LEN}" >&2
  cat "$TMP"
  exit 0
fi
echo "tier2 실패 (http=${CODE} content-type=${CTYPE} len=${LEN})" >&2

echo "ERROR: 두 티어 모두 실패 (tier1/tier2 http 코드 확인) — WebFetch 폴백 또는 사용자 직접 붙여넣기 요청" >&2
exit 1
