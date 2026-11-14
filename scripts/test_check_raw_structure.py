#!/usr/bin/env python3
"""`check-raw-structure.py` ⓓ(수집 이유 첫 줄) 회귀 시험 — 2026-11-08 사용자 결정 «ingest 제안 ① 채택 + 검사기».
경고 S2·S3(AI 생성 정황 후보) 시험 — 2026-11-10 사용자 결정, 원장 #104 ②.

실행: `uv run -q --with pyyaml python3 scripts/test_check_raw_structure.py`  (exit 0 = 통과)
"""
import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("crs", os.path.join(HERE, "check-raw-structure.py"))
crs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(crs)

FM = lambda body: f"---\n{body}\n---\n\n# 본문\n내용\n"
AFTER, BEFORE = "2026-11-09", "2026-11-08"

# (이름, frontmatter, ⓓ 위반이어야 하는가)
CASES = [
    ("기준일 전·note 없음",        f"title: a\ningested_date: {BEFORE}",                                   False),
    ("기준일 전·이유 없는 note",   f"title: a\ningested_date: {BEFORE}\nnote: |\n  수집 경로: curl",      False),
    ("기준일 이후·note 없음",      f"title: a\ningested_date: {AFTER}",                                    True),
    ("기준일 이후·첫 줄이 경로",   f"title: a\ningested_date: {AFTER}\nnote: |\n  수집 경로: curl\n  수집 이유: x", True),
    ("기준일 이후·이유 비어 있음", f"title: a\ningested_date: {AFTER}\nnote: |\n  수집 이유:   ",          True),
    ("기준일 이후·정상(블록)",     f"title: a\ningested_date: {AFTER}\nnote: |\n  수집 이유: KMS 빈칸 보충\n  수집 경로: curl", False),
    ("기준일 이후·정상(한 줄)",    f'title: a\ningested_date: "{AFTER}"\nnote: "수집 이유: 비교용"',        False),
    ("ingested_date 없음",         "title: a\nnote: x",                                                     False),
    ("템플릿 자리표시자 날짜",     "title: a\ningested_date: YYYY-MM-DD\nnote: |\n  (조건부)",             False),
]

fails = 0
with tempfile.TemporaryDirectory() as d:
    for name, fm, want in CASES:
        p = os.path.join(d, "x.md")
        with open(p, "w", encoding="utf-8") as f:
            f.write(FM(fm))
        bad, has_fm = crs.check(p)
        got = any(b.startswith("ⓓ") for b in bad)
        other = [b for b in bad if not b.startswith("ⓓ")]
        ok = has_fm and got == want and not other
        print(("ok  " if ok else "FAIL"), name, bad)
        fails += not ok

# 시험이 무언가를 잡는지 확인: 위반 기대 케이스가 0 이면 시험 설계가 바뀐 것이다.
expected_hits = sum(1 for _, _, w in CASES if w)
assert expected_hits == 3, expected_hits
print(f"{len(CASES) - fails}/{len(CASES)} 통과")

# 경고 S2·S3 (원장 #104) — (이름, 본문 한 줄, 기대 신호 접두 또는 None)
AI_CASES = [
    ("S3 16진 혼합 12자리",        "6f3308650846",                                     "S3"),
    ("S3 커밋 SHA 40자리",         "e5713ea0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6",          "S3"),
    ("S3 아님: 숫자만(전화·ID)",   "202611101714",                                     None),
    ("S3 아님: 문자만",            "deadbeefcafe",                                     None),
    ("S3 아님: 11자리",            "6f330865084",                                      None),
    ("S3 아님: 대문자",            "6F3308650846",                                     None),
    ("S3 아님: 문장 속 해시",      "커밋 6f3308650846 에서 고쳤다",                     None),
    ("S2 utm chatgpt",             "[a](https://x.io/p?utm_source=chatgpt.com)",       "S2"),
    ("S2 turn 인용 표지",          "근거 turn0search3 참고",                           "S2"),
    ("S2 아님: 다른 utm",          "[a](https://x.io/p?utm_source=newsletter)",        None),
    ("S2 아님: 단어 turn",         "turn 3 search 결과",                               None),
]
ai_fails = 0
for name, line, want in AI_CASES:
    text = "---\ntitle: a\n---\n\n" + line + "\n"
    hits = crs.ai_signals(text)
    got = hits[0][1][:2] if hits else None
    ok = got == want and (not hits or hits[0][0] == 5)  # 줄번호는 파일 기준(frontmatter 3줄 + 빈 줄 + 이 줄)
    print(("ok  " if ok else "FAIL"), name, hits)
    ai_fails += not ok
# 시험이 무언가를 잡는지 확인: 기대 적중이 0 이면 시험 설계가 바뀐 것이다.
assert sum(1 for *_, w in AI_CASES if w) == 4
print(f"경고 {len(AI_CASES) - ai_fails}/{len(AI_CASES)} 통과")
sys.exit(1 if (fails or ai_fails) else 0)
