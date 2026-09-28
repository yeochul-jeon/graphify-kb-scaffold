#!/usr/bin/env bash
# YouTube 자막 수집 래퍼. uvx로 youtube-transcript-api를 격리 실행(설치 불필요).
# 패키지명(하이픈)과 실행 파일명(언더스코어)이 달라 --from 지정이 필수 —
# 이 불일치를 스킬 프롬프트에 매번 반복 기술하지 않기 위해 스크립트로 고정한다.
set -euo pipefail

INPUT="${1:?Usage: ingest-youtube.sh <video_id | watch_url | youtu.be_url | shorts_url>}"

case "$INPUT" in
  *youtube.com/watch*v=*)
    VIDEO_ID=$(echo "$INPUT" | sed -n 's/.*[?&]v=\([a-zA-Z0-9_-]\{11\}\).*/\1/p') ;;
  *youtu.be/*)
    VIDEO_ID=$(echo "$INPUT" | sed -n 's#.*youtu\.be/\([a-zA-Z0-9_-]\{11\}\).*#\1#p') ;;
  */shorts/*)
    VIDEO_ID=$(echo "$INPUT" | sed -n 's#.*/shorts/\([a-zA-Z0-9_-]\{11\}\).*#\1#p') ;;
  http://*|https://*)
    # 인식 못하는 YouTube URL 형태(/live/, /embed/ 등) — 전체 URL을 video_id로 오인하지 않도록 명시적으로 추출 실패 처리
    VIDEO_ID="" ;;
  *)
    VIDEO_ID="$INPUT" ;;  # URL이 아니면 video_id를 직접 입력한 것으로 간주
esac

if [ -z "$VIDEO_ID" ]; then
  echo "ERROR: video_id 추출 실패: $INPUT" >&2
  exit 1
fi

echo "video_id=${VIDEO_ID}" >&2
# 원어 우선: AI 더빙 트랙이 있는 영상은 더빙 음성마다 생성 자막이 생겨 `ko en` 만으로는 더빙 ASR 을 고른다.
# 원어 조회 실패 시 orig_lang=unknown 을 알리고 종전 순서로 진행한다 (/ingest 가 note 에 「원어 미확인」 기록).
ORIG=$(uvx --from yt-dlp yt-dlp --skip-download --no-warnings --print language "https://www.youtube.com/watch?v=${VIDEO_ID}" 2>/dev/null) || ORIG=""
[ "$ORIG" = "NA" ] && ORIG=""
echo "orig_lang=${ORIG:-unknown}" >&2
# youtube_transcript_api CLI 는 자막을 못 받아도 exit 0 으로 에러문을 stdout 에 쓴다 — /ingest 의 실패 분기가 돌도록 여기서 exit 1 로 바꾼다.
# 에러 문구 판별이 패키지 업데이트로 조용히 빗나가지 않도록 버전을 고정한다 (올릴 때 실패 문구를 다시 확인).
OUT=$(uvx --from youtube-transcript-api==1.2.4 youtube_transcript_api "$VIDEO_ID" \
  --languages ${ORIG:+"$ORIG" "${ORIG%%-*}"} ko en --format text)
if ! [[ "$OUT" =~ [^[:space:]] ]] || [[ "$OUT" =~ ^[[:space:]]*Could\ not\ retrieve\ a\ transcript ]]; then
  printf '%s\n' "$OUT" >&2
  exit 1
fi
printf '%s\n' "$OUT"
