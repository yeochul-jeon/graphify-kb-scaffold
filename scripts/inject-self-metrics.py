#!/usr/bin/env python3
"""자기 측정 문서(`self_measuring: true`)의 **현재 상태 수치**를 마커 사이에 주입.

배경: 저장소 자신을 측정하는 wiki 문서는 컴파일 한 번으로 표가 낡는다. 수치가 본문에
박혀 있으면 사람 승인(`verified: true`)이 곧 낡을 값에 권위를 얹는다
(`wiki/_meta/suggested-investigations.md` #17). 그 근본 해결이 이 스크립트다 —
수치를 본문에서 떼어내 생성 시점에 주입하고, 승인 대상을 안정적인 서술로 한정한다.

## 경계는 절이 아니라 **주장의 시제**다

- **현재 상태** 수치("지금 개념이 몇 개인가") → 이 스크립트가 주입한다. 사람이 손대지 않는다
- **이력·사건 기록** 수치("그때 680쌍이 덮어써졌다") → 동결. 사람 영역이며 갱신 대상이 아니다

따라서 한 문서 안에 두 영역이 공존하는 것이 정상이고, 마커가 그 경계를 표시한다.

## 마커 문법

    <!--m:concepts-->282<!--/m-->                     인라인 (문장·표 셀 안)

    <!--m:metrics_table-->
    | ... 스크립트가 통째로 재작성 ...
    <!--/m-->                                          블록

`m:` 뒤 이름이 METRICS 레지스트리에 없으면 **실패한다**(오타가 조용히 통과하지 않게).

## `last_verified` 를 건드리지 않는 이유

`.claude/rules/wiki-concepts.md` §자기 측정 문서 3항은 사람이 수치를 갱신할 때
`last_verified` 를 함께 올리라고 규정하지만, **자동 주입 경로는 예외다**:

- `last_verified` 를 채우면 그 파일이 `/lint` 의 **사람 승인 대기 큐**에 자동 편입된다.
  빌드가 사람의 작업 큐를 만들어내는 구조가 된다
- 규칙상 `review_due` 는 `last_verified` 를 채운 주체가 채운다 — 자동 bump 는
  사람이 지정한 재검토 기한을 **빌드마다 조용히 연장**한다

대신 실측 시점을 `measured_at` 마커로 본문에 남긴다. 두 문서의 블록쿼트가 요구하는
"수치 인용 시 실측 시점을 함께 읽을 것" 은 이것으로 충족된다.

## 멱등성

값이 바뀌지 않으면 파일을 쓰지 않는다 — `measured_at` 만 다른 경우도 변경으로 치지
않는다. 안 그러면 매 빌드가 `wiki/` 를 더럽혀 `ALLOW_WIKI_EDIT=1` 우회가 상시화된다.

같은 이유로 `graphify-build.sh --cluster-only` 는 이 패스를 **건너뛴다**. Louvain 이
비결정이라 그 모드는 입력이 그대로여도 커뮤니티 수를 흔들고(실측 840→839→837),
저장소가 이미 노이즈로 규정한 값이 승인 문서의 본문 diff 로 새어 들어온다.
따라서 커뮤니티 수는 **직전 전체 빌드 시점** 값이다.

## 측정 대상에서 `graphify-out/` 을 뺀 이유 (2026-08-11, 원장 #62)

디스크 행은 원래 `raw/` · `graphify-out/` · `wiki/` 셋을 쟀는데 **`graphify-out/` 하나
때문에 `--check` 가 상시 `exit 1`** 이었다. 원인은 반올림 진동이 아니라 **자기 참조**다 —
`graphify-out/` 은 빌드가 그 자리에서 다시 쓰는 디렉터리이고, 이 스크립트는 그 빌드의
**마지막 단계**로 돈다. 주입 시점 크기를 적는 순간 `graph.json`·`GRAPH_REPORT.md`·
`.rebuild.lock` 이 그 뒤/그 사이에 바뀌어 **적자마자 값이 낡는다**(2026-08-10 실측:
커밋값 42MB / 같은 시점 `du -sh` 41MB).

🔴 **상시 1 은 진짜 낡음을 가린다.** `verified` 가 신호를 잃었던 것과 같은 구조이므로,
값을 손으로 맞추는 것(진동하므로 다음 빌드에 다시 어긋나고 원인이 숨는다)도
허용 오차를 두는 것(*"얼마나 틀려야 낡은 것인가"* 라는 새 임계값이 회차 간 수치를
다시 움직인다 — #10·#24)도 택하지 않았다. **재는 것을 그만뒀다.**

⚠️ **`raw/`·`wiki/` 는 같은 문제가 없다** — 빌드가 그 둘을 재작성하지 않는다. 문제는
*"디스크 크기를 잰다"* 가 아니라 **"빌드가 바꾸는 대상을 빌드 중에 잰다"** 였다.
이 행이 답하던 질문(*"저장소가 얼마나 큰가"*)은 남은 두 값으로 이미 답해진다.

⚠️ **`BASELINE_0727['disk']` 의 세 값은 그대로 둔다** — 동결된 이력값이라 재계산·삭제
대상이 아니다. 대신 현재 열이 두 값이 된 비대칭을 표 안에 명시한다.

사용:
    scripts/graphify-py.sh scripts/inject-self-metrics.py           # 주입
    scripts/graphify-py.sh scripts/inject-self-metrics.py --check   # 낡았으면 exit 1
"""
import os, re, sys, json, glob, importlib.util
from collections import Counter
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wiki_scan import tags as _wiki_tags  # 태그 파싱 정본 (원장 #64) — 직접 짜지 말 것

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIKI = os.path.join(ROOT, "wiki")
GRAPH = os.path.join(ROOT, "graphify-out", "graph.json")

MARKER = re.compile(r"(<!--m:([A-Za-z0-9_]+)-->)(.*?)(<!--/m-->)", re.S)
FM = re.compile(r"^---\n(.*?)\n---", re.S)

# `/lint` 가 세는 검증 6필드. 부착률 분모/분자 정의는 여기가 유일 출처다.
VERIFY_FIELDS = ("verified", "confidence", "claim_status",
                 "evidence_level", "last_verified", "review_due")

# §실측 표의 '2026-07-27 초판' 열 — 동결된 이력값이라 재계산 대상이 아니다.
BASELINE_0727 = {
    "counts":    "265 / 6 / 293",
    "graph":     "9,638 / 10,868 / 784",
    "origin":    "`raw/` 4,906 · `wiki/` 3,983 · `docs/` 409 · 기타 242",
    "relation":  "`contains` 8,578 · `references` 1,176 · "
                 "`conceptually_related_to` 420 · `wikilink` 409",
    "wikilink":  "1,402 / 1,403 (99.9%)",
    "backlinks": "1,477 (255 블록)",
    "tags_used": "933종",
    "tags_pref": "518행",
    "disk":      "107MB / 28MB / 18MB",
}


# ── 측정 ────────────────────────────────────────────────────────────────────

def _load(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _frontmatter(text):
    m = FM.match(text)
    if not m:
        return {}
    return dict(re.findall(r"^([a-z_]+):\s*(.*)$", m.group(1), re.M))


def _cross_edge_stats(graph):
    """rebuild-cross-edges.py 의 정의를 그대로 import 해서 쓴다.

    후보 쌍을 여기서 다시 세면 그 패스의 정의와 갈라진다 — `/lint` §재측정 규율 2항.
    """
    spec = importlib.util.spec_from_file_location(
        "rebuild_cross_edges", os.path.join(ROOT, "scripts", "rebuild-cross-edges.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    pairs, missing, _nonode = mod.compute_pairs(graph)
    occupied = {tuple(sorted((l["source"], l["target"])))
                for l in graph["links"] if l.get("relation") != mod.RELATION}
    new = sum(1 for k in pairs if k not in occupied)
    return {"pairs": len(pairs), "new": new,
            "existing": len(pairs) - new, "unresolved": missing}


def _backlink_stats():
    """wiki/backlinks.md 파싱. rebuild-backlinks.py 가 방금 쓴 파일이라 정의가 일치한다."""
    text = _load(os.path.join(WIKI, "backlinks.md"))
    blocks = len(re.findall(r"^##\s*\[\[", text, re.M))
    entries = len(re.findall(r"^-\s*\[\[", text, re.M))
    return {"blocks": blocks, "entries": entries}


def _tag_stats(wiki_files):
    """프리페이스 '행 수' 와 frontmatter 실사용 '종 수' 는 서로 다른 측정이다.

    §실측 표 초판이 이 둘을 한 행에 섞어 값(행 530)과 재현 방법(frontmatter 집계)이
    어긋나 있었다. 스크립트가 둘 다 내므로 쪼개서 보고한다.
    """
    rows = re.findall(r"^\|\s*`#([^`]+)`\s*\|", _load(os.path.join(WIKI, "index.md")), re.M)
    used = Counter()
    for p in wiki_files:
        fm = FM.match(_load(p))
        if not fm:
            continue
        # 🔴 정규식을 여기 다시 쓰지 않는다 — 이 파서가 `wiki_scan.tags` 의 원본이며
        #    사본이 늘면 한쪽만 고쳐져 검사기끼리 다른 값을 낸다(원장 #43·#64).
        for t in _wiki_tags(_load(p)):
            used[t] += 1
    return {"rows": len(rows), "distinct": len(set(rows)), "used": len(used)}


def _verify_stats(wiki_files):
    attached = true = 0
    lv_null = 0
    for p in wiki_files:
        d = _frontmatter(_load(p))
        if all(k in d for k in VERIFY_FIELDS):
            attached += 1
        if d.get("verified", "").strip() == "true":
            true += 1
        if d.get("last_verified", "").strip() in ("", "null"):
            lv_null += 1
    total = len(wiki_files)
    return {"attached": attached, "total": total, "true": true,
            "false": total - true, "lv_null": lv_null,
            "false_pct": 100.0 * (total - true) / total if total else 0.0}


def _du(rel):
    import subprocess
    out = subprocess.run(["du", "-sh", os.path.join(ROOT, rel)],
                         capture_output=True, text=True).stdout
    if not out:
        return "?"
    size = out.split("\t")[0].strip()
    return size + "B" if size[-1:].isalpha() and not size.endswith("B") else size


def collect():
    concepts = sorted(glob.glob(os.path.join(WIKI, "concepts", "*.md")))
    topics = sorted(glob.glob(os.path.join(WIKI, "topics", "*.md")))
    raws = sorted(glob.glob(os.path.join(ROOT, "raw", "*.md")))
    wiki_files = concepts + topics

    graph = json.loads(_load(GRAPH))
    nodes, links = graph["nodes"], graph["links"]
    comms = {n.get("community") for n in nodes if n.get("community") is not None}
    origin = Counter((n.get("source_file") or "").split("/")[0] for n in nodes)
    relation = Counter(l.get("relation") for l in links)

    xe = _cross_edge_stats(graph)
    bl = _backlink_stats()
    tg = _tag_stats(wiki_files)
    vf = _verify_stats(wiki_files)

    n = lambda v: f"{v:,}"
    top_origin = " · ".join(f"`{k}/` {n(v)}" for k, v in origin.most_common(5))
    top_relation = " · ".join(f"`{k}` {n(v)}" for k, v in relation.most_common(5))

    m = {
        "measured_at":          date.today().isoformat(),
        "concepts":             str(len(concepts)),
        "topics":               str(len(topics)),
        "raw_files":            str(len(raws)),
        "wiki_files":           str(len(wiki_files)),
        "nodes":                n(len(nodes)),
        "links":                n(len(links)),
        "communities":          n(len(comms)),
        "wikilink_pairs":       n(xe["pairs"]),
        "wikilink_new":         n(xe["new"]),
        "wikilink_existing":    n(xe["existing"]),
        "wikilink_unresolved":  str(xe["unresolved"]),
        "backlink_entries":     n(bl["entries"]),
        "backlink_blocks":      str(bl["blocks"]),
        "preface_rows":         str(tg["rows"]),
        "preface_distinct":     str(tg["distinct"]),
        "tags_in_use":          str(tg["used"]),
        "fields_attached":      f"{vf['attached']}/{vf['total']}",
        "verified_true":        str(vf["true"]),
        "verified_false_ratio": f"{vf['false']}/{vf['total']}",
        "verified_false_pct":   f"{vf['false_pct']:.1f}%",
        "last_verified_null":   str(vf["lv_null"]),
    }

    b = BASELINE_0727
    m["metrics_table"] = "\n".join([
        "",
        "| 항목 | 값 | 2026-07-27 초판 | 재현 방법 |",
        "|---|---|---|---|",
        f"| 개념 / 주제 / raw | {m['concepts']} / {m['topics']} / {m['raw_files']} "
        f"| {b['counts']} | `ls wiki/concepts/*.md \\| wc -l` |",
        f"| 그래프 노드 / 엣지 / 커뮤니티 | {m['nodes']} / {m['links']} / {m['communities']} "
        f"| {b['graph']} | `graph.json` 파싱 |",
        f"| 노드 출처 분포 | {top_origin} | {b['origin']} | `source_file` 접두 집계 |",
        f"| 관계 분포 | {top_relation} | {b['relation']} | `relation` 집계 |",
        f"| wikilink → 엣지 적재 | **후보 {m['wikilink_pairs']}쌍 전건 적재** "
        f"(신규 `wikilink` {m['wikilink_new']} + 기존 엣지 보유 {m['wikilink_existing']}). "
        f"미해결 {m['wikilink_unresolved']}건은 **미작성 개념 링크** "
        f"| {b['wikilink']} | `rebuild-cross-edges.py` 의 `compute_pairs()` |",
        f"| backlinks | {m['backlink_entries']} 엔트리 ({m['backlink_blocks']} 블록) "
        f"| {b['backlinks']} | `backlinks.md` 파싱 |",
        f"| 태그 — 실사용 | {m['tags_in_use']}종 | {b['tags_used']} "
        f"| frontmatter `tags:` 집계 |",
        f"| 태그 — 프리페이스 | {m['preface_rows']}행 (고유 {m['preface_distinct']}종) "
        f"| {b['tags_pref']} | `index.md` 태그 표 행 집계 |",
        f"| 디스크 | `raw/` {_du('raw')} · `wiki/` {_du('wiki')} "
        f"| {b['disk']} (`raw/` / `graphify-out/` / `wiki/`) "
        f"| `du -sh` — 🔴 `graphify-out/` 은 **재지 않는다**(원장 #62) |",
        "",
    ])
    return m


# ── 주입 ────────────────────────────────────────────────────────────────────

def targets():
    out = []
    for p in sorted(glob.glob(os.path.join(WIKI, "**", "*.md"), recursive=True)):
        if _frontmatter(_load(p)).get("self_measuring", "").strip() == "true":
            out.append(p)
    return out


def render(text, metrics, path):
    unknown = []

    def sub(mo):
        name = mo.group(2)
        if name not in metrics:
            unknown.append(name)
            return mo.group(0)
        return mo.group(1) + metrics[name] + mo.group(4)

    new = MARKER.sub(sub, text)
    if unknown:
        raise SystemExit(
            f"✗ {os.path.relpath(path, ROOT)}: 알 수 없는 마커 {sorted(set(unknown))} "
            f"— METRICS 레지스트리에 없다")
    return new


def date_neutral(text, old_text):
    """`measured_at` 만 다른 경우를 '변경 없음' 으로 보기 위해 옛 날짜로 되돌린 사본."""
    olds = MARKER.findall(old_text)
    prev = next((v for _o, name, v, _c in olds if name == "measured_at"), None)
    if prev is None:
        return text
    return MARKER.sub(
        lambda mo: mo.group(1) + prev + mo.group(4) if mo.group(2) == "measured_at"
        else mo.group(0), text)


def main():
    check = "--check" in sys.argv
    metrics = collect()
    files = targets()
    if not files:
        print("[inject-self-metrics] 대상 없음 (self_measuring: true)", file=sys.stderr)
        return 0

    stale = []
    for p in files:
        old = _load(p)
        new = render(old, metrics, p)
        rel = os.path.relpath(p, ROOT)
        if not MARKER.search(old):
            print(f"  · {rel}: 마커 없음 — 건너뜀", file=sys.stderr)
            continue
        if date_neutral(new, old) == old:
            print(f"  · {rel}: 최신", file=sys.stderr)
            continue
        stale.append(rel)
        if not check:
            with open(p, "w", encoding="utf-8") as f:
                f.write(new)

    if check and stale:
        print(f"✗ 수치가 낡았다: {', '.join(stale)}", file=sys.stderr)
        return 1
    print(f"[inject-self-metrics] {len(files)}개 문서 · "
          f"{'낡음' if check else '갱신'} {len(stale)}건 (측정 {metrics['measured_at']})",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
