#!/usr/bin/env bash
# PostToolUse(Write|Edit) 훅: wiki/concepts/ 또는 wiki/topics/ 변경 감지 → dirty flag 설정
# stdin: {"tool_name":"Write","tool_input":{"file_path":"..."},...}
cd "$(dirname "$0")/.."
INPUT=$(cat)
FILE_PATH=$(python3 -c "
import json, sys
d = json.loads(sys.stdin.read())
print(d.get('tool_input', {}).get('file_path', ''))
" <<< "$INPUT" 2>/dev/null || echo "")
if echo "$FILE_PATH" | grep -qE "wiki/(concepts|topics)/"; then
    mkdir -p .work-log
    touch .work-log/.wiki-dirty
fi
