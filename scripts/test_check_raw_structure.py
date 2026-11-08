#!/usr/bin/env python3
"""`check-raw-structure.py` ⓓ(수집 이유 첫 줄) 회귀 시험 — 2026-11-08 사용자 결정 «ingest 제안 ① 채택 + 검사기».

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
sys.exit(1 if fails else 0)
