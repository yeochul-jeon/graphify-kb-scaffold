# Obsidian 연동 설정 가이드

이 저장소를 Obsidian 볼트로 열고 Web Clipper와 연동하는 방법.

---

## 1. Obsidian 볼트 열기

1. [Obsidian](https://obsidian.md) 설치 (무료)
2. Obsidian 실행 → **Open folder as vault** 선택
3. 이 저장소 루트 폴더(`my-knowledge-base/`) 선택
4. **Trust author and enable plugins** 클릭

이후 `wiki/` 폴더가 자동으로 Obsidian 그래프 뷰에 표시되고, `[[wikilink]]`가 클릭 가능한 링크로 렌더링된다.

---

## 2. 권장 Obsidian 설정

### Files & Links

| 설정 | 값 | 이유 |
|------|-----|------|
| Default location for new notes | `raw/` | 새 메모가 dirty zone에 생성되도록 |
| Default location for new attachments | `raw/attachments/` | 이미지 첨부 관리 |
| Use [[Wikilinks]] | ON | 백링크 호환성 |
| Detect all file extensions | OFF | .md만 관리 |

### Editor

| 설정 | 값 |
|------|-----|
| Readable line length | ON |
| Show frontmatter | ON (source mode) |

---

## 3. Obsidian Web Clipper 설치

### 설치

1. Chrome 웹 스토어에서 **Obsidian Web Clipper** 검색 후 설치
2. 확장 프로그램 아이콘 클릭 → **Settings** 진입

### 저장 위치 설정

| 설정            | 값                            |
| ------------- | ---------------------------- |
| Vault         | `my-knowledge-base` (실제 볼트명과 정확히 일치해야 한다) |
| Note location | `raw/Clippings/`             |
| Note name     | `{{title\|kebab\|safe_name}}` |
| File format   | Markdown                     |

> **왜 `raw/` 가 아니라 `raw/Clippings/` 인가.** `raw/Clippings/` 는 **미처리 캡처 인박스**다 — 클립은 여기 떨어지고, `/ingest` 승격으로 `raw/` 로 **이동**한 뒤에야 그래프·컴파일 대상이 된다. 규정은 `.claude/rules/raw-ingest.md` §Web Clipper 인박스 가 단일 출처다.

> **왜 `{{title}}` 이 아닌가.** 공백 든 파일명은 실제로 저장소 파서를 깨뜨린 전례가 있다(lint 38회차). `kebab` 필터가 공백·언더스코어를 `-` 로 바꾸고 소문자화하며, `safe_name` 이 `/ : # ^ [ ]` 등 파일시스템·Obsidian 금지문자를 지운다. **`kebab` 은 비ASCII를 버리지 않으므로 한글 제목도 안전하다**(음차 변환은 하지 않는다 — 공백만 하이픈이 된다). 어차피 최종 파일명은 승격 단계가 다시 정하므로, 인박스 파일명은 **파서 안전**만 만족하면 된다.

> **도메인별 템플릿 자동 선택**: Web Clipper 의 **Template triggers** 에 URL 패턴을 한 줄씩 넣으면 그 도메인에서 해당 템플릿이 자동 발동한다(예: YouTube·X 는 다른 템플릿).

### 템플릿 설정

템플릿은 **브라우저가 정직하게 채울 수 있는 필드만** 담는다. 나머지는 승격(`/ingest`) 단계가 채운다.

```
---
title: {{title}}
source_url: {{url}}
ingested_date: {{date|date:"YYYY-MM-DD"}}
author: {{author}}
published: {{published|date:"YYYY-MM-DD"}}
---

{{content}}
```

**왜 이것만인가** — 나머지 필수 필드는 브라우저가 채우면 거짓값이 박힌다:

| 필드 | 클리퍼가 못 채우는 이유 |
|---|---|
| `verbatim` / `verbatim_checked` | 규칙이 **기본값을 금지**한다 — 대조 없이 `true` 가 찍히는 것을 막기 위함. 승격 시점에 판정한다 |
| `tags` | 어휘를 **원문이 아니라 저장소에서** 가져와야 한다(`raw/_templates/raw-template.md` 참조). 브라우저는 저장소를 못 본다 — Interpreter(LLM 프롬프트 변수)도 저장소 접근이 없어 이 문제를 풀지 못한다 |
| `compiled` / `compiled_date` | `/compile` 이 관리하는 파이프라인 플래그다 |
| `images` | 첨부는 `raw/attachments/<소스명>/` 로 재배치되며 그 경로는 승격 시점에 정해진다 |

> 🔴 **`{{date:YYYY-MM-DD}}` 로 쓰지 마라.** 그건 Obsidian 코어 템플릿 문법이고 Web Clipper 는 `date:YYYY-MM-DD` 를 **변수 이름 전체**로 읽어 `Unknown variable` 로 실패한다(2026-08-22 실측). 날짜 형식은 **`date` 필터**로 준다 — `{{date|date:"YYYY-MM-DD"}}`.

> **속성 타입도 맞춰라.** Web Clipper 의 속성 타입이 YAML 직렬화를 바꾼다 — `author` 가 **List** 면 `author:` 아래 항목으로 떨어져 스칼라를 기대하는 raw 규격과 어긋난다. `title`·`source_url`·`author` 는 **텍스트**, `ingested_date`·`published` 는 **날짜**(«날짜 & 시간» 아님)로 둔다.

`author`·`published` 는 페이지 메타데이터에서 나오므로 값이 있으면 채워지고, 없으면 빈 값이 된다 — 빈 값은 승격 시 지운다.

**템플릿 적용 방법:**
1. Web Clipper Settings → **Templates** 탭
2. **Add template** → 위 내용 붙여넣기
3. 템플릿 이름: `knowledge-base`
4. 기본 템플릿으로 설정

---

## 4. 권장 Obsidian 플러그인

### 커뮤니티 플러그인 (선택 사항)

| 플러그인 | 역할 | 설치 방법 |
|----------|------|-----------|
| **Marp Slides** | `.marp.md` 파일을 슬라이드로 렌더링 | Community plugins → search "Marp" |
| **Dataview** | wiki 파일을 표/쿼리로 탐색 | Community plugins → search "Dataview" |
| **Graph Analysis** | 백링크 그래프 심화 분석 | Community plugins → search "Graph Analysis" |

### Dataview 플러그인 설정

`wiki/index.md` 하단에 Dataview 쿼리 블록이 포함되어 있어, 플러그인 활성화 시 동적 테이블로 렌더링된다.

1. Community plugins → **Dataview** 설치 및 활성화
2. Dataview Settings:
   - **Enable JavaScript Queries**: OFF (보안상 불필요)
   - **Enable Inline Queries**: ON (선택)
3. `wiki/index.md` 열기 → Reading View에서 다음 쿼리 확인:
   - 미검증 파일 목록 (`verified: false`)
   - 최근 30일 업데이트
   - 신뢰도별 분류 (`confidence: low/medium`)
   - 태그별 개념 수

> 일반 마크다운 뷰어(GitHub, VS Code)에서는 코드블록으로 표시되며 정적 테이블은 그대로 유지된다.

### Marp 플러그인 설정

`/ask [질문] --slides` 로 생성된 `.marp.md` 파일을 Obsidian에서 바로 미리보기:

1. Community plugins → **Marp Slides** 설치 및 활성화
2. `.marp.md` 파일 열기 → 우측 상단 슬라이드 아이콘 클릭

---

## 5. 작업 흐름 (Web Clipper → wiki)

```
웹 페이지 발견 (로그인 상태 그대로)
   ↓
Chrome에서 Web Clipper 아이콘 클릭
   ↓
raw/Clippings/[kebab-제목].md 저장          ← 미처리 인박스
   ↓
Claude Code에서: /ingest raw/Clippings/[파일]   ← 승격 (raw/ 로 이동)
   · 중복 검사(URL 축 + 제목 축) · verbatim 판정
   · tags 를 저장소 어휘에서 선택 · 이미지 재배치
   ↓
raw/[kebab-제목].md (frontmatter 완비)
   ↓
Claude Code에서: /compile
   ↓
wiki/concepts/ 또는 wiki/topics/ 파일 생성
   ↓
Obsidian 그래프 뷰에서 지식 네트워크 시각화
```

> **인박스를 모아뒀다가 묶어서 승격해도 된다.** `ls raw/Clippings/` 로 쌓인 클립을 확인한다. 관련 자료를 세트로 모아 컴파일하면 개별 아티클 단위보다 결과가 낫다는 것이 `wiki/concepts/satellite-vault-architecture.md` §00 Inbox 버퍼 의 관찰이다.

### 이 경로가 여는 것 — 인증 벽

`/ingest <URL>` 의 수집 3티어(Jina Reader → raw HTML → WebFetch)는 **전부 익명 요청**이라 로그인월·페이월·403/402 로 막힌 출처를 열지 못한다. 2026-08-22 실측으로 `raw/*.md` **18건**이 그 이유로 스텁이거나 반쪽이다.

**Web Clipper 는 사용자의 로그인 세션 안에서 돌기 때문에 이 계열을 여는 유일한 경로다.** 공개 URL 은 `/ingest <URL>` 이 더 싸므로(에이전트가 페이지를 컨텍스트로 읽지 않는다) 그대로 쓰고, 클리퍼는 막힌 출처에 쓴다.

---

## 6. 오염 방지 원칙 (Obsidian 사용 시)

- `wiki/` 폴더 파일은 **Obsidian에서 직접 편집하지 않는다**
  - Claude Code가 관리하는 영역이므로 직접 수정 시 컴파일 이력과 불일치 발생 가능
- `raw/` 폴더는 자유롭게 편집 가능 (Web Clipper, 직접 작성 모두 OK)
- `raw/Clippings/` **본문은 수정하지 않는다** — 승격 전 임시 보관 위치이며 캡처 원문 무결성을 지킨다. 고칠 것이 있으면 승격 후 `raw/` 에서 고친다
- `output/` 결과물은 읽기용. 검증 후 wiki에 피드백은 Claude Code를 통해 진행

---

## 7. .gitignore 참고

`.obsidian/` 폴더는 gitignore에 포함되어 있어 Obsidian 설정이 버전 관리에 포함되지 않는다.
팀 공유가 필요하다면 `.obsidian/` 항목을 제거하고 커밋.
