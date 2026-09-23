#!/usr/bin/env bash
# UserPromptSubmit 훅: 매 턴 시작 시 현재 KST 시각을 additionalContext로 주입한다.
# 목적: output 파일명(YYYYMMDD-HHmm)·frontmatter 날짜를 채우려고 매번
# Bash(TZ=Asia/Seoul date ...)를 호출하던 왕복을 없앤다 — 값은 여기서 한 번만 계산한다.
set -euo pipefail
cd "$(dirname "$0")/.."

python3 -c "
import json
from datetime import datetime, timezone, timedelta
kst = timezone(timedelta(hours=9))
now = datetime.now(kst)
msg = (
    f'현재 시각(KST): {now:%Y-%m-%d %H:%M} '
    f'— 파일명 등에 쓸 형식: YYYYMMDD-HHmm={now:%Y%m%d-%H%M}, YYYY-MM-DD={now:%Y-%m-%d}. '
    'date 커맨드를 다시 호출하지 말고 이 값을 쓸 것.'
)
print(json.dumps({'hookSpecificOutput': {'hookEventName': 'UserPromptSubmit', 'additionalContext': msg}}, ensure_ascii=False))
"
