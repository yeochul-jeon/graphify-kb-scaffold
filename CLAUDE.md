## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- 코드/아키텍처/개념 질의의 **첫 행동(FIRST ACTION)** 은 반드시 Bash 로 `scripts/graphify-py.sh -m graphify query "<질문>" --budget 1500` 실행이다 (좁은 추적은 `--dfs --budget 800`). 그 출력의 source_file 목록에서 핵심 파일만 골라 읽고 답한다.
  - ⚠️ **파일을 읽는 행위(Read GRAPH_DIGEST.md / GRAPH_REPORT.md / wiki/*)는 query 명령 실행을 대체하지 않는다.** "다이제스트를 먼저 읽기"는 이 규칙 위반이다 — 반드시 query 명령(Bash)을 먼저 돌리고, 그 결과로 읽을 파일을 정한다.
  - query 결과로 좁힌 뒤 전역 지형이 추가로 필요할 때만 `graphify-out/GRAPH_DIGEST.md`(top god nodes·hubs) → 필요 시 `GRAPH_REPORT.md` 순으로 본다.
  - 보조 명령: `graphify path "A" "B"`, `explain "X"`, `affected "X"`. 상세·예외는 .claude/rules/graphify-pipeline.md 참조
- Navigate wiki/index.md (tag preface at top) to find relevant concepts; read raw files only when wiki is insufficient
- 루트 md (log.md, README.md) 는 질문이 해당 파일을 명시할 때만 읽는다; 일반 질의는 wiki/ 와 graphify-out/GRAPH_DIGEST.md 로 제한
- After modifying code files in this session, run `bash scripts/graphify-build.sh` to keep the graph and GRAPH_DIGEST.md current (wrapper: update + DIGEST regen)
- /graphify skill은 프로젝트 오버라이드(.claude/skills/graphify/SKILL.md)를 사용하며, python 호출은 scripts/graphify-py.sh 경유.
- graphify 스킬은 이 프로젝트가 유일한 소스 오브 트루스다. 수정은 `.claude/skills/graphify/SKILL.md` (core) 와 `.claude/skills/graphify/references/advanced-subcommands.md` (고급 서브커맨드) 를 직접 편집.
- scaffold 동기화: `bash scripts/sync-scaffold.sh [--apply]` 로 템플릿 자산을 graphify-kb-scaffold에 단방향 재전파. 가이드: docs/guide/scaffold-sync.md

## AI Memory Boundaries

For memory-layer responsibilities, see `docs/guide/ai-memory-stack.md`. Keep this file focused on procedural rules.
