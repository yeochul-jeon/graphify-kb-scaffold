## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- 코드/아키텍처/개념 질의의 **첫 행동(FIRST ACTION)** 은 반드시 Bash 로 `scripts/graphify-py.sh -m graphify query "<질문>" --budget 1500` 실행이다 (좁은 추적은 `--dfs --budget 800`). 그 출력의 source_file 목록에서 핵심 파일만 골라 읽고 답한다.
  - ⚠️ **파일을 읽는 행위(Read GRAPH_DIGEST.md / GRAPH_REPORT.md / wiki/*)는 query 명령 실행을 대체하지 않는다.** "다이제스트를 먼저 읽기"는 이 규칙 위반이다 — 반드시 query 명령(Bash)을 먼저 돌리고, 그 결과로 읽을 파일을 정한다.
  - 파일 목록·설정값 확인처럼 파일 간 관계가 필요 없는 작업은 이 규칙의 대상이 아니다 — `git ls-files`·Read 로 바로 확인한다.
  - query 결과로 좁힌 뒤 전역 지형이 추가로 필요할 때만 `graphify-out/GRAPH_DIGEST.md`(top god nodes·hubs) → 필요 시 `GRAPH_REPORT.md` 순으로 본다.
  - 보조 명령: `graphify path "A" "B"`, `explain "X"`, `affected "X"`. 상세·예외는 .claude/rules/graphify-pipeline.md 참조
- Navigate wiki/index.md (tag preface at top) to find relevant concepts; read raw files only when wiki is insufficient
- 루트 md (log.md, README.md) 는 질문이 해당 파일을 명시할 때만 읽는다; 일반 질의는 wiki/ 와 graphify-out/GRAPH_DIGEST.md 로 제한
- After modifying code files in this session, run `bash scripts/graphify-build.sh` to keep the graph and GRAPH_DIGEST.md current (wrapper: update + DIGEST regen)
- /graphify skill은 프로젝트 오버라이드(.claude/skills/graphify/SKILL.md)를 사용하며, python 호출은 scripts/graphify-py.sh 경유.
- 🔴 **정본 전용 규칙** — 아래 하위 항목은 `scripts/check-mirrors.py` 가 **있는** 저장소(graphify-kb 정본)에만 적용한다. 없는 저장소(scaffold 와 scaffold 로 만든 저장소)에서는 `.claude/skills/graphify/`·`.agents/`·`.codex/` 를 고치지 않고 아래 명령도 실행하지 않는다 — 엔진 수정은 graphify-kb 에서 하고, **graphify-kb 쪽에서** `scripts/sync-scaffold.sh --target <이 저장소 경로>` 를 실행해 이 저장소로 밀어 넣는다.
  - (**정본에서만**) graphify 스킬은 graphify-kb(정본)가 유일한 소스 오브 트루스다 (현재 upstream **0.9.40** 기반 포크). 수정은 `.claude/skills/graphify/SKILL.md` (core) 와 `.claude/skills/graphify/references/*.md` (8분할 lazy-load) 를 직접 편집. 🔴 **고친 뒤 반드시 Codex 용 사본 `.agents/skills/graphify/` 에 그대로 복사한다** — `python3 scripts/check-mirrors.py` 가 통과해야 한다. 이 검사가 종전 `diff -rq` 를 **흡수**했고(병행 실행 불필요), `.claude/settings.json` ↔ `.codex/hooks.json` 등 다른 미러 자산까지 함께 본다 — 매핑표에 선언되지 않은 파일이 `.agents/`·`.codex/` 에 있어도 실패한다(원장 `#74`). 실패 사례: 복사 없이 `.graphify_version` 만 올리면 사본이 거짓 버전을 들게 된다(2026-08-17 실제 발생·동기화).
  - scaffold 동기화 (**정본 graphify-kb 안에서만 실행**): `bash scripts/sync-scaffold.sh [--apply]` 로 템플릿 자산을 graphify-kb-scaffold에 단방향 재전파. 인자가 없으면 기본 타겟은 `../graphify-kb-scaffold` 이고, scaffold 로 만든 다른 저장소로 보낼 때만 `--target <경로>` 를 붙인다. 가이드: docs/guide/scaffold-sync.md
- ⚠️ **`graphify install` 실행 금지 (어떤 형태로도)** — 이 `AGENTS.md` 를 가진 저장소(graphify-kb·scaffold·scaffold 로 만든 저장소)는 모두 이미 설정돼 있다. `--project` 없이 실행하면 `~/.claude/skills/graphify/` 와 `~/.claude/CLAUDE.md` 등록 블록을 전역에 만들어 이 포크를 가리고, `--project` 로 실행하면 기존 `CLAUDE.md`·`.claude/settings.json` 을 덮어쓴다. 런타임 설치는 `bash scripts/graphify-bootstrap.sh`. 전역 차단 훅(docs/guide/graphify.md §재발 이력과 방어선)이 있어도 터미널 직접 실행은 못 막는다. 경위: docs/guide/graphify.md §전역 스코프 금지 · §이 프로젝트에서 사용하는 방법

## 위임 규율 (서브에이전트 · 모델 선택)

- **결정론적 검사는 위임하지 않는다** (exit code·JSON 키·파일 존재). 커맨드 출력 자체가 증거인데, 위임하면 「출력을 요약한 말」이 「출력」을 대체해 증거가 약해진다.
- **판단이 들어가는 검수는 위임한다** (중복·모호성·충돌). 내가 쓴 문안을 내가 검수하면 「내가 의도한 뜻」으로 읽어 모호성을 못 본다.
- 🔴 **제외 목록 없는 검증 위임 금지.** 이 저장소는 결론을 파일로 남긴다(계획서·인계·원장). 제외하지 않으면 서브에이전트가 기대값을 읽고 그대로 확인해주는 **에코**가 된다 — 깨진 눈가림은 없느니만 못한 확신을 준다.
- 🔴 **측정을 위임할 때는 돌릴 커맨드를 지정한다.** 지정할 수 없는 측정은 위임하지 않는다. 원장 `#83`(승인 큐 인용 횟수를 `grep -rl` 로 재서 16/27/6 — 정본 `scripts/approval-targets.py` 의 `citations()` 는 3/5/2)·`#82`(한 소비자만 보고 누락 3종 — 실제 25종) 둘 다 「어떻게 세는가」를 위임받은 쪽이 스스로 정한 데서 왔다.
- 모델 배치는 작업 성격을 따른다 — 파일 위치 찾기·텍스트 추출은 haiku / 문면 대조·중복 검수·구조 점검은 sonnet / **측정 정의 판단·규칙 설계·원장 판정은 위임하지 않는다.**
- ⚠️ **서브에이전트는 output style 을 상속하지 않는다** (fork 만 예외). 돌려받은 보고에는 이 저장소의 응답 규약(있다면 `.claude/output-styles/` 아래)이 걸려 있지 않으므로, **그 수치를 그대로 인용하지 말고 다시 잰다.**

## 현재 시각

- `UserPromptSubmit` 훅(`scripts/inject-current-time.sh`)이 매 턴 시작 시 "현재 시각(KST): ..." 를 컨텍스트에 주입한다. output 파일명(`YYYYMMDD-HHmm`)·frontmatter 날짜(`ingested_date`·`compiled_date` 등)가 필요하면 이 값을 쓰고 `Bash(date ...)` 를 다시 호출하지 않는다.
- 훅이 없거나 값이 안 보이는 예외 상황(구버전 세션 등)에서만 `TZ=Asia/Seoul date +"%Y%m%d-%H%M"` 로 폴백한다.

## AI Memory Boundaries

For memory-layer responsibilities, see `docs/guide/ai-memory-stack.md`. Keep this file focused on procedural rules.
