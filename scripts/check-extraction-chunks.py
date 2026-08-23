#!/usr/bin/env python3
"""check-extraction-chunks.py — 시맨틱 추출 청크의 extraction-spec 준수 검사.

배경 (인계 2026-08-23-003/-004, 계획서 2026-08-23-spec-compliance-check-and-refork):
    `extraction-spec.md` 의 `_origin RULE` 은 **프롬프트 수준 방어**일 뿐이다.
    엔진의 `graphify/validate.py` 는 `_origin` 누락도, `^L\\d` 인 `source_location`
    도 거르지 않는다(실측: `_origin` 문자열 0건). 서브에이전트가 규칙을 어기면:

      ① `build.py:41` `_AST_LOC_RE = ^L\\d` shape 폴백이 그 항목을 `ast` 로 판정
      ② 티어가 갈려 `build_merge` 의 tier-scoped replace 가 기존 노드를 못 지움
      ③ 같은 ID 2건이 `dedup.py:365` `_collision_rank` 에 도달
      ④ `len(label)` 로 **짧은 옛 라벨이 이긴다** — 새로 뽑은 좋은 라벨이 소리 없이 소실

    경고는 stderr `note:` 한 줄뿐이다. 이 스크립트가 그 조용한 실패를 시끄럽게 만든다.

🔴 호출 시점이 중요하다 — **캐시 저장 직전**이다.
    위반 청크가 `save_semantic_cache` 를 통과하면 네임스페이스 안에 눌러붙고,
    이후 캐시 히트는 **재검증을 거치지 않아** 모든 빌드를 계속 오염시킨다.
    2026-08-23 마이그레이션이 캐시 본문 53노드·62엣지를 손으로 고쳐야 했던 이유다.
    호출 자리: `.claude/skills/graphify/SKILL.md` Step B3, 청크 병합 직후.

⚠️ 이 검사는 **새로 추출된 청크**를 대상으로 한다. 기존 캐시(레거시)에 돌리면
    `_origin` 미보유가 대량으로 걸리는데 그것은 결함이 아니다 — 그 항목들은
    `source_location` 이 `null` 이라 shape 폴백이 `semantic` 으로 옳게 판정한다.
    마이그레이션은 실제 위험군(L형)만 골라 stamp 했다. 레거시 감사는
    「L형 + `_origin` 없음」 조합만 보면 되고 그 값은 이미 0이다.

사용법:
    python3 scripts/check-extraction-chunks.py                  # 기본 glob
    python3 scripts/check-extraction-chunks.py <경로> [<경로>…]  # 명시 지정

종료 코드:
    0  위반 없음
    1  스펙 위반 발견 (위반 전건을 stdout 에 열거)
    2  대상 없음 또는 JSON 파싱 실패
"""

from __future__ import annotations

import glob
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_GLOB = "graphify-out/.graphify_chunk_*.json"

# build.py:41 의 `_AST_LOC_RE` 와 같은 패턴이어야 한다. 여기가 갈리면 검사가 무의미해진다.
AST_LOC_RE = re.compile(r"^L\d")


def _ident(item: dict, kind: str) -> str:
    """위반을 사람이 찾아갈 수 있는 최소 식별자."""
    if kind == "edge":
        return f"{item.get('source')} -> {item.get('target')}"
    return str(item.get("id"))


def check_items(items: list, kind: str, where: str) -> list[str]:
    """node/edge 공통 규칙: `_origin` 은 있어야 하고 `semantic` 이어야 하며,
    `source_location` 이 AST 서명(`^L\\d`)이면 안 된다."""
    out = []
    for item in items:
        if not isinstance(item, dict):
            out.append(f"{where}: {kind} 가 dict 가 아니다 — {item!r:.80}")
            continue
        who = _ident(item, kind)
        if "_origin" not in item:
            out.append(f'{where}: {kind} {who} — `_origin` 누락 (spec: "_origin":"semantic")')
        elif item["_origin"] != "semantic":
            out.append(f'{where}: {kind} {who} — `_origin`={item["_origin"]!r}, "semantic" 이어야 한다')
        loc = item.get("source_location")
        if isinstance(loc, str) and AST_LOC_RE.match(loc):
            out.append(
                f"{where}: {kind} {who} — source_location={loc!r} 가 AST 서명 `^L\\d` 에 매치한다 "
                f"(spec: null 로 둔다)"
            )
    return out


def check_hyperedges(items: list, where: str) -> list[str]:
    """하이퍼엣지는 구성상 시맨틱 티어라 stamp 하지 않는다 (build.py:1608·:1811)."""
    out = []
    for he in items:
        if isinstance(he, dict) and "_origin" in he:
            out.append(
                f"{where}: hyperedge {he.get('id')} — `_origin` 이 있으면 안 된다 "
                f"(하이퍼엣지는 구성상 시맨틱 티어)"
            )
    return out


def check_file(path: Path) -> list[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[설정 오류] {path}: 읽거나 파싱할 수 없다 — {exc}", file=sys.stderr)
        raise SystemExit(2)
    where = str(path.relative_to(REPO)) if path.is_absolute() and REPO in path.parents else str(path)
    # 청크는 `edges`, graph.json 은 `links` 를 쓴다. 둘 다 받는다.
    edges = data.get("edges", data.get("links", []))
    return (
        check_items(data.get("nodes", []), "node", where)
        + check_items(edges, "edge", where)
        + check_hyperedges(data.get("hyperedges", []), where)
    )


def main(argv: list[str]) -> int:
    targets = argv[1:]
    if targets:
        paths = [Path(t) for t in targets]
    else:
        paths = [Path(p) for p in sorted(glob.glob(str(REPO / DEFAULT_GLOB)))]

    missing = [p for p in paths if not p.is_file()]
    if missing:
        for p in missing:
            print(f"[설정 오류] 대상이 없다: {p}", file=sys.stderr)
        return 2
    if not paths:
        print(
            f"[설정 오류] 검사 대상이 없다 ({DEFAULT_GLOB} 에 매치하는 파일 0건). "
            f"청크가 생성되기 전에 부른 것이 아닌지 확인하라.",
            file=sys.stderr,
        )
        return 2

    violations = []
    for p in paths:
        violations += check_file(p)

    if violations:
        print(f"🔴 extraction-spec 위반 {len(violations)}건 — 파일 {len(paths)}건 검사")
        for v in violations:
            print(f"  {v}")
        print()
        print(
            "이 청크를 캐시에 저장하면 되돌리기 어렵다 — 캐시 히트는 재검증을 거치지 않는다.\n"
            "해당 서브에이전트를 재실행하라. 규칙은 "
            ".claude/skills/graphify/references/extraction-spec.md 의 `_origin RULE`."
        )
        return 1

    print(f"위반 없음 — 파일 {len(paths)}건 검사.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
