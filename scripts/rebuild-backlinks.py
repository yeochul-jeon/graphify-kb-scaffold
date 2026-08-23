#!/usr/bin/env python3
"""wiki/backlinks.md 결정론적 재생성 (strict-inbound 역인덱싱).

backlinks.md 는 source 파일의 명시적 [[link]] 를 역인덱싱한 파생 산출물이다.
LLM/임베딩 불필요 — 순수 기계적 재계산이므로 매 인제스트 후 안전하게 재실행 가능.

정책 (A′):
- inbound[target] = target 을 [[link]] 로 참조하는 concept/topic source 집합 (raw/·output/·self·플레이스홀더 제외)
- 주석 이월: 기존 backlinks.md 의 (target←source) 주석을 그대로 보존 (큐레이션 보호)
- 신규 엔트리: source 의 '## 관련 개념' 라인 주석을 "(... 으로 참조)" 로 보강, 없으면 bare 링크
- STALE(역전·소멸) 엔트리: 자동 제외 (실제 [[link]] 없으면 등재 안 함)
- 멱등: target/source 정렬 고정 → 재실행 시 diff 0

⚠️ 주석 freeze 비대칭 (의도된 트레이드오프):
  precedence 가 carry > src_ann 이므로, 한 번 backlinks.md 에 기록된 주석은 이후
  재생성 시 verbatim 보존된다. **링크 구조(추가/삭제)는 항상 source 기준으로 갱신되나,
  기존 엔트리의 주석 텍스트는 source '관련 개념' 을 나중에 고쳐도 전파되지 않는다.**
  (신규 링크는 src_ann 으로 주석이 붙고, 기존 큐레이션은 보존된다.)
  주석 텍스트까지 source 와 동기화하려면 precedence 를 src_ann > carry 로 뒤집을 것
  (단 기존 target-perspective 큐레이션 주석 손실).

사용: scripts/graphify-py.sh scripts/rebuild-backlinks.py
"""
import os, re, glob, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wiki_scan

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIKI = os.path.join(ROOT, "wiki")
BL = os.path.join(WIKI, "backlinks.md")
PLACEHOLDER = wiki_scan.PLACEHOLDER   # 정본은 wiki_scan (원장 #24)

W = re.compile(r"\[\[([^\]]+)\]\]")
W_LINE = re.compile(r"^-\s*\[\[([^\]]+)\]\]\s*(.*)$")
# 코드 스팬·펜스 마스킹의 정본은 `wiki_scan` 이다 (원장 #24·#43).
# `_meta/` 작성 규약이 "링크 문법은 백틱으로 감쌀 것" 을 요구하는데(weather.md §메타 파일
# 작성 주의), 벗기지 않으면 그 규약이 무력해져 백틱 안 예시가 실제 링크로 집계된다.
# 2026-08-03(lint 19회차) 도입 시 델타 0 — 정당한 링크는 코드 스팬 안에 살지 않는다.
# 2026-08-07(#43): 정규식 하나로 처리하던 것을 줄머리 펜스 토글로 교체했다 —
#   `re.S` 판은 펜스 짝이 안 맞으면 그 사이를 통째로 삼켜 링크를 조용히 지웠다.


def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def read_scan(p):
    """링크 스캔용 읽기 — 코드 스팬을 공백으로 덮어 예시 링크를 배제한다.

    줄 수를 보존하므로 줄 번호로 보고하는 소비자도 이 함수를 그대로 쓸 수 있다.
    """
    return wiki_scan.mask_text(read(p), source=os.path.relpath(p, ROOT))


def main():
    cf = glob.glob(os.path.join(WIKI, "concepts", "*.md"))
    tf = glob.glob(os.path.join(WIKI, "topics", "*.md"))
    slug_map = {os.path.splitext(os.path.basename(f))[0]: f for f in cf + tf}

    # 1) inbound + source-side annotation from '관련 개념'
    inbound = {}            # target -> set(source)
    src_ann = {}            # (source, target) -> annotation text (no parens)
    for src, f in slug_map.items():
        txt = read_scan(f)                        # 코드 스팬 제거 후 스캔
        for m in W.finditer(txt):
            t = m.group(1).split("|")[0].split("#")[0].strip()
            if t in slug_map and t != src and t not in PLACEHOLDER:
                inbound.setdefault(t, set()).add(src)
        sec = re.search(r"##\s*관련 개념\s*\n(.*?)(?:\n##\s|\Z)", txt, re.S)
        if sec:
            for ln in sec.group(1).splitlines():
                mm = W_LINE.match(ln.strip())
                if not mm:
                    continue
                t = mm.group(1).split("|")[0].split("#")[0].strip()
                rest = mm.group(2).strip()
                rest = re.sub(r"^[—\-–]\s*", "", rest).strip()
                if t in slug_map and t != src:
                    src_ann[(src, t)] = rest

    # 2) carry-over annotations from existing backlinks.md: (target, source) -> "(...)" suffix verbatim
    carry = {}
    if os.path.exists(BL):
        cur = None
        for ln in read(BL).splitlines():
            h = re.match(r"##\s*\[\[([^\]]+)\]\]", ln)
            if h:
                cur = h.group(1).split("|")[0].strip()
                continue
            m = W_LINE.match(ln.strip())
            if m and cur:
                s = m.group(1).split("|")[0].split("#")[0].strip()
                suffix = m.group(2).strip()  # e.g. "(헥사고날 ... 으로 참조)"
                if suffix:
                    carry[(cur, s)] = suffix

    # 3) render — targets & sources sorted for idempotency
    blocks = []
    for t in sorted(inbound):
        lines = [f"## [[{t}]]", "", "참조하는 파일:"]
        for s in sorted(inbound[t]):
            if (t, s) in carry:                       # 기존 큐레이션 주석 보존 (verbatim)
                lines.append(f"- [[{s}]] {carry[(t, s)]}")
            elif src_ann.get((s, t)):                 # source 관련개념 주석 보강
                ann = src_ann[(s, t)].strip()
                ann = re.sub(r"^\((.*)\)$", r"\1", ann).strip()   # 이중 괄호 방지
                lines.append(f"- [[{s}]] ({ann})")
            else:
                lines.append(f"- [[{s}]]")
        blocks.append("\n".join(lines))

    header = (
        "# 백링크 맵\n\n"
        "> 자동 생성 — scripts/rebuild-backlinks.py (strict-inbound 역인덱싱). 수동 편집 금지.\n"
        "> 각 개념을 참조하는 다른 파일 목록 (source 의 명시적 [[link]] 기준).\n"
    )
    # 결과가 비면 덮어쓰지 않는다 (원장 #35). carry(:77-90) 를 방금 이 파일에서 읽었으므로
    # 빈 결과로 덮어쓰면 큐레이션 주석까지 같은 실행에서 사라진다 — 종료코드도 stderr 도 없는
    # 조용한 데이터 손실이라 fail-open 계열(#8)과 실패 양상이 다르다.
    # 기존 파일이 없을 때는 잃을 것이 없으므로 통과시킨다 (scaffold 초기 배포).
    if not blocks and os.path.exists(BL) and "## [[" in read(BL):
        sys.stderr.write(
            "[rebuild-backlinks] 중단: inbound 0건인데 기존 backlinks.md 에는 블록이 있다.\n"
            "  덮어쓰지 않았다. wiki/concepts·topics 가 제자리에 있는지 먼저 확인할 것.\n")
        sys.exit(1)

    out = header + "\n---\n\n" + "\n\n---\n\n".join(blocks) + "\n"
    with open(BL, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"[rebuild-backlinks] {len(blocks)} blocks · "
          f"{sum(len(v) for v in inbound.values())} entries · "
          f"carried={sum(1 for k in carry if k[0] in inbound and k[1] in inbound.get(k[0], set()))}")


if __name__ == "__main__":
    main()
