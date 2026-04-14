# 아키텍처 구조

> graphify-kb가 무엇을, 어디서, 어떻게 하는지 한 장으로 설명합니다.
> 설치·실행 방법은 [docs/tutorial.md](tutorial.md)를 참고하세요.

---

## 한 문단 요약

`graphify-kb`는 **LLM을 "컴파일러"로 사용하는 개인 지식 베이스**입니다.
사람이 원본 자료를 `raw/`에 넣으면 Claude Code 슬래시 커맨드가 `wiki/`(구조화된 마크다운)로 변환하고,
질의응답 결과는 `output/`에 저장됩니다.
별도로, 외부 `graphify` 도구가 볼트 전체를 스캔해 `graphify-out/`에
인터랙티브 지식그래프와 커뮤니티 지도를 생성합니다.
Vector DB나 별도 서버 없이 **파일 시스템 + LLM 직접 읽기**만으로 동작합니다.

---

## 3가지 구성 요소

```
┌──────────────────────────────────────────────────────────────────┐
│  1. 볼트 (Vault)               사람 + LLM이 함께 관리           │
│     raw/ ──/compile──▶ wiki/ ──/ask──▶ output/                  │
├──────────────────────────────────────────────────────────────────┤
│  2. Claude Code 하네스 (Harness)   실행 엔진                     │
│     .claude/commands/*.md  ·  scripts/kb.sh                     │
├──────────────────────────────────────────────────────────────────┤
│  3. graphify 그래프             자동 생성 메타데이터              │
│     전체 볼트 스캔 ──▶ graphify-out/ (graph.html, GRAPH_REPORT) │
└──────────────────────────────────────────────────────────────────┘
```

### 1. 볼트 (Vault)

지식의 실제 내용이 담기는 파일 공간입니다.

| 디렉토리 | 역할 | 관리 주체 |
|---|---|---|
| `raw/` | 원본 자료 보관함 (URL, Notion, 직접 입력) | 사람이 `/ingest`로 추가 |
| `wiki/` | 구조화된 지식 베이스 (개념·주제·역참조) | LLM 전용 (직접 편집 비권장) |
| `output/` | Q&A 답변, 슬라이드, 차트 결과물 | LLM이 `/ask`·`/lint`로 생성 |
| `raw/Clippings/` | Obsidian Web Clipper로 가져온 원본 (`.graphifyignore`로 스캔 제외) | 자동 수집 |

**오염 방지 원칙**: `wiki/`는 LLM만 편집합니다. 사람이 직접 수정하면 다음 `/compile` 시 내용이 덮어쓰여질 수 있습니다. 수정이 필요하면 `raw/`에 내용을 추가한 뒤 `/compile`을 다시 실행하세요.

### 2. Claude Code 하네스

볼트를 조작하는 "실행 엔진"입니다. 이 저장소에는 Python/JS 코드가 없고, 모든 로직은 **프롬프트(`.claude/commands/*.md`) + 쉘 래퍼(`scripts/kb.sh`)**에 들어 있습니다.

| 컴포넌트 | 경로 | 역할 |
|---|---|---|
| 슬래시 커맨드 | `.claude/commands/*.md` | `/ingest`, `/compile`, `/ask`, `/lint` 등 7개 정의 |
| CLI 래퍼 | `scripts/kb.sh` | 일반 터미널에서 Claude CLI 프록시 |
| 행동 지침 | `CLAUDE.md` | LLM이 따를 규칙 (graphify 통합 포함) |
| 권한/훅 | `.claude/settings.json` | 허용 툴 + PreToolUse 자동 훅 |
| 스케일링 규칙 | `.claude/rules/scaling.md` | 규모별 탐색 전략 |

### 3. graphify 그래프

볼트 전체(raw, wiki, output, docs)를 스캔해 노드·엣지로 변환하는 **자동 생성 메타데이터**입니다. `raw/Clippings/`는 `.graphifyignore`로 스캔에서 제외됩니다.

| 산출물 | 경로 | 역할 |
|---|---|---|
| 인터랙티브 뷰 | `graphify-out/graph.html` | 브라우저에서 볼 수 있는 지식그래프 |
| 커뮤니티 지도 | `graphify-out/GRAPH_REPORT.md` | god nodes, 22개 커뮤니티 요약 (LLM이 먼저 읽음) |
| 전체 그래프 | `graphify-out/graph.json` | GraphRAG·외부 도구 연동용 |
| 증분 추적 | `graphify-out/manifest.json` | mtime 기반 변경 파일만 재처리 |
| 비용 기록 | `graphify-out/cost.json` | LLM 호출 비용 추적 |
| 응답 캐시 | `graphify-out/cache/*.json` | 동일 파일 재처리 방지 |

> `graphify`는 이 저장소에 포함된 코드가 **아닙니다**. `~/.claude/skills/graphify/SKILL.md`가 관리하는 외부 `graphifyy` pip 패키지입니다.

---

## 디렉토리 전체 트리

```
graphify-kb/
├── raw/                        ← 원본 자료 (사람 + Web Clipper)
│   ├── _templates/             ← 새 raw 파일 템플릿
│   ├── attachments/            ← 이미지 등 첨부 파일
│   ├── sessions/               ← /capture 결과 (대화 인사이트)
│   └── Clippings/              ← Web Clipper 원본 (.graphifyignore 제외)
│
├── wiki/                       ← LLM 전용 지식 베이스 (직접 편집 비권장)
│   ├── index.md                ← 탐색 허브 (61 개념, 6 주제)
│   ├── backlinks.md            ← 개념 간 역참조 맵 (자동 생성)
│   ├── concepts/               ← 개별 개념 파일 (61개)
│   ├── topics/                 ← 상위 주제 파일 (6개)
│   └── _meta/
│       ├── compile-log.md      ← 컴파일 이력
│       └── suggested-investigations.md  ← /lint 제안 탐구 주제
│
├── output/                     ← /ask, /lint 결과물
│   ├── answer-YYYYMMDD-HHmm.md
│   ├── slides-*.marp.md
│   ├── chart-*.py
│   └── lint-report-YYYYMMDD.md
│
├── graphify-out/               ← 외부 graphify 도구 자동 생성 (수동 편집 금지)
│   ├── graph.html              ← PyVis 인터랙티브 시각화
│   ├── GRAPH_REPORT.md         ← 커뮤니티/god nodes 요약
│   ├── graph.json              ← 노드·엣지 전체
│   ├── manifest.json           ← mtime 증분 추적
│   ├── cost.json               ← LLM 호출 비용
│   └── cache/                  ← LLM 응답 해시 캐시
│
├── docs/                       ← 사람용 문서
│   ├── architecture.md         ← 이 파일
│   ├── tutorial.md             ← 초보자 단계별 튜토리얼
│   ├── obsidian-setup.md       ← Obsidian + Web Clipper 연동
│   ├── improvement-plan.md     ← 기획·분석 (내부용)
│   ├── guide/
│   │   ├── commands.md         ← 슬래시 커맨드 레퍼런스
│   │   ├── graphify.md         ← 지식그래프 통합 가이드
│   │   └── troubleshooting.md  ← 초보자 막힘 해결
│   └── superpowers/            ← 내부 설계 스펙
│
├── scripts/
│   ├── kb.sh                   ← CLI 래퍼 (status/ingest/compile/ask/lint)
│   └── setup-hooks.sh          ← wiki/ 편집 경고 git hook 설치
│
├── .claude/
│   ├── commands/               ← 슬래시 커맨드 7개 (ingest/compile/ask/lint/capture/review/dev-log)
│   ├── rules/scaling.md        ← 규모별 탐색 전략
│   └── settings.json           ← 허용 툴 + PreToolUse 훅
│
├── logs/                       ← 일자별 DEV_LOG
├── .githooks/                  ← pre-commit hook 원본
├── .obsidian/                  ← Obsidian 볼트 설정
├── CLAUDE.md                   ← LLM 행동 지침 (graphify 규칙 포함)
├── PLAN.md                     ← 프로젝트 설계·로드맵
├── README.md                   ← 프로젝트 개요 + 빠른 시작
└── log.md                      ← 전체 작업 이력
```

---

## 데이터 플로우

```
[외부 자료]  URL / Notion / GitHub / 직접 입력
     │
     │  /ingest
     ▼
  raw/*.md          (frontmatter: compiled: false)
     │
     │  /compile
     ▼
  wiki/concepts/*.md
  wiki/topics/*.md
  wiki/index.md        ←──────────────┐
  wiki/backlinks.md                   │  피드백 루프
     │                                │  (새 인사이트 발견)
     │  /ask [--slides|--chart|--html] │
     ▼                                │
  output/answer-*.md  ────────────────┘
  output/slides-*.md
  output/chart-*.py

     │  /review
     ▼
  wiki/ (승격된 인사이트 반영)

     │  /lint [--fix]
     ▼
  output/lint-report-*.md
  wiki/ (자동 수정)


[볼트 전체 (raw + wiki + output + docs)]  ※ raw/Clippings/는 .graphifyignore 제외
     │
     │  /graphify  (외부 graphify CLI)
     ▼
  graphify-out/graph.html        ← 브라우저 시각화
  graphify-out/GRAPH_REPORT.md   ← LLM이 탐색 전 먼저 읽음
  graphify-out/graph.json        ← GraphRAG 연동
  graphify-out/manifest.json     ← 증분 재빌드용 mtime 추적
```

---

## 외부 의존성 맵

| 도구 | 필수 여부 | 용도 | 설치 방법 |
|---|---|---|---|
| **Claude Code** | 필수 | 슬래시 커맨드 런타임 | [공식 설치 가이드](https://docs.anthropic.com/ko/docs/claude-code) |
| **Git** | 필수 | 버전 관리, pre-commit hook | 시스템 기본 |
| **graphifyy** (pip) | graphify 사용 시 필수 | 지식그래프 생성 | SKILL.md가 자동 설치 |
| **Python 3** | graphify 사용 시 필수 | graphifyy 런타임 | 시스템 기본 또는 Homebrew |
| **Obsidian** | 선택 | wiki/ 그래프 뷰, Web Clipper | [obsidian.md](https://obsidian.md) |
| **Marp CLI** | 선택 | `/ask --slides` 슬라이드 출력 | `npm install -g @marp-team/marp-cli` |
| **matplotlib** | 선택 | `/ask --chart` 차트 출력 | `pip3 install matplotlib` |
| **Notion MCP** | 선택 | `/ingest` Notion 페이지 자동 수집 | Claude Code MCP 설정 |

---

## 핵심 파일 레퍼런스

| 파일 | 라인 | 역할 |
|---|---|---|
| `CLAUDE.md` | L4–9 | graphify 재빌드 명령 + GRAPH_REPORT.md 우선 읽기 규칙 |
| `.claude/settings.json` | PreToolUse | Glob/Grep 호출 시 GRAPH_REPORT.md 읽기 훅 |
| `.claude/rules/scaling.md` | 전체 | 100/500/500+ 아티클 규모별 탐색 전략 |
| `scripts/kb.sh` | L28– | 슬래시 커맨드 CLI 프록시 구현 |
| `.claude/commands/ingest.md` | 전체 | `/ingest` 처리 로직 (프롬프트) |
| `.claude/commands/compile.md` | 전체 | raw → wiki 변환 로직 |
| `.claude/commands/ask.md` | 전체 | wiki 기반 Q&A 로직 |
| `graphify-out/manifest.json` | 전체 | mtime 기반 증분 재빌드 추적 |
| `graphify-out/GRAPH_REPORT.md` | 전체 | 372 노드 · 644 엣지 · 22 커뮤니티 현황 |

---

## 설계 원칙 3가지

### 1. 오염 방지 — wiki는 LLM 전용

`wiki/`는 `/compile`이 관리하는 "검증된 지식 공간"입니다.
사람이 직접 편집하면 다음 컴파일 때 내용이 덮어쓰여집니다.
pre-commit hook이 `wiki/` 파일이 staged되면 경고를 표시합니다.
사람의 수정은 반드시 `raw/`를 경유해야 합니다.

### 2. 증분 재빌드 — 비용 절약

`graphify-out/manifest.json`이 각 파일의 수정 시간(mtime)을 기록합니다.
`/graphify . --update`는 변경된 파일만 재처리합니다.
`graphify-out/cache/*.json`은 동일 파일의 LLM 응답을 캐시해 중복 호출을 방지합니다.

### 3. 컨텍스트 절약 — index.md 우선 읽기

Claude가 질문에 답할 때 `wiki/` 전체를 읽지 않습니다.
`.claude/settings.json`의 PreToolUse 훅이 Glob/Grep 호출 시
`graphify-out/GRAPH_REPORT.md`를 먼저 읽도록 유도합니다.
탐색 순서: `GRAPH_REPORT.md` → `wiki/index.md` → `wiki/topics/` → 관련 `wiki/concepts/`

---

## 확장성 (스케일링)

`.claude/rules/scaling.md` 기준의 규모별 권장 전략:

| 규모 | 아티클 수 | 전략 |
|---|---|---|
| **소규모** | ~100개 | `wiki/index.md` 먼저 읽기 → 관련 파일만 선택적 읽기 |
| **중규모** | 100~500개 | 태그로 후보 좁히기 → 최대 10개 파일만 읽기. `topics/` 우선 탐색 |
| **대규모** | 500개 이상 | `index.md` + `backlinks.md` + Grep 3단계만으로 답변 시도. 벡터 DB 도입 권장 |

현재 이 저장소: **61 concepts · 6 topics** (2026-04-13 기준) — 소규모 단계.

---

## 관련 문서

- [docs/tutorial.md](tutorial.md) — 설치부터 첫 실행까지 단계별 따라하기
- [docs/guide/commands.md](guide/commands.md) — 슬래시 커맨드 전체 레퍼런스
- [docs/guide/graphify.md](guide/graphify.md) — 지식그래프 통합 상세 가이드
- [docs/guide/troubleshooting.md](guide/troubleshooting.md) — 막힘 해결
- [PLAN.md](../PLAN.md) — 시스템 설계 결정 및 미래 로드맵
