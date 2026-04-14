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
3. **일반 URL** (`http://` 또는 `https://` 시작): `WebFetch`로 가져와 마크다운 변환
4. **로컬 파일 경로**: 해당 파일을 `raw/`로 복사
5. **텍스트/없음**: 사용자에게 내용 직접 입력 요청

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

### 저장 처리

1. 제목을 kebab-case 파일명으로 변환 (예: "Attention Is All You Need" → `attention-is-all-you-need.md`)
2. 파일명 중복 시 `-2`, `-3` 등 suffix 추가
3. 이미지가 포함된 경우 아래 이미지 핸들링 규칙 적용

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
---
```

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
