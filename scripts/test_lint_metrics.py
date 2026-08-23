#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`wiki_scan` 의 `#3`·`#4`·`#14` 정의 회귀 시험 (원장 #64-b 부분 집행).

🔴 **파손본이 정말 파손되는지 먼저 확인한다** — naive 파서 4종을 함께 돌려
«기대와 다른 케이스» 수를 실측값으로 못박는다. 그 수가 달라지면 시험 설계가
바뀐 것이므로 즉시 실패한다(원장 #52: 파손본이 파손되지 않은 채 통과한 전례).

파손본 4종은 전부 **실제로 일어난 실패**를 재현한 것이다:
  - `_naive_updated_fullline` : 36회차가 #3 을 168 대신 165 로 보고한 파서
  - `_naive_updated_bodyscan` : /lint §재측정 규율 4항의 2026-07-27 오탐
  - `_naive_editdist`         : 36회차 #4 및 그것을 지시한 `lint.md:58` 문면
  - `_naive_enum_pipe_any`    : 정본을 «안 열고 훑는» 부류. 인접 키까지 집는다
  - `_naive_island_grep`      : lint 41회차가 인바운드 0인 `unlazy-skill` 을
                                «4곳 이상» 이라 보고한 오독 — grep 히트 수 판정

실행: `python3 scripts/test_lint_metrics.py`  (exit 0 = 통과)
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wiki_scan import (  # noqa: E402
    updated_date, name_similarity, is_dup_name, is_dup_tags, claim_enums,
    island_slugs, DUP_NAME_THRESHOLD, STALE_DAYS,
)

FM = lambda body: f"---\n{body}\n---\n\n# 본문\n"

# ── #3 오래된 콘텐츠 ──────────────────────────────────────────────────────────
# 본문에 ```yaml 예시가 든 파일. frontmatter 에는 `updated` 가 없다.
BODY_YAML = (
    "---\ntitle: x\n---\n\n# 본문\n\n프론트매터 형식은 이렇다:\n\n"
    "```yaml\nupdated: 2020-01-01\n```\n"
)
NO_FM = "# 본문\n\nupdated: 2020-01-01\n"

UPDATED_CASES = [
    ("평범",           FM("updated: 2026-04-10"),            "2026-04-10"),
    ("괄호 주석",      FM("updated: 2026-04-10 (설명)"),     "2026-04-10"),
    ("후행 공백",      FM("updated: 2026-04-10   "),         "2026-04-10"),
    ("해시 주석",      FM("updated: 2026-04-10 # 메모"),     "2026-04-10"),
    ("필드 부재",      FM("title: x"),                        None),
    ("ISO 아님",       FM("updated: 미상"),                   None),
    ("따옴표(현행 한계)", FM('updated: "2026-04-10"'),        None),
    ("본문 yaml 예시", BODY_YAML,                             None),
    ("frontmatter 부재", NO_FM,                               None),
]


def _naive_updated_fullline(text):
    """파손본 A — 줄 전체를 파싱한다. 36회차 #3 회귀 그 자체."""
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return None
    um = re.search(r"^updated:[ \t]*(.*)$", m.group(1), re.M)
    if not um:
        return None
    tok = um.group(1).strip()
    return tok if re.fullmatch(r"\d{4}-\d{2}-\d{2}", tok) else None


def _naive_updated_bodyscan(text):
    """파손본 B — frontmatter 경계 없이 전문을 훑는다. 2026-07-27 오탐 형태."""
    um = re.search(r"^updated:[ \t]*(\S+)", text, re.M)
    if not um:
        return None
    tok = um.group(1)
    return tok if re.fullmatch(r"\d{4}-\d{2}-\d{2}", tok) else None


# ── #4 중복 개념 ─────────────────────────────────────────────────────────────
# 🔴 기대 ratio 는 §측정 정의가 남긴 기록값과 대조된 **실측치**다.
#    `weather.md` 가 0.864·0.844·0.839·0.821 을 적어 뒀고 자릿수까지 일치한다 —
#    그 일치가 «피연산자는 .md 를 뗀 파일명 그대로» 를 확정한다.
DUP_CASES = [
    ("harness/setup",  "claude-code-harness", "claude-code-harness-setup",      0.8636, True),
    ("view/teams",     "claude-code-agent-view", "claude-code-agent-teams",     0.8444, True),
    ("낙관/비관 락",   "optimistic-lock", "pessimistic-lock",                   0.8387, True),
    ("PD/절제실험",    "progressive-disclosure-ablation", "progressive-disclosure", 0.8302, True),
    ("harness/routines", "claude-code-harness", "claude-code-routines",         0.8205, True),
    ("경계 아래",      "agent-observability", "observability",                  0.8125, False),
]


def _naive_editdist(a, b):
    """파손본 C — 편집 거리 ≤3 (길이 8자 초과). `lint.md:58` 이 지시하던 측도."""
    if len(a) <= 8 or len(b) <= 8:
        return False
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1] <= 3


# ── #14 enum ─────────────────────────────────────────────────────────────────
SPEC_TMPL = """### `claim_status` / `evidence_level` 열거값 — 이 절이 단일 출처다

**`claim_status` — 주장의 출처 성격**

| 값 | 사용 조건 |
|---|---|
{cs_rows}

##### 두 필드의 역할 분담

- `claim_status: source_backed` 를 유지하고 `evidence_level: ai_synthesis` 로 표현한다.
- `confidence: high | medium | low` 와 `last_verified: YYYY-MM-DD | null` 은 축이 다르다.

**`evidence_level` — 근거의 계층**

| 값 | 사용 조건 |
|---|---|
{el_rows}

### 다음 절 — 여기부터는 대상이 아니다

| `절대_아님` | 이 표는 절 밖이라 걷히면 안 된다 |
"""


def _spec(cs, el):
    row = lambda vs: "\n".join(f"| `{v}` | 설명 |" for v in vs)
    return SPEC_TMPL.format(cs_rows=row(cs), el_rows=row(el))


CANON_CS = ["source_backed", "inferred", "unverified"]
CANON_EL = ["primary", "secondary", "ai_synthesis"]

ENUM_CASES = [
    ("정본",       _spec(CANON_CS, CANON_EL),                  (set(CANON_CS), set(CANON_EL))),
    ("값 추가",    _spec(CANON_CS + ["deprecated"], CANON_EL), (set(CANON_CS) | {"deprecated"}, set(CANON_EL))),
    ("값 제거",    _spec(CANON_CS[:2], CANON_EL),              (set(CANON_CS[:2]), set(CANON_EL))),
]


def _naive_enum_hardcoded(_text):
    """파손본 D — 열거값을 하드코딩해 방출한다. 정본이 바뀌어도 따라가지 못한다."""
    return set(CANON_CS), set(CANON_EL)


def _naive_enum_pipe_any(text):
    """파손본 E — 「파이프 있는 아무 `키: a | b` 줄」을 열거값으로 본다."""
    keys = set()
    for line in text.splitlines():
        m = re.match(r"^\s*`?([a-z_]+)`?:\s*(.+\|.+)$", line.strip().lstrip("-").strip())
        if m:
            keys.add(m.group(1))
    return keys


# ── island (인바운드 0) ─────────────────────────────────────────────────────
# 실제 `backlinks.md` 의 구조를 축약한 것이다. 요점 셋:
#   ⓐ `alpha` 는 블록이 있다 → island 아님
#   ⓑ `beta` 는 **다른 블록 안에 referrer 로 3번** 나오지만 자기 블록이 없다 → island
#      (= 41회차가 «인바운드 4곳 이상» 으로 오독한 바로 그 형태. 아웃바운드다)
#   ⓒ `gamma` 는 큐레이션 주석의 **펜스 안 예시**로만 블록 헤딩이 있다 → island
BACKLINKS_FIXTURE = """# 백링크 맵

> 자동 생성 — 수동 편집 금지.

---

## [[alpha]]

참조하는 파일:
- [[beta]] (베타가 알파를 가리킨다)
- [[delta]] (델타도 알파를 가리킨다)

## [[delta]]

참조하는 파일:
- [[beta]] (베타가 델타를 가리킨다)

## [[epsilon]]

참조하는 파일:
- [[beta]] (베타가 엡실론을 가리킨다)

<!-- 큐레이션 주석: 블록 형식은 이렇다

```
## [[gamma]]

참조하는 파일:
- [[alpha]]
```
-->
"""
ISLAND_SLUGS = ["alpha", "beta", "gamma", "delta", "epsilon"]
ISLAND_EXPECT = ["beta", "gamma"]


def _naive_island_grep(text, slugs):
    """41회차의 오독: `grep <슬러그>` 히트가 있으면 «인바운드 있음» 으로 본다.

    히트 대부분은 *다른 블록 안의 referrer 항목* = 그 슬러그의 **아웃바운드**다.
    이 파서는 `beta`(히트 3, 인바운드 0)를 island 이 아니라고 판정한다.
    """
    return sorted(s for s in slugs if s not in text)


def main():
    bad = []

    # ── #3 ──
    broke_fullline = broke_bodyscan = 0
    for name, text, exp in UPDATED_CASES:
        got = updated_date(text)
        if got != exp:
            bad.append(f"[#3 {name}] updated_date 기대={exp!r} 실제={got!r}")
        if _naive_updated_fullline(text) != exp:
            broke_fullline += 1
        if _naive_updated_bodyscan(text) != exp:
            broke_bodyscan += 1

    if STALE_DAYS != 30:
        bad.append(f"STALE_DAYS 가 §측정 정의와 다르다: {STALE_DAYS} (기대 30)")

    # ── #4 ──
    broke_editdist = 0
    for name, a, b, exp_ratio, exp_dup in DUP_CASES:
        r = round(name_similarity(a, b), 4)
        if r != exp_ratio:
            bad.append(f"[#4 {name}] ratio 기대={exp_ratio} 실제={r}")
        if is_dup_name(a, b) != exp_dup:
            bad.append(f"[#4 {name}] is_dup_name 기대={exp_dup} 실제={not exp_dup}")
        if _naive_editdist(a, b) != exp_dup:
            broke_editdist += 1

    if DUP_NAME_THRESHOLD != 0.82:
        bad.append(f"DUP_NAME_THRESHOLD 가 §측정 정의와 다르다: {DUP_NAME_THRESHOLD}")
    # 임계값 민감도 — 0.81/0.83 이 다른 쌍 수를 낸다는 정본 주장을 이 표본으로 못박는다.
    ratios = [round(name_similarity(a, b), 4) for _, a, b, _, _ in DUP_CASES]
    if sum(r >= 0.81 for r in ratios) != 6 or sum(r >= 0.82 for r in ratios) != 5 \
            or sum(r >= 0.83 for r in ratios) != 4:
        bad.append(f"임계값 민감도가 바뀌었다: {ratios}")

    # 태그셋 축 — 빈 집합끼리를 일치로 세면 안 된다.
    if not is_dup_tags({"a", "b"}, {"b", "a"}):
        bad.append("#4 태그셋: 순서만 다른 동일 집합을 못 봤다")
    if is_dup_tags(set(), set()):
        bad.append("🔴 #4 태그셋: 빈 집합끼리를 «일치» 로 셌다 — 태그 없는 파일이 전부 짝이 된다")
    if is_dup_tags({"a"}, set()) or is_dup_tags({"a"}, {"a", "b"}):
        bad.append("#4 태그셋: 부분집합·한쪽 빔을 일치로 셌다")

    # ── #14 ──
    broke_hardcoded = broke_pipe_any = 0
    for name, text, exp in ENUM_CASES:
        got = claim_enums(text)
        pair = (set(got["claim_status"]), set(got["evidence_level"]))
        if pair != exp:
            bad.append(f"[#14 {name}] claim_enums 기대={exp} 실제={pair}")
        if _naive_enum_hardcoded(text) != exp:
            broke_hardcoded += 1
    # 「파이프 있는 아무 키」는 정본 케이스에서 2키가 아니라 더 많이 집는다.
    pipe_keys = _naive_enum_pipe_any(ENUM_CASES[0][1])
    if pipe_keys != {"claim_status", "evidence_level"}:
        broke_pipe_any = 1

    # fail-closed — 조용한 기본값을 내면 안 된다.
    for name, text in [
        ("절 자체 부재", "# 아무 문서\n\n본문뿐이다.\n"),
        ("한 필드 누락", _spec(CANON_CS, [])),
    ]:
        try:
            claim_enums(text)
            bad.append(f"🔴 #14 fail-closed 실패: «{name}» 인데 ValueError 를 던지지 않았다")
        except ValueError:
            pass

    # 정본 파일 실물 — 절 밖 표를 걷지 않는지까지 본다.
    spec_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             ".claude/rules/wiki-concepts.md")
    real = claim_enums(open(spec_path, encoding="utf-8").read())
    if set(real["claim_status"]) != set(CANON_CS) or set(real["evidence_level"]) != set(CANON_EL):
        bad.append(f"🔴 #14 정본 파일 파싱이 갈렸다: {sorted(real['claim_status'])} / "
                   f"{sorted(real['evidence_level'])}")
    # 두 자리 정합 — weather.md §측정 정의는 frontmatter 템플릿(`:24-25`)을 인용하고
    # lint.md §14 는 열거값 «절» 을 인용한다. 두 자리가 갈리면 회차마다 값이 달라진다.
    tmpl = dict(re.findall(r"^\s*(claim_status|evidence_level):\s*(.+)$",
                           open(spec_path, encoding="utf-8").read(), re.M))
    for f in ("claim_status", "evidence_level"):
        vals = {v.strip() for v in tmpl.get(f, "").split("|") if v.strip()}
        if vals != set(real[f]):
            bad.append(f"🔴 #14 두 자리 불일치({f}): 템플릿={sorted(vals)} 절={sorted(real[f])}")

    # ── island (인바운드 0) ──
    got_isl = island_slugs(BACKLINKS_FIXTURE, ISLAND_SLUGS)
    if got_isl != ISLAND_EXPECT:
        bad.append(f"🔴 island 정본이 갈렸다: {got_isl} (기대 {ISLAND_EXPECT})")
    # 🔴 파손본이 정말 파손되는지 — `beta` 를 놓쳐야 이 시험이 의미가 있다.
    broke_island = len(set(ISLAND_EXPECT) - set(_naive_island_grep(BACKLINKS_FIXTURE, ISLAND_SLUGS)))

    # ── 파손본 검증 — 실측 고정값. 바뀌면 시험 설계가 바뀐 것이다. ──
    pins = [
        # naive_fullline : «괄호 주석» · «해시 주석» = 2건
        ("naive_updated_fullline", broke_fullline, 2),
        # naive_bodyscan : «본문 yaml 예시» · «frontmatter 부재» = 2건
        ("naive_updated_bodyscan", broke_bodyscan, 2),
        # naive_editdist : 정본 5쌍 전부를 놓친다 (lev 6·5·4·9·6) = 5건
        ("naive_editdist", broke_editdist, 5),
        # naive_enum_hardcoded : «값 추가» · «값 제거» = 2건
        ("naive_enum_hardcoded", broke_hardcoded, 2),
        # naive_enum_pipe_any : 정본 케이스에서 인접 키까지 집는다 = 1건
        ("naive_enum_pipe_any", broke_pipe_any, 1),
        # naive_island_grep : `beta`(히트 3·인바운드 0)와 `gamma`(펜스 예시)를 놓친다 = 2건
        ("naive_island_grep", broke_island, 2),
    ]
    for label, got, exp in pins:
        if got != exp:
            bad.append(f"파손본 검증 실패: {label} 이 {got}건에서 깨졌다 (기대 {exp})")

    for b in bad:
        print("🔴", b)
    print(f"\n케이스 #3 {len(UPDATED_CASES)} · #4 {len(DUP_CASES)} · #14 {len(ENUM_CASES)}"
          f" · island {len(ISLAND_SLUGS)}")
    print("파손본 검증 " + " / ".join(f"{l} {g}" for l, g, _ in pins))
    print("위반 없음." if not bad else f"위반 {len(bad)}건.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
