현재 대화에서 특정 주제의 인사이트를 추출해 `raw/sessions/`에 저장합니다. Triggers: capture, save session, extract insights, 캡처, 세션 저장, 인사이트 추출

## 사용법

```
/capture 주제 설명 텍스트
```

## 처리 순서

### Step 1: 입력 확인

- `$ARGUMENTS`가 비어있으면 에러 출력 후 종료:
  > "캡처할 주제를 입력해주세요. 예: `/capture Claude Code 훅 시스템 설계`"
- 주제 텍스트에서 파일명용 slug 생성 (영문 kebab-case, 최대 40자)
  - 한국어·영문 혼합인 경우 의미 있는 영문 키워드 추출
  - 예: "Claude Code 훅 시스템" → `claude-code-hooks`
  - 예: "MCP 서버 연동 패턴" → `mcp-server-patterns`

### Step 2: 인사이트 추출

현재 대화 컨텍스트에서 `$ARGUMENTS` 주제와 관련된 내용을 분석해 다음을 작성:

1. **제목**: 주제를 명확하게 표현하는 한국어 제목 (1줄)
2. **요약**: 주제의 핵심을 2~3문장으로 압축
3. **핵심 인사이트**: 대화에서 도출된 구체적 결론, 패턴, 결정 사항
   - 3개 이상, 7개 이하
   - 각 항목은 하나의 명확한 사실/결론으로 작성
4. **관련 개념**: wiki에 연결 가능한 개념들 (`[[wikilink]]` 형식)
   - `wiki/concepts/` 또는 `wiki/topics/`에 이미 있거나 생성 가능한 개념
   - 없으면 해당 섹션 생략
5. **원본 컨텍스트**: 이 인사이트가 도출된 배경, 문제 상황, 또는 실험 내용 (2~4문장)

### Step 3: 파일 생성

**저장 경로 결정**:
- 현재 날짜·시간: `YYYYMMDD-HHmm` 형식
- 기본 파일명: `session-YYYYMMDD-HHmm.md`
- Glob으로 `raw/sessions/session-YYYYMMDD-HHmm*.md` 패턴 확인 후 중복 시 suffix 결정
- 동일 분에 이미 파일이 존재하면: `session-YYYYMMDD-HHmm-2.md`, `-3.md` 순서로

**디렉토리 확인**: `raw/sessions/`가 없으면 생성

**파일 내용**:

```yaml
---
title: {Step 2에서 작성한 제목}
type: session
source_url: null
ingested_date: YYYY-MM-DD
compiled: false
compiled_date: null
tags: []
session_topic: {Step 1에서 생성한 slug}
key_insights:
  - {인사이트 1}
  - {인사이트 2}
  - ...
---

## 요약

{2~3문장 요약}

## 핵심 인사이트

- {구체적 인사이트}
- ...

## 관련 개념

- [[concept-name]] — 한 줄 설명
- ...

## 원본 컨텍스트

{배경·문제 상황 2~4문장}
```

관련 개념이 없으면 `## 관련 개념` 섹션 전체 생략.

### 완료 후 보고

```
캡처 완료: raw/sessions/{파일명}
주제: {$ARGUMENTS}
인사이트: {N}개

다음 단계: /compile raw/sessions/{파일명}
```

### 작업 로그 업데이트

`log.md` (프로젝트 루트) 파일 끝에 다음 형식으로 append:

```
## [YYYY-MM-DD] capture | {$ARGUMENTS}
- file: raw/sessions/{파일명}
- topic: {session_topic slug}
- insights: {N}개
- next: /compile raw/sessions/{파일명}
```
