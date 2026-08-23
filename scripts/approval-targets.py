#!/usr/bin/env python3
"""승인 모집단 — `output/` 실사용 인용 횟수로 `verified` 대상을 정한다.

**왜 있는가 (2026-08-09 결정 1).** `verified` 목표가 *"`wiki` 전건"* 이었는데
295건은 페이지당 사람 승인이라 산술적으로 끝나지 않는다. 더 나쁜 것은 **어디서
시작할지 신호가 없었다**는 점이다 — 실측하니 승인 12건 중 4건이 `output/` 인용
0회였고, 인용 상위 39건 중 승인된 것은 3건뿐이었다. **노력 부족이 아니라 목표
정의의 결함**이다.

그래서 모집단을 **실제로 읽히는 페이지**로 줄인다.

  모집단   `output/*.md` 가 인용한 횟수가 **임계값 이상**인 `wiki/concepts` 페이지
  인용     한 `output` 파일 안에서 같은 개념을 여러 번 써도 **1회**로 센다
           (파일 단위 = "이 답변이 그 페이지에 기댔다")
  탐지     `[[개념]]` 위키링크 + `wiki/concepts/<개념>.md` 경로 표기 둘 다

⚠️ **시점 의존값이다.** `output/` 이 늘면 목록도 바뀐다. **수치를 인용할 때 측정일과
임계값을 함께 적는다**(#10 규율). 목록을 파일로 굳히지 않는 이유가 이것이다.

⚠️ **"대상 아님" 은 "미승인" 이 아니다.** 임계값 미만 페이지는 승인 대기가 아니라
**모집단 밖**이다. 진행률 분모에 넣지 않는다.

사용:
  python3 scripts/approval-targets.py              # 기본 임계값 5
  python3 scripts/approval-targets.py --min 3      # 임계값 변경
  python3 scripts/approval-targets.py --remaining  # 미승인분만

종료 코드: 항상 0. **판정이 아니라 목록이다.**
"""
import os, re, sys, glob, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FM = re.compile(r"\A---\n(.*?)\n---(?:\n|\Z)", re.S)


def concepts():
    return {os.path.basename(p)[:-3]: p
            for p in glob.glob(os.path.join(ROOT, "wiki/concepts/*.md"))}


def citations(names):
    """output/ 파일 단위로 센다 — 한 파일 안의 반복은 1회."""
    count = collections.Counter()
    files = glob.glob(os.path.join(ROOT, "output/*.md"))
    for p in files:
        with open(p, encoding="utf-8") as f:
            text = f.read()
        hit = set()
        for m in re.finditer(r"\[\[([^\]|#]+)", text):
            n = os.path.basename(m.group(1).strip()).replace(".md", "")
            if n in names:
                hit.add(n)
        for m in re.finditer(r"wiki/concepts/([\w\-]+)\.md", text):
            if m.group(1) in names:
                hit.add(m.group(1))
        for n in hit:
            count[n] += 1
    return count, len(files)


def verified(path):
    with open(path, encoding="utf-8") as f:
        m = FM.match(f.read())
    return bool(m and re.search(r"^verified:\s*true\s*$", m.group(1), re.M))


def main():
    argv = sys.argv[1:]
    threshold = 5
    if "--min" in argv:
        threshold = int(argv[argv.index("--min") + 1])
    names = concepts()
    cite, n_out = citations(names)
    targets = sorted(((v, k) for k, v in cite.items() if v >= threshold), reverse=True)
    done = [(v, k) for v, k in targets if verified(names[k])]
    todo = [(v, k) for v, k in targets if not verified(names[k])]

    print(f"승인 모집단 — 인용 {threshold}회 이상 (측정: output/ {n_out}건 · wiki/concepts {len(names)}건)")
    print(f"  모집단      {len(targets)}")
    print(f"  승인 완료   {len(done)}")
    print(f"  남은 것     {len(todo)}")
    print(f"  모집단 밖   {len(names) - len(targets)}  ← 미승인이 아니라 '대상 아님'")
    print()
    rows = todo if "--remaining" in argv else targets
    label = "미승인" if "--remaining" in argv else "전체"
    print(f"{label} {len(rows)}건 — 인용 횟수 순")
    for v, k in rows:
        mark = "✅" if verified(names[k]) else "  "
        print(f"  {mark} {v:3d}회  {k}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
