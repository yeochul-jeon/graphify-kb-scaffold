원본 자료를 `raw/` 폴더에 수집합니다. Triggers: ingest, save article, collect, add source, clip, URL 저장, 수집, 원본 추가

## 사용법

```
/ingest [URL | Notion URL | 텍스트 설명]
```

## 처리 규칙

### 입력 유형 판별

`$ARGUMENTS`를 분석해 다음 중 하나로 처리:

1. **Notion URL** (`notion.so` 포함): `mcp__claude_ai_Notion__notion-fetch`로 가져오기
2. **GitHub URL** (`github.com/` 포함): 아래 GitHub 처리 규칙 적용
3. **YouTube URL** (`youtube.com/watch`, `youtu.be/`, `youtube.com/shorts/` 포함): 아래 YouTube URL 처리 규칙 적용
4. **일반 URL** (`http://` 또는 `https://` 시작, 위 항목에 해당 없음): 아래 일반 URL 처리 규칙 적용
5. **로컬 파일 경로**: 해당 파일을 `raw/`로 복사
6. **텍스트/없음**: 사용자에게 내용 직접 입력 요청

### GitHub URL 처리 규칙

URL 형식 예시:
- 저장소: `https://github.com/owner/repo`
- 특정 파일: `https://github.com/owner/repo/blob/main/path/to/file.md`
- 특정 디렉토리: `https://github.com/owner/repo/tree/main/docs/`

**처리 순서:**

1. **URL 파싱**: `owner`, `repo`, 경로(있으면) 추출
2. **콘텐츠 수집** (우선순위 순):
   - 특정 파일 URL인 경우: 해당 파일만 `WebFetch`로 가져오기
     - GitHub raw URL로 변환: `https://raw.githubusercontent.com/owner/repo/main/path`
   - 저장소 또는 디렉토리 URL인 경우:
     a. `README.md` 가져오기 (raw URL 사용)
     b. `WebFetch`로 저장소 메인 페이지를 가져와 docs/, wiki/ 등 문서 디렉토리 탐지
     c. 탐지된 핵심 문서 파일 최대 5개 추가 수집 (CONTRIBUTING.md, docs/index.md 등)
3. **통합 마크다운 생성**: 수집한 파일들을 하나의 raw 파일로 병합
   - 각 파일 내용 앞에 `## [파일명]` 헤더 추가
   - 파일 간 `---` 구분선 삽입
4. **파일명 결정**: `owner-repo` 형식 (예: `anthropics-claude-code.md`)

**YAML Frontmatter 추가 필드:**
```yaml
github_repo: https://github.com/owner/repo
github_files: [README.md, docs/index.md, ...]
```

### YouTube URL 처리 규칙

**대상**: `youtube.com/watch?v=`, `youtu.be/`, `youtube.com/shorts/` 형식 URL

**처리 순서:**

1. `scripts/ingest-youtube.sh "<URL>"` 실행 (자막을 `youtube-transcript-api`로 직접 수집, 로그인/API 키 불필요)
2. **성공 시** (종료 코드 0): stdout이 자막 전문(텍스트). 이를 본문으로 raw 파일 생성
3. **실패 시** (종료 코드 0이 아님, 예: 자막 비활성·비공개 영상): 기존 방식대로 스텁 생성
   - 본문: 영상 제목(추정 가능하면) + URL만 기록, `<!-- 자막 수집 실패: 수동 입력 필요 -->` 주석 추가
   - 사용자에게 자막 수동 입력 또는 요약 붙여넣기 가능 여부 확인

**파일명 규칙**: `youtube-[video_id].md` (제목 kebab-case 규칙의 예외 — 자막 API로 영상 제목을 얻을 수 없어 ID 기반 고정)
**frontmatter `source_url`**: 원본 시청 URL 전체

### 일반 URL 처리 규칙

**처리 순서 (우선순위):**

1. `scripts/ingest-fetch.sh "<URL>"` 실행 (Jina AI Reader 1차 시도 → 실패 시 raw HTML로 자동 폴백)
2. **종료 코드 0** (성공): stdout이 본문. stderr 첫 줄의 `tier=` 표기로 어느 티어가 성공했는지 확인
   - `tier=1 (jina-reader)`: 이미 정제된 마크다운 — 사용 전 로그인월·페이월 미리보기·쿠키 동의 문구가 아닌 실제 기사 본문인지 확인할 것 (Jina는 대상 페이지를 그대로 렌더링하므로 페이월 미리보기도 "깔끔한 마크다운"으로 반환될 수 있음)
   - `tier=2 (raw-html)`: 원시 HTML — 본문을 추출해 마크다운으로 변환 (스크립트는 변환하지 않음). 로그인 페이지·빈 SPA 셸이 200으로 반환될 수 있으니 내용이 실제 기사인지 확인할 것
3. **종료 코드 1** (양쪽 티어 모두 실패): `WebFetch`로 마지막 시도
   - `WebFetch`도 실패(로그인월, 403/402 차단, 빈 셸 등)하면 사용자에게 URL 접근 불가를 알리고 내용 직접 붙여넣기 요청

**주의**: `WebFetch`는 결과를 소형 모델로 요약할 수 있어(내용이 크면 손실 발생) 원문 보존이 필요한 이 파이프라인에서는 최후의 수단으로만 사용한다.

### 저장 처리

1. **`source_url` 중복 검사** (파일명 변환보다 **먼저**) — 아래 §중복 `source_url` 검사
2. 제목을 kebab-case 파일명으로 변환 (예: "Attention Is All You Need" → `attention-is-all-you-need.md`)
3. 파일명 중복 시 `-2`, `-3` 등 suffix 추가
4. 이미지가 포함된 경우 아래 이미지 핸들링 규칙 적용

### 중복 `source_url` 검사

파일명 중복 검사만으로는 **같은 글을 다른 파일명으로 두 번 저장하는 것**을 막지 못한다. 저장 전에 URL 층위에서 확인한다.

**1) 정규화 후 비교** — 아래를 모두 무시하고 비교한다:

| 항목 | 예 |
|---|---|
| 스킴·`www.` | `http://www.a.com/x` ≡ `https://a.com/x` |
| 대소문자 (호스트만) | `A.COM` ≡ `a.com` |
| 끝 슬래시 | `/x/` ≡ `/x` |
| 퍼센트 인코딩 | `%EC%A7%88...` ≡ 디코딩된 한글 경로 |
| YouTube 표기 | `youtube.com/watch?v=ID` ≡ `youtu.be/ID` → **비디오 ID 로만 비교** |
| 모바일 서브도메인 | `m.blog.naver.com/x` ≡ `blog.naver.com/x` |
| AMP 경로 | `/amp/x`·`/x/amp` ≡ `/x` |
| 추적 파라미터 | `utm_*`·`fbclid`·`gclid`·`ref` 는 제거 후 비교 |
| 프래그먼트 | `#section` 은 제거 후 비교 |

경로 대소문자와 위에 열거되지 않은 쿼리스트링은 **구분한다** — `?tl=ko`·`?hl=ko`·`?id=N` 처럼 실제로 다른 문서를 가리키는 경우가 있다.

**2) 일치가 없으면** 그대로 저장 — 이하 절차 생략.

**3) 일치가 있으면 저장을 멈추고 보고한다.** 기존 파일의 `duplicate_url_verdict` 를 먼저 확인:

- **필드가 있으면** — 이미 판정된 그룹이다. 그 판정과 사유를 보여주고 신규 파일도 같은 `duplicate_url_group` 으로 편입할지 묻는다.
- **필드가 없으면** — 미판정이다. 기존 파일의 `title`·줄 수·`ingested_date` 를 제시하고 아래 3분기 중 사용자 선택을 받는다:

| 분기 | 조건 | 조치 | 기재할 `duplicate_url_verdict` |
|---|---|---|---|
| **중단** | 같은 글의 재수집이고 새로 얻는 내용이 없다 | 저장하지 않는다 | — (파일이 생기지 않음) |
| **공존** | 같은 출처를 소재로 한 다른 정리물이거나, 한쪽에만 있는 내용이 있다 | 저장하고 **그룹 전원**에 판정 3필드 기재 | `coexist` |
| **혼합 출처** | 신규 파일 내용이 `source_url` **하나로 대표되지 않는다** (다른 출처 내용이 섞여 URL 이 우연히 겹친 것) | 저장하고 판정 3필드 + `additional_sources` 기재. URL 을 모르면 **추정하지 말고** 확인 필요 상태로 적는다 | `mixed-origin` |
| **병합** | 한쪽이 다른 쪽의 상위집합이다 | 내용을 합치고 남길 파일을 정한다. **흡수된 파일을 삭제하면 `wiki/` 의 `sources:` 와 `[[raw/...]]` 인용을 반드시 함께 재매핑**하고, 삭제 대신 이력용으로 남길 경우 그 파일에 `merged` 를 기재한다 | `merged` (남길 때만) |

열거값 정의는 `.claude/rules/raw-ingest.md` §중복 `source_url` 판정 필드 가 단일 출처다.

> **혼합 출처 분기를 빠뜨리기 쉽다.** 겉보기엔 "같은 URL 의 두 정리물" 이라 공존으로 분류되지만, 실제로는 한쪽 파일의 `source_url` 이 그 내용을 대표하지 못하는 **메타데이터 결함**이다. 공존으로 적으면 원장에 틀린 사실이 남는다 — `youtube-karpathy-claude-md-secret.md` 가 이 케이스였다.

> **자동 거부·자동 suffix 금지.** 같은 URL 을 소재로 서로 다른 정리물을 만드는 것은 이 저장소의 정상 워크플로다. 2026-07-27 실측에서 중복 5쌍 전부가 양쪽에 고유 내용을 가진 `partial-overlap` 이었고 삭제가 정당한 쌍은 **0건**이었다. 하드 블록이었다면 정당한 인제스트를 막았을 것이다.

> **병합·삭제 판정은 본문 대조 없이 내리지 않는다.** 제목과 URL 이 문자 단위로 같아도 한쪽에만 있는 내용이 있을 수 있다 — 실제로 무신사 쌍이 그랬다(전문 캡처본이 원문의 규칙 1건을 누락, 요약본에만 남아 있었다).

### 이미지 핸들링

원본 자료에 이미지가 포함된 경우:

1. **이미지 저장 경로**: `raw/attachments/[article-name]/` 디렉토리 생성
   - `[article-name]`은 raw 파일명에서 `.md` 제외한 부분 (예: `attention-is-all-you-need`)
2. **이미지 다운로드**: 본문에 포함된 이미지 URL을 `curl`로 로컬 다운로드
   - 파일명: 원본 파일명 유지, 불명확하면 `img-01.png`, `img-02.png` 순번
   - 지원 형식: `.png`, `.jpg`, `.jpeg`, `.gif`, `.svg`, `.webp`
3. **마크다운 참조 변환**: 원본 URL을 상대 경로로 교체
   - 변환 전: `![alt](https://example.com/image.png)`
   - 변환 후: `![alt](attachments/article-name/image.png)`
4. **다운로드 실패 시**: 원본 URL 유지 + 주석 추가 `<!-- 이미지 다운로드 실패: URL -->`
5. **이미지 없는 자료**: attachments 디렉토리 미생성

### YAML Frontmatter 추가

모든 raw 파일에 다음 frontmatter를 반드시 추가:

```yaml
---
title: [추출한 제목]
source_url: [원본 URL 또는 "직접 입력"]
ingested_date: [오늘 날짜 YYYY-MM-DD]
compiled: false
compiled_date: null
tags: []
images: []  # 이미지 있으면 상대 경로 목록 (예: [attachments/article-name/img-01.png])
verbatim: [true | false]        # 필수 — 아래 §수집 시점 판정 참조. 기본값을 두지 않는다
verbatim_checked: [오늘 날짜]    # 필수 — verbatim 을 기재한 날
---
```

#### `verbatim` — 수집 시점에 판정한다 (2026-08-09 신설, 원장 #50)

**받은 것이 곧 원본인 순간이므로 판정에 대조 비용이 들지 않는다.** 방금 저장한 본문이 가져온 것 그대로면 `true`, 요약·발췌·재서술이 섞였으면 `false` 를 적고 **무엇이 빠졌는지 `note:` 에 적는다**(규격: `.claude/rules/raw-ingest.md` §`verbatim`).

🔴 **이 순간을 놓치면 되돌릴 수 없다.** http 출처에는 `github_ref` 같은 시점 고정 수단이 없어, 나중에 다시 받으면 **인제스트 시점 판이 아니라 그날 판**이 온다. 수집기가 차단되면(실례: `cncf.co.kr` 이 jina-reader 에 403) **수집 경로조차 재현되지 않는다.** 그 파일은 영구히 승인 체크리스트 0번 **(d) 고정 불가** 로 떨어진다 — **1회 비용이 영구 비용으로 바뀐다.**

⚠️ **`compiled: false` 처럼 고정 기본값을 주지 않는다.** 대조 없이 `true` 가 찍히면 이 필드가 신설된 이유가 그대로 사라진다(원장 #47 조치안 ③). **판단이 서지 않으면 필드를 비우지 말고 `false` + `note:` 로 사유를 적는다.**

### 완료 후 보고

- 저장된 파일 경로
- 파일 크기 (대략적인 단어/줄 수)
- 다음 단계 안내: `/compile [파일명]`

### 작업 로그 업데이트

`log.md` (프로젝트 루트) 파일 끝에 다음 형식으로 append:

```
## [YYYY-MM-DD] ingest | [자료 제목]
- source: [원본 URL 또는 "직접 입력"]
- saved: raw/[파일명].md
- size: [줄 수]줄
```

allowed-tools: Read, Write, Bash, WebFetch, mcp__claude_ai_Notion__notion-fetch
