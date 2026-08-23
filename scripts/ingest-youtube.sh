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
uvx --from youtube-transcript-api youtube_transcript_api "$VIDEO_ID" --languages ko en --format text
