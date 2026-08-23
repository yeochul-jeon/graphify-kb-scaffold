#!/usr/bin/env bash
# SessionStart 훅: raw/Clippings/ 에 미처리 클립이 남아 있으면 한 줄로 알린다.
# 출력 규약 — 0건이면 아무것도 내지 않는다(침묵이 기본 상태다).
#   1건 이상이면 훅 JSON 한 줄:
#     systemMessage      → 사람 화면 (hook_system_message attachment 로 렌더)
#     additionalContext  → 모델 컨텍스트 (hook_additional_context)
#   두 채널의 경로 분리는 2026-08-22 실측으로 확인했다.
# 근거·결정: docs/plan/plans/2026-08-22-clippings-inbox-notify.md
set -euo pipefail
cd "$(dirname "$0")/.."

INBOX="raw/Clippings"
[ -d "$INBOX" ] || exit 0
git rev-parse --git-dir >/dev/null 2>&1 || exit 0

# 카운터 정의: git 미추적(untracked)만 센다.
#   `ls | wc -l` 을 쓰지 않는 이유 — `compiled: true` 인 레거시 클립 1건이
#   2026-08-22 «제자리 유지» 결정으로 인박스에 영구 거주한다. 그래서 인박스가
#   실제로 비어 있어도 1 을 준다. 레거시는 tracked, 새 클립은 항상 untracked 라
#   이 정의가 둘을 가른다.
#   ⚠ 약점: 승격 전에 클립을 커밋하면 카운트에서 사라진다.
#   -z 는 공백·개행이 든 파일명 대응이다(레거시 파일명에 실제로 공백이 있다).
git ls-files --others --exclude-standard -z -- "$INBOX" | python3 -c '
import json, os, sys

names = [os.path.basename(p.decode("utf-8", "replace"))
         for p in sys.stdin.buffer.read().split(b"\0") if p]
if not names:
    sys.exit(0)

n = len(names)
shown = names[:3]
more = " 외 {}건".format(n - len(shown)) if n > len(shown) else ""
line = "▶ Clippings 인박스 미처리 {}건 — {}{} · 승격: /ingest raw/Clippings/<파일>".format(
    n, ", ".join(shown), more)
ctx = "raw/Clippings/ 에 미처리 클립 {}건. 승격은 /ingest <경로> — 복사가 아니라 이동이다.\n".format(n)
ctx += "\n".join("- " + x for x in names)

print(json.dumps({
    "systemMessage": line,
    "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": ctx},
}, ensure_ascii=False))
'
