#!/usr/bin/env python3
"""`wiki/index.md` 목록 표의 **최종 업데이트 열**을 각 파일 frontmatter `updated` 로 주입.

## 왜 이 스크립트가 생겼는가 (원장 #61 · 사람 결정 ①)

이 열은 **손으로 관리되는 사본**이었다. 30회차 실측에서 **76건이 어긋나** 있었고
그중 71건이 선재였다. 어떤 검사도 이 열을 보지 않아(#6 은 **등재 여부만** 본다)
언제부터 어긋났는지조차 알 수 없었다.

31회차가 사람 결정으로 ③(**대조만 추가**)을 집행해 수치를 노출했다. ①·②는
*"이 열의 독자가 누구인지"* 가 확인될 때까지 보류였다 — 사람이 탐색에 쓰는지
스크립트가 파싱하는지 모르는 채 지우면 되돌리기 어렵기 때문이다.

**2026-08-11 사람 결정: 독자는 «사람 + AI» 이며 ① 을 채택한다.**
읽는 쪽이 실재하므로 ②(열 삭제)는 배제되고, 손 관리를 그만두고
**파생값(derived value — 다른 값에서 자동으로 계산되는 값)으로 선언**한다.

## 전량이거나 0이거나

#61 은 **부분 동기화를 금지**한다 — 76건 중 일부만 고치면 나머지가 남아
**회차 간 수치가 원인 불명으로 움직인다.** 이 스크립트는 **등재 행 전건**을
맞추며, 그것이 ① 결정 이후에야 허용되는 이유다.

## 두 가지 행 모양을 다룬다

    | [x.md](concepts/x.md) | 제목 | 태그 | 2026-08-05 |   ← 4열: 날짜 셀 **치환**
    | [y.md](concepts/y.md) | 제목 | 태그 |                 ← 3열: 날짜 셀 **추가**

3열 행은 표 헤더가 4열을 선언하는데 셀이 빠진 것이다(2026-08-11 실측 **4건**).
`index_rows()` 는 이것을 `None` 으로 돌려주며 **«불일치» 와 구별해 세야 한다** —
합치면 조치 대상이 부풀려진다. 이 스크립트는 둘 다 채운다.

## 무엇을 건드리지 않는가

- 🔴 **`wiki/concepts/**`·`topics/**` 를 쓰지 않는다.** 이 스크립트는 `index.md`
  **한 파일만** 쓴다. 반대 방향(열 값을 `updated` 로 밀어넣기)은 본문을 안 고치고
  `updated` 를 올리는 것이라 **#40 경로**를 그대로 밟는다 — "오래된 콘텐츠"·"90일+"
  두 지표에서 파일이 빠져 분류 작업이 자기가 겨냥한 문제를 숨긴다.
- **`## 최근 변경 이력` 표.** 그쪽은 대상 파일을 **산문**(`concepts/x.md`, 링크 아님)으로
  적으므로 `INDEX_LINK_RE` 에 걸리지 않는다. 걸리게 하면 이력 기록을 덮어쓴다.
- **등재 행인데 대상 파일이 없는 경우.** 그것은 #6 «유령 등재» 이고 이 스크립트의
  일이 아니다 — 조용히 건너뛰고 `--check` 에서도 세지 않는다.

## 멱등성 (idempotent — 몇 번 돌려도 결과가 같음)

값이 그대로면 파일을 쓰지 않는다. 매 빌드가 `wiki/` 를 더럽히면
`ALLOW_WIKI_EDIT=1` 우회가 상시화된다(`inject-self-metrics.py` 와 같은 판단).

사용:
    python3 scripts/sync-index-dates.py           # 주입
    python3 scripts/sync-index-dates.py --check   # 어긋나 있으면 exit 1
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wiki_scan import INDEX_LINK_RE, ISO_DATE_RE, mask_lines, updated_date  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIKI = os.path.join(ROOT, "wiki")
INDEX = os.path.join(WIKI, "index.md")

# 줄 끝의 «| 2026-08-05 |» — 날짜 셀 치환용. 값의 괄호 주석은 열에 싣지 않는다.
TAIL_DATE_RE = re.compile(r"\|[ \t]*\d{4}-\d{2}-\d{2}[ \t]*\|[ \t]*$")


def _updated(rel):
    """`concepts/x.md` 의 frontmatter `updated` 선두 토큰. 없으면 None.

    ✅ **파싱은 `wiki_scan.updated_date` 가 정본이다** (원장 #64-b). 여기 있던 로컬
    `UPDATED_RE` 는 걷어냈다 — 남겨 두면 그 자체가 사본이고, 한쪽만 고쳐지면 검사기끼리
    다른 값을 낸다(#43·#24). 이 함수에 남은 일은 **파일 IO 뿐**이다.

    ⚠️ 종전의 `f.read(4096)` 머리 휴리스틱도 함께 걷었다. 정본 함수는 frontmatter 블록을
    직접 잡으므로 범위를 미리 좁힐 이유가 없고, 4096 은 근거 없는 상수였다.
    행위 보존은 322행 `{rel: updated}` 맵 전문 diff **0건**으로 확인했다.
    """
    path = os.path.join(WIKI, rel)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        return updated_date(f.read(), source=rel)


def sync(text):
    """(새 본문, 변경 목록) 을 돌려준다. 변경 목록 = [(rel, 옛값, 새값)]."""
    lines = text.splitlines(keepends=True)
    masked = mask_lines(lines, source="wiki/index.md")
    out, changed = [], []
    for raw, m in zip(lines, masked):
        hit = INDEX_LINK_RE.search(m)
        if not hit or not m.lstrip().startswith("|"):
            out.append(raw)
            continue
        rel = hit.group(1)
        new = _updated(rel)
        if new is None:                      # 유령 등재 — #6 소관, 건드리지 않는다
            out.append(raw)
            continue
        body = raw.rstrip("\n")
        nl = raw[len(body):]
        old_m = TAIL_DATE_RE.search(body)
        old = old_m.group(0).strip("| \t") if old_m else None
        if old == new:
            out.append(raw)
            continue
        body = TAIL_DATE_RE.sub(f"| {new} |", body) if old_m else f"{body.rstrip()} {new} |"
        out.append(body + nl)
        changed.append((rel, old, new))
    return "".join(out), changed


def main():
    check = "--check" in sys.argv
    with open(INDEX, encoding="utf-8") as f:
        text = f.read()
    new_text, changed = sync(text)

    if not changed:
        print("[sync-index-dates] 최신 — 등재 행 날짜 열이 `updated` 와 전건 일치")
        return 0

    fill = sum(1 for _, o, _ in changed if o is None)
    print(f"[sync-index-dates] {len(changed)}건 어긋남 (치환 {len(changed) - fill} · 빈 칸 채움 {fill})")
    for rel, o, n in changed[:15]:
        print(f"  · {rel}: {o or '(빈 칸)'} -> {n}")
    if len(changed) > 15:
        print(f"  … 외 {len(changed) - 15}건")

    if check:
        print("🔴 `--check` 이므로 쓰지 않았다. 동기화하려면 플래그 없이 실행하라.")
        return 1
    with open(INDEX, "w", encoding="utf-8") as f:
        f.write(new_text)
    print(f"✓ wiki/index.md 갱신 — {len(changed)}건")
    return 0


if __name__ == "__main__":
    sys.exit(main())
