output 파일의 인사이트를 검토하고 wiki로 승격합니다. Triggers: review, promote to wiki, elevate output, 승격, 검토, output 반영

## 사용법

```
/review [output 파일 경로]       # 특정 output 파일 검토
/review --list                   # 아직 리뷰되지 않은 output 파일 목록
```

## 처리 순서

### Step 1: 대상 파일 확인

- `$ARGUMENTS`에 파일 경로가 있으면 해당 파일
- `--list` 플래그 시: `output/` 내 모든 `.md` 파일 중 하단에 `## Review Summary`가 없는 파일 목록만 출력하고 종료
- 인자 없으면 에러: "리뷰할 파일을 지정해주세요. `/review --list`로 미리뷰 파일을 확인할 수 있습니다."

`/ask --loop`가 만든 `## Promotion Candidates` 섹션이 있으면 이를 우선 참고하되, 실제 승격 전에는 반드시 output 전체와 대상 wiki 파일을 다시 검토한다.

### Step 2: output 파일 분석

대상 파일을 전체 읽고 다음을 식별:

1. **승격 후보 인사이트**: output 파일에서 wiki에 아직 없는 새로운 주장, 합성, 비교 분석
2. **기존 wiki 보완점**: output이 참조한 wiki 파일에 추가할 만한 내용
3. **신규 개념 후보**: output에서 언급되었지만 wiki/concepts/에 파일이 없는 개념

각 후보에 대해 다음을 정리:
- 인사이트 요약 (1~2문장)
- 승격 유형: `신규 개념` | `기존 보완` | `신규 주제`
- 대상 파일: 생성하거나 업데이트할 wiki 파일 경로

### Step 3: 사용자에게 승격 계획 제시

분석 결과를 사용자에게 보고하고 확인 요청:

```
## 승격 계획

### 신규 생성
1. `wiki/concepts/foo.md` — [인사이트 요약]

### 기존 보완
1. `wiki/concepts/bar.md` — [추가할 내용 요약]

### 승격 없음
- [해당 없는 이유]

진행할까요?
```

**중요**: 사용자가 확인하기 전까지 wiki 파일을 수정하지 않는다.

### Step 4: wiki 승격 실행

사용자가 승인하면:

**신규 개념 생성** — `/compile`과 동일한 포맷 사용:
```markdown
---
title: [개념명]
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: [tag1, tag2]
sources: [output/원본파일.md]
verified: false
confidence: medium
claim_status: inferred
evidence_level: ai_synthesis
last_verified: null
review_due: null
---
```
- `sources`에는 원본 output 파일 경로를 기록
- `confidence: medium` 기본값 (output은 합성 결과이므로 raw보다 한 단계 낮게)
- output 승격은 사람이 검증하기 전까지 합성 지식으로 보고 `claim_status: inferred`, `evidence_level: ai_synthesis`를 기본값으로 사용
  - 이는 **`/review` 워크플로의 기본값**이다. 전체 열거값과 판정 기준은 `.claude/rules/wiki-concepts.md` 가 단일 출처 — `/compile` 은 `source_backed` 를 기본값으로 쓴다

**기존 파일 보완** — 기존 파일을 완전히 읽은 후:
- 새 정보를 적절한 섹션에 append (기존 내용 삭제 금지)
- `updated` 날짜 갱신
- `sources`에 output 파일 추가

### Step 5: index.md, backlinks.md 갱신

- 신규 파일 생성 시 `wiki/index.md` 테이블에 추가
- `wiki/backlinks.md`에서 관련 링크 업데이트

### Step 6: output 파일에 리뷰 기록 추가

리뷰한 output 파일 끝에 다음 섹션 append:

```markdown
---
## Review Summary
- 리뷰일: YYYY-MM-DD
- 승격된 wiki 페이지: [파일 목록 또는 "없음"]
- 보완된 wiki 페이지: [파일 목록 또는 "없음"]
- 승격 안 함: [이유 (해당 시)]
```

### 완료 후 보고

- 승격/보완된 wiki 파일 목록
- 승격하지 않은 인사이트와 이유
- 다음 단계 안내: `/lint`로 품질 점검 권장

### 작업 로그 업데이트

`log.md` (프로젝트 루트) 파일 끝에 다음 형식으로 append:

```
## [YYYY-MM-DD] review | [output 파일명]
- source: output/[파일명]
- promoted: [승격된 wiki 파일 목록 또는 "없음"]
- updated: [보완된 wiki 파일 목록 또는 "없음"]
```
