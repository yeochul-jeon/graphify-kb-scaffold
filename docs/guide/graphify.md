# 지식그래프 통합 가이드 (`/graphify`)

> 이 가이드는 `graphify-out/` 지식그래프가 무엇이며, 어떻게 만들고 활용하는지 설명합니다.
> 슬래시 커맨드 전체 목록은 [docs/guide/commands.md](commands.md)를 참고하세요.

---

## 설치

### 기본 설치 (권장: pipx)

```bash
pipx install graphifyy          # pipx 없으면: brew install pipx
# 또는 pip (macOS Sonoma 이상에서 PEP 668 오류 시 → troubleshooting.md 3번)
pip install graphifyy
```

### 선택 extras

| extras | 설치 명령 | 활성화 기능 |
|---|---|---|
| `[video]` | `pipx install 'graphifyy[video]'` | MP4 · MOV · MKV · WebM · AVI · MP3 · WAV · M4A · OGG · YouTube URL |
| `[office]` | `pipx install 'graphifyy[office]'` | DOCX · XLSX |

### 이 프로젝트에서 사용하는 방법

`bash scripts/graphify-bootstrap.sh` 를 실행하면 `graphifyy` 설치 + Python 인터프리터 경로 감지 (`graphify-out/.graphify_python`)를 한 번에 처리합니다.

> **주의: `graphify install` / `graphify claude install` 실행 금지**  
> 상위 graphify v0.4.13+는 설치 후 `graphify install` 명령으로 `CLAUDE.md` / `.claude/settings.json` 에 훅을 자동 주입합니다.  
> 이 프로젝트는 이미 커스텀 설정을 보유하므로, 위 명령을 실행하면 **기존 파일이 덮어써집니다**.  
> 신규 저장소에서 graphify를 처음 통합할 때만 사용하세요.

---

## graphify란?

**graphify**는 볼트 전체 파일을 읽어 **노드·엣지 지식그래프**로 변환하는 외부 도구입니다.

> 중요: graphify는 이 저장소에 포함된 코드가 아닙니다. `~/.claude/skills/graphify/SKILL.md`가 관리하는 외부 `graphifyy` pip 패키지 (v0.4.13+, MIT 라이선스)입니다. 설치는 `bash scripts/graphify-bootstrap.sh` 로 처리합니다.

### 왜 필요한가?

| 볼트 규모 | graphify 없이 | graphify 있으면 |
|---|---|---|
| ~10개 파일 | wiki/index.md 한 번 읽으면 충분 | 큰 차이 없음 |
| ~60개 파일 | 관련 파일을 일일이 찾아야 함 | god nodes/communities로 핵심 파악 |
| 100개+ 파일 | Claude가 전체 컨텍스트를 읽다가 한계 도달 | graphify query로 관련 source_file을 좁힌 뒤 필요 시 GRAPH_REPORT.md로 전체 지도 파악 |

이 볼트가 지금 어느 구간인지, 노드·엣지·커뮤니티가 몇 개인지는 `graphify-out/GRAPH_REPORT.md` 를 직접 본다. **수치는 여기에 옮겨 적지 않는다** — 재빌드마다 바뀌므로 사본은 반드시 낡는다 (`docs/architecture.md` 산출물 표와 같은 규율).

---

## 출력 산출물

모든 산출물은 `graphify-out/` 에 저장됩니다.

| 파일 | 역할 |
|---|---|
| `graph.html` | 브라우저에서 볼 수 있는 인터랙티브 지식그래프 |
| `GRAPH_REPORT.md` | god nodes · 커뮤니티 요약 · Knowledge Gaps (query 결과 이후 전역 지형이 필요할 때 확인) |
| `graph.json` | 노드·엣지 전체 데이터 (GraphRAG · 외부 도구 연동) |
| `cache/*.json` | SHA256 기반 LLM 응답 캐시 (중복 호출 방지) |
| `transcripts/` | 영상·오디오 파일 전사(transcription) 캐시 (`[video]` extras 사용 시) |
| `.graphify_python` | 인터프리터 경로 캐시 (`scripts/graphify-bootstrap.sh` 생성) |

### `graph.html` — 인터랙티브 시각화

브라우저에서 볼 수 있는 PyVis 기반 지식그래프입니다.

```bash
open graphify-out/graph.html
```

- 노드를 클릭하면 연결된 개념이 강조됩니다.
- 드래그로 레이아웃을 조정할 수 있습니다.
- 연결이 많은 god nodes가 중앙에 위치합니다.

### 2. `GRAPH_REPORT.md` — LLM + 사람 읽기용 요약

가장 자주 참조하는 파일입니다. 다음 내용을 담고 있습니다:

- **God Nodes** (연결 수 기준 핵심 추상 10개)
- **22개 Community 목록** (코드 클러스터별 설명 + 구성 노드)
- **Knowledge Gaps** (고립된 노드, 저응집 커뮤니티)
- **Surprising Connections** (예상치 못한 연결 관계)
- **Suggested Questions** (그래프가 답하기 좋은 질문)

```bash
# query 결과로 전역 지형이 더 필요할 때 확인한다
cat graphify-out/GRAPH_REPORT.md
```

### 3. `graph.json` — 기계 읽기용

GraphRAG, 외부 도구, 커스텀 스크립트와 연동할 때 사용합니다.
모든 노드와 엣지의 메타데이터(파일 경로, 신뢰도, 관계 유형)가 담겨 있습니다.

---

## 최초 빌드

Claude Code 세션에서:

```
/graphify .
```

또는:

```
/graphify
```

처음 실행 전 준비:
1. `bash scripts/graphify-bootstrap.sh` — `graphifyy` 설치 + 인터프리터 경로 저장 (Python 3.10+ 필요).
2. `/graphify .` 실행 시 볼트 전체 파일을 스캔합니다 (시간이 다소 걸릴 수 있습니다).
3. `graphify-out/` 디렉토리에 산출물이 생성됩니다 (아래 "출력 산출물" 참고).

완료 후 확인:

```bash
open graphify-out/graph.html
```

---

## 재빌드 방법

파일을 추가하거나 수정한 뒤에는 그래프를 업데이트해야 합니다.

### 방법 1: 증분 재빌드 (권장)

변경된 파일만 처리해 빠르게 업데이트합니다.

```
/graphify . --update
```

또는 CLAUDE.md에 정의된 Python 직접 호출:

```bash
python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"
```

> CLAUDE.md 규칙: 코드 파일을 수정한 뒤에는 이 명령을 실행해 그래프를 최신 상태로 유지하세요.

### 방법 2: 전체 재빌드

캐시를 무시하고 처음부터 다시 빌드합니다.

```
/graphify . --wiki
```

### 어떤 방법을 언제?

| 상황 | 방법 |
|---|---|
| 파일 몇 개 추가/수정 | 증분 재빌드 (`--update`) |
| 대량 파일 변경 (50개+) | 전체 재빌드 (`--wiki`) |
| 그래프 이상하게 느껴질 때 | 전체 재빌드 |
| 코드 수정 후 CLAUDE.md 지시 | Python 직접 호출 |

---

## /graphify 하위 명령

### `/graphify add <URL>`

URL 자료를 바로 그래프에 추가합니다.

```
/graphify add https://example.com/article
```

### `/graphify query "질문"`

그래프 구조 기반으로 질의합니다.

```
/graphify query "Circuit Breaker와 가장 연결된 개념은?"
```

### `/graphify path A B`

두 노드 사이의 최단 경로를 찾습니다.

```
/graphify path "kafka" "circuit-breaker"
```

### `/graphify explain <노드명>`

특정 노드의 연결 관계와 커뮤니티 역할을 설명합니다.

```
/graphify explain "Claude Code Harness"
```

### `--watch` 모드

파일 변경을 감지해 자동으로 증분 재빌드합니다.

```
/graphify . --watch
```

### `--obsidian` 모드

Obsidian Graph View와 호환되는 형식으로 출력합니다.

```
/graphify . --obsidian
```

### `--mode deep`

심층 분석 모드로 빌드합니다. LLM 호출 횟수가 증가해 더 세밀한 관계를 추출합니다 (비용 주의).

```
/graphify . --mode deep
```

### 내보내기 플래그

```
/graphify . --svg       ← SVG 그래프 이미지 내보내기
/graphify . --graphml   ← GraphML 형식 (Gephi, yEd 등 외부 도구 호환)
/graphify . --neo4j     ← Neo4j 가져오기 파일 생성
```

---

## 지원 입력 타입

graphify는 아래 파일 형식을 모두 그래프 노드로 처리합니다.

| 카테고리 | 형식 |
|---|---|
| **코드** | Python, TypeScript, JavaScript, Go, Rust, Java, C/C++, Ruby, C#, Kotlin, Scala, PHP, Swift, Dart, Lua, Zig 등 20+ 언어 |
| **문서** | Markdown, 텍스트, RST, DOCX, XLSX, PDF |
| **이미지** | PNG, JPG, WebP, GIF |
| **영상·오디오** | MP4, MOV, MKV, WebM, AVI, M4V, MP3, WAV, M4A, OGG (`[video]` extras 필요) |
| **URL** | YouTube URL (`[video]` extras 필요) |

---

## CLAUDE.md 자동 통합

`CLAUDE.md`에는 두 가지 graphify 관련 규칙이 있습니다:

**규칙 1**: 아키텍처·코드베이스·개념 질문 전에 `scripts/graphify-py.sh -m graphify query "<질문>" --budget 1500`을 먼저 실행합니다.

**규칙 2**: `.claude/settings.json`의 PreToolUse 훅이 Glob/Grep 호출 시 query-first 탐색을 자동 유도합니다.

탐색 순서: `graphify query` → query 결과의 `source_file` → 필요 시 `wiki/index.md` 태그 프리페이스 → 필요 시 `graphify-out/GRAPH_DIGEST.md` → 최후에 `GRAPH_REPORT.md`.

---

## 비용 관리

### `graphify-out/cost.json`

각 빌드 세션의 LLM 호출 비용을 기록합니다.

```bash
cat graphify-out/cost.json
```

### `graphify-out/cache/`

동일 파일의 LLM 응답을 해시 기반으로 캐시합니다.
파일 내용이 변경되지 않으면 캐시를 재사용하므로 비용이 들지 않습니다.
현재 캐시 파일 수: ~140개 (`graphify-out/cache/*.json`)

### 비용 절약 팁

- 전체 재빌드보다 증분 재빌드(`--update`)를 우선 사용하세요.
- 여러 파일을 수정한 뒤 한 번에 재빌드하세요 (파일마다 재빌드하지 않고).
- `--watch` 모드는 편리하지만 빈번한 저장 시 비용이 누적될 수 있습니다.

---

## 볼트 그래프 상태는 어디서 보나

🔴 **수치를 이 문서에 옮겨 적지 않는다.** 재빌드마다 바뀌므로 사본은 반드시 낡는다 — 실제로 이 절은 2026-04-14 값(`372 노드 · 644 엣지 · 22 커뮤니티` · `138 파일`)을 4개월간 들고 있었고, 2026-08-17 시점 실측은 노드가 **17배 이상**이었다.

`graphify-out/GRAPH_REPORT.md` 를 직접 본다. 거기 실리는 항목은 이렇다:

- 처리한 파일 수 · 단어 수 (`## Corpus Check`)
- 노드 · 엣지 · 커뮤니티 수 (`## Summary`)
- Top God Nodes (연결이 가장 많은 노드)
- Knowledge Gaps (고립 노드 — 연결 개선 여지)

빠른 요약만 필요하면 `graphify-out/GRAPH_DIGEST.md` (≤80줄).

---

## 관련 문서

- [docs/architecture.md](../architecture.md) — 전체 시스템 구조에서 graphify의 위치
- [docs/guide/commands.md](commands.md) — 전체 슬래시 커맨드 레퍼런스
- [docs/guide/troubleshooting.md](troubleshooting.md) — graphify 설치·실행 오류 해결
- [graphify-out/GRAPH_REPORT.md](../../graphify-out/GRAPH_REPORT.md) — 현재 그래프 상태 (자동 생성)

---

## 업스트림 레퍼런스

이 프로젝트가 사용하는 graphify 상위 소스 (스킬 포크 기준 v0.8.39, MIT 라이선스, 2026-08-10 기준):

| 링크 | 내용 |
|---|---|
| [github.com/safishamsi/graphify](https://github.com/safishamsi/graphify) | 공식 GitHub 저장소 (README · CHANGELOG · Issue) |
| [pypi.org/project/graphifyy/](https://pypi.org/project/graphifyy/) | PyPI 패키지 (패키지명 `graphifyy`, double-y) |
| [graphify.net/kr/](https://graphify.net/kr/) | 공식 홈페이지 (한국어) |
| [github.com/sponsors/safishamsi](https://github.com/sponsors/safishamsi) | 후원 |

> graphify 스킬 수정 시: `.claude/skills/graphify/SKILL.md` (core) 와 `.claude/skills/graphify/references/*.md` (8분할 lazy-load) 를 직접 편집하세요.

## 전역 스코프 금지

graphify 스킬은 **repo-local 사본만** 쓴다. 사용처 3곳은 각자 사본을 갖는다:
`graphify-kb`(포크) · `graphify-kb-scaffold`(sync 대상) · `NextStyle/wiki`(바닐라).

### 왜 금지인가

`graphify install` 을 `--project` 없이 실행하면 CLI 가 두 가지를 **전역에** 만든다
(`graphify/__main__.py:656-657`):

| 산출물 | 영향 |
|---|---|
| `~/.claude/skills/graphify/` | graphify 를 안 쓰는 **모든 프로젝트**에 스킬이 로드됨 |
| `~/.claude/CLAUDE.md` 등록 블록 | 하드코딩된 전역 경로가 모든 세션 컨텍스트에 주입됨 |

게다가 전역 사본이 프로젝트 오버라이드를 **가린다**. 2026-08-10 조사에서
이 프로젝트가 자기 포크(0.4.12)가 아니라 전역(0.8.39)으로 돌고 있던 것이 확인됐다.

### 재발 이력과 방어선

2026-04-16 커밋 `8093488` 이 전역 스킬·CLAUDE.md 블록을 제거했으나 6월에 되살아났다.
원인 사슬: CLI 가 `install`/`uninstall`/`hook-check` 를 뺀 **모든 명령**에서 버전을 대조해
`Run 'graphify install' to update` 경고를 띄운다(`__main__.py:2091`) → 프로젝트 규칙이
강제하는 `graphify-build.sh`(내부적으로 `graphify update`)마다 경고가 뜸 → 지시대로 실행 → 전역 부활.

방어선 3중:
1. **원인 제거** — 포크를 upstream 과 같은 버전으로 유지 (현재 0.8.39). 버전이 맞으면 경고가 안 뜬다.
2. **차단** — 전역 `~/.claude/hooks/block-global-graphify-install.sh` (PreToolUse/Bash).
   `--project`·`--help`·`-h` 없는 `graphify install` 을 exit 2 로 막는다.
3. **탐지** — 전역 SessionStart 훅이 `~/.claude/skills/graphify` 존재 시 경고한다.
   터미널에서 직접 친 경우처럼 (2)가 못 보는 경로를 잡는다.

### upstream 버전 추적 · 재포크 절차

`regen-graphify-skill.sh` 는 `8093488` 에서 삭제됐다. 수동 절차:

```bash
graphify --version                     # upstream 현재 버전
cat .claude/skills/graphify/.graphify_version   # 포크 기준 버전
```

다르면 재포크한다 — upstream 원본을 가져와 **델타 3종만** 재적용:

1. **Step 1 탐지 블록** → `bash scripts/graphify-bootstrap.sh INPUT_PATH` 한 줄.
   Interpreter guard 블록도 `[ -f graphify-out/.graphify_python ] || bash scripts/graphify-bootstrap.sh`.
2. **인터프리터 호출** → `$(cat graphify-out/.graphify_python)` 및 bare `python3` 을
   `scripts/graphify-py.sh` 로 치환.
3. **잔여 `$(...)`** 제거 — `PROJECT_ROOT=$(cat ...)`, `LOCAL_PATH=$(graphify clone ...)` 처럼
   값을 셸 변수에 담는 곳은 "출력해서 읽고 직접 치환" 방식으로 바꾼다.

> 델타의 목적은 하나다: `$(...)` command substitution 이 Claude Code 승인 프롬프트를
> 유발하므로 치환을 스킬 밖(스크립트 내부)에서 처리한다.

**재포크 사후 검사** (눈으로 넘기지 말 것):

```bash
grep -rn '\$(' .claude/skills/graphify/SKILL.md .claude/skills/graphify/references/*.md
#   → 실행 블록 내 0건. 산문 설명(`$(...)` 표기)만 남아야 한다.
grep -rn 'python3\|\$PYTHON' .claude/skills/graphify/SKILL.md .claude/skills/graphify/references/*.md
#   → 2건만 정상: SKILL.md 의 치환 규약 설명 1건,
#      references/exports.md 의 Claude Desktop MCP 설정 JSON 1건
#      (외부 앱이 읽는 설정이라 상대경로 래퍼로 바꾸면 안 된다)
python3 scripts/check-mirrors.py
#   → exit 0. Codex 용 사본 복사가 실제로 됐는지 보는 검사다.
#      2026-08-19 신설. 종전 `diff -rq .agents/skills/graphify/ .claude/skills/graphify/`
#      를 흡수했으므로 그것을 따로 돌릴 필요는 없다.
#      같은 실행이 `.claude/settings.json` ↔ `.codex/hooks.json` 투영도 대조하고,
#      매핑표에 선언되지 않은 미러 자산이 있으면 실패한다 (원장 #74).
```

마지막으로 `.graphify_version` 을 새 버전으로 갱신하고,
`.agents/skills/graphify/` (Codex 용 사본) 에 같은 내용을 복사한 뒤
`bash scripts/sync-scaffold.sh --apply` 로 scaffold 에 전파한다.

> 🔴 **복사와 버전 스탬프의 순서를 붙여 두지 말 것 — 갈리면 사본이 거짓 버전을 든다.**
> 0.9.40 재포크(`1f814aa`)가 `.claude/` 만 고치고 이 복사 단계를 건너뛴 뒤,
> 후속 커밋(`98910f1`)이 **양쪽 `.graphify_version` 을 함께 0.9.40 으로 올렸다.**
> 그래서 `.agents/skills/graphify/` 는 **0.9.40 을 표방하면서 내용은 재포크 직전
> (`1f814aa~1`) 상태로 4개 파일이 동결**돼 있었다 — SKILL.md·`extraction-spec`·`query`·
> `update` 가 `1f814aa~1` 의 `.claude/` 판과 **바이트 동일**임을 md5 로 확인했다(2026-08-17).
> 누락분에는 시맨틱 캐시 `prompt_file`(SPEC_PATH) 귀속, `check_semantic_cache`/
> `save_semantic_cache` 의 `root=`·`allowed_source_files=`, 빈 그래프·축소 가드가 들어 있어
> **Codex 쪽이 그 사본으로 돌면 캐시를 엉뚱한 자리에 쓰고 가드 없이 산출물을 덮어쓴다.**
> 위 `scripts/check-mirrors.py` 가 이 상태를 잡는 검사이며, 그래서 사후 검사 블록 안에 있다
> (2026-08-19 이전에는 `diff -rq` 였고, 그 검사는 스킬 폴더 한 쌍만 봤다 — 원장 `#74`).
> 재포크 생성 시점(`4e84e32`)의 의도적 델타는 `Claude`→`Codex` 낱말 치환 6곳뿐이었고
> 그것도 `4aa0ec5` 의 references 재편에서 이미 사라졌다 — **지금 규범은 그대로 복사다.**
