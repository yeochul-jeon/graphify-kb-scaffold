#!/usr/bin/env python3
"""`raw/**/*.md` frontmatter 구조 검사 — 원장 #52 조치안 ①.

**왜 있는가.** `raw/` 는 위키 주장의 근거 보관소인데 **그 구조를 보는 눈이 저장소에
없었다.** 2026-08-09 에 `note:` 를 붙이며 닫는 `---` 을 빠뜨려 본문 한 절이
블록 스칼라에 삼켜졌고, 파일은 여전히 유효해 보였으며 **어느 검사기도 잡지 못했다.**
발견 경로가 우연이었다(대조 수치가 이상해서 파서를 의심하다 나왔다).

네 항목을 본다 — 전부 기계 판정이다.

  ⓐ 닫는 `---` 실재
  ⓑ 본문 길이 0 아님
  ⓒ 정본 YAML 파서로 frontmatter 파싱 성공
  ⓓ `ingested_date` 가 REASON_SINCE 이후면 `note` 첫 줄이 `수집 이유: <내용>`
     (2026-11-08 사용자 결정 «ingest 제안 ① 채택 + 검사기». 그 전 raw 는 고치지 않으므로
     대상에서 뺀다. 목적: «ingest 가 무분별했는가» 를 다음 달에 수로 판정하려고)

🔴 **ⓐ·ⓑ 는 #52 를 잡지 못한다. ⓒ 만 잡는다.** 2026-08-09 에 커밋 `2c3d4b2` 의
실제 파손본으로 확인했다 — 본문의 수평선(`---`)이 닫는 구분자 노릇을 해 ⓐ 가 통과했고,
남은 본문이 3,808자라 ⓑ 도 통과했다. ⓒ 만 `ScannerError` 로 잡았다.
**세 항목 중 하나를 빼도 되는 것이 아니다.**

🔴 **ⓒ 는 진짜 YAML 파서여야 한다.** `check-source-drift.py` 의 `frontmatter()` 는
줄 단위 정규식이라 블록 스칼라를 모르고, 파손본에서 `note` 를 **길이 1로 읽고 통과**했다.
그 파서로 ⓒ 를 구현하면 검사기가 있는데 결함을 못 잡는 상태가 된다.

⚠️ PyYAML 이 필요하다. `graphify-out/.graphify_python` 인터프리터에는 없으므로
`scripts/graphify-py.sh` 로 돌리지 말고 PyYAML 이 있는 `python3` 로 돌린다.
없으면 **exit 2 로 죽는다** — ⓒ 를 조용히 건너뛰면 이 검사기의 존재 이유가 사라진다.

사용:
  python3 scripts/check-raw-structure.py            # 위반만
  python3 scripts/check-raw-structure.py --verbose  # 집계까지

종료 코드: 0 위반 없음 · 1 위반 있음 · 2 검사기 미완(PyYAML 부재)
"""
import os, re, sys, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "raw")
REASON_SINCE = "2026-11-09"
REASON_PREFIX = "수집 이유:"
FM = re.compile(r"\A---\n(.*?)\n---(?:\n|\Z)", re.S)

try:
    import yaml
except ImportError:
    sys.stderr.write(
        "🔴 PyYAML 이 없어 ⓒ(정본 YAML 파싱)를 실행할 수 없다.\n"
        "   ⓐ·ⓑ 만 돌리는 것은 의미가 없다 — #52 를 잡는 것은 ⓒ 뿐이다.\n"
        "   PyYAML 이 있는 인터프리터로 실행하라: python3 scripts/check-raw-structure.py\n")
    sys.exit(2)


def reason_violation(meta):
    """ⓓ — 위반 문구 하나 또는 None. meta 는 파싱된 frontmatter dict."""
    if not isinstance(meta, dict):
        return None
    d = str(meta.get("ingested_date") or "")[:10]
    # 날짜 형식이 아니면(템플릿의 `YYYY-MM-DD` 등) 판정하지 않는다 — 문자열 비교로 'Y' > '2' 가 된다
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d) or d < REASON_SINCE:
        return None
    note = meta.get("note")
    first = next((l.strip() for l in str(note or "").splitlines() if l.strip()), "")
    if not first.startswith(REASON_PREFIX) or not first[len(REASON_PREFIX):].strip():
        return f"ⓓ `note` 첫 줄이 `{REASON_PREFIX} <내용>` 이 아니다 (ingested_date {d} ≥ {REASON_SINCE})"
    return None


def check(path):
    """(위반 목록, frontmatter 유무) 를 돌려준다."""
    with open(path, encoding="utf-8") as f:
        text = f.read()

    if not text.startswith("---\n"):
        # frontmatter 자체가 없는 파일. `raw/Clippings/**` 등에 실재하므로
        # 위반이 아니라 별도 집계로 뺀다 — 신규 생성 금지는 다른 규칙이다.
        return [], False

    m = FM.match(text)
    if not m:
        return ["ⓐ 닫는 `---` 이 없다 — frontmatter 가 파일 끝까지 열려 있다"], True

    bad = []
    if not text[m.end():].strip():
        bad.append("ⓑ 본문이 비어 있다")
    try:
        meta = yaml.safe_load(m.group(1))
    except Exception as e:
        first = str(e).strip().splitlines()[0]
        bad.append(f"ⓒ YAML 파싱 실패 — {type(e).__name__}: {first}")
        return bad, True
    r = reason_violation(meta)
    if r:
        bad.append(r)
    return bad, True


def main():
    verbose = "--verbose" in sys.argv
    files = sorted(glob.glob(os.path.join(RAW, "**", "*.md"), recursive=True))
    violations = []
    with_fm = 0
    for p in files:
        bad, has_fm = check(p)
        with_fm += has_fm
        for b in bad:
            violations.append((os.path.relpath(p, ROOT), b))

    if verbose:
        print(f"검사 대상 `raw/**/*.md`: {len(files)}건")
        print(f"  └ frontmatter 보유: {with_fm}  · 없음: {len(files) - with_fm} (판정 제외)")
        print(f"검사 항목: ⓐ 닫는 `---` · ⓑ 본문 길이 · ⓒ 정본 YAML 파싱 · ⓓ 수집 이유(ingested_date ≥ {REASON_SINCE})")
        print()

    if violations:
        print(f"🔴 위반 {len(violations)}건")
        for path, b in violations:
            print(f"  {path}\n      {b}")
        return 1

    print("위반 없음.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
