#!/usr/bin/env python3
"""PostToolUse(Bash) 훅 — `git push` 가 끝나면 실제로 올라간 커밋 목록을 컨텍스트에 넣는다.

push 보고의 커밋 목록은 이 출력에서만 옮긴다 (2026-11-06 없는 커밋 3개를 해시까지 지어낸 사례).
커밋·push 를 하지 않는다 — 읽기 전용 조회만 한다.

동작: push 출력의 `<old>..<new>  <src> -> <dst>` 줄마다 `git log --oneline <old>..<new>` 를 돌려 붙인다.
범위 줄이 없으면(새 브랜치·Everything up-to-date) push 출력 원문 꼬리를 그대로 붙인다.
"""
import json
import os
import re
import subprocess
import sys

RANGE = re.compile(r"^\s*[+ ]?\s*([0-9a-f]{7,40})\.\.\.?([0-9a-f]{7,40})\s+(\S+)\s+->\s+(\S+)", re.M)
# `git add scripts/push-log-hook.py` 처럼 인자 속 push 는 제외한다 (2026-11-08 잘못된 cd 선택).
PUSH_CMD = re.compile(r"""\bgit\s+(?:-C\s+(["']?)[^\s"']+\1\s+)?push\b""")
PUSH_OUT = re.compile(r"^To \S+|Everything up-to-date", re.M)
REPO_DIR = re.compile(r"""(?:\bcd\s+|\bgit\s+-C\s+)(["']?)([^\s;&|"']+)\1""")


def repo_dir(command: str, cwd: str | None) -> str | None:
    """push 를 실행한 저장소. 명령 안의 `cd X &&`·`git -C X` 는 끝나면 셸 cwd 에 남지 않으므로
    (2026-11-08 scaffold push 에서 조회 exit 128) push 앞의 마지막 경로를 cwd 기준으로 푼다."""
    head = command[: PUSH_CMD.search(command).end()]
    found = REPO_DIR.findall(head)
    if not found:
        return cwd
    path = os.path.expanduser(found[-1][1])
    return path if os.path.isabs(path) else os.path.join(cwd or os.getcwd(), path)


def response_text(resp) -> str:
    if isinstance(resp, dict):
        return "\n".join(str(resp.get(k) or "") for k in ("stdout", "stderr"))
    return str(resp or "")


def build_context(command: str, output: str, cwd: str | None) -> str | None:
    # 명령 문자열만 보면 printf·echo 안의 "git push" 에도 걸린다(2026-11-08 오탐 1건).
    # 성공한 push 는 stderr 에 `To <remote>` 줄이나 `Everything up-to-date` 를 남긴다.
    if not PUSH_CMD.search(command) or not PUSH_OUT.search(output):
        return None
    lines = ["[push-log-hook] push 보고의 커밋 목록은 아래 git 출력에서만 옮긴다."]
    ranges = RANGE.findall(output)
    repo = repo_dir(command, cwd)
    for old, new, src, dst in ranges:
        lines.append(f"$ git log --oneline {old}..{new}   # {src} -> {dst}  (in {repo})")
        try:
            r = subprocess.run(
                ["git", "log", "--oneline", f"{old}..{new}"],
                cwd=repo, capture_output=True, text=True,
            )
        except OSError as e:  # 명령에서 푼 경로가 없을 때 — 조용히 넘기지 않고 출력에 남긴다
            lines.append(f"(조회 실패) {e}")
            continue
        lines.append(r.stdout.rstrip() if r.returncode == 0 else f"(조회 실패 exit {r.returncode}) {r.stderr.strip()}")
    if not ranges:
        tail = "\n".join(output.strip().splitlines()[-6:])
        lines.append("범위 줄(<old>..<new>) 없음 — push 출력 꼬리:")
        lines.append(tail or "(출력 없음)")
    return "\n".join(lines)


def main() -> int:
    data = json.load(sys.stdin)
    command = (data.get("tool_input") or {}).get("command", "")
    ctx = build_context(command, response_text(data.get("tool_response")), data.get("cwd"))
    if ctx:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": ctx}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
