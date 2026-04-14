# 트러블슈팅 — 자주 막히는 지점

> 설치·실행 중 막혔을 때 이 문서를 먼저 확인하세요.
> 빠른 설정은 [docs/tutorial.md](../tutorial.md), 전체 구조는 [docs/architecture.md](../architecture.md)를 참고하세요.

---

## 1. `pyproject.toml`이나 `requirements.txt`가 없어요

**현상**: 다른 Python 프로젝트처럼 `pip install -e .`나 `pip install -r requirements.txt`를 찾는데 없다.

**이유**: 이 저장소는 Python 패키지가 아닙니다.
`graphify-kb`는 **마크다운 볼트 + shell 스크립트 + Claude 슬래시 커맨드**로 구성됩니다.
Python 그래프 엔진(`graphifyy`)은 외부 pip 패키지로, `/graphify` 커맨드를 처음 실행할 때 자동으로 설치됩니다.

**해결**: 별도 Python 패키지 설치 없이 바로 사용하세요.

```bash
git clone https://github.com/yeochul-jeon/my-knowledge-base.git
cd my-knowledge-base
# 끝. Claude Code에서 /ingest 로 시작하면 됩니다.
```

---

## 2. `/ingest`가 동작하지 않아요

**현상**: 터미널에 `/ingest https://...`를 입력했더니 "명령어를 찾을 수 없습니다" 같은 오류가 나온다.

**이유**: 슬래시 커맨드는 **Claude Code 세션 내부**에서만 동작합니다. 일반 zsh/bash 터미널에서는 실행할 수 없습니다.

**해결 A**: Claude Code 터미널을 열고 입력하세요.

```bash
# 프로젝트 디렉토리에서
claude           # Claude Code 세션 시작
# 세션 안에서:
/ingest https://example.com
```

**해결 B**: 일반 터미널에서 CLI 래퍼를 사용하세요.

```bash
./scripts/kb.sh ingest https://example.com
```

> `kb.sh`가 내부적으로 `claude "/ingest ..."` 를 호출하므로 `claude` CLI가 PATH에 있어야 합니다.

---

## 3. macOS에서 `pip install`이 실패해요 (PEP 668)

**현상**:
```
error: externally-managed-environment
× This environment is externally managed
```

**이유**: macOS Sonoma 이후 Homebrew Python은 시스템 패키지 관리자와 충돌을 막기 위해 pip 직접 설치를 제한합니다.

**해결 A** (권장): venv를 만들어 그 안에 설치하세요.

```bash
python3 -m venv ~/.venv/graphify
~/.venv/graphify/bin/pip install graphifyy
```

이후 `/graphify` 커맨드를 실행할 때 이 venv의 Python을 사용하도록 `graphify-out/.graphify_python` 파일에 경로를 기록하세요:

```bash
echo "~/.venv/graphify/bin/python3" > graphify-out/.graphify_python
```

**해결 B** (간편): `--break-system-packages` 플래그를 사용하세요 (비권장이지만 테스트 목적으로 허용 가능).

```bash
pip3 install graphifyy --break-system-packages
```

**해결 C**: pipx를 사용하세요.

```bash
brew install pipx
pipx install graphifyy
```

---

## 3-1. Python 버전이 3.10 미만이에요

**현상**:
```
ModuleNotFoundError: No module named 'graphify'
# 또는
SyntaxError: match statement requires Python 3.10+
```

**이유**: `graphifyy` v0.4.13+는 Python 3.10 이상이 필요합니다.

**해결**:

```bash
python3 --version          # 현재 버전 확인
brew install python        # 최신 Python 설치 (macOS)
pyenv install 3.11 && pyenv global 3.11   # 또는 pyenv 사용
```

설치 후 `bash scripts/graphify-bootstrap.sh` 를 다시 실행하면 새 인터프리터 경로가 저장됩니다.

---

## 3-2. `graphify install` 명령이 CLAUDE.md를 덮어썼어요

**현상**: `/graphify` 실행 후 `CLAUDE.md` 나 `.claude/settings.json` 내용이 변경되었다.

**이유**: `graphify install` (또는 `graphify claude install`) 명령은 Claude Code 통합 훅을 파일에 자동 주입합니다. 이 프로젝트처럼 이미 커스텀 설정을 보유한 경우 기존 내용을 덮어씁니다.

**복구 방법**:

```bash
git diff CLAUDE.md .claude/settings.json   # 변경 내용 확인
git checkout CLAUDE.md .claude/settings.json   # 이전 버전으로 복원
```

**예방**: `graphify install` 명령을 이 프로젝트에서는 실행하지 마세요. 자세한 내용은 [docs/guide/graphify.md](graphify.md) 설치 섹션 참고.

---

## 4. pre-commit hook이 커밋을 차단해요

**현상**:
```
⚠️  wiki/ 파일이 staged되어 있습니다.
wiki/는 LLM 전용 영역입니다. 직접 편집 후 커밋하려는 것이 맞나요? (y/N)
```

**이유**: `bash scripts/setup-hooks.sh` 설치 후 `wiki/` 파일을 staged하면 경고가 표시됩니다.

**해결 A**: 의도한 수정이면 `y`를 입력하세요.

**해결 B**: Claude Code가 자동 커밋할 때 막히면 환경 변수를 설정하세요.

```bash
ALLOW_WIKI_EDIT=1 git commit -m "feat: wiki 수동 수정"
```

**해결 C**: hook을 완전히 비활성화하려면:

```bash
git config --unset core.hooksPath
```

---

## 5. `graphify-out/`이 오래된 정보를 보여요

**현상**: 새 파일을 추가했는데 `GRAPH_REPORT.md`나 `graph.html`에 반영이 안 됨.

**이유**: graphify-out/은 자동으로 갱신되지 않습니다. 수동 재빌드가 필요합니다.

**해결**: 다음 중 하나를 실행하세요.

```
# Claude Code 세션에서
/graphify . --update

# 또는 일반 터미널에서 (Python 직접 호출)
python3 -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"
```

> CLAUDE.md 규칙: 코드 파일을 수정한 뒤에는 재빌드 명령을 실행하세요.

**팁**: `.graphify_python` 파일이 있으면 그 경로의 Python 인터프리터를 사용합니다. 수동 Python 호출 전에 확인하세요:

```bash
cat graphify-out/.graphify_python   # 예: /Users/cjenm/.venv/graphify/bin/python3
```

---

## 6. ANTHROPIC_API_KEY가 필요한가요?

**현상**: "API key not found" 오류가 발생하거나, 키 설정 방법을 모르겠다.

**설명**:

| 상황 | API 키 필요 여부 |
|---|---|
| Claude Code 세션에서 `/ingest`, `/compile`, `/ask` 실행 | **불필요** — Claude Code 세션 자체가 Anthropic 인증 제공 |
| `/graphify`로 처음 그래프 빌드 (LLM 호출 포함) | 필요할 수 있음 |
| `graphify . --update` 증분 재빌드 (캐시된 파일만) | **불필요** |
| `--mcp` 플래그로 외부 에이전트 연동 | 필요 |

**해결**: Claude Code에 이미 로그인된 상태라면 별도 설정이 필요 없습니다.
graphifyy 엔진이 별도 API 키를 요구하는 경우:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

`.zshrc`나 `.bashrc`에 추가하면 영구 설정됩니다.

---

## 7. Windows에서 `scripts/kb.sh`가 실행 안 돼요

**현상**: `bash: ./scripts/kb.sh: not found` 또는 줄바꿈 문제.

**이유**: `kb.sh`는 bash 기준으로 작성되었으며 macOS/Linux를 전제합니다.

**해결**:
- **WSL** (Windows Subsystem for Linux)을 설치하고 그 안에서 실행하세요.
- **Git Bash**에서 실행하면 대부분 동작합니다.
- 슬래시 커맨드는 CLI 래퍼 없이도 Claude Code 세션 안에서 직접 사용할 수 있습니다.

---

## 8. `.graphify_python` 파일은 뭔가요?

**현상**: `graphify-out/` 디렉토리에 `.graphify_python` 파일이 있는데 모르겠다.

**역할**: graphify가 사용할 Python 인터프리터 경로를 기록합니다.
macOS에서 여러 Python이 설치된 경우 올바른 인터프리터를 사용하도록 고정합니다.

```bash
cat graphify-out/.graphify_python
# 예: /usr/local/bin/python3
# 또는: /Users/user/.venv/graphify/bin/python3
```

**수동 재빌드 전**: 이 파일에 기록된 Python으로 호출하면 호환성 문제를 예방할 수 있습니다:

```bash
$(cat graphify-out/.graphify_python) -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"
```

---

## 9. `./scripts/kb.sh`가 "Permission denied"를 반환해요

**해결**:

```bash
chmod +x scripts/kb.sh
```

---

## 10. wiki/ 파일이 자꾸 "verified: false" 상태예요

**설명**: 이는 버그가 아닙니다. `/compile`이 생성하는 wiki 파일은 기본적으로 `verified: false`입니다.

내용을 직접 읽고 정확하다고 판단하면 파일을 열어 수정하세요:

```yaml
verified: true    # 사람이 검토 완료
```

Claude는 이 값을 자동으로 변경하지 않습니다. 검증은 사람의 몫입니다.

---

## 해결이 안 될 때

1. `./scripts/kb.sh status`로 현재 볼트 상태를 확인하세요.
2. `logs/DEV_LOG_YYYYMMDD.md`에서 최근 작업 이력을 확인하세요.
3. `graphify-out/GRAPH_REPORT.md`의 Knowledge Gaps 섹션에서 연결 문제를 파악하세요.
4. Claude Code 세션에서 오류 메시지를 붙여넣고 질문하세요.

---

## 관련 문서

- [docs/tutorial.md](../tutorial.md) — 단계별 설치·실행 가이드
- [docs/architecture.md](../architecture.md) — 전체 구조 이해
- [docs/guide/commands.md](commands.md) — 슬래시 커맨드 레퍼런스
- [docs/guide/graphify.md](graphify.md) — graphify 상세 가이드
