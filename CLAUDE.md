@AGENTS.md

<!--
이 파일에는 규칙 본문을 쓰지 않는다. 본문의 단일 원본은 AGENTS.md 이며 위 한 줄로 불러온다.

왜 이 구조인가
- Claude Code 는 `AGENTS.md` 를 직접 읽지 않고 `CLAUDE.md` 만 읽는다. 공식 문서가
  이 경우에 대해 "create a CLAUDE.md that imports it so both tools read the same
  instructions without duplicating them" 을 지시한다.
- Codex CLI 는 `AGENTS.md` 를 읽는다.
- 따라서 이 한 줄이 두 도구가 같은 원본을 보게 하는 유일한 연결점이다.

규칙을 고칠 때
- `AGENTS.md` 를 고친다. 여기에 본문을 다시 쓰면 두 벌이 되어 갈라진다.
- Claude Code 에만 해당하는 지시가 생기면 이 주석 아래에 절을 만들어 추가한다.

경위 (2026-08-19 통합)
- 그 전에는 두 파일이 각각 20줄짜리 거의 같은 내용이었고, 실측 결과 14번째 줄이
  이미 갈라져 있었다. 두 판이 각각 다른 실패 사례를 담고 있어 병합 시 둘 다 보존했다.
- 전파 설정도 함께 고쳤다 — `scripts/sync-scaffold.sh` 의 목록에 `CLAUDE.md` 만 있고
  `AGENTS.md` 가 없어서, 이 구조 그대로 전파하면 대상 저장소가 없는 파일을 불러오게 된다.

이 주석은 컨텍스트에 실리지 않는다 (Claude Code 가 블록 주석을 제거한 뒤 주입한다).
-->
