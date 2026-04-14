## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- After modifying code files in this session, run `scripts/graphify-py.sh -c "from graphify.watch import _rebuild_code; from pathlib import Path; _rebuild_code(Path('.'))"` to keep the graph current
- /graphify skill은 프로젝트 오버라이드(.claude/skills/graphify/SKILL.md)를 사용하며, python 호출은 scripts/graphify-py.sh 경유.
- 업스트림 스킬 업데이트 시: `bash scripts/regen-graphify-skill.sh` 실행 후 Step 1 bootstrap 블록 수동 검증.
