#!/usr/bin/env python3
"""출처가 움직였는가 — `raw/` 인제스트 시점 대비 업스트림 변경 신호.

원장 #45·#46(ⓞ-3). 90일 경과일수는 **일정 구동** 신호라 기록형 문서를 영원히
"미조치" 로 세고, 최신성형 문서는 출처가 실제로 바뀌었는지와 무관하게 센다.
이 스크립트는 그것을 **이벤트 구동** 신호로 바꾼다 — *경과일수*가 아니라
*출처가 움직였는가*를 묻는다.

**스키마 변경이 0이다.** 재료가 이미 있다:
  - `raw/*.md` frontmatter 의 `source_url` · `github_repo` · `github_ref` · `ingested_date`
  - `wiki/**/*.md` frontmatter 의 `sources: [raw/x.md, ...]`
`raw/okf-spec-v02.md` 의 `note:` 가 "업스트림 커밋 0건" 을 **수기로** 적고 있었다 —
관행이 먼저 있었고 검사가 없었을 뿐이다.

⚠️ **`graphify-build.sh` 에 물리지 않는다.** 그쪽은 `set -euo pipefail` 이라
네트워크가 없으면 빌드 전체가 죽는다(#43 이 조치안 ⓐ 를 배제한 것과 같은 판단).
이 스크립트는 **명시적 실행 전용**이며, 네트워크 실패는 결함이 아니라 `unknown` 이다.

사용:
  scripts/graphify-py.sh scripts/check-source-drift.py            # 조회 포함
  scripts/graphify-py.sh scripts/check-source-drift.py --no-net   # 재고만 (오프라인)
  scripts/graphify-py.sh scripts/check-source-drift.py --wiki     # 영향받는 wiki 페이지까지

종료 코드: 항상 0. **판정이 아니라 신호다** — 드리프트가 곧 결함은 아니다
(`github_ref_note` 가 명시하듯 고정 SHA 는 의도된 것이고, 최신본으로 덮어쓰면
그 판을 근거로 컴파일된 본문의 근거가 어긋난다).
"""
import os, re, sys, glob, json, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "raw")
WIKI = os.path.join(ROOT, "wiki")

FM = re.compile(r"\A---\n(.*?)\n---", re.S)
# 스칼라 한 줄만 본다. 대상 필드가 전부 단일 값이거나 인라인 리스트다.
SCALAR = re.compile(r"^(\w+):[ \t]*(.*?)[ \t]*$", re.M)


def frontmatter(path):
    """frontmatter 를 평면 dict 로. yaml 모듈이 없는 환경이라 줄 단위로 읽는다.

    블록 리스트(`sources:` 다음 줄부터 `- x`)도 잡는다 — 인라인만 파싱하면
    블록 표기 파일이 "출처 없음" 으로 오판된다(`attach-claim-metadata.py` 가
    실제로 그렇게 여러 회차 오보했다).
    """
    with open(path, encoding="utf-8") as f:
        m = FM.match(f.read())
    if not m:
        return {}
    body = m.group(1)
    # 값을 감싼 따옴표를 벗긴다. `github_repo: "https://…"` 표기가 실제로 있고,
    # 벗기지 않으면 `git ls-remote` 가 URL 을 통째로 못 읽어 조용히 unknown 이 된다.
    out = {k: v[1:-1] if len(v) > 1 and v[0] == v[-1] and v[0] in "\"'" else v
           for k, v in SCALAR.findall(body)}
    for key in ("sources", "github_files"):
        if out.get(key, "").startswith("["):
            continue
        block = re.search(rf"^{key}:[ \t]*\n((?:[ \t]*-[ \t]*.*\n?)+)", body, re.M)
        if block:
            out[key] = "[" + ", ".join(
                l.strip().lstrip("-").strip() for l in block.group(1).splitlines() if l.strip()
            ) + "]"
    return out


def listval(raw):
    if not raw or not raw.startswith("["):
        return []
    return [x.strip().strip("'\"") for x in raw[1:-1].split(",") if x.strip()]


def remote_head(repo_url, timeout=15):
    """업스트림 기본 브랜치 HEAD SHA. 실패는 None — 결함이 아니라 unknown 이다."""
    try:
        r = subprocess.run(["git", "ls-remote", repo_url, "HEAD"],
                           capture_output=True, text=True, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError):
        return None
    if r.returncode != 0 or not r.stdout.strip():
        return None
    return r.stdout.split()[0]


def ahead_by(repo_url, base, head, timeout=20):
    """base..head 커밋 수. `gh` 가 없거나 실패하면 None (best-effort)."""
    m = re.search(r"github\.com/([^/]+)/([^/.]+)", repo_url or "")
    if not m or not base or not head:
        return None
    try:
        r = subprocess.run(
            ["gh", "api", f"repos/{m.group(1)}/{m.group(2)}/compare/{base}...{head}",
             "--jq", ".ahead_by"],
            capture_output=True, text=True, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError):
        return None
    if r.returncode != 0:
        return None
    try:
        return int(r.stdout.strip())
    except ValueError:
        return None


def wiki_consumers():
    """raw 상대경로 -> 그것을 `sources` 로 삼는 wiki 파일 목록."""
    out = {}
    for p in sorted(glob.glob(os.path.join(WIKI, "concepts", "*.md")) +
                    glob.glob(os.path.join(WIKI, "topics", "*.md"))):
        for s in listval(frontmatter(p).get("sources", "")):
            if s.startswith("raw/"):
                out.setdefault(s, []).append(os.path.relpath(p, ROOT))
    return out


def main():
    argv = sys.argv[1:]
    no_net = "--no-net" in argv
    show_wiki = "--wiki" in argv

    consumers = wiki_consumers() if show_wiki else {}

    total = with_url = trackable = 0
    rows = []
    for p in sorted(glob.glob(os.path.join(RAW, "**", "*.md"), recursive=True)):
        fm = frontmatter(p)
        if not fm:
            continue
        total += 1
        url = fm.get("source_url", "")
        if url:
            with_url += 1
        repo = fm.get("github_repo", "")
        if not repo:
            continue
        trackable += 1
        rel = os.path.relpath(p, ROOT)
        pin = fm.get("github_ref", "")
        # 브랜치명은 핀이 아니다. `github_ref: main` 이 실제로 있고, 그대로 두면
        # HEAD 와 영원히 불일치해 **항상 moved** 로 잡히는 고정 오탐이 된다.
        if pin and not re.fullmatch(r"[0-9a-f]{7,40}", pin):
            pin = ""
        head = None if no_net else remote_head(repo)
        if head is None:
            state = "skipped" if no_net else "unknown"
            delta = None
        elif not pin:
            state = "unpinned"      # 기준선이 없어 델타를 못 센다
            delta = None
        elif head.startswith(pin) or pin.startswith(head):
            state = "current"
            delta = 0
        else:
            state = "moved"
            delta = ahead_by(repo, pin, head)
        rows.append((rel, repo, pin, head, state, delta, fm.get("ingested_date", "")))

    print(f"raw/ {total}건 · source_url {with_url}건 · github_repo {trackable}건"
          f"{' | --no-net (조회 생략)' if no_net else ''}")
    print()
    order = {"moved": 0, "unpinned": 1, "unknown": 2, "current": 3, "skipped": 4}
    for rel, repo, pin, head, state, delta, ing in sorted(rows, key=lambda r: (order[r[4]], r[0])):
        mark = {"moved": "🔴", "unpinned": "🟡", "unknown": "⚪️",
                "current": "✅", "skipped": "·"}[state]
        d = f" · +{delta}커밋" if delta else ""
        print(f"{mark} {state:9} {rel}{d}")
        print(f"     {repo}  pin={pin[:12] or '—'}  head={(head or '—')[:12]}  ingested={ing or '—'}")
        for w in consumers.get(rel, []):
            print(f"     └ {w}")

    moved = sum(1 for r in rows if r[4] == "moved")
    if not no_net:
        print()
        print(f"출처가 움직인 것: {moved}건 / 추적 가능 {trackable}건")
        print("⚠️ 드리프트는 신호이지 판정이 아니다 — `github_ref_note` 가 명시하듯 "
              "고정 SHA 는 의도된 것이며, 최신본으로 덮어쓰면 그 판을 근거로 컴파일된 본문의 근거가 어긋난다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
