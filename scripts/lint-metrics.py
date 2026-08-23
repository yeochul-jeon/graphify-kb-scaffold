#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`/lint` 구조 지표 러너 — `#3`(오래된 콘텐츠) · `#4`(중복 개념) · `#14`(enum 위반) · island(인바운드 0).

## 왜 이 파일이 있는가 (원장 #64-b)

**37회차 측정 스크립트가 세션 scratchpad 에만 있었고 소실됐다.** 그래서 다음 세션이
`#3=167`·`#4=5쌍` 을 **재현할 수단이 없었다** — 인계 문서가 정직하게 적었는데도 검증이
불가능했다. 정의를 함수로 옮기는 것만으로는 이 구멍이 닫히지 않는다. `#4`·`#14` 는
저장소에 호출자가 아예 없어서, 러너가 없으면 함수만 남고 **다음 회차가 다시 짠다**
(원장 #60 종결 기록의 교훈).

판정 정의는 전부 `scripts/wiki_scan.py` 가 정본이다. **이 파일은 정의를 갖지 않는다** —
코퍼스를 순회하고 관측일 산술을 하고 보고할 뿐이다.

## 관측일

`#3` 의 경과일수는 **관측일에 의존**하므로 함수가 아니라 여기서 계산한다
(`is_fast_moving` 이 ≥90일을 담지 않은 것과 같은 판단). 컷 날짜를 출력에 함께 찍는다 —
다음 회차가 같은 값을 재현했는지 확인할 수 있어야 한다.

⚠️ **`−N(조치)/+M(경계 통과)` 두 값은 내지 않는다.** 그 분해는 *이전 회차 트리*의 30일+
집합을 필요로 하는데 이 러너는 현재 트리 한 시점만 잰다. `--json` 이 정렬된 파일 집합을
싣고, 조합은 회차 세션의 일이다(원장 #40·#48).

⚠️ **`--fix` 를 만들지 않았다.** 이것은 측정 장치다. `#3`·`#4` 의 조치는 사람 판단이고
`#14` 소급 부착은 `scripts/attach-claim-metadata.py` 소관이다.

사용:
    python3 scripts/lint-metrics.py                       # 보고 (exit 0)
    python3 scripts/lint-metrics.py --as-of 2026-08-17    # 관측일 고정 (회차 재현)
    python3 scripts/lint-metrics.py --json                # 기계 판독
    python3 scripts/lint-metrics.py --check               # #14 위반 있으면 exit 1

종료코드: 0 정상 · 1 `--check` 위반 · 2 **정본 스펙 파싱 실패**(fail-closed).
"""
import argparse
import glob
import json
import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wiki_scan import (  # noqa: E402
    updated_date, name_similarity, is_dup_name, is_dup_tags, tags, claim_enums,
    island_slugs, DUP_NAME_THRESHOLD, STALE_DAYS,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(ROOT, ".claude/rules/wiki-concepts.md")
SCOPE = ("wiki/concepts/*.md", "wiki/topics/*.md")
# `island` 판정의 입력. 결정론적 strict-inbound 역인덱스라 코퍼스 재스캔이 필요 없다.
# ⚠️ 낡았으면 값도 낡는다 — `rebuild-backlinks.py` 를 먼저 돌린 뒤 재라
#    (`graphify-build.sh` 에 내장돼 있어 빌드를 돌렸다면 이미 최신이다).
BACKLINKS = os.path.join(ROOT, "wiki/backlinks.md")

# frontmatter 스칼라 1개를 읽는 국소 헬퍼. `wiki_scan` 에 올리지 않은 이유는 이것이
# **정의가 아니라 조회**이기 때문이다 — `#14` 의 판정 기준은 열거값 집합이지 이 정규식이
# 아니다. ⚠️ 다만 frontmatter 경계는 반드시 잡는다: 본문 산문이 `claim_status: …` 를
# 문장으로 쓰는 파일이 실재해 전문 grep 은 가짜 값을 집는다(실측 6건).
FM_RE = re.compile(r"^---\n(.*?)\n---", re.S)


def _files():
    out = []
    for pat in SCOPE:
        out += glob.glob(os.path.join(ROOT, pat))
    return sorted(out)


def _read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def _fm_scalar(text, key):
    m = FM_RE.match(text)
    if not m:
        return None
    v = re.search(rf"^{key}:[ \t]*(\S+)", m.group(1), re.M)
    return v.group(1) if v else None


def measure(as_of):
    files = _files()
    docs = [(os.path.basename(p)[:-3], _read(p)) for p in files]
    cut = date.fromordinal(as_of.toordinal() - STALE_DAYS)

    # ── #3 오래된 콘텐츠 ──
    stale = []
    for slug, text in docs:
        v = updated_date(text)
        if not v:
            continue
        y, mo, d = (int(x) for x in v.split("-"))
        if (as_of - date(y, mo, d)).days >= STALE_DAYS:
            stale.append(slug)

    # ── #4 중복 개념 (두 축을 OR 로 각각) ──
    slugs = [s for s, _ in docs]
    tagset = {s: tags(t) for s, t in docs}
    name_pairs, tag_pairs = [], []
    for i in range(len(slugs)):
        for j in range(i + 1, len(slugs)):
            a, b = slugs[i], slugs[j]
            if is_dup_name(a, b):
                name_pairs.append((a, b, round(name_similarity(a, b), 4)))
            if is_dup_tags(tagset[a], tagset[b]):
                tag_pairs.append((a, b))
    name_pairs.sort(key=lambda t: -t[2])

    # ── island (인바운드 0) ── 정의·오독 경로는 wiki_scan.island_slugs 도크스트링
    islands = island_slugs(_read(BACKLINKS), slugs) if os.path.exists(BACKLINKS) else None

    # ── #14 enum ── (ValueError 는 호출자가 exit 2 로 변환한다)
    canon = claim_enums(_read(SPEC))
    enum_bad = []
    for slug, text in docs:
        for field, allowed in canon.items():
            val = _fm_scalar(text, field)
            if val is not None and val not in allowed:
                enum_bad.append((slug, field, val))

    return {
        "as_of": as_of.isoformat(),
        "cut": cut.isoformat(),
        "denominator": len(files),
        "stale_30d": sorted(stale),
        "dup_pairs_082": name_pairs,
        "dup_pairs_tags": tag_pairs,
        "islands": islands,
        "enum_violations": enum_bad,
        "enum_canon": {k: sorted(v) for k, v in canon.items()},
    }


def report(r):
    n_c = len(glob.glob(os.path.join(ROOT, SCOPE[0])))
    n_t = len(glob.glob(os.path.join(ROOT, SCOPE[1])))
    print(f"분모 {r['denominator']} (concepts {n_c} + topics {n_t}) · 관측일 {r['as_of']}")
    print()
    print(f"#3  오래된 콘텐츠 (>={STALE_DAYS}일): {len(r['stale_30d'])}"
          f"   [컷 <= {r['cut']}]")
    print("    ⚠️ −N(조치)/+M(경계 통과) 분해는 이 러너가 내지 않는다 — 이전 회차 집합이 필요하다.")
    print(f"#4  중복 개념 — 파일명 ratio >= {DUP_NAME_THRESHOLD}: {len(r['dup_pairs_082'])}쌍"
          f" · 태그셋 완전 일치: {len(r['dup_pairs_tags'])}쌍")
    for a, b, ratio in r["dup_pairs_082"]:
        print(f"      {ratio}  {a} <-> {b}")
    for a, b in r["dup_pairs_tags"]:
        print(f"      tags  {a} <-> {b}")
    isl = r["islands"]
    if isl is None:
        print("island (인바운드 0): 측정 불가 — wiki/backlinks.md 없음")
    else:
        print(f"island (인바운드 0): {len(isl)}"
              f"   [wiki/backlinks.md 의 `## [[슬러그]]` 블록 부재]")
        for slug in isl:
            print(f"      {slug}")
        # 🔴 «#2 orphan 과 다른 지표» 를 산출에 남긴다. 이 구분이 없어 39~41회차가
        #    index 에 등재된 island 4건을 3회차 연속 놓쳤다(원장 #81).
        print("    ⚠️ `#2` orphan(= index 미등재 AND 인바운드 0) 과 다른 지표다. 합쳐 세지 말 것.")
    print(f"#14 enum 위반: {len(r['enum_violations'])}")
    for slug, field, val in r["enum_violations"]:
        print(f"      {slug}: {field} = {val}")
    # 🔴 «어떤 정의로 쟀는가» 를 산출에 남긴다. 37회차가 지어낸 열거값으로 오탐 333건을
    #    냈고 그 술어가 소실돼 재현조차 안 됐다 — 이 두 줄이 그 재발을 막는다.
    print(f"    정본 {os.path.relpath(SPEC, ROOT)}")
    for k, v in r["enum_canon"].items():
        print(f"      {k}: {' | '.join(v)}")


def main():
    ap = argparse.ArgumentParser(description="lint 구조 지표 (#3·#4·#14)")
    ap.add_argument("--as-of", metavar="YYYY-MM-DD",
                    help="관측일 고정 (기본 오늘). 과거 회차 재현용")
    ap.add_argument("--json", action="store_true", help="기계 판독 출력")
    ap.add_argument("--check", action="store_true", help="#14 위반이 있으면 exit 1")
    a = ap.parse_args()

    as_of = date.today()
    if a.as_of:
        as_of = date(*(int(x) for x in a.as_of.split("-")))

    try:
        r = measure(as_of)
    except ValueError as e:
        # fail-closed — 정본을 못 읽으면 «위반 0» 이 아니라 «측정 불가» 다.
        sys.stderr.write(f"[lint-metrics] 정본 스펙 파싱 실패: {e}\n")
        return 2

    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        report(r)
    return 1 if (a.check and r["enum_violations"]) else 0


if __name__ == "__main__":
    sys.exit(main())
