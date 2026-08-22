# 슬래시 커맨드 레퍼런스

> graphify-kb에서 사용할 수 있는 모든 슬래시 커맨드를 설명합니다.
> 모든 커맨드는 **Claude Code 터미널 내부**에서 실행합니다.
> 일반 터미널에서는 `./scripts/kb.sh <커맨드>` 로 동일하게 사용할 수 있습니다.

---

## 커맨드 한눈에 보기

| 커맨드 | 용도 | 입력 → 출력 |
|---|---|---|
| `/ingest [URL\|텍스트]` | 자료 수집 | 외부 자료 → `raw/` |
| `/compile [파일명]` | wiki 컴파일 | `raw/` → `wiki/` |
| `/ask [질문] [--flags]` | 질의응답 | wiki → `output/` only |
| `/lint [--fix]` | 품질 점검 | wiki → `output/lint-report-*.md`, `wiki/_meta/*` |
| `/capture [주제]` | 대화 인사이트 저장 | 현재 대화 → `raw/sessions/` |
| `/review [파일\|--list]` | output → wiki 승격 | `output/` → `wiki/` |
| `/dev-log [단계명]` | 작업 기록 | 현재 대화 → `.work-log/dev/DEV_LOG_*.md` |
| `/handoff [부제]` | 세션 인계 | 현재 세션 → `.claude/reports/handoff/<YYYY-MM-DD>.md` |
| `/graphify [명령]` | 지식그래프 빌드 | 볼트 전체 → `graphify-out/` |

---

## /ingest

**원본 자료를 수집해 `raw/`에 저장합니다.**

### 구문

```
/ingest [URL | 텍스트]
```

### 지원 입력 유형

| 유형 | 예시 |
|---|---|
| 웹 URL | `/ingest https://news.ycombinator.com/item?id=...` |
| Notion 페이지 | `/ingest https://www.notion.so/your-page-id` |
| GitHub 저장소 | `/ingest https://github.com/owner/repo` |
| 직접 텍스트 | `/ingest` (인수 없이 실행하면 내용 입력 요청) |

### 출력

`raw/원본제목-YYYYMMDD.md` 파일이 생성됩니다. 상단 frontmatter:

```yaml
---
title: 아티클 제목
source_url: https://...
ingested_date: 2026-04-06
compiled: false   ← 아직 wiki로 변환 안 됨
compiled_date: null
verbatim: true    ← 가져온 원문 그대로인가 (요약·발췌가 섞였으면 false + note)
verbatim_checked: 2026-04-06
---
```

> `verbatim` 은 **수집한 그날 채웁니다.** 받은 것이 곧 원본인 순간이라 확인 비용이 없고, 나중에 다시 받으면 그날 판이 와서 *"출처가 바뀐 것"* 과 *"저장분이 요약본인 것"* 을 가를 수 없습니다. 규격: `.claude/rules/raw-ingest.md` §`verbatim`

### 주의

- Notion URL은 Notion MCP가 연동된 경우에만 자동 수집됩니다. 미연동 시 내용을 직접 붙여넣기 하세요.
- 민감 자료는 `raw/private/`, `raw/company/`, `raw/medical/`, `raw/finance/` 아래에 둡니다.
  이 경로는 git, Claude direct scan, Graphify indexing에서 제외합니다.
  공유 가능한 자료만 일반 `raw/`에 둡니다.

---

## /compile

**`raw/`의 미컴파일 파일을 읽어 `wiki/`에 개념·주제로 정리합니다.**

### 구문

```
/compile                    ← 미컴파일 파일 전체 처리
/compile raw/파일명.md      ← 특정 파일만 처리
```

### 출력

| 파일 | 내용 |
|---|---|
| `wiki/concepts/개념명.md` | 추출된 개념 (verified: false 상태) |
| `wiki/index.md` | 전체 개념 목록 자동 갱신 |
| `wiki/backlinks.md` | 개념 간 역참조 맵 자동 갱신 |
| `wiki/_meta/compile-log.md` | 컴파일 이력 |

### 주의

- 생성된 wiki 파일은 기본적으로 `verified: false`입니다. 내용을 검토한 뒤 직접 `verified: true`로 변경하세요.
- 새 wiki frontmatter는 선택적으로 `claim_status`, `evidence_level`, `last_verified`, `review_due`를 포함할 수 있습니다. 값 정책은 [wiki schema guide](wiki-schema.md)를 따릅니다.
- `wiki/`는 LLM 전용 영역입니다. 직접 수정하면 다음 `/compile` 시 덮어쓰여질 수 있습니다.

---

## /ask

**`wiki/`를 바탕으로 질문에 답하고 결과를 `output/`에 저장합니다.**

### 구문

```
/ask [질문]
/ask [질문] --slides      ← Marp 슬라이드 출력
/ask [질문] --chart       ← matplotlib 차트 스크립트 출력
/ask [질문] --html        ← Mermaid 다이어그램 포함 HTML 출력
/ask [질문] --loop        ← 승격 후보만 output에 정리
/ask [질문] --no-loop     ← deprecated alias; 기본 동작과 동일
```

### 출력

| 플래그 | 출력 파일 |
|---|---|
| (없음) | `output/answer-YYYYMMDD-HHmm.md` |
| `--slides` | `output/slides-YYYYMMDD-HHmm.marp.md` |
| `--chart` | `output/chart-YYYYMMDD-HHmm.py` |
| `--html` | `output/report-YYYYMMDD-HHmm.html` |

### 예시

```
/ask MSA에서 Circuit Breaker 패턴이 왜 필요한가?
/ask error-handling 커뮤니티의 핵심 원칙 5개를 표로 정리해줘
/ask Spring Boot와 Kotlin 조합의 장단점을 슬라이드로 만들어줘 --slides
```

### 주의

- wiki에 없는 내용은 추정하지 않고 "위키에 해당 내용 없음"으로 명시합니다.
- `/ask`는 기본적으로 읽기 전용이며 `wiki/`를 직접 생성하거나 수정하지 않습니다. `--loop`는 `output/`에 승격 후보만 남기며, 실제 반영은 `/review`에서 승인 후 진행합니다.
- `--slides`는 Marp CLI, `--chart`는 matplotlib이 설치된 경우에만 출력됩니다.

---

## /lint

**wiki 품질을 점검하고 이슈를 보고합니다.**

### 구문

```
/lint             ← 점검만 (자동 수정 없음)
/lint --fix       ← 자동 수정 가능한 항목 처리
```

### 점검 항목

| 항목 | 자동 수정 (`--fix`) |
|---|---|
| 깨진 `[[wikilink]]` | 불가 (수동 처리) |
| 고아 파일 (어디서도 링크 안 됨) | 가능 |
| `wiki/index.md` 동기화 | 가능 |
| `wiki/backlinks.md` 정확성 | 가능 |
| 미검증 파일 (`verified: false`) | 불가 (사람이 직접 검토) |
| 선택 claim/evidence 필드 (`claim_status`, `evidence_level`, `last_verified`, `review_due`) | 불가 (WARN만 보고) |

### 출력

- `output/lint-report-YYYYMMDD.md`: 상세 점검 보고서
- `wiki/_meta/weather.md`: 현재 상태 대시보드인 Knowledge Weather

### 주의

정기적으로 (새 자료 컴파일 후, 또는 주 1회) 실행하면 wiki 상태를 건강하게 유지할 수 있습니다.

---

## /capture

**현재 Claude와의 대화에서 인사이트를 추출해 `raw/sessions/`에 저장합니다.**

### 구문

```
/capture [주제 설명]
```

### 예시

```
/capture Claude Code 훅 시스템 설계
/capture MSA 에러 처리 패턴 정리
/capture HikariCP 튜닝 결정 배경
```

### 출력

`raw/sessions/session-YYYYMMDD-HHmm.md` 파일이 생성됩니다:

```yaml
---
title: {주제 제목}
type: session
source_url: null
ingested_date: YYYY-MM-DD
compiled: false
tags: []
session_topic: {slug}
key_insights:
  - 인사이트 1
  - 인사이트 2
---
```

이후 `/compile raw/sessions/세션파일명.md`로 wiki에 반영합니다.

### 언제 쓰나요?

- 대화하며 얻은 결론이나 패턴을 나중에 다시 찾고 싶을 때
- URL이나 문서가 아닌, 대화 자체가 지식 원천일 때
- 의사결정 배경을 기록해두고 싶을 때

---

## /review

**`output/`의 답변 파일을 검토하고 가치 있는 내용을 `wiki/`에 승격합니다.**

### 구문

```
/review output/answer-파일명.md     ← 특정 파일 검토
/review --list                      ← 아직 리뷰 안 된 output 파일 목록
```

### 동작 방식

1. output 파일을 분석해 "wiki에 없는 새 인사이트"를 식별합니다.
2. `/ask --loop`가 남긴 `## Promotion Candidates`가 있으면 우선 참고합니다.
3. 승격 계획을 보여주고 사람의 확인을 기다립니다 (자동으로 수정하지 않습니다).
4. 승인하면 `wiki/concepts/`에 새 파일을 생성하거나 기존 파일을 보완합니다.
5. `wiki/index.md`, `wiki/backlinks.md`를 자동 갱신합니다.
6. 리뷰한 output 파일 끝에 `## Review Summary`를 추가합니다.

신규 승격 페이지는 사람이 검증하기 전까지 `claim_status: inferred`, `evidence_level: ai_synthesis`, `last_verified: null`, `review_due: null`로 시작합니다.

### 언제 쓰나요?

- `/ask`로 생성한 답변이 새로운 합성·비교 분석을 담고 있을 때
- 자주 참조될 것 같은 결론을 wiki에 영구 보관하고 싶을 때

---

## /dev-log

**현재 작업 단계를 `.work-log/dev/DEV_LOG_YYYYMMDD.md`에 구조화된 형식으로 기록합니다.**
핵심 결정 요약은 루트 `log.md` 전체 타임라인에도 함께 남깁니다.

### 구문

```
/dev-log [단계명]
/dev-log                  ← 단계명 없이 실행하면 자동 추론
```

### 예시

```
/dev-log 아키텍처 문서 초안 작성
/dev-log graphify 증분 재빌드 설정
```

### 출력 형식

```markdown
## [단계명] — YYYY-MM-DD

- **결정**: 선택한 방식과 이유
- **시도**: 사용한 방법/도구/커맨드
- **오류**: 발생한 에러 또는 "없음"
- **해결**: 해결 방법 또는 "-"
- **메모**: 다음 단계 참고사항
```

### 언제 쓰나요?

- 중요한 의사결정을 기록하고 싶을 때
- 에러와 해결 과정을 남기고 싶을 때
- 세션 사이에 작업 맥락을 유지하고 싶을 때

---

## /handoff

**현재 세션을 다음 세션이 이어받을 수 있는 문서로 `.claude/reports/handoff/<YYYY-MM-DD>.md`에 기록합니다.**
회고가 아니라 인계입니다 — 다음 세션이 문맥 없이 읽어도 이어갈 수 있어야 합니다.

### 구문

```
/handoff              ← 오늘 날짜로 작성
/handoff [부제]       ← 부제를 지정
```

### 문서 구조

머리말(세션 성격·측정 기준일·커밋 상태) 뒤에 6절.

| 절 | 내용 |
|---|---|
| 1. 완료된 작업 | 산출물 표 + 재실행 가능한 형태의 측정 기록. 의도적으로 하지 않은 일도 이유와 함께 |
| 2. 주요 결정 | `D1`, `D2` … 각 항목에 왜 그렇게 정했는지. 기각·폐기한 안도 포함 |
| 3. 피해야 할 함정 | `T1`, `T2` … **이 세션이 실제로 밟았거나 밟을 뻔한 것만.** 🔴 결론을 바꾼 오류 / ⚠️ 서술을 약화시킨 오류 |
| 4. 관련 파일 | 만든 것 / 조치 대상(`경로:줄` 필수) / 근거·규율 문서 |
| 5. 남은 작업 상태 | **상태 서술형.** "적용하라"가 아니라 "미적용 상태다" |
| 6. Prompt for New Chat | 새 대화에 붙여넣을 블록 |

### 작성 원칙

- **검증 가능한 것만.** 경로에는 줄 번호를, 수치에는 측정일과 방법을 붙입니다. 확인하지 않은 것은 "미확인"으로 적습니다.
- **미실행을 0으로 적지 않습니다.** 재지 않은 항목은 "미측정"입니다.
- **줄 번호는 기억으로 적지 않습니다.** `grep -n`으로 다시 잡습니다.
- **같은 값이 두 파일에서 갈리면** 어느 파일에서 읽었는지 명시합니다.
- **자기 오류를 숨기지 않습니다.** 세션 중에 뒤집힌 주장이 §3에서 가장 값나가는 부분입니다.

### `/dev-log` 와의 차이

| | `/dev-log` | `/handoff` |
|---|---|---|
| 단위 | 작업 단계 | 세션 전체 |
| 산출 | `.work-log/dev/DEV_LOG_*.md` + `log.md` | `.claude/reports/handoff/<날짜>.md` |
| 독자 | 나중의 나 (시간순 이력) | 문맥 없는 다음 세션 |

`/handoff`는 `log.md`를 건드리지 않습니다.

### 하지 않는 것

- 커밋 — 사용자가 요청할 때만
- `_current.md` 같은 누적 상태 문서 자동 갱신 — §5에 "미갱신 상태"로 적고 사용자 판단에 맡깁니다
- 다음 세션의 작업 지시 — 상태만 넘깁니다

---

## /graphify

**볼트 전체를 스캔해 지식그래프를 생성합니다.**

자세한 내용은 [docs/guide/graphify.md](graphify.md)를 참고하세요.

### 구문 요약

```
/graphify .                  ← 현재 디렉토리 전체 빌드
/graphify . --update         ← 변경된 파일만 증분 빌드 (권장)
/graphify . --mode deep      ← 심층 분석 모드 (LLM 호출 증가, 비용 주의)
/graphify add <URL>          ← URL 자료를 바로 그래프에 추가
/graphify query "..."        ← 그래프 구조 기반 질의
/graphify path "A" "B"       ← 두 노드 사이 최단 경로 탐색
/graphify explain <노드명>   ← 특정 노드의 연결 관계 설명
```

### 내보내기 플래그

```
/graphify . --svg        ← SVG 형식으로 그래프 내보내기
/graphify . --graphml    ← GraphML 형식으로 내보내기 (Gephi 등 호환)
/graphify . --neo4j      ← Neo4j 가져오기 형식으로 내보내기
```

---

## CLI 래퍼 (`scripts/kb.sh`)

Claude Code 없이 일반 터미널에서도 커맨드를 실행할 수 있습니다.
내부적으로 `claude "/커맨드 ..."` 를 호출하므로 `claude` CLI가 PATH에 있어야 합니다.

```bash
./scripts/kb.sh status          # raw/wiki/output 파일 수 통계
./scripts/kb.sh ingest [URL]    # /ingest 실행
./scripts/kb.sh compile         # /compile 실행
./scripts/kb.sh ask [질문]      # /ask 실행
./scripts/kb.sh lint            # /lint 실행
```

### 슬래시 커맨드 vs CLI 래퍼

| 상황 | 권장 방법 |
|---|---|
| Claude Code 세션 안에 있을 때 | 슬래시 커맨드 (`/ingest`, `/compile` ...) |
| 일반 터미널에서 빠르게 실행할 때 | `./scripts/kb.sh <커맨드>` |
| 자동화 스크립트에서 호출할 때 | `./scripts/kb.sh <커맨드>` |

---

## 관련 문서

- [docs/tutorial.md](../tutorial.md) — 처음 시작하는 분을 위한 단계별 가이드
- [docs/guide/graphify.md](graphify.md) — `/graphify` 상세 가이드
- [docs/guide/troubleshooting.md](troubleshooting.md) — 실행 오류 해결
- [docs/architecture.md](../architecture.md) — 시스템 전체 구조
