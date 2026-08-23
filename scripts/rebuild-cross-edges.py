#!/usr/bin/env python3
"""graphify-out/graph.json 에 wiki [[wikilink]] 기반 cross-concept 엣지를 재적용.

`graphify update` 는 graph.json 을 전체 재생성하므로, wiki 개념 간 의미 엣지가
매 빌드마다 유실된다(2026-07-02 회귀 확인). 이 스크립트는 rebuild-backlinks.py 와
같은 **결정론적 후처리**로 wiki 원본의 링크를 엣지로 되돌린다. LLM 불필요.

빌드 순서상 `graphify update` **다음**에 실행되므로 덮어쓰기가 구조적으로 해소된다.

정책:
- 대상 링크: `wiki/concepts/*.md`·`wiki/topics/*.md` 의 `## 관련 개념` 섹션 `[[link]]`
  (본문 중간 링크는 제외 — 스치듯 언급까지 관계로 잡지 않는다)
- 연결 노드: **파일 레벨 노드끼리만**. 섹션 노드는 쓰지 않는다(탐색 홉이 깊어짐)
- 대상 개념 파일이 없으면 스킵 — **미작성 개념으로의 링크가 노드를 만들지 않는다**
- `relation="wikilink"` 로 고유 표시. 매 실행마다 이 타입만 전량 삭제 후 재생성하므로
  ① 다른 relation 을 건드리지 않고(비파괴) ② 재실행 diff 가 0 이다(멱등)
- 무방향 1쌍당 엣지 1개. (a,b) 정렬로 방향 고정
- **이미 다른 relation 엣지가 있는 쌍은 건너뛴다.** graphify 는 `nx.Graph`(단순 그래프)라
  같은 (src,tgt) 에 엣지를 두 번 넣으면 나중 것이 앞을 **덮어쓴다**. 정렬상 `wikilink` 가
  `references` 보다 뒤라 항상 이기므로, 겹치는 쌍에 엣지를 만들면 `cluster-only` 같은
  재적재 경로에서 기존 relation·메타데이터가 영구 소실된다(2026-07-27 검증에서 680쌍 확인).
  이 패스의 목적은 **없는 연결을 채우는 것**이지 있는 연결을 다시 쓰는 것이 아니다.

사용: scripts/graphify-py.sh scripts/rebuild-cross-edges.py
"""
import os, re, glob, json, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wiki_scan

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIKI = os.path.join(ROOT, "wiki")
GRAPH = os.path.join(ROOT, "graphify-out", "graph.json")

# 정본은 wiki_scan (원장 #24) — 사본을 두면 한쪽만 고쳐져 값이 갈린다
PLACEHOLDER = wiki_scan.PLACEHOLDER
RELATION = "wikilink"

W = re.compile(r"\[\[([^\]]+)\]\]")
SEC = re.compile(r"##\s*관련 개념\s*\n(.*?)(?:\n##\s|\Z)", re.S)
# 코드 스팬 마스킹도 정본은 wiki_scan 이다 (원장 #43) — 여기 있던 사본은
# `re.S` 판이라 펜스 짝이 안 맞으면 `## 관련 개념` 절째로 삼켜 cross-edge 를
# 조용히 0 으로 만들 수 있었다.


def related_links(path):
    """'## 관련 개념' 섹션의 [[link]] 슬러그 집합.

    줄당 첫 링크만이 아니라 섹션 안의 모든 링크를 잡는다 —
    `- [[a]], [[b]]` 처럼 한 줄에 여러 개를 나열하는 표기가 실제로 존재한다.
    """
    with open(path, encoding="utf-8") as f:
        m = SEC.search(wiki_scan.mask_text(f.read(), source=os.path.relpath(path, ROOT)))
    if not m:
        return set()
    return {g.split("|")[0].split("#")[0].strip() for g in W.findall(m.group(1))}


def slug_node_id(source_file):
    """`wiki/concepts/a-b.md` -> `wiki_concepts_a_b` (추출기의 파일 노드 명명 관례)."""
    return "wiki_" + source_file[len("wiki/"):-3].replace("/", "_").replace("-", "_")


def file_nodes(graph):
    """source_file -> 파일 레벨 노드 id.

    선택 순서: ① source_location == 'L1' ② 파일 경로에서 유도한 slug id
    ③ 최단 id 폴백.

    🔴 ②가 없던 판은 문서층에서 **섹션 노드를 파일 노드로 골랐다**(2026-08-19 발견).
      이 함수의 원래 주석은 *"파일 노드는 source_location == 'L1' 인 노드다
      (267개 중 265개)"* 였는데 그 수치는 **코드층 기준**이다 — 실측하면
      wiki concept/topic 322개 중 L1 을 가진 파일은 **17개**뿐이라, 문서층은
      사실상 전부 폴백 경로를 탔다. 최단 id 폴백은 제목이 짧은 섹션 노드를
      집으므로 파일 노드가 cross-edge 를 한 개도 못 받고 고립된다.
      실측 3건: integration-test-scenario-design(→ts_tc_two_stage_structure) ·
      kafka-cluster-migration(→mirrormaker2) · hidden-technical-decisions
      (→decision_axis_spec_design). 앞의 둘은 backlinks.md 유래 엣지가
      degree 를 채워주고 있어 드러나지 않다가, 그 엣지를 걷어내자 degree 0 으로
      드러났다(2026-08-19 원장 #72 계열 조치).
    ⚠️ ②는 계약이 아니라 관례다 — slug 일치 노드가 없는 파일이 322개 중 152개라
      ③ 폴백을 지운 것이 아니라 ② 를 그 **앞에** 끼운 것이다.
    """
    by_src = {}
    for n in graph["nodes"]:
        sf = n.get("source_file") or ""
        if sf.startswith("wiki/concepts/") or sf.startswith("wiki/topics/"):
            by_src.setdefault(sf, []).append(n)
    out = {}
    for sf, ns in by_src.items():
        l1 = [n for n in ns if str(n.get("source_location")) == "L1"]
        if l1:
            out[sf] = l1[0]["id"]
            continue
        want = slug_node_id(sf)
        if any(n["id"] == want for n in ns):
            out[sf] = want
            continue
        out[sf] = min(ns, key=lambda n: (len(n["id"]), n["id"]))["id"]
    return out


def compute_pairs(graph):
    """'## 관련 개념' 링크로부터 무방향 (a_id, b_id) 후보 쌍을 계산.

    main() 과 scripts/inject-self-metrics.py 가 **같은 정의**를 쓰도록 분리했다 —
    후보 쌍 수를 다른 곳에서 다시 세면 그 수치가 이 패스의 정의와 갈라진다.
    """
    files = sorted(glob.glob(os.path.join(WIKI, "concepts", "*.md")) +
                   glob.glob(os.path.join(WIKI, "topics", "*.md")))
    slug_rel = {}   # slug -> 저장소 상대 경로
    for p in files:
        slug_rel[os.path.splitext(os.path.basename(p))[0]] = os.path.relpath(p, ROOT)

    nid = file_nodes(graph)

    pairs = {}          # (a_id, b_id) -> 근거 source_file
    skipped_missing = 0  # 미작성 개념으로의 링크
    skipped_nonode = 0   # 파일은 있으나 그래프에 노드가 없는 경우
    for slug, rel in slug_rel.items():
        src_id = nid.get(rel)
        if src_id is None:
            continue
        for tgt in sorted(related_links(os.path.join(ROOT, rel))):
            if tgt == slug or tgt in PLACEHOLDER:
                continue
            if tgt not in slug_rel:
                skipped_missing += 1
                continue
            tgt_id = nid.get(slug_rel[tgt])
            if tgt_id is None:
                skipped_nonode += 1
                continue
            key = tuple(sorted((src_id, tgt_id)))
            pairs.setdefault(key, rel)
    return pairs, skipped_missing, skipped_nonode


def main():
    if not os.path.exists(GRAPH):
        print(f"graph.json 없음: {GRAPH}", file=sys.stderr)
        return 1

    with open(GRAPH, encoding="utf-8") as f:
        graph = json.load(f)

    pairs, skipped_missing, skipped_nonode = compute_pairs(graph)

    before = len(graph["links"])
    kept = [l for l in graph["links"] if l.get("relation") != RELATION]
    removed = before - len(kept)

    # 이미 다른 relation 이 있는 쌍은 제외 — nx.Graph 재적재 시 덮어쓰기 방지 (docstring 참조)
    occupied = {tuple(sorted((l["source"], l["target"]))) for l in kept}
    added = 0
    for (a, b), rel in sorted(pairs.items()):
        if (a, b) in occupied:
            continue
        kept.append({
            "relation": RELATION,
            "confidence": "EXTRACTED",   # graphify validator 허용값: AMBIGUOUS/EXTRACTED/INFERRED
            "confidence_score": 1.0,
            "source_file": rel,
            "source_location": None,
            "weight": 1.0,
            "source": a,
            "target": b,
        })
        added += 1

    graph["links"] = kept
    # 🔴 직렬화는 `graphify/cli.py:471` 과 **바이트 호환**이어야 한다 (2026-08-24).
    #   그쪽은 `write_json_atomic(graph_path, data, indent=2)` — 즉 `indent=2` +
    #   `ensure_ascii` 기본값(True)이다. 이 스크립트는 `graphify-build.sh` 에서
    #   `graphify update` **다음에** 돌아 graph.json 을 덮어쓰는 **마지막 writer** 라,
    #   여기서 형식이 어긋나면 매 빌드가 업스트림의 들여쓰기를 날린다.
    #   ⚠️ 실제로 그랬다 — 이력에서 형식이 4회 이상 뒤집혔고(`bf5564d` pretty →
    #   `67c99ae` compact → `d03e02b` pretty → `5d39252` compact) 그때마다 25만 줄
    #   diff 가 나 **내용 델타를 사람이 읽을 수 없었다.** 이 저장소는 그래프 diff 를
    #   실제로 판독한다(유령 리맵 커밋 `83bca3c` 가 «14 insertions / 44 deletions» 를
    #   수술 정밀도의 근거로 인용했다) — 그 판독 가능성이 이 한 줄에 달려 있다.
    #   ⚠️ `ensure_ascii=False` 로 되돌리지 마라. 한글이 읽기 좋아 보이지만 `cli.py`
    #   와 갈려 같은 진동이 재발한다. 형식 권한은 업스트림 writer 한 곳이다.
    with open(GRAPH, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2)

    print(f"✓ cross-edge 재적용: {added}쌍 신규 "
          f"(wikilink 후보 {len(pairs)}쌍 중 {len(pairs) - added}쌍은 기존 엣지 존재로 스킵, "
          f"이전 {RELATION} {removed}개 제거) | 총 links {before} → {len(kept)}", file=sys.stderr)
    print(f"  스킵: 미작성 개념 링크 {skipped_missing} · 노드 없음 {skipped_nonode}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
