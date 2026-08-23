#!/usr/bin/env python3
"""`wiki_scan.tags` / `is_fast_moving` 회귀 시험 (원장 #64 조치).

🔴 **파손본이 정말 파손되는지 먼저 확인한다** — naive 파서 2종을 함께 돌려
«기대와 다른 케이스» 수를 실측값으로 못박는다. 그 수가 달라지면 시험 설계가
바뀐 것이므로 즉시 실패한다(원장 #52: 파손본이 파손되지 않은 채 통과한 전례).

실행: `python3 scripts/test_wiki_scan_tags.py`  (exit 0 = 통과)
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wiki_scan import tags, is_fast_moving, FAST_MOVING_TAGS  # noqa: E402

FM = lambda body: f"---\n{body}\n---\n\n# 본문\n"

CASES = [
    ("점 포함 태그",   "tags: [claude-code, SKILL.md, CLAUDE.md]", {"claude-code", "SKILL.md", "CLAUDE.md"}),
    ("하이픈 내부 ai", "tags: [ai-engineering, agentic]",          {"ai-engineering", "agentic"}),
    ("따옴표",         "tags: ['a-b', \"c-d\"]",                    {"a-b", "c-d"}),
    ("빈 리스트",      "tags: []",                                  set()),
    ("블록 리스트",    "tags:\n  - alpha\n  - beta-gamma",          {"alpha", "beta-gamma"}),
    ("공백 다수",      "tags:   [ x ,  y ]",                        {"x", "y"}),
    ("필드 부재",      "title: x",                                  set()),
]

# 현행/과거 구현. 이것들이 «틀려야» 시험이 의미를 갖는다.
_naive_token = lambda fm: {t for t in re.findall(r"[\w-]+", fm.split(":", 1)[1])} if ":" in fm else set()


def _naive_inline(fm):
    m = re.search(r"^tags:\s*\[(.*?)\]", fm, re.M)
    return {t.strip().strip("'\"") for t in m.group(1).split(",") if t.strip()} if m else set()


def main():
    bad = []
    broke_token = broke_inline = 0
    for name, body, exp in CASES:
        got = tags(FM(body))
        if got != exp:
            bad.append(f"[{name}] tags() 기대={sorted(exp)} 실제={sorted(got)}")
        if _naive_token(body) != exp:
            broke_token += 1
        if _naive_inline(body) != exp:
            broke_inline += 1

    # 파손본 검증 — 실측 고정값. 바뀌면 시험 설계가 바뀐 것이다.
    #   naive_token  : «점 포함» · «블록 리스트» · «필드 부재» = 3건
    #   naive_inline : «블록 리스트» = 1건
    # 🔴 즉 `inject-self-metrics.py:155` 현행 파서의 결함은 **블록 표기 미지원 하나뿐**이며,
    #    그것이 «새로 짜지 말고 끌어올린다» 판단의 근거다(#43: 사본이 늘면 갈라진다).
    # ⚠️ 이 두 숫자는 **추정이 아니라 실측**이다. 초안이 각각 «≥3»·«2» 로 적었다가
    #    시험이 잡아 3·1 로 정정했다 — 파손본 시험이 자기 과잉 주장을 먼저 잡은 사례다.
    if broke_token != 3:
        bad.append(f"파손본 검증 실패: naive_token 이 {broke_token}건에서 깨졌다 (기대 3)")
    if broke_inline != 1:
        bad.append(f"파손본 검증 실패: naive_inline 이 {broke_inline}건에서 깨졌다 (기대 1)")

    # #12 축 — 부분 문자열과 집합 교집합이 갈리는 케이스
    only_hyphen = FM("tags: [ai-engineering, harness-engineering]")
    if re.search(r"\b(llm|ai|claude-code|agent)\b", "ai-engineering, harness-engineering") is None:
        bad.append("#12 시험 무효: 이 케이스가 부분 문자열 매칭에 걸리지 않는다")
    if is_fast_moving(only_hyphen):
        bad.append("#12 오탐: 하이픈 내부 `ai` 를 대상으로 셌다")
    if not is_fast_moving(FM("tags: [claude-code, x]")):
        bad.append("#12 누락: 정확 일치 태그를 못 봤다")
    if FAST_MOVING_TAGS != {"llm", "ai", "claude-code", "agent"}:
        bad.append(f"FAST_MOVING_TAGS 가 §측정 정의와 다르다: {sorted(FAST_MOVING_TAGS)}")

    for b in bad:
        print("🔴", b)
    print(f"\n케이스 {len(CASES)} · 파손본 검증 naive_token {broke_token} / naive_inline {broke_inline}")
    print("위반 없음." if not bad else f"위반 {len(bad)}건.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
