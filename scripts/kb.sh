#!/bin/bash
# Knowledge Base CLI wrapper
# 사용법: ./scripts/kb.sh [ingest|compile|ask|lint|status] [args...]

set -e

KB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TODAY=$(date +%Y%m%d)

# 통계 출력
show_status() {
  echo "=== Knowledge Base 현황 ==="
  local raw_total raw_uncompiled wiki_concepts wiki_topics outputs
  raw_total=$(find "$KB_DIR/raw" -name "*.md" -not -path "*/\_templates/*" 2>/dev/null | wc -l | tr -d ' ')
  raw_uncompiled=$(grep -rl "compiled: false" "$KB_DIR/raw" 2>/dev/null | wc -l | tr -d ' ')
  wiki_concepts=$(find "$KB_DIR/wiki/concepts" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
  wiki_topics=$(find "$KB_DIR/wiki/topics" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')
  outputs=$(find "$KB_DIR/output" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')

  echo "raw/ 파일:      $raw_total 개 (미컴파일: $raw_uncompiled 개)"
  echo "wiki 개념:      $wiki_concepts 개"
  echo "wiki 주제:      $wiki_topics 개"
  echo "output 파일:    $outputs 개"
  echo ""
  echo "오늘 작업 로그: .work-log/dev/DEV_LOG_${TODAY}.md"
  echo "전체 타임라인: log.md"
}

case "$1" in
  ingest)
    echo "→ /ingest 실행: ${*:2}"
    claude "/ingest ${*:2}"
    ;;
  compile)
    echo "→ /compile 실행: ${*:2}"
    claude "/compile ${*:2}"
    ;;
  ask)
    echo "→ /ask 실행: ${*:2}"
    claude "/ask ${*:2}"
    ;;
  lint)
    echo "→ /lint 실행: ${*:2}"
    claude "/lint ${*:2}"
    ;;
  status)
    show_status
    ;;
  *)
    echo "사용법: $0 [ingest|compile|ask|lint|status] [args...]"
    echo ""
    echo "  ingest [URL|Notion URL]   원본 자료 수집 → raw/"
    echo "  compile [파일명]          raw/ → wiki/ 컴파일"
    echo "  ask [질문] [--slides]     wiki 기반 질의응답"
    echo "  lint [--fix]              wiki 품질 점검"
    echo "  status                    현황 통계"
    exit 1
    ;;
esac
