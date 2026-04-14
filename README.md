# graphify-kb

Andrej Karpathy 방식의 LLM 기반 개인 지식 베이스.
LLM이 "컴파일러" 역할을 하여 원본 자료를 구조화된 마크다운 위키로 변환한다.
벡터 DB 없이 파일 시스템 + LLM 직접 읽기만으로 동작.

> 원본 아이디어: [Andrej Karpathy 트윗](https://x.com/karpathy/status/2039805659525644595)

---

## 전제조건

| 도구 | 버전 | 용도 |
|---|---|---|
| [Claude Code](https://claude.ai/code) | 최신 | 슬래시 커맨드 런타임 |
| Python | **3.10+** | graphifyy 런타임 (`brew install python`) |
| Git | 2.x+ | 버전 관리 |

---

## 빠른 시작

### 1. 저장소 클론

```bash
git clone https://github.com/yeochul-jeon/graphify-kb-scaffold.git
cd graphify-kb-scaffold
```

### 2. Claude Code에서 실행

```bash
# 원본 자료 수집
/ingest https://example.com/article
/ingest https://www.notion.so/your-page-id
/ingest https://github.com/owner/repo

# wiki로 컴파일
/compile

# 질의응답
/ask 이 주제에서 가장 중요한 개념은?
/ask 개념 비교 슬라이드 만들어줘 --slides

# 품질 점검
/lint
/lint --fix

# 지식그래프 빌드 (선택, 처음 한 번)
/graphify .
# 이후 업데이트
/graphify . --update
```

### 3. Git Hooks 활성화 (권장)

```bash
bash scripts/setup-hooks.sh
```

`wiki/` 파일을 직접 편집할 때 경고를 표시하는 pre-commit hook이 활성화됩니다.

### 4. CLI wrapper 사용 (선택)

```bash
chmod +x scripts/kb.sh
./scripts/kb.sh status          # 현황 통계
./scripts/kb.sh ingest [URL]    # 자료 수집
./scripts/kb.sh compile         # wiki 컴파일
./scripts/kb.sh ask [질문]      # 질의응답
./scripts/kb.sh lint            # 품질 점검
```

---

## 디렉토리 구조

```
graphify-kb/
├── raw/                  # 원본 자료 (사람 + Web Clipper 추가)
│   ├── _templates/       # raw 파일 템플릿
│   └── attachments/      # 이미지 등 첨부 파일
├── wiki/                 # 컴파일된 지식 베이스 (Claude 전용)
│   ├── index.md          # 네비게이션 허브
│   ├── concepts/         # 개별 개념 파일
│   ├── topics/           # 상위 주제 파일
│   ├── backlinks.md      # 역참조 맵 (자동 생성)
│   └── _meta/
│       └── compile-log.md
├── output/               # Q&A 생성물 (답변, 슬라이드, 차트)
├── scripts/
│   └── kb.sh             # CLI wrapper
├── log/                  # 작업 로그
├── CLAUDE.md             # LLM 행동 지침
└── PLAN.md               # 프로젝트 설계 문서
```

---

## 슬래시 커맨드

| 커맨드 | 설명 |
|--------|------|
| `/ingest [URL\|Notion\|GitHub\|텍스트]` | 원본 자료 수집 → `raw/` |
| `/compile [파일명]` | `raw/` → `wiki/` 컴파일 |
| `/ask [질문] [--slides] [--chart] [--html]` | wiki 기반 질의응답 → `output/` |
| `/lint [--fix]` | wiki 품질 점검 및 자동 수정 |
| `/capture [주제]` | 대화 인사이트 → `raw/sessions/` |
| `/review [파일\|--list]` | `output/` 답변을 wiki로 승격 |
| `/dev-log [단계명]` | 작업 단계 → `logs/DEV_LOG_*.md` |
| `/graphify [. --update]` | 볼트 전체 → `graphify-out/` 지식그래프 빌드 |

---

## 워크플로우

```
자료 발견
   ↓
/ingest → raw/
   ↓
/compile → wiki/ (개념 추출, 백링크 생성)
   ↓
/ask → output/ (답변, 슬라이드, 차트)
   ↓           ↑
   └─ 새 인사이트 wiki 피드백 (지식 루프)
   ↓
/lint → 품질 점검 + 자동 수정
```

---

## Obsidian 연동

이 저장소는 Obsidian 볼트로 바로 사용할 수 있습니다.
자세한 설정 방법은 [docs/obsidian-setup.md](docs/obsidian-setup.md)를 참조하세요.

---

## 관련 문서

### 시작하기
- [docs/tutorial.md](docs/tutorial.md) — 초보자용 단계별 튜토리얼 (설치 → 첫 실행)
- [docs/architecture.md](docs/architecture.md) — 전체 시스템 구조 (3가지 구성 요소·데이터 플로우)

### 레퍼런스
- [docs/guide/commands.md](docs/guide/commands.md) — 슬래시 커맨드 8개 전체 레퍼런스
- [docs/guide/graphify.md](docs/guide/graphify.md) — 지식그래프 통합 상세 가이드
- [docs/guide/troubleshooting.md](docs/guide/troubleshooting.md) — 설치·실행 막힘 해결

### 설정
- [docs/obsidian-setup.md](docs/obsidian-setup.md) — Obsidian + Web Clipper 설정

### 설계
- [CLAUDE.md](CLAUDE.md) — LLM 행동 지침 (오염 방지 원칙 등)
- [wiki/index.md](wiki/index.md) — 지식 베이스 인덱스 (첫 `/compile` 후 자동 생성)

---

## 업스트림 graphify

| 링크 | 내용 |
|---|---|
| [github.com/safishamsi/graphify](https://github.com/safishamsi/graphify) | 공식 GitHub (v0.4.13, MIT) |
| [pypi.org/project/graphifyy/](https://pypi.org/project/graphifyy/) | PyPI — 패키지명 `graphifyy` (double-y) |
| [graphify.net/kr/](https://graphify.net/kr/) | 공식 홈페이지 |
