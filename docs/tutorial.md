# 시작하기 — 초보자 튜토리얼

처음 사용하는 분을 위한 단계별 안내입니다.
설치부터 첫 번째 자료 수집, 질문, 품질 점검까지 직접 따라해보세요.

---

## 1. 이 프로젝트가 뭔가요?

**LLM(Claude)을 "컴파일러"처럼 사용하는 개인 지식 베이스**입니다.

코드 컴파일러가 소스 코드를 읽어 실행 파일을 만들듯,
Claude가 여러분이 모아둔 원본 자료(`raw/`)를 읽어 구조화된 위키(`wiki/`)로 변환합니다.
Vector DB나 별도 서버 없이 **파일 시스템 + Claude의 직접 읽기**만으로 동작합니다.

| 구분 | 기존 노트앱 (Notion, Obsidian) | 이 프로젝트 |
|------|-------------------------------|------------|
| 작성자 | 사람이 직접 정리 | Claude가 자동 구조화 |
| 검색 | 키워드 또는 임베딩 | Claude가 파일 직접 읽기 |
| 연결 | 수동 링크/태그 | 자동 backlink 생성 |

---

## 2. 사전 준비

### 필수

- **Claude Code** — [설치 방법](https://docs.anthropic.com/ko/docs/claude-code)
  - 터미널에서 `claude --version` 으로 설치 확인
- **Git** — `git --version` 으로 확인

### 선택 (기능 확장용)

| 도구 | 용도 | 설치 |
|------|------|------|
| Obsidian | wiki/ 파일을 그래프로 시각화 | [obsidian.md](https://obsidian.md) |
| Marp CLI | `/ask --slides` 슬라이드 출력 | `npm install -g @marp-team/marp-cli` |
| matplotlib | `/ask --chart` 차트 출력 | `pip3 install matplotlib` |

---

## 3. 설치 & 초기 설정

### ✅ Clone 직후 체크리스트

새로 clone한 경우 아래 순서대로 실행하면 누락 없이 시작할 수 있습니다.

- [ ] **1. 저장소 클론 & 이동** — `git clone https://github.com/yeochul-jeon/graphify-kb.git && cd graphify-kb`
- [ ] **2. Git hooks 활성화** — `bash scripts/setup-hooks.sh` (`wiki/` 직접 편집 보호)
- [ ] **3. Claude Code 실행 확인** — `claude --version` 으로 설치 확인 후 이 폴더에서 `claude` 실행
- [ ] **4. 지식그래프 생성** — Claude Code 세션에서 `/graphify .` 실행
  > `graphify-out/`은 `.gitignore`되어 있어 첫 clone 시 비어 있습니다. 완료 후 `open graphify-out/graph.html`로 확인하세요.
- [ ] **5. 상태 확인** — `./scripts/kb.sh status` 로 볼트 통계 확인

> 5단계까지 완료하면 아래 섹션 4부터 실제 자료 수집을 시작할 수 있습니다.

---

### 상세 단계

```bash
# 저장소 클론
git clone https://github.com/yeochul-jeon/graphify-kb.git
cd graphify-kb

# Git hooks 활성화 (wiki/ 직접 편집 방지 경고)
bash scripts/setup-hooks.sh
```

### 디렉토리 구조 한눈에 보기

```
graphify-kb/
├── raw/        ← 원본 자료 보관함 (여기에 자료를 넣어요)
├── wiki/       ← Claude가 정리한 지식 베이스 (Claude 전용, 직접 편집 비권장)
├── output/     ← Q&A 답변, 슬라이드, 차트 결과물
├── log.md      ← 전체 요약 타임라인
└── .work-log/  ← 상세 작업 로그 (DEV_LOG_YYYYMMDD.md)
```

> **비유**: `raw/`는 재료 창고, `wiki/`는 Claude가 만든 정리된 레시피북, `output/`은 요리 결과물입니다.

---

## 4. 첫 번째 자료 수집 (`/ingest`)

Claude Code 터미널에서 다음을 입력하세요:

```
/ingest https://example.com/some-article
```

### 지원하는 입력 유형

| 유형 | 예시 |
|------|------|
| 웹 URL | `/ingest https://news.ycombinator.com/item?id=...` |
| Notion 페이지 | `/ingest https://www.notion.so/your-page-id` |
| GitHub 저장소 | `/ingest https://github.com/owner/repo` |
| 직접 텍스트 | `/ingest` (인수 없이 실행하면 내용 입력 요청) |

### 실행 후 확인할 것

`raw/` 폴더에 새 파일이 생겼는지 확인:

```bash
./scripts/kb.sh status
# 출력 예시:
# raw/ 파일:  1 개 (미컴파일: 1 개)
# wiki 개념:  0 개
```

생성된 raw 파일의 상단에는 아래와 같은 정보가 자동으로 추가됩니다:

```yaml
---
title: 아티클 제목
source_url: https://...
ingested_date: 2026-04-06
compiled: false       ← 아직 wiki로 변환 안 됨
compiled_date: null
---
```

---

## 5. Wiki로 컴파일하기 (`/compile`)

```
/compile
```

Claude가 `raw/`의 미컴파일 파일을 읽고 개념을 추출해 `wiki/`에 정리합니다.

### 실행 후 확인할 것

```bash
./scripts/kb.sh status
# 출력 예시:
# raw/ 파일:  1 개 (미컴파일: 0 개)  ← compiled: true로 변경됨
# wiki 개념:  3 개                    ← 개념 파일 생성됨
```

생성되는 파일들:

| 파일 | 내용 |
|------|------|
| `wiki/concepts/개념명.md` | 각 개념 설명 파일 (`verified: false` 상태) |
| `wiki/index.md` | 전체 개념 목록 및 태그 분류 |
| `wiki/backlinks.md` | 개념 간 역참조 지도 |
| `wiki/_meta/compile-log.md` | 컴파일 이력 |

> **참고**: 특정 파일만 컴파일하려면 `/compile raw/파일명.md`

---

## 6. 질문하기 (`/ask`)

컴파일된 wiki 내용을 바탕으로 질문에 답합니다.

```
/ask 이 자료에서 가장 중요한 개념 3가지는?
```

### 출력 형식 옵션

```
/ask [질문]               → output/answer-YYYYMMDD-HHmm.md
/ask [질문] --slides      → output/slides-YYYYMMDD-HHmm.marp.md (Marp 슬라이드)
/ask [질문] --chart       → output/chart-YYYYMMDD-HHmm.py (matplotlib)
/ask [질문] --html        → output/report-YYYYMMDD-HHmm.html (Mermaid 다이어그램 포함)
```

> wiki에 없는 내용은 추정하지 않고 "위키에 해당 내용 없음"으로 명시합니다.

---

## 7. 품질 점검 (`/lint`)

```
/lint
```

다음 항목을 자동으로 점검하고 `output/lint-report-YYYYMMDD.md`에 저장합니다:

| 점검 항목 | 자동 수정 |
|-----------|----------|
| 깨진 `[[wikilink]]` | ✗ (수동) |
| 고아 파일 (어디서도 링크 안 됨) | ✓ (`--fix`) |
| index.md 동기화 | ✓ (`--fix`) |
| backlinks.md 정확성 | ✓ (`--fix`) |
| 미검증 파일 (`verified: false`) | ✗ (수동) |

```
/lint --fix    # 자동 수정 가능한 항목 처리
```

### `verified` 필드란?

Claude가 컴파일한 wiki 파일은 기본적으로 `verified: false` 상태입니다.
내용을 직접 읽고 정확하다고 판단되면, 파일을 열어 직접 수정하세요:

```yaml
verified: true    # 사람이 검토 완료
```

> Claude는 이 값을 자동으로 변경하지 않습니다. 검증은 사람의 몫입니다.

---

## 7.5. 지식그래프 빌드 (`/graphify`)

wiki와 raw 파일이 쌓이면 **전체 볼트를 그래프로 시각화**할 수 있습니다.

```
/graphify .
```

처음 실행 전에 `bash scripts/graphify-bootstrap.sh` 를 실행하면 `graphifyy` 설치 및 인터프리터 경로 설정이 자동으로 처리됩니다. (`Python 3.10+` 필요)

**지원 입력**: Markdown · PDF · DOCX · XLSX · PNG/JPG/WebP · MP4/MOV · MP3/WAV · YouTube URL 등 광범위한 파일 형식을 처리합니다 (영상·오디오는 `[video]` extras 설치 필요).

### 실행 후 확인할 것

```bash
open graphify-out/graph.html    # 브라우저에서 인터랙티브 그래프 열기
```

`graphify-out/GRAPH_REPORT.md`를 열면 텍스트 요약을 볼 수 있습니다:
- **God Nodes** — 가장 많이 연결된 핵심 개념
- **Communities** — 주제 클러스터 (현재 22개)
- **Knowledge Gaps** — 연결이 부족한 파일

### 파일 추가 후 업데이트

파일을 새로 추가·수정한 뒤에는 그래프를 업데이트하세요:

```
/graphify . --update
```

> 자세한 사용법은 [docs/guide/graphify.md](guide/graphify.md)를 참고하세요.

---

## 8. 일상 워크플로우

### 매일 반복하는 패턴

```
자료 발견
   ↓
/ingest [URL]          → raw/ 에 파일 저장
   ↓
/compile               → wiki/ 에 개념 정리
   ↓
/ask [질문]            → output/ 에 답변 생성
   ↓                         ↑
   └── 새 인사이트 발견 → wiki 자동 피드백
   ↓
/lint [--fix]          → 품질 점검
```

### 슬래시 커맨드 vs CLI wrapper

| 방법 | 사용 환경 | 예시 |
|------|-----------|------|
| 슬래시 커맨드 | Claude Code 터미널 내부 | `/ingest https://...` |
| CLI wrapper | 일반 터미널 (셸 스크립트) | `./scripts/kb.sh ingest https://...` |

두 방법은 동일하게 동작합니다. Claude Code가 이미 열려있다면 슬래시 커맨드가 더 편합니다.

---

## 8.5. 추가 커맨드 둘러보기

기본 4개 커맨드(ingest/compile/ask/lint) 외에 더 있습니다.

| 커맨드 | 역할 | 예시 |
|---|---|---|
| `/capture [주제]` | 현재 대화의 인사이트를 `raw/sessions/`에 저장 | `/capture MSA 에러 처리 패턴` |
| `/review [파일]` | `output/` 답변을 검토해 wiki에 승격 | `/review output/answer-20260410.md` |
| `/dev-log [단계명]` | 작업 단계를 `.work-log/dev/DEV_LOG_*.md`에 기록 | `/dev-log 튜토리얼 작성 완료` |

> 전체 커맨드 레퍼런스: [docs/guide/commands.md](guide/commands.md)

---

## 9. 자주 묻는 질문

**Q. `wiki/` 파일을 직접 수정해도 되나요?**

권장하지 않습니다. `wiki/`는 Claude 전용 영역입니다.
직접 편집하면 다음 `/compile` 시 내용이 덮어쓰여질 수 있습니다.
수정이 필요하면 `raw/`에 수정 내용을 추가한 뒤 `/compile`을 다시 실행하세요.

**Q. Obsidian으로 볼 수 있나요?**

이 저장소를 Obsidian vault로 바로 열 수 있습니다.
`[[wikilink]]` 형식이 Obsidian 네이티브와 호환되어 Graph View에서 개념 연결을 시각화할 수 있습니다.
자세한 설정은 [docs/obsidian-setup.md](obsidian-setup.md)를 참고하세요.

**Q. 자료가 많아지면 느려지나요?**

약 100개 아티클 / 40만 단어 규모까지는 Claude가 컨텍스트 내에서 직접 처리 가능합니다.
이 시스템은 `wiki/index.md`를 먼저 읽어 관련 파일만 선택적으로 읽는 전략을 사용하므로
일반 사용 범위에서는 큰 문제가 없습니다.

**Q. 기존 Notion 페이지를 가져올 수 있나요?**

네. Notion URL을 그대로 사용하세요:

```
/ingest https://www.notion.so/your-page-id
```

Notion MCP가 연동되어 있으면 자동으로 내용을 가져옵니다.

**Q. `graphify-out/`은 무엇인가요?**

볼트 전체를 스캔해 자동으로 생성되는 **지식그래프 산출물** 폴더입니다.
`graph.html`(브라우저 시각화), `GRAPH_REPORT.md`(커뮤니티·핵심 노드 요약), `graph.json`(기계 읽기용)이 들어 있습니다.
이 파일들은 직접 편집하면 안 되며, `/graphify . --update`로 갱신합니다.
자세한 내용은 [docs/guide/graphify.md](guide/graphify.md)를 참고하세요.

**Q. pre-commit hook이 커밋을 막아요.**

`wiki/` 파일이 staged된 경우 경고가 표시됩니다.
의도한 수정이라면 `y`를 입력해 계속 진행하거나,
Claude Code 커밋이라면 `ALLOW_WIKI_EDIT=1 git commit -m "..."` 으로 우회하세요.

---

## 다음 단계

- [README.md](../README.md) — 프로젝트 전체 개요
- [docs/architecture.md](architecture.md) — 전체 시스템 구조 이해 (3가지 구성 요소·데이터 플로우)
- [docs/guide/commands.md](guide/commands.md) — 슬래시 커맨드 전체 레퍼런스 (8개)
- [docs/guide/graphify.md](guide/graphify.md) — 지식그래프 통합 상세 가이드
- [docs/guide/troubleshooting.md](guide/troubleshooting.md) — 막힘 해결 (설치·실행 오류)
- [docs/obsidian-setup.md](obsidian-setup.md) — Obsidian + Web Clipper 연동
- [PLAN.md](../PLAN.md) — 시스템 설계 및 미래 로드맵
