#!/usr/bin/env bash
# scripts/graphify-build.sh
# graphify 그래프 갱신 후 GRAPH_DIGEST.md 를 자동 재생성하는 wrapper.
#
# Usage:
#   scripts/graphify-build.sh                # 증분 코드 재추출 (LLM 없음)
#   scripts/graphify-build.sh --cluster-only # 클러스터링 재실행만
#
# 이 스크립트를 쓰면 'graphify update' 후 DIGEST 재생성을 한 번에 처리.
# 전체 (LLM) 재빌드가 필요할 때는 /graphify 스킬을 직접 사용.
set -euo pipefail
cd "$(dirname "$0")/.."

MODE="${1:-update}"

echo "▶ graphify 그래프 갱신 (mode=$MODE) ..." >&2

if [ "$MODE" = "--cluster-only" ]; then
  scripts/graphify-py.sh -m graphify cluster-only .
else
  # 기본: 증분 코드 재추출 (--update 포함)
  scripts/graphify-py.sh -m graphify update .
  # meta 파일(index.md, backlinks.md, compile-log.md) 구버전 캐시 정리
  scripts/graphify-py.sh scripts/cleanup-meta-caches.py
  # wiki/backlinks.md 결정론적 재생성 (strict-inbound 역인덱싱 — 드리프트 방지)
  echo "▶ wiki/backlinks.md 재생성 ..." >&2
  scripts/graphify-py.sh scripts/rebuild-backlinks.py
  # index.md 목록 표의 「최종 업데이트」 열을 각 파일 frontmatter `updated` 로 주입.
  # 손 관리 사본이라 30회차 실측에서 76건이 어긋나 있었다 — 원장 #61, 사람 결정 ①(2026-08-11).
  # 🔴 방향이 한쪽뿐이다: index.md 만 쓰고 concepts/topics 의 `updated` 는 건드리지 않는다
  #    (반대로 밀면 본문 무변경인데 `updated` 가 올라 #40 경로를 밟는다).
  # ⚠️ PyYAML 불필요 — 시스템 python3 로 돈다.
  echo "▶ index.md 날짜 열 주입 ..." >&2
  python3 scripts/sync-index-dates.py
  # raw→wiki 대조표 재생성. 내용이 같으면 쓰기를 건너뛰므로(generate-source-ledger.py:135-137)
  # 무변경 빌드는 mtime·git diff 를 만들지 않는다 — 실측 real 0.19/0.09/0.09s (3회, 2026-08-25).
  # wiki/_meta 는 .graphifyignore 대상이라 그래프 비용도 0 이다.
  # 편입 근거: 2026-08-12~08-25 실측에서 빌드 36회 대 원장 갱신 8회로 표류가 기본값이었다.
  echo "▶ source-ledger.md 재생성 ..." >&2
  scripts/graphify-py.sh scripts/generate-source-ledger.py
  # wiki [[wikilink]] → graph cross-edge 재적용.
  # 반드시 'graphify update' 다음이어야 한다 — update 가 graph.json 을 전체 재생성하며
  # doc 개념 간 엣지를 지우기 때문. 여기서 되돌려야 회귀가 구조적으로 해소된다.
  echo "▶ cross-concept 엣지 재적용 ..." >&2
  scripts/graphify-py.sh scripts/rebuild-cross-edges.py
  # GRAPH_REPORT.md 를 방금 바뀐 graph.json 기준으로 재서술.
  # 🔴 반드시 rebuild-cross-edges 다음, build-graph-digest 앞이다.
  #   - 앞: 'graphify update'(:22)가 쓴 REPORT 는 cross-edge **이전** 그래프를 서술한다.
  #         cross-edge 가 엣지 수를 바꾸면 REPORT 만 낡고 DIGEST 와 갈린다 — 2026-08-17
  #         4차 세션에서 실제로 REPORT 9480 vs DIGEST 9490 으로 갈렸다. 그 전 네 세션은
  #         cross-edge 순증이 0이라(866→866, 8387→8387) 우연히 일치해 드러나지 않았다.
  #   - 뒤: build-graph-digest 가 REPORT 를 커뮤니티 이름 파싱용으로 읽는다
  #         (build-graph-digest.py:26,42). REPORT 가 먼저 최신이어야 한다.
  # ⚠️ 재클러스터링하지 않는다. graph.json 의 community 속성을 그대로 읽어 다시 서술만 한다
  #    (`cluster-only` 를 여기 넣으면 파티션이 이동하고 라벨이 hub-fill 로 강등된다).
  # ⚠️ Corpus Check·Token cost 는 'graphify update' 만 아는 값이라 기존 REPORT 에서 승계한다.
  echo "▶ GRAPH_REPORT.md 재서술 (cross-edge 반영) ..." >&2
  scripts/graphify-py.sh scripts/rebuild-graph-report.py
fi

echo "▶ GRAPH_DIGEST.md 재생성 ..." >&2
scripts/graphify-py.sh scripts/build-graph-digest.py

# 자기 측정 문서(self_measuring: true)의 현재 상태 수치 주입.
# 반드시 마지막 — 위 파생 패스가 끝난 뒤라야 방금 만든 graph.json·backlinks.md 를 잰다.
# 주입 결과는 다음 빌드에서야 그래프에 반영되므로, 문서는 "직전 빌드 시점" 임을 명시한다.
#
# --cluster-only 는 제외한다. 그 모드의 목적이 Louvain 재실행인데 Louvain 은 비결정이라
# **입력이 그대로여도 커뮤니티 수가 흔들린다**(실측 840→839→837). 저장소는 이 흔들림을
# 이미 노이즈로 규정했으므로(ID 변동만 있는 diff 는 회귀가 아니다), 여기서 주입하면
# 승인된 wiki 문서의 본문 diff 가 매번 발생해 ALLOW_WIKI_EDIT 우회가 상시화된다.
#
# 🔴 정정 (2026-08-17). 이 자리에 있던 *"기본 경로는 입력이 같으면 클러스터링도 안정적이라
# 이 문제가 없다"* 는 **틀렸다** — 원장 #72 잔여 ②의 「판정 보류」를 실측으로 닫는다.
#   ⓐ 같은 graph.json(6607n/8388e)에 cluster() 만 반복 실행한 결과가 **965·964·966·964**
#      였다. 즉 기본 경로의 Louvain 도 입력이 같아도 안정적이지 않다. 원인은 난수 시드가
#      아니라(networkx 폴백은 seed=42 로 이미 고정) **PYTHONHASHSEED 미고정**이다.
#   ⓑ 기본 경로가 평소 흔들리지 않았던 진짜 이유는 안정성이 아니라 **단락(short-circuit)**
#      이다 — `graphify/watch.py` 가 `same_topology` 면 `cluster(G)` 앞에서 반환하고
#      *"No code-graph topology changes detected; outputs left untouched"* 를 찍는다.
#      토폴로지가 바뀌는 순간 클러스터링이 돌고 커뮤니티 수가 무작위로 ±2 움직인다.
#   ⓒ 따라서 참인 트리거는 「코드 수정」이 아니라 **「graphify update 가 토폴로지 변화를
#      인정할 때」** 다. 2차 세션의 965→964 와 3차 세션의 무변화가 둘 다 이것으로 설명된다.
# 2026-08-17 부로 `scripts/graphify-py.sh` 가 PYTHONHASHSEED=0 을 고정하므로 이 흔들림은
# 제거됐다. 위 --cluster-only 제외는 그대로 둔다 — 고정 이전 산출물과의 비교 가능성과
# 「클러스터링만 돌린 결과를 승인 문서에 주입하지 않는다」는 규범이 독립적으로 유효하다.
if [ "$MODE" != "--cluster-only" ]; then
  echo "▶ 자기 측정 수치 주입 ..." >&2
  scripts/graphify-py.sh scripts/inject-self-metrics.py
else
  echo "▶ 자기 측정 수치 주입 건너뜀 (--cluster-only — Louvain 노이즈 유입 방지)" >&2
fi

echo "✓ graphify build + DIGEST 재생성 완료" >&2
