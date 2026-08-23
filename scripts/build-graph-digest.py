#!/usr/bin/env python3
"""
scripts/build-graph-digest.py
graph.json 에서 Top-10 god nodes / community hubs 를 추출해
graphify-out/GRAPH_DIGEST.md 를 갱신한다.

실행:
  scripts/graphify-py.sh scripts/build-graph-digest.py

주의: graph.json 은 대용량(~414 KB)이지만 이 스크립트만 읽는다.
      에이전트가 직접 graph.json 을 열면 안 된다 (.claude/rules/graphify-pipeline.md 참조).
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GRAPH_JSON = REPO_ROOT / "graphify-out" / "graph.json"
OUT_MD = REPO_ROOT / "graphify-out" / "GRAPH_DIGEST.md"
TOPICS_DIR = REPO_ROOT / "wiki" / "topics"
REPORT_MD = REPO_ROOT / "graphify-out" / "GRAPH_REPORT.md"

TOP_N = 10
HUB_NODES = 4  # community hub 당 대표 노드 수


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_graph() -> dict:
    with GRAPH_JSON.open(encoding="utf-8") as f:
        return json.load(f)


def load_community_names() -> dict[int, str]:
    """Parse GRAPH_REPORT.md for community names.

    Looks for lines like: ### Community 5 - "AI Engineering & Agent Design"
    Returns {community_id: name} dict. Falls back to empty dict if not found.
    """
    if not REPORT_MD.exists():
        return {}
    names: dict[int, str] = {}
    pattern = re.compile(r"^###\s+Community\s+(\d+)\s+-\s+\"(.+?)\"", re.MULTILINE)
    text = REPORT_MD.read_text(encoding="utf-8")
    for m in pattern.finditer(text):
        names[int(m.group(1))] = m.group(2)
    return names


def compute_degrees(nodes: list[dict], links: list[dict]) -> dict[str, int]:
    """Return node_id → total degree (in + out)."""
    deg: dict[str, int] = {n["id"]: 0 for n in nodes}
    for lnk in links:
        src, tgt = lnk.get("source") or lnk.get("_src"), lnk.get("target") or lnk.get("_tgt")
        if src in deg:
            deg[src] += 1
        if tgt in deg:
            deg[tgt] += 1
    return deg


def top_god_nodes(nodes: list[dict], deg: dict[str, int], n: int = TOP_N) -> list[dict]:
    ranked = sorted(nodes, key=lambda nd: deg.get(nd["id"], 0), reverse=True)
    return ranked[:n]


def community_hubs(
    nodes: list[dict],
    deg: dict[str, int],
    comm_names: dict[int, str],
    n: int = TOP_N,
    k: int = HUB_NODES,
) -> list[dict]:
    """Return top-n communities (by size) with representative node labels and names."""
    by_comm: dict[int, list[dict]] = defaultdict(list)
    for nd in nodes:
        comm = nd.get("community")
        if comm is not None:
            by_comm[comm].append(nd)

    # sort communities by size descending
    sorted_comms = sorted(by_comm.items(), key=lambda kv: len(kv[1]), reverse=True)

    result = []
    for comm_id, members in sorted_comms[:n]:
        top_members = sorted(members, key=lambda nd: deg.get(nd["id"], 0), reverse=True)[:k]
        result.append({
            "community": comm_id,
            "name": comm_names.get(comm_id, f"Community {comm_id}"),
            "size": len(members),
            "top_nodes": [m["label"] for m in top_members],
        })
    return result


def read_topics() -> list[dict]:
    """Parse wiki/topics/*.md frontmatter for title and tags."""
    topics = []
    if not TOPICS_DIR.exists():
        return topics
    for path in sorted(TOPICS_DIR.glob("*.md")):
        content = path.read_text(encoding="utf-8")
        title_m = re.search(r"^title:\s*(.+)$", content, re.MULTILINE)
        tags_m = re.search(r"^tags:\s*\[([^\]]+)\]", content, re.MULTILINE)
        title = title_m.group(1).strip() if title_m else path.stem
        tags_raw = tags_m.group(1) if tags_m else ""
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()][:4]
        topics.append({
            "title": title,
            "file": f"../wiki/topics/{path.name}",
            "tags": tags,
        })
    return topics


def count_graph_stats(nodes: list[dict], links: list[dict]) -> tuple[int, int, int]:
    node_count = len(nodes)
    edge_count = len(links)
    community_ids = {nd.get("community") for nd in nodes if nd.get("community") is not None}
    return node_count, edge_count, len(community_ids)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render(
    stats: tuple[int, int, int],
    god_nodes: list[dict],
    deg: dict[str, int],
    hubs: list[dict],
    topics: list[dict],
    comm_names: dict[int, str],
) -> str:
    node_count, edge_count, comm_count = stats
    ts = datetime.now().strftime("%Y-%m-%d")

    lines: list[str] = []

    lines.append(f"# Graph Digest — graphify-kb ({ts})")
    lines.append("")
    lines.append(
        f"> **빠른 탐색용 요약**. {node_count} nodes · {edge_count} edges · {comm_count} communities."
    )
    lines.append("> 상세 커뮤니티 설명·엣지 목록은 [GRAPH_REPORT.md](GRAPH_REPORT.md) 참조.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Top 10 God Nodes (최다 연결)")
    lines.append("")
    lines.append("| # | 개념 | 엣지 수 | 커뮤니티 |")
    lines.append("|---|------|--------|---------|")
    for i, nd in enumerate(god_nodes, 1):
        d = deg.get(nd["id"], 0)
        comm_id = nd.get("community")
        comm = comm_names.get(comm_id, f"Community {comm_id}") if comm_id is not None else "?"
        lines.append(f"| {i} | `{nd['label']}` | {d} | {comm} |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Top 10 Community Hubs (지식 군집)")
    lines.append("")
    lines.append("| 커뮤니티 | 크기 | 대표 개념 |")
    lines.append("|---------|------|---------|")
    for hub in hubs:
        nodes_str = ", ".join(f"`{n}`" for n in hub["top_nodes"])
        name = hub["name"]
        lines.append(f"| **{name}** | {hub['size']} | {nodes_str} |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Topics (최상위 주제 파일)")
    lines.append("")
    for t in topics:
        tags_str = ", ".join(t["tags"]) if t["tags"] else ""
        tag_part = f" — {tags_str}" if tags_str else ""
        lines.append(f"- [{t['title']}]({t['file']}){tag_part}")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("> **탐색 순서**: 이 파일 → `wiki/index.md` 태그 프리페이스 → `wiki/topics/` → 해당 `wiki/concepts/`")
    lines.append("> 심층 분석 필요 시: [GRAPH_REPORT.md](GRAPH_REPORT.md) (전체 커뮤니티·엣지)")
    lines.append(f">")
    lines.append(f"> *(자동 생성: `scripts/build-graph-digest.py` @ {ts})*")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if not GRAPH_JSON.exists():
        print(f"ERROR: {GRAPH_JSON} 없음. `graphify build` 를 먼저 실행하세요.", file=sys.stderr)
        sys.exit(1)

    print(f"Loading {GRAPH_JSON} ...", file=sys.stderr)
    g = load_graph()
    nodes = g.get("nodes", [])
    links = g.get("links", [])

    deg = compute_degrees(nodes, links)
    comm_names = load_community_names()
    god = top_god_nodes(nodes, deg)
    hubs = community_hubs(nodes, deg, comm_names)
    topics = read_topics()
    stats = count_graph_stats(nodes, links)

    content = render(stats, god, deg, hubs, topics, comm_names)

    OUT_MD.write_text(content, encoding="utf-8")
    line_count = content.count("\n")
    print(f"✓ {OUT_MD} 갱신 완료 ({line_count} lines)", file=sys.stderr)


if __name__ == "__main__":
    main()
