# AI Memory Stack Boundaries

This guide documents memory-layer responsibilities only. It does not require installing Mem0, Claude Code auto memory, or any other external memory service.

| Layer | Current path/tool | Stores | Do not store |
|---|---|---|---|
| Agent procedural rules | `AGENTS.md`, `CLAUDE.md`, `.claude/rules/` | How agents should work, test, and stay safe | Long documents, conversation transcripts |
| Project knowledge | `wiki/`, `docs/` | Architecture, decisions, concepts, command behavior | Raw private data |
| Source archive | `raw/` | Original inputs intended for compilation | Sensitive data outside ignored private zones |
| Work memory | `.work-log/`, `log.md` | Session notes, dev-log, decisions | Permanent project facts without review |
| User/global memory | future Mem0 or equivalent | Stable user preferences and cross-project patterns | PR diffs, API docs, full chat logs |
| Claude project auto memory | future Claude Code auto memory | Local project observations and debugging patterns | Secrets, source archives |
