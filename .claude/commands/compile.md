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
  - `raw/Clippings/` 는 **미처리 캡처 인박스**다 — `/ingest <경로>` 승격으로 `raw/` 에 올라온 뒤에 컴파일 대상이 된다 (`.claude/rules/raw-ingest.md` §Web Clipper 인박스)

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
claim_status: source_backed
evidence_level: secondary
last_verified: null
review_due: null
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

`claim_status: source_backed`는 raw 원문에서 직접 컴파일된 페이지에만 사용한다.
그 외 합성 중심 페이지는 `evidence_level: ai_synthesis`로 표시한다.

> 위 두 줄은 **`/compile` 워크플로의 기본값**이지 전체 허용값이 아니다.
> `claim_status`/`evidence_level` 의 **전체 열거값과 판정 기준은 `.claude/rules/wiki-concepts.md` 가 단일 출처**다
> 다른 값을 쓴 파일을 만나면 **그 절을 열어 대조하라 — 이 문서만 근거로 "enum 위반" 으로 판정하지 말 것.** (여기에 허용값 목록을 다시 적지 않는 이유: 사본이 늘면 낡는다. lint 4~8회차가 이 문서만 보고 5회 연속 오보한 것이 그 결과다.)
>
> 특히 `claim_status` 는 `sources` 구성만 본다 — 본문이 출처 범위를 넘는 것은 `evidence_level: ai_synthesis` 로만 표현하고 `claim_status` 는 건드리지 않는다 (같은 절 §두 필드의 역할 분담).

> **`evidence_level: primary` 는 출처 도메인이 아니라 본문으로 판정한다.** 출처가 공식문서·명세·논문 원문이어도, **본문에 그 출처를 넘어서는 서술이 하나라도 있으면 `secondary` 로 낮춘다**(우선순위 규칙). 2026-07-27 실측에서 `aws.amazon.com` 인용 8건 중 primary 는 0건이었고(전부 `/blogs/` 해설글), `linked-data`·`hipporag` 는 출처가 1차 자료인데도 본문이 범위를 넘어 secondary 가 됐다.
>
> 기존 파일에 4필드를 소급 부착할 때는 `scripts/attach-claim-metadata.py` 를 쓴다 (`.claude/rules/wiki-concepts.md` §부착 도구와 파생 규칙).

### Step 3.5: 이미지 참조 처리

raw 파일 frontmatter에 `images` 필드가 있거나 본문에 이미지 참조(`![...]`)가 있는 경우:

🔴 **이미지를 복사하지 않는다.** 첨부의 단일 저장 위치는 `raw/attachments/<소스명>/` 이며 `wiki/attachments/` 는 쓰지 않는다 — 정본은 `.claude/rules/raw-ingest.md` §디렉터리 구조다.

1. **상대경로 참조**: wiki 문서에서 원본 위치를 그대로 가리킨다
   - `![alt](../../raw/attachments/<소스명>/img-01.png)` (`wiki/concepts/` 기준 2단계 상위)
2. **선택적 참조**: 해당 개념에서 실제로 인용하는 이미지만 건다
3. **이미지 없으면 건너뛰기**: 이미지 관련 처리 생략

### Step 3.6: 충실도 감사 (서브에이전트 위임)

Step 3 에서 새로 만들었거나 절을 추가한 페이지마다 본문을 raw 원문과 대조하는 감사를 위임한다.

1. **위임 단위**: 페이지당 sonnet 서브에이전트 1개. 넘길 것은 셋뿐이다 — 그 페이지(기존 페이지면 이번에 추가한 절 이름을 프롬프트에 적어 범위를 정한다), 근거 raw 전문 경로(여러 개면 모두), `docs/guide/compile-audit-standards.md`. `:N` 인용은 `sed -n N,Mp` 로 직접 열어 확인하게 지정한다
   - 프롬프트에 «파일을 고치지 말고 표준 파일의 보고 형식으로 지적만 보고하라»를 넣는다 — 아래 3번(반영)의 재확인을 거치지 않은 수정이 들어가지 않게
   - 표준 파일은 **감사하는 쪽에만** 넘긴다. 컴파일하는 쪽(이 세션)은 집필 전에 표준 파일을 읽어 두지 않는다 — 표준은 구현자가 아니라 리뷰어 컨텍스트에 둔다(Matt Pocock 의 에이전트 PR 리뷰 발표 원칙). 집필 컨텍스트를 늘리지 않고, 다음 retro 가 표준을 미리 본 집필이 아니라 평소 집필의 지적 분포를 재게 하려는 것이다
2. **제외 목록**을 프롬프트에 적는다: `log.md`·`compile-log`·`wiki/index.md`·`wiki/backlinks.md`·`wiki/_meta/`·`output/`·`.claude/reports/`·`docs/plan/`·`graphify-out/`, 다른 `wiki/concepts/` 의 내용(관련 개념 링크는 대상 파일이 있는지 `ls` 로만 확인한다). 결론이 적힌 파일을 읽으면 감사가 기대값을 확인해 주는 데 그친다(`AGENTS.md` §위임 규율). 표준 파일의 «출처» 줄이 가리키는 `output/` 도 열지 않는다
3. **반영**: 지적마다 해당 raw 줄을 `sed -n` 으로 다시 열어 사실인지 확인한 뒤 고친다. 서브에이전트 보고의 수치·줄번호는 그대로 옮기지 않는다
4. **기록**: 반영 후 frontmatter `last_verified: <대조한 날>`, §출처에 대조 범위 한 줄(추가한 절만 감사했으면 그 절 이름을 범위에 적는다 — 부분 대조도 `last_verified` 를 적는다, `.claude/rules/wiki-concepts.md` §대조가 부분일 때).
   지적 목록은 한 건씩 유형 코드(서브에이전트 보고의 A~H)와 함께 같은 세션 `/lint` 보고서의 «이번 회차에 조치한 것» 절(형식은 `.claude/commands/lint.md` §보고서 형식)에 적는다 — 다음 retro(`output/compile-audit-retro-*.md`, graphify-kb 정본 저장소에만 있다)의 입력이다. 이 세션에서 `/lint` 를 돌리지 않으면 아래 §작업 로그 업데이트의 `- audit:` 줄에 적는다
   - 대조 범위 예: `- 대조 범위(2026-10-07, 서브에이전트 sonnet 충실도 감사): 본문 전 절의 구체 주장과 :N 인용 범위를 raw 전문과 대조. 지적 17건 중 원음 미확인 표현 한정·누락 복원·인용 범위 2건 보정을 반영. 원음(영상 음성)·슬라이드 대조는 범위 밖`

### Step 4: wiki/index.md 업데이트

- 새로 생성된 개념/주제를 테이블에 추가
- 최근 변경 이력 상단에 추가
- 파일 상단 "총 개념 수" 카운터 갱신

### Step 5: wiki/backlinks.md 재생성

🔴 **손으로 고치지 않는다.** 스크립트를 호출한다:

```bash
scripts/graphify-py.sh scripts/rebuild-backlinks.py
```

결정론적 strict-inbound 역인덱싱으로 파일 전체를 다시 만든다 — 멱등이며 빈 블록을 남기지 않고 큐레이션 주석을 이월한다. 증분 편집(항목 제거 후 재삽입)은 드리프트를 만들어 금지됐다: `.claude/rules/wiki-concepts.md` §연동 의무 · `.claude/commands/lint.md` §7.

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
- audit: [같은 세션에서 /lint 를 돌리지 않았을 때만 — Step 3.6 지적을 «유형 코드 · 위치 · raw 줄 · 고친 내용» 으로 한 건씩, 여러 건이면 줄을 나눠 `  - ` 로]
```
