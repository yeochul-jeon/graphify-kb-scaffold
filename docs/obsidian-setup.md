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

| 설정            | 값                    |
| ------------- | -------------------- |
| Vault         | `my-knowledge-base`  |
| Note location | `raw/`               |
| Note name     | `{{title}}` (제목 그대로) |
| File format   | Markdown             |

### 템플릿 설정

Web Clipper에서 아래 템플릿을 사용하면 raw 파일에 자동으로 올바른 frontmatter가 추가된다:

```
---
title: {{title}}
source_url: {{url}}
ingested_date: {{date:YYYY-MM-DD}}
compiled: false
compiled_date: null
tags: []
---

{{content}}
```

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
웹 페이지 발견
   ↓
Chrome에서 Web Clipper 아이콘 클릭
   ↓
raw/[제목].md 자동 저장 (compiled: false 포함)
   ↓
Claude Code에서: /compile
   ↓
wiki/concepts/ 또는 wiki/topics/ 파일 생성
   ↓
Obsidian 그래프 뷰에서 지식 네트워크 시각화
```

---

## 6. 오염 방지 원칙 (Obsidian 사용 시)

- `wiki/` 폴더 파일은 **Obsidian에서 직접 편집하지 않는다**
  - Claude Code가 관리하는 영역이므로 직접 수정 시 컴파일 이력과 불일치 발생 가능
- `raw/` 폴더는 자유롭게 편집 가능 (Web Clipper, 직접 작성 모두 OK)
- `output/` 결과물은 읽기용. 검증 후 wiki에 피드백은 Claude Code를 통해 진행

---

## 7. .gitignore 참고

`.obsidian/` 폴더는 gitignore에 포함되어 있어 Obsidian 설정이 버전 관리에 포함되지 않는다.
팀 공유가 필요하다면 `.obsidian/` 항목을 제거하고 커밋.
