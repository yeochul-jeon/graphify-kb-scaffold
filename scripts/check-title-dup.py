#!/usr/bin/env python3
"""`raw/` 제목 유사도로 **중복 후보를 보고**한다 — 판정은 사람이 한다 (원장 #55).

배경: `/ingest` 의 중복 검사는 정규화한 `source_url` 비교인데, `source_url` 이
`직접 입력` 계열이면 **같은 리터럴이 수십 건에 붙어 있어 비교가 성립하지 않는다.**
2026-08-10 에 같은 발표 2건이 그 사각지대로 들어왔고(`claude-code-well-usage` ↔
`claude-code-well-used-seminar` · `harness-engineering-hoyeon` ↔
`harness-engineering-team-attention`) **컴파일 단계에서 우연히** 발견됐다.

## 🔴 이것은 게이트가 아니라 **순위 매긴 보고서**다

**문턱으로 가를 수 없다는 것이 실측이다.** 2026-08-11 전수 측정:

| | 유사도 |
|---|---|
| 진양성 최저 (`claude-code-well-us*` 2건) | **0.444** |
| 위양성 최고 (`simon-willison-kb` ↔ `steph-ango-kb` 등) | **0.545** |
| 같은 저자 다른 자료 최고 (`Grace (InfoGrab)` 5건) | 0.493 |

**진양성 최저가 위양성 최고보다 낮다.** 어떤 단일 문턱도 두 집단을 가르지 못하므로
**자동 거부·자동 suffix 는 설계상 불가능**하며, 조치안이 *"하드 블록이 아니라 보고 후
사람 판정"* 으로 확정된 이유가 이것이다. `--threshold` 는 *판정 기준*이 아니라
**목록에 실을 하한**이다. 점수를 숨기지 않고 전부 찍는 이유도 같다.

## `author` 는 가중치이며, **정확 일치로 쓰면 안 된다** (2026-08-11 실측)

확정안의 *"`author` 는 있을 때만 가중"* 을 문자 그대로 **동일 문자열 비교**로 구현하면
**이 검사기가 겨냥한 진양성 2쌍이 전건 빠진다**:

    AI 1팀 김영동            vs  김영동
    이호연 (Builder, Team Attention)  vs  이호연 (Team Attention)

둘 다 같은 사람인데 문자열이 다르다. 그래서 **정규화 토큰 집합의 포함 관계**로 본다.
⚠️ **이 신호는 위양성도 함께 올린다** — `Grace (InfoGrab)` 5건은 저자가 완전히 같다.
**가중치이지 판별자가 아니다.**

## 후보 범위 — `직접 입력` 22 가 아니라 **41** 이다

⚠️ **원장 #55 의 *"표적 22 / 341"* 은 `source_url` 이 문자열 `직접 입력` 으로 시작하는
것만 센 값이다.** 같은 사각지대에 있는데 그 셈법에서 빠지는 것이 둘 더 있다:

| 형태 | 수 | 왜 같은 사각지대인가 |
|---|---:|---|
| `직접 입력…` | **22** | 원장이 센 것 |
| `manual (PDF: …)` · 로컬 절대경로 | **6** | URL 이 아니므로 **비교가 똑같이 무의미**하다 |
| `source_url` **필드 자체가 없음** | **13** | 비교할 값이 아예 없다 |
| **계** | **41 / 341** | 이 검사기의 후보 범위 |

🔴 **22 로 좁히면 `harness-engineering-seminar.md`(로컬 `.pdf` 경로)가 빠지는데**, 그
파일은 위 진양성 2쌍과 **같은 발표 계열**이고 실제로 최고 유사도 쌍(0.652)을 만든다.
**두 수치 다 맞다 — 정의가 다르다**(재측정 규율 3). 원장 숫자를 정정하지 않고 여기에
정의를 적는다.

## 이미 판정된 쌍은 보고하지 않는다

`duplicate_url_group` 이 **양쪽에 같은 값**으로 붙어 있으면 사람이 이미 판정한 쌍이다
(`.claude/rules/raw-ingest.md` §중복 `source_url` 판정 필드 — *"존재 여부로 「판정 완료」를
판별"*). 억제하지 않으면 `coexist` 로 종결된 쌍이 매 회차 다시 올라와 **보고서가
학습된 소음**이 된다. `--all` 로 포함시킬 수 있다(감사·시험용).

⚠️ **새 필드를 만들지 않는다** — 사람 판정은 기존 `duplicate_url_group`/`_verdict`/`_note`
3필드에 기록한다(`raw-ingest.md` 가 명시).

## 종료 코드

- `0` — 후보 없음
- `2` — **후보 있음 → 사람 판정 필요.** 🔴 **실패가 아니다.** 하드 블록이 아니므로
  이 값을 보고 인제스트를 중단시키지 말 것. `graphify-build.sh` 에 넣지 않은 이유이기도
  하다(`set -euo pipefail` 아래에서 빌드를 세운다).

사용:
    scripts/graphify-py.sh scripts/check-title-dup.py                    # 전수 보고
    scripts/graphify-py.sh scripts/check-title-dup.py --new raw/x.md     # /ingest — 1건 대조
    scripts/graphify-py.sh scripts/check-title-dup.py --threshold 0.5    # 하한 조정
    scripts/graphify-py.sh scripts/check-title-dup.py --all              # 판정 완료 쌍도 포함
"""
import os, re, sys, glob, difflib, argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FM = re.compile(r"^---\n(.*?)\n---", re.S)

# 목록 하한. **판정 기준이 아니다** — 위 docstring 참조.
DEFAULT_THRESHOLD = 0.40


def _fields(path):
    try:
        m = FM.match(open(path, encoding="utf-8", errors="replace").read())
    except OSError:
        return None
    body = m.group(1) if m else ""
    get = lambda k: (lambda x: x.group(1).strip().strip("\"'") if x else None)(
        re.search(rf"^{k}:\s*(.*)$", body, re.M))
    return {"title": get("title") or "", "author": get("author"),
            "source_url": get("source_url"), "group": get("duplicate_url_group")}


def normalize(text):
    """제목 정규화 — 선행 대괄호 태그(`[패스트캠퍼스 세미나]`)를 떼고 문장부호를 지운다."""
    text = re.sub(r"^\[[^\]]*\]\s*", "", text or "")
    return " ".join(re.sub(r"[^0-9a-z가-힣]+", " ", text.lower()).split())


def title_score(a, b):
    return difflib.SequenceMatcher(None, normalize(a), normalize(b)).ratio()


def author_hint(a, b):
    """저자 토큰이 한쪽을 포함하면 True. **가중치이지 판별자가 아니다.**"""
    if not a or not b:
        return False
    ta, tb = set(normalize(a).split()), set(normalize(b).split())
    return bool(ta) and bool(tb) and (ta <= tb or tb <= ta)


def unpinnable(f):
    """URL 비교가 성립하지 않는 것 — `직접 입력` 뿐 아니라 `manual`·로컬 경로·필드 부재."""
    return f["source_url"] is None or not f["source_url"].startswith("http")


def load():
    out = {}
    for p in sorted(glob.glob(os.path.join(ROOT, "raw", "**", "*.md"), recursive=True)):
        if "/_templates/" in p or "/attachments/" in p:
            continue
        f = _fields(p)
        if f:
            out[os.path.relpath(p, ROOT)] = f
    return out


def compare(cand, cand_f, corpus, threshold, include_judged):
    hits = []
    for path, f in corpus.items():
        if path == cand:
            continue
        judged = bool(cand_f["group"]) and cand_f["group"] == f["group"]
        if judged and not include_judged:
            continue
        s = title_score(cand_f["title"], f["title"])
        if s < threshold:
            continue
        hint = author_hint(cand_f["author"], f["author"])
        hits.append({"other": path, "score": s, "author_hint": hint, "judged": judged,
                     "rank": s + (0.05 if hint else 0.0)})
    return sorted(hits, key=lambda h: -h["rank"])


def main():
    ap = argparse.ArgumentParser(description="raw/ 제목 유사도 중복 후보 보고 (원장 #55)")
    ap.add_argument("--new", metavar="PATH", help="이 파일 1건만 전체와 대조 (/ingest 용)")
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                    help=f"목록 하한 (기본 {DEFAULT_THRESHOLD}) — 판정 기준이 아니다")
    ap.add_argument("--all", action="store_true", help="이미 판정된 쌍도 포함")
    args = ap.parse_args()

    corpus = load()
    if args.new:
        ap = os.path.abspath(args.new)
        rel = os.path.relpath(ap, ROOT)
        if rel.startswith(".."):      # 저장 전 임시 경로 — 말뭉치 밖이라 그대로 보여준다
            rel = ap
        f = corpus.get(rel) or _fields(ap)
        if not f:
            sys.exit(f"읽을 수 없다: {args.new}")
        cands = {rel: f}
        print(f"대조 대상 1건 · 말뭉치 {len(corpus)}건 · 하한 {args.threshold}")
    else:
        cands = {p: f for p, f in corpus.items() if unpinnable(f)}
        print(f"raw 실 자료 {len(corpus)}건 중 **URL 비교 불가** {len(cands)}건이 후보 "
              f"(원장 #55 의 '직접 입력 22' 보다 넓다 — docstring §후보 범위)")
        print(f"하한 {args.threshold} · 판정 완료 쌍 "
              f"{'포함' if args.all else '제외'}")

    seen, rows = set(), []
    for c, cf in cands.items():
        for h in compare(c, cf, corpus, args.threshold, args.all):
            key = tuple(sorted((c, h["other"])))
            if key in seen:
                continue
            seen.add(key)
            rows.append((h["rank"], h["score"], h["author_hint"], h["judged"], c, h["other"]))

    rows.sort(reverse=True)
    print()
    for rank, score, hint, judged, a, b in rows:
        tag = " [판정완료]" if judged else ""
        print(f"  {score:.3f}{' +저자' if hint else '     '}{tag}  {a}\n"
              f"         ↔ {b}")
    print()
    if not rows:
        print("후보 없음.")
        return 0
    print(f"🔴 **{len(rows)}쌍 — 사람 판정 필요.** 이 목록은 판정이 아니라 순위다: "
          f"진양성 최저(0.444)가 위양성 최고(0.545)보다 낮아 문턱으로 갈리지 않는다.")
    print("   판정은 **본문 대조**로 내리고 결과를 `duplicate_url_group`/`_verdict`/`_note` "
          "3필드에 기록한다 (.claude/rules/raw-ingest.md).")
    print("   ⚠️ 종료 코드 2 는 실패가 아니다 — 하드 블록이 아니므로 인제스트를 중단시키지 말 것.")
    return 2


if __name__ == "__main__":
    sys.exit(main())
