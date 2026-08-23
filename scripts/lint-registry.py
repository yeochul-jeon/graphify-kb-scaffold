#!/usr/bin/env python3
"""탐구 제안 원장(wiki/_meta/suggested-investigations.md) 구조 검사기.

기본 동작: **읽기 전용 보고**. 지표를 출력하고 항상 exit 0.
  python3 scripts/lint-registry.py

판정 모드: 위반이 하나라도 있으면 exit 1.
  python3 scripts/lint-registry.py --check

⚠️ 이 스크립트는 파일을 **쓰지 않는다.** `--fix`/`--apply` 는 없다.
   원장 편집은 문맥 판단이 필요해 사람이 수행한다.
   (저장소 내 다른 스크립트는 `--apply` 로 쓰기를 여는 관습이지만,
    이 스크립트에는 쓰기 경로 자체가 없다. 극성 혼동을 막으려 여기 명시한다.)

규격 단일 출처: `.claude/commands/lint.md` §11.
  `유형` 열거값은 그 파일에서 **읽어온다**. 하드코딩하면 규격이 두 곳으로
  갈라져 검사기 정의가 흔들리는 결함(#16 계열)이 된다.

지표:
  M2  종결 상태 부착률   — 취소선 항목 중 `- **종결**:` 키를 가진 비율
  M3  취소선 ↔ 상태 정합 — 한쪽만 있는 항목 수 (0이어야 한다)
  M4  번호 중복          — 항목 번호 중복 수 (0이어야 한다)
  M6  `유형` 축 순수성   — `유형` 값에 종결 어휘가 섞인 수 (0이어야 한다)
  M7  `유형` 열거값 정합 — 기저 유형이 규정 집합에 있는 수 (전건이어야 한다)
"""

import argparse
import re
import sys

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import wiki_scan
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REGISTRY = REPO / "wiki/_meta/suggested-investigations.md"
SPEC = REPO / ".claude/commands/lint.md"

TYPE_PREFIX = "- **유형**: "
CLOSURE_PREFIX = "- **종결**: "

# lint.md §11-3 의 종결 축 열거값
CLOSURE_VALUES = {"resolved", "refuted"}

# lint.md §11-3 — 분류 축에 섞이면 안 되는 종결 어휘
CLOSURE_VOCAB = ["해소", "종결", "대기", "이월", "반증", "승계"]

# lint.md §11-3 — 기저 유형을 끊는 구분자.
# `→` 를 빼면 `오래된 커버리지 → `/ingest`+`/compile` 재실행` 에서
# 코드 경로의 `/` 를 첫 구분자로 잡아 기저 유형이 깨진다.
BASE_TYPE_DELIMS = ("—", "/", "(", "→")

ITEM_NUM_RE = re.compile(r"^### ([0-9]+(?:-[a-z])?)\.")


def mask_code(lines):
    """코드 스팬·펜스 마스킹 — 정본은 `wiki_scan` 이다 (원장 #24·#41·#43).

    원장 규약(`weather.md` §메타 파일 작성 주의)이 링크·태그 문법을 백틱으로 감싸라고
    요구하므로, 벗기지 않으면 산문에 인용한 `<details>` 가 실제 태그로 집계된다.
    실측(2026-08-07, 원장 #41): 인용 한 곳에 depth 가 열린 채 남아 이후 항목 전부가
    한 항목의 보관본으로 잡혀 **팬텀 M4 위반 15건 + `--check` exit 1** 이 났다.

    ⚠️ 마스킹은 **줄 수와 개행을 보존**해야 한다 — 이 검사기는 줄 번호로 보고하므로
    통째 치환하면 L번호가 전부 어긋난다. `wiki_scan` 이 그것을 보장한다.
    """
    return wiki_scan.mask_lines(lines)


def outside_details(lines):
    """각 줄이 `<details>` 바깥(depth 0)인지 판정한다.

    ⚠️ 호출자는 **`mask_code` 를 통과시킨 줄**을 넘겨야 한다 (원장 #41).

    ⚠️ 정규식으로 `<details>...</details>` 를 통째로 지우는 방식
    (`re.sub(r'<details>.*?</details>', '', text, flags=re.S)`)을 **쓰지 않는다.**
    이 저장소에서 그 방식이 실제로 오탐을 냈다 — 존재하지 않는 항목 번호
    중복(#14)을 보고했고, 줄 번호 depth 누적으로 재측정해 반증됐다.

    판정 시점은 **줄 시작 시점**이다. 여는 태그가 있는 줄과 닫는 태그가
    있는 줄 자체는 블록 경계이므로 항목 헤딩이 올 수 없다.
    """
    depth = 0
    flags = []
    for line in lines:
        flags.append(depth == 0)
        depth += len(re.findall(r"<details\b", line))
        depth -= len(re.findall(r"</details>", line))
    return flags, depth


def load_enum_set(spec_path):
    """`lint.md` §11-3 스키마 예시에서 `유형` 열거값 집합을 읽는다.

    형식: `- **유형**: A | B | C | ...` (파이프 구분)
    파싱 실패는 조용히 넘기지 않고 에러로 처리한다 — 규격을 못 읽었는데
    하드코딩 기본값으로 통과시키면 규격 드리프트를 검사기가 감춘다.
    """
    if not spec_path.exists():
        sys.exit(f"규격 문서를 찾을 수 없다: {spec_path}")
    for line in spec_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith(TYPE_PREFIX) and "|" in stripped:
            values = [v.strip() for v in stripped[len(TYPE_PREFIX):].split("|")]
            return [v for v in values if v]
    sys.exit(
        f"{spec_path} 에서 `유형` 열거값 행을 찾지 못했다.\n"
        "  §11-3 스키마 예시에 `- **유형**: A | B | ...` 행이 있어야 한다."
    )


def base_type(value):
    positions = [value.find(d) for d in BASE_TYPE_DELIMS if value.find(d) != -1]
    return (value[:min(positions)] if positions else value).strip()


def collect_items(lines, outside):
    """항목 = `<details>` 바깥의 `^### ` 헤딩. 본문은 다음 항목 헤딩 직전까지."""
    starts = [i for i, line in enumerate(lines)
              if line.startswith("### ") and outside[i]]
    items = []
    for n, start in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        items.append({
            "line": start + 1,
            "heading": lines[start].rstrip("\n"),
            "body": lines[start + 1:end],
        })
    return items


def analyze(registry_path, enum_set):
    lines = registry_path.read_text(encoding="utf-8").splitlines(keepends=True)
    # 코드 스팬을 덮은 사본으로 태그 depth 를 센다. 본문 판정은 원문(`lines`)으로 한다.
    outside, final_depth = outside_details(mask_code(lines))
    items = collect_items(lines, outside)

    report = {"items": len(items), "violations": [], "notes": []}

    if final_depth != 0:
        report["violations"].append(
            f"구조: `<details>` 태그가 불균형이다 (파일 끝 depth={final_depth})")

    # ---- M2 / M3 : 취소선 ↔ 종결 키 -------------------------------------
    closed, with_key, only_tilde, only_key, bad_value = [], [], [], [], []
    for item in items:
        has_tilde = "~~" in item["heading"]
        key_lines = [l for l in item["body"] if l.startswith(CLOSURE_PREFIX)]
        if has_tilde:
            closed.append(item)
            if key_lines:
                with_key.append(item)
            else:
                only_tilde.append(item)
        elif key_lines:
            only_key.append(item)
        for kl in key_lines:
            value = kl[len(CLOSURE_PREFIX):].split("|")[0].strip()
            if value not in CLOSURE_VALUES:
                bad_value.append((item["line"], value))

    report["M2"] = (len(with_key), len(closed))
    report["M3"] = len(only_tilde) + len(only_key)
    for item in only_tilde:
        report["violations"].append(
            f"M3(a) L{item['line']}: 취소선은 있는데 `종결` 키가 없다 — {item['heading'][:70]}")
    for item in only_key:
        report["violations"].append(
            f"M3(b) L{item['line']}: `종결` 키는 있는데 취소선이 없다 — {item['heading'][:70]}")
    for line_no, value in bad_value:
        report["violations"].append(
            f"종결 열거값 위반 L{line_no}: {value!r} — 허용값 {sorted(CLOSURE_VALUES)}")

    # ---- M4 : 항목 번호 중복 --------------------------------------------
    numbers = defaultdict(list)
    unnumbered = []
    for item in items:
        m = ITEM_NUM_RE.match(item["heading"])
        if m:
            numbers[m.group(1)].append(item["line"])
        else:
            # `### A.` `### B.` 형태의 미분류 제안 (lint.md §11-2 (d)).
            # 번호가 없으므로 중복 판정 대상이 아니다. 조용히 빠뜨리지 않고
            # 건수를 보고해 회귀 감시에 구멍이 생기지 않게 한다.
            unnumbered.append(item["line"])
    dupes = {k: v for k, v in numbers.items() if len(v) > 1}
    report["M4"] = len(dupes)
    report["unnumbered"] = unnumbered
    for num, locs in sorted(dupes.items()):
        report["violations"].append(f"M4 번호 중복: '{num}' 이 {locs} 에 중복")

    # M4 보조 — 보관본 번호 재사용 (lint.md §11-2 (b)).
    # `<details>` 안쪽을 항목 집계에서 빼기만 하면, 보관된 옛 번호를 새 제안에
    # 다시 발급해도 검사가 통과한다. 보관본의 번호는 그것을 품은 항목의 번호와
    # 같아야 한다는 규칙으로 이 구멍을 막는다.
    for item in items:
        m = ITEM_NUM_RE.match(item["heading"])
        owner = m.group(1) if m else None
        for offset, body_line in enumerate(item["body"], start=item["line"] + 1):
            am = ITEM_NUM_RE.match(body_line)
            if am and am.group(1) != owner:
                report["violations"].append(
                    f"M4 보관본 번호 불일치 L{offset}: 항목 #{owner} 안의 "
                    f"보관본이 #{am.group(1)} 을 쓴다 — 번호 재사용 가능성")

    # 원문 보존 표식 (lint.md §11-2 (b)) — 경고 전용.
    # 종결 항목에 `<details>` 보관본 또는 `- **근거**:` 가 있으면 원문 보존이 확인된다.
    # ⚠️ 둘 다 없다고 **소실은 아니다** (원장 #42). §11-3 의 `근거` 필드는 신규 항목용
    #   스키마이고 소급 적용 대상이 아니라, 그 필드를 아예 안 쓰는 항목이 상당수다.
    #   실측 기저율을 함께 내서 읽는 쪽이 판단하게 한다 — 미종결 항목도 같은 비율로
    #   비어 있으면 그것은 포맷 변이지 소실 신호가 아니다.
    # ⚠️ exit code 에 반영하지 않는다 — 이미 소실된 건은 표기를 고쳐서 되돌릴
    #   수 없다. 위반으로 세면 검사기가 영구히 exit 1 이 되어 회귀 감시가 죽는다.
    def has_rationale(item):
        return any(l.startswith("- **근거**: ") for l in item["body"])

    unmarked = []
    for item in closed:
        if "<details" in "".join(item["body"]):
            continue
        if has_rationale(item):
            continue
        unmarked.append(item["line"])
    report["unmarked_original"] = unmarked
    open_items = [i for i in items if "~~" not in i["heading"]]
    report["rationale_base"] = (
        sum(1 for i in open_items if not has_rationale(i)), len(open_items))

    # ---- M6 / M7 : `유형` 두 축 ------------------------------------------
    # 활성(`<details>` 바깥)과 보관본(안쪽)을 분리해 센다.
    # ⚠️ 보관본의 `유형` 은 **고칠 수 없다** — §11-2 (b) 가 원 제안 원문의 수정을
    #   금지하기 때문이다. 보관본 위반을 exit code 에 반영하면 검사기가 영구히
    #   실패하고, 그렇다고 집계에서 지우면 정의가 사라진다. 그래서 **둘 다 세되
    #   판정은 활성만** 한다. 총계(활성+보관)는 과거 측정값과의 비교용으로 남긴다.
    live_total = live_mixed = live_enum_ok = 0
    arch_total = arch_mixed = arch_enum_ok = 0
    off_enum = defaultdict(list)
    for i, line in enumerate(lines, start=1):
        if not line.startswith(TYPE_PREFIX):
            continue
        value = line.rstrip("\n")[len(TYPE_PREFIX):]
        # 규격 문서 자체의 스키마 예시 행(파이프 나열)은 데이터가 아니다.
        if "|" in value and registry_path == SPEC:
            continue
        is_live = outside[i - 1]
        hits = [v for v in CLOSURE_VOCAB if v in value]
        bt = base_type(value)
        in_enum = bt in enum_set
        if is_live:
            live_total += 1
            live_mixed += bool(hits)
            live_enum_ok += in_enum
            if hits:
                report["violations"].append(
                    f"M6 L{i}: `유형` 에 종결 어휘 {hits} 가 섞였다 — {value!r}")
            if not in_enum:
                report["violations"].append(
                    f"M7 L{i}: 기저 유형 {bt!r} 이 규정 집합 밖 — {value!r}")
        else:
            arch_total += 1
            arch_mixed += bool(hits)
            arch_enum_ok += in_enum
            if hits or not in_enum:
                report["notes"].append(
                    f"보관본 L{i}: {value!r} — 원문이므로 수정하지 않는다")
        if not in_enum:
            off_enum[bt].append(i)

    report["M6"] = (live_mixed, live_total)
    report["M7"] = (live_enum_ok, live_total)
    report["M6_arch"] = (arch_mixed, arch_total)
    report["M7_arch"] = (arch_enum_ok, arch_total)
    report["off_enum"] = dict(off_enum)
    return report


def main():
    parser = argparse.ArgumentParser(
        description="탐구 제안 원장 구조 검사기 (읽기 전용)")
    parser.add_argument("--check", action="store_true",
                        help="위반이 있으면 exit 1 (기본은 보고만 하고 exit 0)")
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument("--spec", type=Path, default=SPEC)
    args = parser.parse_args()

    enum_set = load_enum_set(args.spec)
    r = analyze(args.registry, enum_set)

    def show(p):
        # `--spec` 으로 저장소 밖 경로(예: git show 로 뽑은 과거 규격)를
        # 지정할 수 있으므로 relative_to 실패를 절대경로로 흡수한다.
        try:
            return p.resolve().relative_to(REPO)
        except ValueError:
            return p

    print(f"원장: {show(args.registry)}")
    print(f"규격: {show(args.spec)}  (유형 열거값 {len(enum_set)}종)")
    print(f"  항목(`<details>` 바깥 `### `): {r['items']}")
    if r["unnumbered"]:
        print(f"  └ 번호 없는 미분류 제안: {len(r['unnumbered'])}건 L{r['unnumbered']}")
    print(f"  M2 종결 상태 부착률 : {r['M2'][0]} / {r['M2'][1]}")
    print(f"  M3 취소선↔상태 정합 : {r['M3']}건 위반")
    print(f"  M4 번호 중복        : {r['M4']}건")
    print(f"  M6 `유형` 축 순수성 : {r['M6'][0]} / {r['M6'][1]} 위반 (활성)"
          f"  · 보관본 {r['M6_arch'][0]} / {r['M6_arch'][1]} (판정 제외)")
    print(f"  M7 `유형` 열거값정합: {r['M7'][0]} / {r['M7'][1]} (활성)"
          f"  · 보관본 {r['M7_arch'][0]} / {r['M7_arch'][1]} (판정 제외)")
    if r["off_enum"]:
        print("  └ 규정 밖 기저 유형:")
        for bt, locs in sorted(r["off_enum"].items(), key=lambda kv: -len(kv[1])):
            print(f"       {len(locs):3d}  {bt!r}  L{locs}")

    if r["unmarked_original"]:
        miss, total = r["rationale_base"]
        pct = round(100 * miss / total) if total else 0
        print(f"\n⚠ 참고 — 종결 항목 {len(r['unmarked_original'])}건에 원문 보존 표식이 없다 "
              f"(exit code 미반영):")
        for line_no in r["unmarked_original"]:
            print(f"  - L{line_no}: `<details>` 보관본도 `- **근거**:` 도 없다")
        print(f"  ⚠ 이것은 **소실 근거가 아니다** — 미종결 {total}건 중 {miss}건({pct}%)도 "
              f"`- **근거**:` 를 쓰지 않는다.")
        print( "    §11-3 의 `근거` 는 신규 항목 스키마이고 소급 적용 대상이 아니다. "
               "실제 소실 여부는 git 이력으로 확인한다.")
        print( "    ⚠ 표식을 만들려고 없던 `- **근거**:` 를 지어내지 말 것 — 그것이 이력 위조다.")

    if r["violations"]:
        print(f"\n위반 {len(r['violations'])}건:")
        for v in r["violations"]:
            print(f"  - {v}")
    else:
        print("\n위반 없음.")

    if args.check and r["violations"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
