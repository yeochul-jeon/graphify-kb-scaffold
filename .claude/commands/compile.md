LLM 컴파일러: `raw/` 자료를 읽고 `wiki/`를 점진적으로 구축합니다. Triggers: compile, build wiki, convert raw to wiki, 컴파일, raw 처리

## 사용법

```
/compile              # 미컴파일 파일 전체 처리
/compile [파일명]     # 특정 raw 파일만 처리
```

## 처리 순서

### Step 1: 대상 파일 수집

- `$ARGUMENTS`가 있으면 해당 파일만
- 없으면 `raw/` 에서 frontmatter의 `compiled: false`인 파일 전체 (Grep으로 탐색)
- `raw/_templates/`, `raw/Clippings/`는 제외

### Step 2: 각 raw 파일 분석

각 파일에 대해 다음을 수행:

1. 전체 내용 읽기
2. **핵심 개념 추출**: 독립적으로 설명 가능한 개념 목록화
   - 예: "Transformer", "Self-Attention", "Positional Encoding"
3. **상위 주제 판별**: 여러 개념을 아우르는 큰 주제 식별
   - 예: "딥러닝 아키텍처", "자연어 처리"

### Step 3: wiki 파일 생성 또는 병합

각 개념에 대해:

**신규 개념인 경우** (Grep으로 wiki/에 유사 제목 없음):
- `wiki/concepts/[kebab-case].md` 신규 생성
- 아래 포맷 사용

**기존 개념인 경우** (유사 파일 발견):
- 기존 파일을 **반드시 먼저 완전히 읽기**
- 새 정보를 적절한 섹션에 **append** (기존 내용 삭제 금지)
- frontmatter의 `updated` 날짜 갱신
- `sources`에 새 raw 파일 추가

### wiki 파일 포맷

```markdown
---
title: [개념명]
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: [tag1, tag2]
sources: [raw/파일명.md]
verified: false
confidence: high|medium|low
---

# [개념명]

## 개요
2~3문장 핵심 요약.

## 핵심 내용

### [섹션1]
...

### [섹션2]
...

## 관련 개념
- [[관련개념1]]
- [[관련개념2]]

## 출처
- [[raw/파일명.md]]
```

### Step 3.5: 이미지 참조 처리

raw 파일 frontmatter에 `images` 필드가 있거나 본문에 이미지 참조(`![...]`)가 있는 경우:

1. **이미지 복사**: `raw/attachments/[article-name]/` → `wiki/attachments/[concept-name]/`
   - 해당 개념에서 참조하는 이미지만 선택적으로 복사
2. **경로 변환**: wiki 파일에서의 상대 경로로 변환
   - `![alt](attachments/concept-name/image.png)`
3. **이미지 없으면 건너뛰기**: 이미지 관련 처리 생략

### Step 4: wiki/index.md 업데이트

- 새로 생성된 개념/주제를 테이블에 추가
- 최근 변경 이력 상단에 추가
- 파일 상단 "총 개념 수" 카운터 갱신

### Step 5: wiki/backlinks.md 업데이트 (증분)

이번 컴파일에서 생성/수정한 wiki 파일만 처리:

1. 기존 `wiki/backlinks.md` 읽기
2. 변경된 파일에 해당하는 기존 backlink 항목 제거
3. 변경된 파일의 `[[wikilink]]` 추출 후 backlink 항목 재삽입
4. Grep으로 다른 wiki 파일에서 변경된 파일을 `[[참조]]`하는지 확인 후 반영

형식:
```
## [[개념명]]
참조하는 파일:
- [[다른개념]] (이유/맥락)
```

### Step 6: raw 파일 frontmatter 업데이트

처리한 raw 파일의 frontmatter를 수정:
```yaml
compiled: true
compiled_date: YYYY-MM-DD
```

### Step 7: compile-log.md 업데이트

`wiki/_meta/compile-log.md` 테이블에 행 추가:
```
| YYYY-MM-DD | raw/파일명.md | concepts/개념1.md (신규), concepts/개념2.md (업데이트) | - |
```

### 완료 후 보고

- 처리한 raw 파일 수
- 생성된 wiki 파일 목록
- 업데이트된 wiki 파일 목록
- 다음 단계 안내: `/ask` 또는 `/lint`

### 작업 로그 업데이트

`log.md` (프로젝트 루트) 파일 끝에 다음 형식으로 append:

```
## [YYYY-MM-DD] compile | [처리한 raw 파일명]
- processed: raw/[파일명].md
- created: [신규 생성된 wiki 파일 목록]
- updated: [업데이트된 wiki 파일 목록]
```

allowed-tools: Read, Write, Edit, Bash, Glob, Grep
