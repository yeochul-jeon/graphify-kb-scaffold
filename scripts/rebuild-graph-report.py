#!/usr/bin/env python3
"""graphify-out/GRAPH_REPORT.md 를 현재 graph.json 기준으로 재생성.

## 왜 필요한가 (파이프라인 순서 결함)

`scripts/graphify-build.sh` 의 실행 순서는 이렇다:

    :22  graphify update .          → graph.json 재생성 + GRAPH_REPORT.md 작성
    :39  rebuild-cross-edges.py     → graph.json 만 수정 (wiki [[wikilink]] 엣지 재적용)
    :43  build-graph-digest.py      → graph.json 에서 수치 계산 → GRAPH_DIGEST.md

즉 **REPORT 는 cross-edge 적용 *이전* 그래프를, DIGEST 는 *이후* 그래프를 서술한다.**
cross-edge 순증이 0이면 우연히 일치하므로 네 세션 동안 드러나지 않았고, 2026-08-17
4차 세션 2차 실행에서 순증 +10 이 나며 REPORT 9480 vs DIGEST 9490 으로 갈렸다.
경위·후보안 비교는 `.claude/reports/handoff/2026-08-17-004-*.md` §6-0c.

이 스크립트는 `:39` 와 `:43` **사이**에 들어간다. DIGEST 가 REPORT 를 커뮤니티 이름
파싱용으로 읽으므로(`build-graph-digest.py:26,42`) REPORT 가 먼저 최신이어야 한다.

## 설계 원칙 — 재계산과 승계를 가른다

🔴 **graph.json 이 아는 것만 재계산하고, 나머지는 기존 REPORT 에서 승계한다.**

- **재계산**: nodes·edges·communities 수, 커뮤니티 구성·cohesion, god nodes,
  Extraction 비율, surprising connections, hyperedges, import cycles,
  knowledge gaps, suggested questions
  → 전부 `graph.json` + upstream `analyze`/`cluster` 순수 함수로 복원된다.
    노드 전건이 `community`·`community_name` 을, 엣지 전건이 `confidence`·
    `confidence_score` 를 들고 있다(2026-08-17 실측).
- **승계**: `## Corpus Check` 줄, `Token cost` 줄, `## Graph Freshness` 섹션 유무
  → 이 값들은 `graphify update` 만 알고 graph.json 에는 없다. **재발명하면 안 된다.**
    ⚠️ 실제로 REPORT 의 Corpus Check 파일 수는 회차마다 785 → 8 → 6 → 83 으로 흔들리는데
    (코퍼스는 manifest 1301건) 그것은 `detection_result['total_files']` 가 **그 회차의
    증분 dispatch 배치 크기**이기 때문이다. 별개 결함이며 여기서 고치지 않는다 —
    이 스크립트가 그 값을 "복원" 하려 들면 없는 사실을 지어내게 된다.

즉 **입력이 바뀌지 않았다면 출력은 기존 REPORT 와 바이트 동일해야 한다.** 그것이
이 스크립트의 수용 기준이고, `--check` 로 확인할 수 있다.

## 사용

    scripts/graphify-py.sh scripts/rebuild-graph-report.py
    scripts/graphify-py.sh scripts/rebuild-graph-report.py --root <경로>   # 사본 대상 (테스트)
    scripts/graphify-py.sh scripts/rebuild-graph-report.py --check         # 쓰지 않고 diff 여부만

⚠️ `scripts/graphify-py.sh` 경유 필수 — upstream 패키지가 pipx venv 에만 있다.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# report.generate() 의 upstream 기본값. 여기서 재정의하지 않는다 —
# 값이 갈리면 `graphify update` 가 쓴 REPORT 와 이 스크립트가 쓴 REPORT 의
# "thin omitted" 개수가 달라져 매 빌드마다 가짜 diff 가 난다.
MIN_COMMUNITY_SIZE = 3

CORPUS_FILES_RE = re.compile(r"^- ([\d,]+) files · ~([\d,]+) words$")
TOKEN_COST_RE = re.compile(r"^- Token cost: ([\d,]+) input · ([\d,]+) output$")


def _section(text: str, header: str) -> list[str]:
    """`## header` 섹션의 본문 줄들을 돌려준다 (없으면 빈 리스트)."""
    lines = text.splitlines()
    try:
        start = lines.index(f"## {header}")
    except ValueError:
        return []
    body: list[str] = []
    for line in lines[start + 1:]:
        if line.startswith("## "):
            break
        body.append(line)
    return body


def carry_over(report_text: str | None) -> tuple[dict, dict, bool]:
    """기존 REPORT 에서 승계 대상 3종을 뽑는다.

    Returns (detection_result, token_cost, wants_freshness).

    승계원이 없거나(첫 빌드) 형식이 바뀌어 파싱에 실패하면 **추측하지 않고**
    upstream 이 같은 상황에서 쓰는 warning 형태로 떨어진다(`cli.py:2021` 이
    cluster-only 에서 동일하게 처리한다). 지어낸 숫자보다 명시적 미상이 낫다.
    """
    if not report_text:
        return (
            {"warning": "report regenerated from graph.json — corpus stats not available"},
            {"input": 0, "output": 0},
            False,
        )

    detection: dict = {}
    for line in _section(report_text, "Corpus Check"):
        m = CORPUS_FILES_RE.match(line)
        if m:
            detection = {
                "total_files": int(m.group(1).replace(",", "")),
                "total_words": int(m.group(2).replace(",", "")),
            }
            break
        if line.startswith("- ") and not line.startswith("- Verdict:"):
            # upstream 의 warning 분기를 그대로 되돌린다
            detection = {"warning": line[2:]}
            break
    if not detection:
        detection = {"warning": "report regenerated from graph.json — corpus stats not available"}

    token_cost = {"input": 0, "output": 0}
    for line in _section(report_text, "Summary"):
        m = TOKEN_COST_RE.match(line)
        if m:
            token_cost = {
                "input": int(m.group(1).replace(",", "")),
                "output": int(m.group(2).replace(",", "")),
            }
            break

    # Graph Freshness 는 호출 경로마다 유무가 갈린다 — 전체 재빌드는 넣고
    # `graphify update` 경로는 넣지 않는다(2026-08-17 실측: 36c8edc 有, ab15d57·d959aa7 無).
    # 어느 쪽이 옳은지 판정하지 않고 기존 REPORT 의 상태를 그대로 따른다.
    wants_freshness = "\n## Graph Freshness\n" in report_text

    return detection, token_cost, wants_freshness


def rebuild(root: Path) -> str:
    from graphify.analyze import god_nodes, suggest_questions, surprising_connections
    from graphify.build import build_from_json
    from graphify.cluster import score_all
    from graphify.report import generate, load_learning_for_report

    out = root / "graphify-out"
    graph_json = out / "graph.json"
    if not graph_json.exists():
        sys.exit(f"graph.json 없음: {graph_json}")

    raw = json.loads(graph_json.read_text(encoding="utf-8"))
    G = build_from_json(raw, directed=bool(raw.get("directed", False)))

    # 커뮤니티는 노드의 `community` 속성에서 복원한다. **재클러스터링하지 않는다** —
    # cross-edge 적용 후 다시 클러스터링하면 파티션이 이동하고 라벨이 강등돼
    # (멤버십이 바뀐 커뮤니티는 hub-fill 로 떨어진다) 매 빌드마다 누적 열화한다.
    # 이 스크립트의 일은 "같은 그래프를 다시 서술" 이지 "다시 분할" 이 아니다.
    # ⚠️ 순회 순서는 **cid 오름차순**이다. `generate()` 가 Community Hubs·Communities 를
    #    dict 순서 그대로 뽑으므로, 노드 배열 순서로 그룹핑하면 섹션 전체가 뒤섞여
    #    내용이 같아도 수천 줄짜리 가짜 diff 가 난다(2026-08-17 실측으로 확인하고 고쳤다).
    #    멤버 리스트도 **노드 id 오름차순**이다 — upstream `cluster()` 의 마지막 줄이
    #    `{i: sorted(nodes) ...}` 이고, `generate()` 가 그 순서의 앞 8개를 대표로 찍는다.
    grouped: dict[int, list[str]] = {}
    for node in raw.get("nodes", []):
        cid = node.get("community")
        if cid is None:
            continue
        grouped.setdefault(int(cid), []).append(node["id"])
    communities: "OrderedDict[int, list[str]]" = OrderedDict(
        (cid, sorted(nodes)) for cid, nodes in sorted(grouped.items())
    )

    # 라벨 정본은 사이드카다. graph.json 의 `community_name` 은 같은 값의 사본이며,
    # 사본을 읽으면 upstream 이 사이드카만 갱신했을 때 갈린다.
    labels: dict[int, str] = {}
    labels_json = out / ".graphify_labels.json"
    if labels_json.exists():
        labels = {
            int(k): v
            for k, v in json.loads(labels_json.read_text(encoding="utf-8")).items()
        }
    for cid, members in communities.items():
        if cid not in labels:
            name = next(
                (n.get("community_name") for n in raw.get("nodes", [])
                 if n.get("community") == cid and n.get("community_name")),
                None,
            )
            if name:
                labels[cid] = name

    report_path = out / "GRAPH_REPORT.md"
    prev = report_path.read_text(encoding="utf-8") if report_path.exists() else None
    detection, token_cost, wants_freshness = carry_over(prev)

    return generate(
        G,
        communities,
        score_all(G, communities),
        labels,
        god_nodes(G),
        surprising_connections(G, communities),
        detection,
        token_cost,
        str(root),
        suggested_questions=suggest_questions(G, communities, labels),
        min_community_size=MIN_COMMUNITY_SIZE,
        built_at_commit=raw.get("built_at_commit") if wants_freshness else None,
        learning=load_learning_for_report(graph_json),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, default=REPO_ROOT,
                    help="graphify-out/ 을 담은 디렉터리 (기본: 저장소 루트). "
                         "사본 대상 검증에 쓴다 — 저장소를 건드리지 않기 위함.")
    ap.add_argument("--check", action="store_true",
                    help="파일을 쓰지 않고 기존 REPORT 와 달라지는지만 알린다 "
                         "(달라지면 exit 1)")
    args = ap.parse_args()

    root = args.root.resolve()
    report_path = root / "graphify-out" / "GRAPH_REPORT.md"
    new = rebuild(root)
    old = report_path.read_text(encoding="utf-8") if report_path.exists() else None

    if args.check:
        if old == new:
            print("✓ GRAPH_REPORT.md 는 현재 graph.json 과 일치한다", file=sys.stderr)
            return 0
        print("✗ GRAPH_REPORT.md 가 현재 graph.json 과 다르다", file=sys.stderr)
        return 1

    if old == new:
        # 값이 그대로면 쓰지 않는다 — mtime 만 흔들면 무의미한 diff·재빌드를 유발한다.
        print("▶ GRAPH_REPORT.md 변경 없음", file=sys.stderr)
        return 0

    report_path.write_text(new, encoding="utf-8")
    summary = next((l for l in new.splitlines() if l.startswith("- ") and " nodes · " in l), "")
    print(f"▶ GRAPH_REPORT.md 재생성 {summary.lstrip('- ')}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
