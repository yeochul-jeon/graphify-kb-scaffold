#!/usr/bin/env python3
"""fm `sources` ↔ §출처 절 정합 검사 (원장 #57)

정의 (2026-08-10 사람 결정) — `.claude/rules/wiki-concepts.md` §출처 표기의 두 자리 가 단일 출처다:

    fm `sources` 가 정본이고 §출처 절은 그 **부분집합**이다.

따라서 이 검사기가 보는 위반은 **③절 ⊃ fm** 하나뿐이다.
  · ②fm ⊃ 절 (fm 에만 있음) 은 정상이다 — 외부 URL·`output/` 인용은 §출처 절에 쓰지 않는 관행이 있다
  · ④교차 는 2026-08-10 전수 실측에서 **0건**이었다. 나오면 ③으로 함께 보고한다

왜 fm 이 정본인가: 집계·검사기·`attach-claim-metadata.py` 가 읽는 것이 fm 이다.
§출처 절에만 있는 출처는 **어느 집계에도 잡히지 않는다** — 원장 #57 이 나온 자리다
(`claude-code-configuration-strategy` 의 `harness-engineering-seminar` 가 그 상태였다).

🔴 **파싱 범위 — 「위반 0」을 「전건 정합」으로 읽지 말 것 (2026-08-10 명시).**

절 쪽에서 세는 것은 **`[[raw/…]]`·`[[output/…]]` 위키링크뿐**이다. 아래는 **보이지 않는다**:
  · 외부 URL 을 산문으로 적은 인용 — `- Sam Newman — "Building Microservices"` (`bff-pattern` 실례)
  · 마크다운 링크 `[제목](url)`
  · `- 웹 리서치: output/…` 처럼 링크 표기를 쓰지 않은 줄 (`qmd` 실례)

fm 쪽은 URL 을 그대로 담으므로(`bff-pattern` 의 `https://samnewman.io/...`), **같은 출처가 fm 은 URL·절은 산문**이면
이 검사기는 그 파일을 ② 로 분류한다. **실질은 ①일 수 있다.**

그래서 원장 #57 이 `bff-pattern` 을 ③ 으로 적은 것과 이 검사기의 ② 는 **둘 다 자기 정의 안에서 맞다** —
원장은 표기 무관 대조였고 이 검사기는 위키링크 한정이다. **수치가 다르다고 한쪽이 틀린 것이 아니다.**

넓히지 않은 이유: 산문 인용은 자유 텍스트라 기계 대조의 대상이 아니다. **넓히는 대신 범위를 적었다** —
못 보는 것을 「없다」로 보고하는 것이 이 저장소가 반복해서 틀린 방식이기 때문이다.

사용: scripts/graphify-py.sh scripts/check-source-section.py [--check] [--verbose]
  --check    위반이 있으면 exit 1
  --verbose  형태 분포(①②③④)를 함께 출력
"""
import os
import re
import sys
import glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wiki_scan

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# fm `sources` 는 인라인 `[...]` 과 블록 리스트 두 표기가 섞여 있다.
# 인라인만 파싱하면 블록 리스트 파일이 "출처 없음" 으로 오판된다
# (`envelope-encryption`·`spring-date-format` 이 실제로 여러 회차 오보됐다).
INLINE = re.compile(r"^sources:\s*\[(.*?)\]", re.M)
BLOCK = re.compile(r"^sources:\s*\n((?:[ \t]*-[ \t]*\S.*\n)+)", re.M)
REF = re.compile(r"\[\[((?:raw|output)/[^\]]+?)\]\]")


def fm_sources(text):
    m = INLINE.search(text)
    if m:
        return {x.strip() for x in m.group(1).split(",") if x.strip()}
    m = BLOCK.search(text)
    if m:
        return {ln.strip().lstrip("-").strip() for ln in m.group(1).splitlines() if ln.strip()}
    return set()


def section_refs(text, path):
    """§출처 절의 `[[raw/...]]`·`[[output/...]]` 인용.

    코드 스팬·펜스는 정본 마스킹으로 벗긴다 — 규약이 링크 문법을 백틱으로 감싸라고
    요구하므로(원장 #24·#43), 벗기지 않으면 예시가 실제 인용으로 집계된다.
    """
    if "\n## 출처" not in text:
        return set()
    sec = text.split("\n## 출처", 1)[1]
    # 다음 최상위 절이 있으면 거기서 끊는다
    nxt = re.search(r"^## ", sec, re.M)
    if nxt:
        sec = sec[: nxt.start()]
    return set(REF.findall(wiki_scan.mask_text(sec, source=path)))


def scan(paths):
    forms = {"①동일": 0, "②fm⊃절": 0, "③절⊃fm": 0, "④교차": 0}
    violations = []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            text = f.read()
        fm = fm_sources(text)
        sec = section_refs(text, p)
        if not fm and not sec:
            continue
        only_sec = sec - fm
        if fm == sec:
            forms["①동일"] += 1
        elif not only_sec:
            forms["②fm⊃절"] += 1
        elif sec >= fm:
            forms["③절⊃fm"] += 1
        else:
            forms["④교차"] += 1
        if only_sec:
            violations.append((os.path.relpath(p, ROOT), sorted(only_sec)))
    return forms, violations


def main():
    check = "--check" in sys.argv
    verbose = "--verbose" in sys.argv
    paths = sorted(glob.glob(os.path.join(ROOT, "wiki/concepts/*.md"))) + sorted(
        glob.glob(os.path.join(ROOT, "wiki/topics/*.md"))
    )
    forms, violations = scan(paths)

    print("fm `sources` ↔ §출처 절 정합 (정본: fm ⊇ 절)")
    print(f"  대상: {len(paths)} 파일")
    if verbose:
        total = sum(forms.values())
        for k, v in forms.items():
            print(f"  {k}: {v}")
        print(f"  (출처 표기가 있는 파일 {total})")

    print("  ⚠️ 절 쪽은 `[[raw/…]]`·`[[output/…]]` 위키링크만 센다 —")
    print("     산문 인용·마크다운 링크·외부 URL 은 보이지 않는다 (docstring §파싱 범위).")

    if not violations:
        print("\n위반 없음 — **이 범위 안에서**.")
        return 0

    print(f"\n🔴 위반 {len(violations)}건 — §출처 절에만 있고 fm `sources` 에 없다:")
    for rel, only in violations:
        print(f"  {rel}")
        for s in only:
            print(f"      + {s}")
    print("\n  ⚠️ 조치는 **fm 에 추가**다. §출처 절에서 지우는 것이 아니다 —")
    print("     그 인용은 근거로 실제 쓰이고 있으며, 지우면 근거가 사라진다.")
    print("  ⚠️ fm 보강은 메타 편집이므로 `updated:` 를 올리지 않는다 (원장 #40).")
    return 1 if check else 0


if __name__ == "__main__":
    sys.exit(main())
