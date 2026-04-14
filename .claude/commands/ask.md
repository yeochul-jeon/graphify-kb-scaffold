wiki 기반 질의응답. 결과를 `output/`에 저장하고 새 인사이트는 wiki에 피드백합니다. Triggers: ask, query, question, search wiki, 질문, 검색, 답변

## 사용법

```
/ask [질문]
/ask [질문] --slides      # Marp 슬라이드 형식 출력
/ask [질문] --chart       # matplotlib 차트 포함
/ask [질문] --html        # 인터랙티브 standalone HTML 출력
/ask [질문] --no-loop     # Knowledge Loop 건너뛰기 (단순 조회)
```

## 처리 순서

### Step 1: 질문 분석

`$ARGUMENTS`에서 질문과 옵션 플래그 분리 (`--slides`, `--chart`, `--html`, `--no-loop`).
질문의 핵심 키워드와 관련 개념 파악.

### Step 2: 관련 wiki 파일 탐색

1. `wiki/index.md` 읽어 관련 개념/주제 파악
2. Grep으로 키워드 검색: `wiki/concepts/`, `wiki/topics/`
3. 관련 wiki 파일들 읽기 (백링크 포함)

### Step 3: 답변 생성

wiki 내용을 기반으로 답변 작성. wiki에 없는 내용은 추정/창작하지 말고 "위키에 해당 내용 없음"으로 명시.

### Step 4: 출력 형식 선택

**기본 (마크다운):**
파일명: `output/answer-YYYYMMDD-HHmm.md`

```markdown
# [질문 요약]

> 질문: [원본 질문]
> 생성일: YYYY-MM-DD HH:MM
> 참조: [[wiki/concepts/개념1]], [[wiki/concepts/개념2]]

[답변 내용]

---
## 참조 위키 파일
- [[개념1]]: [간략 설명]
- [[개념2]]: [간략 설명]
```

**`--slides` 옵션 (Marp 형식):**
파일명: `output/slides-YYYYMMDD-HHmm.marp.md`

```markdown
---
marp: true
theme: default
paginate: true
---

# [제목]

---

## 슬라이드 1 제목

내용

---
```

**`--chart` 옵션:**
- matplotlib Python 코드를 생성
- `output/chart-YYYYMMDD-HHmm.py`로 저장
- `python3 output/chart-YYYYMMDD-HHmm.py` 실행해 PNG 생성
- 간단한 관계도는 mermaid 코드블록으로 마크다운에 인라인 포함

**`--html` 옵션 (동적 HTML):**
파일명: `output/report-YYYYMMDD-HHmm.html`

다음 요소를 포함하는 standalone HTML 파일 생성:
- 브라우저에서 바로 열 수 있는 self-contained 단일 파일 (외부 CDN 사용 가능)
- **Mermaid.js** 다이어그램 (개념 관계도, 플로우차트 등)
- **접을 수 있는 섹션** (`<details>/<summary>` 태그)
- 목차(TOC) 자동 생성 (사이드바 또는 상단 링크)
- 기본 CSS 스타일링 (읽기 편한 타이포그래피, 다크/라이트 모드 미지원 — 심플 유지)

HTML 파일 기본 구조:
```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <title>[질문 요약]</title>
  <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
  <style>/* 인라인 CSS */</style>
</head>
<body>
  <nav><!-- TOC --></nav>
  <main>
    <h1>[제목]</h1>
    <blockquote>질문: ... | 생성일: ... | 참조: ...</blockquote>
    <!-- 답변 내용 (섹션별 details 태그 활용) -->
    <!-- Mermaid 다이어그램 (개념 관계도 등) -->
  </main>
  <script>mermaid.initialize({startOnLoad:true});</script>
</body>
</html>
```

**사용 시 고려사항:**
- 인터넷 연결 필요 (Mermaid CDN)
- 슬라이드보다 참조/탐색에 적합한 긴 분석 결과에 사용
- `--slides`와 중복 사용 불가 (둘 중 하나 선택)

### Step 5: 지식 루프 (Knowledge Loop)

`--no-loop` 플래그가 있으면 이 단계를 건너뛰고 output 파일 끝에 "Knowledge Loop: 건너뜀 (--no-loop)" 을 명시.

그 외에는 다음 체크리스트를 수행:

1. **누락 개념 페이지 생성**: 답변에서 언급한 개념 중 `wiki/concepts/`에 파일이 없는 것 → stub 페이지 생성
2. **새 합성 페이지 생성**: 2개 이상의 위키 페이지를 새로운 방식으로 연결·합성한 인사이트 → 새 wiki 페이지 생성
3. **기존 페이지 보완**: 답변 과정에서 기존 wiki 페이지의 내용을 수정·보완할 사항 발견 시 → 해당 파일 업데이트
4. 위 3가지 모두 해당 없으면 "피드백 없음"으로 명시

output 파일 끝에 반드시 다음 섹션 추가:

```markdown
---
## Knowledge Loop Summary
- 생성된 wiki 페이지: [파일 목록 또는 "없음"]
- 업데이트된 wiki 페이지: [파일 목록 또는 "없음"]
```

### Step 6: output 파일을 wiki에 피드백

답변 파일을 wiki에서 참조 가능하도록:
- `wiki/index.md` 최근 변경 이력에 추가 (선택)

### 완료 후 보고

- 생성된 output 파일 경로
- 참조한 wiki 파일 목록
- wiki에 추가/업데이트한 내용 (있는 경우)

### 작업 로그 업데이트

`log.md` (프로젝트 루트) 파일 끝에 다음 형식으로 append:

```
## [YYYY-MM-DD] ask | [질문 요약]
- refs: [참조한 wiki 파일들]
- output: output/[파일명]
- loop: [생성/업데이트된 wiki 파일 또는 "없음"]
```

allowed-tools: Read, Write, Edit, Bash, Glob, Grep
