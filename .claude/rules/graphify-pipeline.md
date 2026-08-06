---
paths:
  - "graphify-out/**"
  - "scripts/graphify-*.sh"
---

# Graphify 파이프라인 규칙

**Scope**: `graphify-out/**`, `scripts/graphify-*.sh` 편집 또는 관련 작업 시 참조.

## 직접 열지 말 것 (대용량·바이너리성)

- `graphify-out/graph.json` (414 KB)
- `graphify-out/graph.html` (326 KB)
- `graphify-out/manifest.json`, `cost.json`
- `graphify-out/cache/*.json` (147 파일, 652 KB) — **절대 금지**
- `graphify-out/_logs/*`

> `.claudeignore` 는 Glob/Grep 결과를 차단하지 않으므로 **이 규칙으로 대체**.
> 파일 내용을 알아야 하면 우선 담당자에게 확인하거나, 스크립트로 파싱할 것.

## 읽기 순서

0. **(필수) 읽기 전 graph query 로 후보 좁히기** — 본문 파일을 열기 전에 먼저 실행:
   ```bash
   scripts/graphify-py.sh -m graphify query "<질문>" --budget 1500   # BFS, 넓은 컨텍스트
   scripts/graphify-py.sh -m graphify query "<질문>" --dfs --budget 800  # 특정 경로 추적
   ```
   - ⚠️ **GRAPH_DIGEST.md / GRAPH_REPORT.md / wiki 파일을 읽는 것은 query 명령 실행을 대체하지 않는다.** 첫 행동은 반드시 위 Bash `query` 명령이어야 한다 — 다이제스트 읽기로 시작하면 규칙 위반.
   - 반환된 `[파일:줄:커뮤니티]` 포인터 중 **핵심 source_file 만 선택적으로 읽고** 답한다 (전체 wiki/raw 스캔 금지).
   - 두 개념 사이 관계: `graphify path "A" "B"`, 한 노드 이웃: `graphify explain "X"`, 역방향 영향: `graphify affected "X"`.
   - 근거: JIT 경량 식별자 패턴(Anthropic) + aider repo-map 그래프 랭킹과 동형. 실측 ~158x 토큰 절감.
   - 주의: query 결과에 `output/`·`log.md`·`dev-logs/`·`.work-log/` 세션 산출물 노드가 섞일 수 있음 → wiki/raw/docs 노드 우선 채택.
1. `graphify-out/GRAPH_DIGEST.md` (≤80줄) — query 로 좁힌 뒤 전체 지형이 필요할 때
2. `graphify-out/GRAPH_REPORT.md` (474줄) — 드릴다운 필요 시에만
3. `wiki/index.md` 태그 프리페이스 → 해당 `wiki/concepts/`

## Python 호출

- **필수 경유**: `scripts/graphify-py.sh -c "<code>"` 또는 `-m graphify`
- **금지**: `python3`, `python` 직접 호출 (pipx venv 경로가 아님)

## 파이프라인 명령 (권장: wrapper 사용)

```bash
bash scripts/graphify-build.sh           # 증분 코드 재추출 + DIGEST 재생성
bash scripts/graphify-build.sh --cluster-only  # 클러스터링 재실행 + DIGEST 재생성
```

> **마지막 단계에서 `wiki/` 를 쓴다.** `inject-self-metrics.py` 가 자기 측정 문서(`self_measuring: true`, 현재 2건)의 `<!--m:이름-->값<!--/m-->` 마커에 현재 상태 수치를 주입한다. 따라서 빌드 후 `wiki/` diff 가 나올 수 있고, 그 커밋에는 `ALLOW_WIKI_EDIT=1` 이 필요하다. 값이 그대로면 파일을 쓰지 않으므로 평소에는 diff 가 0 이다. 규격은 `.claude/rules/wiki-concepts.md` §수치 주입.

전체(LLM) 재빌드가 필요하면 `/graphify` 스킬 사용. 상세 플래그는 `.claude/skills/graphify/references/advanced-subcommands.md` 참조.

## DIGEST 갱신 (단독 실행)

wrapper 없이 DIGEST 만 갱신할 때:

```bash
scripts/graphify-py.sh scripts/build-graph-digest.py
```

출력 ≤ 80 lines, god nodes / community hubs / topics 섹션 포함.

## 커밋 규칙

- `graphify-out/` 변경은 그래프 재빌드 결과물 → 보통 별도 커밋으로 분리
- `GRAPH_DIGEST.md` 는 build 후 재생성 스크립트 실행 결과를 함께 커밋
