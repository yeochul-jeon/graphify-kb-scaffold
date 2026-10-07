wiki 기반 질의응답. 답변 본문을 화면에 출력하고 사본을 `output/`에 저장합니다 (`wiki/`는 수정하지 않음). 승격은 `--loop` 후보 정리 후 `/review`로 처리합니다. Triggers: ask, query, question, search wiki, 질문, 검색, 답변

## 사용법

```
/ask [질문]
/ask [질문] --slides      # Marp 슬라이드 형식 출력
/ask [질문] --chart       # matplotlib 차트 포함
/ask [질문] --html        # 인터랙티브 standalone HTML 출력
/ask [질문] --eli12       # 12살 눈높이: 비유·쉬운 문체·도식·교훈 절 (다른 옵션과 함께 사용)
/ask [질문] --loop        # output 끝에 승격 후보만 정리 (wiki 수정 없음)
/ask [질문] --no-loop     # deprecated alias; 기본 동작과 동일
```

## 처리 순서

### Step 1: 질문 분석

`$ARGUMENTS`에서 질문과 옵션 플래그 분리 (`--slides`, `--chart`, `--html`, `--eli12`, `--loop`, `--no-loop`).
질문의 핵심 키워드와 관련 개념 파악.

### Step 2: 관련 wiki 파일 탐색

1. `wiki/index.md` 읽어 관련 개념/주제 파악
2. Grep으로 키워드 검색: `wiki/concepts/`, `wiki/topics/`
3. 관련 wiki 파일들 읽기 (백링크 포함)

### Step 3: 답변 생성

wiki 내용을 기반으로 답변 작성. wiki에 없는 내용은 추정/창작하지 말고 "위키에 해당 내용 없음"으로 명시.
`--eli12` 가 있으면 Step 4 의 「눈높이 옵션」 규칙을 따라 쓴다.

### Step 4: 답변 출력 + 파일 저장

**답변 본문은 응답에 그대로 출력한다. `output/` 저장은 병행되는 부수효과다.**
파일 경로만 보고하고 본문을 생략하지 않는다.

예외: `--slides` / `--html` / `--chart` 는 렌더 산출물이므로 화면에는 파일 경로와 핵심 요지만 출력한다.

#### 출력 형식 선택

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
- 도식이 길면(대략 15노드 초과) mermaid 블록을 `<details>` 로 접는다. 생성한 도식의 PNG 첨부는 하지 않는다 — `output/*.png` 는 gitignore 대상이다

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

#### 눈높이 옵션 — `--eli12` (12살 눈높이)

다른 옵션과 함께 쓸 수 있다(`--slides`·`--html` 동시 사용 불가는 그대로). Step 3 의 위키 근거 규칙도 그대로다 — 비유와 도식은 설명을 돕는 장치이고 근거를 대신하지 않는다.

- 독자: 이 주제를 처음 보는 12살. 전문 용어는 처음 나올 때 한 번 풀어 쓴다.
- 문체: 짧은 문장, 쉬운 단어, 한 문장에 한 가지 (ASD-STE100 을 80% 정도로 누그러뜨린 수준).
- 비유: 답변 본문의 내용 `## 절`마다 `12살 비유:` 로 시작하는 문단 하나(교훈·참조·Promotion 절은 제외). 절이 없는 짧은 답변과 `--slides` 는 전체에 하나 이상.
- 교훈: 답변 본문의 마지막(`---` 와 `## 참조 위키 파일` 앞)에 `## 교훈과 제안` 절. 항목마다 `[위키 근거]`(위키 페이지에 있는 내용) 또는 `[제안]`(위키 근거에서 끌어낸 행동 제안)을 붙인다. `[제안]` 에도 위키에 없는 사실 주장은 쓰지 않는다.
- 도식: 관계·흐름·순서를 설명하면 도식을 하나 이상 넣는다. 기본 마크다운 출력에서는 같은 도식을 화면에는 ASCII 코드 블록(표시 폭 60칸 이내, 한글은 2칸)으로, `output/` 파일에는 mermaid 로 낸다. 화면 본문과 파일 본문은 도식 형식만 다르다.
- `--slides`·`--chart`·`--html` 과 함께: ASCII/mermaid 쌍 규칙은 빼고(각 형식의 기존 도식 규칙을 따른다) 위 독자·문체·비유·교훈 규칙을 적용한다. 화면 출력은 Step 4 의 기존 예외(경로와 요지만)를 따른다.
- `--html` 과 함께: 큰 그림, 적은 글. mermaid 도식을 설명 글보다 앞에 둔다. 저장 위치는 `output/report-YYYYMMDD-HHmm.html` 그대로이고 claude.ai Artifact 로 게시하지 않는다.

예: `/ask LLM Wiki 는 어떻게 동작하나 --eli12`

### Step 5: Review 후보 정리

기본 동작은 읽기 전용입니다. `/ask`는 `wiki/`를 직접 생성/수정하지 않습니다.

`--loop` 플래그가 있으면 output 파일 끝에 `## Promotion Candidates` 섹션을 추가합니다:
- 신규 개념 후보
- 기존 wiki 보완 후보
- 출처/근거로 쓰인 wiki 파일
- 권장 후속 명령: `/review output/<파일명>.md`

`--loop`가 없으면 output 파일 끝에 `Knowledge Promotion: not requested`를 기록합니다.
`--no-loop`는 하위 호환 플래그로 허용하되 기본 동작과 동일하게 처리합니다.

### Step 6: 리뷰 후속 안내

승격 후보가 있더라도 `/ask`는 output 파일에 후보만 남긴다.
wiki 반영은 사람이 `/review output/<파일명>.md`를 실행하고 승인한 뒤에만 수행한다.

### 완료 후 보고

답변 본문 뒤에 붙는 꼬리표다. 본문을 대신하지 않는다.

- 생성된 output 파일 경로
- 참조한 wiki 파일 목록
- 승격 후보 요약 또는 "없음"
- wiki 변경: 없음 (`/review` 승인 전까지 `/ask`는 읽기 전용)

### 작업 로그 업데이트

`log.md` (프로젝트 루트) 파일 끝에 다음 형식으로 append:

```
## [YYYY-MM-DD] ask | [질문 요약]
- refs: [참조한 wiki 파일들]
- output: output/[파일명]
- promotion: [승격 후보 요약 또는 "요청 안 함"]
```
