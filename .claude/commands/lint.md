wiki 품질 자가 점검. 깨진 링크, 고아 파일, 중복, 오래된 콘텐츠 등을 탐지합니다. Triggers: lint, check quality, validate wiki, broken links, orphan files, 점검, 검증

## 사용법

```
/lint              # 문제 탐지 후 보고서만 출력 (단, 탐구 제안 파일은 항상 갱신)
/lint --fix        # 탐지 후 자동 수정 가능한 항목 처리
/lint --quick      # 구조적 점검만 (#1~#8) — 의미론적 분석 생략
/lint --quick --fix  # 구조적 점검 + 자동 수정
```

## Step 0: 플래그 파싱

`$ARGUMENTS`에서 플래그를 분리:
- `--fix` → 자동 수정 활성화
- `--quick` → 점검 #9~#12 (의미론적 분석) 건너뛰기

## 점검 항목

### 1. 깨진 `[[wikilink]]` 탐지

- 모든 wiki 파일에서 `[[...]]` 패턴 추출 (Grep)
- 참조 대상 파일 존재 여부 확인
- **`--fix` 시**: 수정 불가 (사람이 판단 필요), 보고서에만 표시

### 2. 고아 파일 탐지

- `wiki/concepts/`, `wiki/topics/`의 모든 파일 목록
- 어디서도 링크되지 않은 파일 탐지
- `wiki/index.md`에도 없는 파일 포함
- **`--fix` 시**: `wiki/index.md`에 추가

### 3. 오래된 콘텐츠 탐지

- frontmatter의 `updated` 날짜가 30일 이상 된 파일
- 보고서에 목록 표시, 사람이 검토 요청

### 4. 중복 개념 탐지

- 파일명이 유사한 파일 쌍 탐지 (편집 거리 기준)
- 태그가 완전히 동일한 파일 쌍
- 보고서에 표시, 병합 여부는 사람이 판단

### 5. 출처 누락 탐지

- frontmatter의 `sources`가 빈 배열이거나 null인 파일
- 보고서에 목록 표시

### 6. index.md 동기화 점검

- `wiki/concepts/`와 `wiki/topics/`의 실제 파일 vs `wiki/index.md` 테이블 비교
- index에 없는 파일, 파일이 없는데 index에 있는 항목 탐지
- **`--fix` 시**: `wiki/index.md` 자동 재생성

### 7. backlinks.md 정확성 점검

- 현재 `wiki/backlinks.md`와 실제 `[[wikilink]]` 스캔 결과 비교
- 누락/잘못된 백링크 탐지
- **`--fix` 시**: `wiki/backlinks.md` 자동 재생성

### 8. 미검증 파일 점검

- frontmatter의 `verified: false`인 wiki 파일 목록 추출
- 보고서에 표시하여 사람이 검토할 수 있도록 안내
- **`--fix` 불가**: 사람이 내용을 직접 검토 후 `verified: true`로 수동 변경

## 의미론적 점검 (Phase 2.1)

> 점검 #9~#12는 의미론적 분석이 필요한 항목입니다.
> `--fix` 시에도 자동 수정 불가 (탐구 제안 파일 갱신 제외).
> 점검 #9는 점검 #1의 결과를 입력으로 사용합니다.

### 9. 누락 개념 페이지 탐지

- 점검 #1(깨진 wikilink)의 결과를 입력으로 사용
- 추가로: 모든 wiki 파일 본문에서 `[[...]]` 없이 일반 텍스트로 반복 언급되는 핵심 개념 식별
  - 서로 다른 wiki 파일에서 3회 이상 등장하는 용어
  - 기존 `wiki/concepts/` 또는 `wiki/topics/`에 해당 파일이 없는 경우
- 각 누락 개념에 대해 다음을 보고:
  - 개념명 + 제안 파일명 (kebab-case)
  - 어디서 참조/언급되었는지 (파일 목록)
  - 독립 페이지가 필요한 이유 (1문장)
- **`--fix` 불가**: 사람 또는 `/compile`이 판단 후 생성

### 10. 모순 감지

- `wiki/backlinks.md`에서 관련 페이지 쌍 목록 추출
- 각 쌍의 두 파일을 읽고, 동일한 주제에 대해 **상충하는 사실적 주장** 비교:
  - 숫자 불일치 (예: "6가지 패턴" vs "5가지 패턴")
  - 정의 충돌 (예: 같은 용어를 다르게 정의)
  - 프로세스/순서 불일치 (예: "3단계" vs "4단계")
- **보수적 기준**: 명확한 사실 충돌만 보고. 관점 차이, 강조점 차이, 추상화 수준 차이는 무시
- 보고서에 각 모순 항목 표시:
  - 충돌하는 두 파일명
  - 각 파일의 해당 주장 인용
  - 모순 유형 (숫자/정의/프로세스)
- **`--fix` 불가**: 사람이 판단 후 수정

### 11. 탐구 제안 생성

- 점검 #1~#10 결과와 전체 wiki 구조를 종합하여 3~5개 탐구 주제 생성
- 탐구 주제 선정 기준:
  - **미연결 영역**: backlinks.md에서 연결이 1개 이하인 개념 클러스터
  - **얕은 커버리지**: 본문이 500자 미만인 wiki 파일의 주제 심화
  - **태그 갭**: index.md 태그별 분류에서 파일이 1~2개뿐인 태그 영역
  - **관련 외부 주제**: 기존 개념들이 자연스럽게 연결되지만 아직 다루지 않은 주제
- 결과를 `wiki/_meta/suggested-investigations.md`에 저장 (기존 내용 덮어쓰기)
- **예외 — 항상 파일 갱신**: `--fix` 없이도 실행마다 파일을 생성/갱신 (메타데이터이므로)
- 파일 형식:
  ```markdown
  # 탐구 제안

  > 마지막 업데이트: YYYY-MM-DD
  > /lint 실행 시 자동 갱신

  ---

  ### 1. [제안 제목]
  - **근거**: [이 제안이 나온 이유 — 어떤 갭이 발견되었는지]
  - **관련 개념**: [[concept-a]], [[concept-b]]
  - **유형**: 미연결 영역 | 얕은 커버리지 | 태그 갭 | 관련 외부 주제
  ```

### 12. 빠르게 변하는 주제 소스 점검

- frontmatter `tags`에 `llm`, `ai`, `claude-code`, `agent` 중 하나 이상 포함된 파일 대상
- `updated` 날짜가 90일 이상 경과한 파일 탐지
- 점검 #3(30일 기준 전체 콘텐츠 점검)과 별도 — 이 점검은 **소스 갱신 권고**에 초점:
  - "이 분야는 빠르게 발전 중이므로 최신 자료로 `/ingest` + `/compile` 재실행을 권장합니다" 형태 권고
- 보고서에 표시:
  - 파일명, 마지막 업데이트 날짜, 경과 일수
  - 해당 도메인 태그 목록
  - 소스 갱신 권고 메시지
- **`--fix` 불가**: 사람이 새 자료를 수집해야 함

### 13. CLAUDE.md 프론트매터 준수 점검

- 대상: `wiki/concepts/` 및 `wiki/topics/` 아래 모든 `.md` 파일
- 필수 프론트매터 필드 7개 존재 여부 확인:
  - `title`, `created`, `updated`, `tags`, `sources`, `verified`, `confidence`
- 필드가 **완전히 누락**된 경우만 보고 (빈 값은 점검 #5에서 처리)
- **`--fix` 불가**: 누락된 필드의 값은 사람 또는 `/compile`이 판단해야 함

## 보고서 형식

`output/lint-report-YYYYMMDD.md`에 저장:

```markdown
# Lint 보고서 — YYYY-MM-DD

## 요약
| 항목 | 발견 수 | 자동수정 |
|------|---------|---------|
| 깨진 링크 | N | - |
| 고아 파일 | N | N (--fix) |
| 오래된 콘텐츠 (30일+) | N | - |
| 중복 개념 | N | - |
| 출처 누락 | N | - |
| index.md 미동기화 | N | N (--fix) |
| backlinks.md 오류 | N | N (--fix) |
| 미검증 파일 | N | - (수동 검토 필요) |
| 누락 개념 페이지 | N | - |
| 모순 감지 | N | - |
| 탐구 제안 | N | (suggested-investigations.md 갱신) |
| 소스 갱신 권고 (AI/LLM) | N | - |
| 프론트매터 필드 누락 | N | - |

## 상세

### 깨진 링크
- `wiki/concepts/foo.md`: `[[bar]]` → bar.md 없음

### 고아 파일
...

### 누락 개념 페이지
- `concept-name` (제안: `concepts/concept-name.md`): 3회 언급 (파일A, 파일B, 파일C) — 독립 페이지 권장

### 모순 감지
- `concepts/file-a.md` vs `concepts/file-b.md`: "6가지 패턴" vs "5가지 패턴" (숫자 불일치)

### 탐구 제안
- 3~5개 주제 → `wiki/_meta/suggested-investigations.md` 참조

### 소스 갱신 권고 (AI/LLM)
- `concepts/llm-compiler.md`: 업데이트 92일 전, 태그 [llm] — 최신 자료로 `/ingest` + `/compile` 재실행 권장

### 프론트매터 필드 누락
- `concepts/example.md`: 누락 필드 — `confidence`, `verified`
```

### 작업 로그 업데이트

`log.md` (프로젝트 루트) 파일 끝에 다음 형식으로 append:

```
## [YYYY-MM-DD] lint | [점검 범위]
- checked: [점검 파일 수]
- issues: [발견된 문제 수]
- fixed: [자동 수정 내역 또는 "없음"]
- report: output/lint-report-YYYYMMDD.md
```

allowed-tools: Read, Write, Edit, Bash, Glob, Grep
