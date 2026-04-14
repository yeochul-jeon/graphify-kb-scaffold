# Getting Started — graphify-kb 팀 온보딩

graphify 기반 지식 저장소를 빠르게 셋업하는 가이드입니다.

---

## 전제조건

| 도구 | 버전 | 설치 방법 |
|---|---|---|
| [Claude Code](https://claude.ai/code) | 최신 | 공식 사이트 |
| Python | **3.10+** | `brew install python` 또는 pyenv (graphifyy 요구사항) |
| git | 2.x+ | 보통 기본 설치됨 |
| gh (GitHub CLI) | 선택 | `brew install gh` |

---

## 1. Clone

```bash
git clone https://github.com/yeochul-jeon/graphify-kb-scaffold.git
cd graphify-kb-scaffold
```

> 팀 저장소를 직접 fork해서 사용하려면:
> ```bash
> gh repo fork yeochul-jeon/graphify-kb-scaffold --clone --remote
> ```

---

## 2. Bootstrap — Python 의존성 + git hooks

```bash
bash scripts/graphify-bootstrap.sh   # graphifyy 설치 + 인터프리터 경로 캐시
bash scripts/setup-hooks.sh          # .githooks/ 활성화 (wiki 편집 가드)
```

---

## 3. 개인 Claude Code 설정 복사

```bash
cp .claude/settings.local.json.example .claude/settings.local.json
```

이후 `.claude/settings.local.json` 을 열어 `YOUR_USER` 를 자신의 macOS 계정명으로 교체하세요.

---

## 4. 첫 자료 투입

**URL로 바로 수집:**
```
/ingest https://example.com/article
```

**직접 파일 드롭:**  
`raw/` 폴더에 `.md`, `.pdf`, `.txt` 등 파일을 넣으면 됩니다.  
템플릿: `raw/_templates/raw-template.md` 참고.

---

## 5. 컴파일 — raw → wiki

```
/compile
```

`wiki/concepts/` 와 `wiki/topics/` 에 구조화된 문서가 생성됩니다.

---

## 6. 질의

```
/ask "질문 내용"
```

결과는 `output/` 에 자동 저장됩니다.

---

## 7. 그래프 빌드 (선택)

```
/graphify
```

`graphify-out/graph.html` 을 브라우저에서 열면 지식 그래프를 시각화할 수 있습니다.

---

## CLI 요약표

| 명령어 | 동작 |
|---|---|
| `/ingest <url>` | URL 수집 → `raw/` |
| `/compile` | `raw/` → `wiki/` 컴파일 |
| `/ask "질문"` | wiki 기반 Q&A |
| `/lint` | wiki 품질 점검 |
| `/capture` | 현재 대화 인사이트 추출 |
| `/review` | `output/` 승격 → wiki |
| `/graphify` | 지식 그래프 빌드 |

---

## 문제해결

→ [`docs/guide/troubleshooting.md`](guide/troubleshooting.md)

---

## 업스트림 graphify

이 스케폴드가 사용하는 지식그래프 엔진 — `graphifyy` (pip 패키지, double-y):

| 링크 | 내용 |
|---|---|
| [github.com/safishamsi/graphify](https://github.com/safishamsi/graphify) | 공식 GitHub (v0.4.13, MIT) |
| [pypi.org/project/graphifyy/](https://pypi.org/project/graphifyy/) | PyPI |
| [graphify.net/kr/](https://graphify.net/kr/) | 공식 홈페이지 |

> `[video]` extras: `pipx install 'graphifyy[video]'` → YouTube URL · MP4 · MP3 등 지원  
> `[office]` extras: `pipx install 'graphifyy[office]'` → DOCX · XLSX 지원

---

## 팀 저장소에 업로드

```bash
gh repo create <조직명>/<저장소명> --public --source=. --push
```
