#!/usr/bin/env python3
"""`wiki/_meta/source-ledger.md` 생성 — `raw/` 출처와 이를 인용하는 wiki 페이지의 추적 뷰.

reporting-only 정책(`.claude/commands/lint.md` §16, 2026-07-09)의 첫 실제 구현.
`sources:` 는 인라인 `[...]` 과 YAML 블록 리스트 두 표기를 모두 파싱한다(`wiki-concepts.md`
경고 — 인라인만 보면 블록 표기 파일이 "출처 없음"으로 오판된다).

사용:
    scripts/graphify-py.sh scripts/generate-source-ledger.py            # 파일 쓰기
    scripts/graphify-py.sh scripts/generate-source-ledger.py --check    # 낡았으면 exit 1
"""
import os, re, sys, glob, argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FM = re.compile(r"^---\n(.*?)\n---", re.S)
OUT_PATH = os.path.join(ROOT, "wiki", "_meta", "source-ledger.md")


def frontmatter(path):
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return {}
    m = FM.match(text)
    return {"body": m.group(1) if m else "", "text": text}


def get_scalar(body, key):
    m = re.search(rf"^{key}:\s*(.*)$", body, re.M)
    return m.group(1).strip().strip("\"'") if m else None


def get_sources(body):
    """인라인 `[a, b]` 와 블록 리스트 `- a\\n- b` 둘 다 파싱."""
    m = re.search(r"^sources:\s*(\[.*?\])\s*$", body, re.M)
    if m:
        items = [s.strip().strip("\"'") for s in m.group(1).strip("[]").split(",")]
        return [s for s in items if s]
    m = re.search(r"^sources:\s*\n((?:^\s*-\s*.+\n?)+)", body, re.M)
    if m:
        return [re.sub(r"^\s*-\s*", "", ln).strip().strip("\"'")
                for ln in m.group(1).splitlines() if ln.strip()]
    return []


def load_raw():
    out = {}
    for p in sorted(glob.glob(os.path.join(ROOT, "raw", "**", "*.md"), recursive=True)):
        rel = os.path.relpath(p, ROOT)
        if "/_templates/" in rel or "/attachments/" in rel:
            continue
        fm = frontmatter(p)
        body = fm["body"]
        out[rel] = {
            "compiled": get_scalar(body, "compiled") or "false",
            "verbatim": get_scalar(body, "verbatim"),
        }
    return out


def load_wiki_citations():
    """raw 경로 -> [(wiki_path, evidence_level), ...]"""
    citations = {}
    for p in sorted(glob.glob(os.path.join(ROOT, "wiki", "concepts", "*.md")) +
                     glob.glob(os.path.join(ROOT, "wiki", "topics", "*.md"))):
        rel = os.path.relpath(p, ROOT)
        fm = frontmatter(p)
        body = fm["body"]
        level = get_scalar(body, "evidence_level") or "?"
        for src in get_sources(body):
            src = src.strip()
            if src.startswith("raw/"):
                citations.setdefault(src, []).append((rel, level))
    return citations


def build_rows(raw, citations):
    rows = []
    for src, meta in raw.items():
        cited = citations.get(src, [])
        wiki_pages = ", ".join(c[0] for c in cited) if cited else "—"
        levels = sorted(set(c[1] for c in cited))
        trust = "/".join(levels) if levels else "unused"
        notes_parts = []
        if meta["verbatim"] == "true":
            notes_parts.append("verbatim: true")
        elif meta["verbatim"] == "false":
            notes_parts.append("verbatim: false")
        else:
            notes_parts.append("verbatim 필드 없음")
        if not cited:
            notes_parts.append("어느 wiki 페이지도 인용하지 않음")
        notes = " · ".join(notes_parts)
        rows.append((src, "raw", meta["compiled"], wiki_pages, trust, notes))
    return sorted(rows, key=lambda r: r[0])


def render(rows):
    lines = ["# Source Ledger", "",
             "> **reporting-only, 자동 생성** — `scripts/generate-source-ledger.py`. 손으로 편집하지 말 것,",
             "> 재실행하면 덮어쓴다. 정책: `.claude/commands/lint.md` §16 · `docs/guide/wiki-schema.md` §Source Ledger.",
             ""]
    total = len(rows)
    compiled = sum(1 for r in rows if r[2] == "true")
    unused = sum(1 for r in rows if r[3] == "—")
    lines.append(f"raw 총 {total}건 · compiled {compiled}건 · 어느 wiki 도 인용 안 함 {unused}건.")
    lines.append("")
    lines.append("| source | kind | compiled | wiki pages | trust | notes |")
    lines.append("|---|---|---:|---|---|---|")
    for src, kind, comp, pages, trust, notes in rows:
        lines.append(f"| {src} | {kind} | {comp} | {pages} | {trust} | {notes} |")
    lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="낡았으면 exit 1, 쓰지 않는다")
    args = ap.parse_args()

    raw = load_raw()
    citations = load_wiki_citations()
    rows = build_rows(raw, citations)
    content = render(rows)

    if args.check:
        old = open(OUT_PATH, encoding="utf-8").read() if os.path.exists(OUT_PATH) else None
        if old != content:
            print("[source-ledger] 낡음 — scripts/generate-source-ledger.py 재실행 필요", file=sys.stderr)
            sys.exit(1)
        print("[source-ledger] 최신")
        return

    old = open(OUT_PATH, encoding="utf-8").read() if os.path.exists(OUT_PATH) else None
    if old == content:
        print("[source-ledger] 변경 없음")
        return
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[source-ledger] 갱신 완료 — raw {len(rows)}건")


if __name__ == "__main__":
    main()
