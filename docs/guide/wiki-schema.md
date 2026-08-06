# Wiki Schema Guide

## Required Fields

```yaml
title: "Concept Name"
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: []
sources: []
verified: false
confidence: medium
```

## Optional Claim/Evidence Fields

```yaml
claim_status: source_backed
evidence_level: secondary
last_verified: YYYY-MM-DD
review_due: YYYY-MM-DD
```

## Allowed Values

| field | allowed values | meaning |
|---|---|---|
| `claim_status` | `source_backed`, `inferred`, `disputed`, `speculative`, `human_declared` | Whether the page's main claims are directly sourced, inferred, contested, exploratory, or manually declared by the user. |
| `evidence_level` | `primary`, `secondary`, `internal_note`, `ai_synthesis` | Strength and origin of the evidence. |

## Section-Level Sources

Use section-level source lists when a concept page mixes multiple raw inputs or combines raw facts with AI synthesis:

```markdown
## 핵심 내용

내용...

출처:
- raw/example.md#relevant-section
- output/answer-YYYYMMDD-HHmm.md
```

## Source Ledger

`wiki/_meta/source-ledger.md` is a generated traceability view maintained by `/lint`.

```markdown
# Source Ledger

| source | kind | compiled | wiki pages | trust | notes |
|---|---|---:|---|---|---|
| raw/example.md | raw | true | wiki/concepts/example.md | secondary | compiled by /compile |
```

## Policy

- `/compile` may add optional fields for newly generated pages.
- `/review` may add or update optional fields for promoted output insights.
- `/lint` reports missing optional fields as migration warnings only.
- `/lint` reports whether `wiki/_meta/source-ledger.md` exists and whether required `sources` fields are missing.
- Do not bulk-edit every existing wiki file only to add these fields.
