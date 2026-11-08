# Ratchet Rules (auto-grown by sprag)

같은 실수가 두 번 발생하면 여기에 한 줄 추가됩니다. 형식: "YYYY-MM-DD: <조건> → <행동>".

`sprag harness promote "<rule>"`로 룰을 추가하면 자동으로
이 파일에 append 됩니다.

이 파일은 CLAUDE.md의 `@` import로 매 세션 로드됩니다 — 즉 여기 있는 모든 줄이
매 요청마다 토큰을 씁니다. 날짜 뒤에 `[태그]`를 붙여두면 나중에 묶어서 정리할 수
있습니다: `- 2026-05-08: [video,tts] ...` →
`sprag harness prune --tag video` (삭제 아니라 ratchet-archive.md로 이동).

## Rules

