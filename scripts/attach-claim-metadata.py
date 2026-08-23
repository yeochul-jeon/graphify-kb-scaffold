"""wiki concept/topic 의 claim_status·last_verified·review_due 를 sources 구성에서 파생한다.

파생 규칙 (`.claude/rules/wiki-concepts.md` §claim_status / evidence_level 열거값 이 단일 출처):

  - sources 가 **전부** output/     → claim_status: inferred
      규칙의 "output 합성 결과를 승격" 정의 그대로다.
  - sources 가 비어있지 않은 나머지 → claim_status: source_backed
      raw 가 주력이고 output 이 보조 인용인 경우는 승격이 아니다.
      선례: bulk-request-transaction-optimization.md · llm-large-scale-document-generation-pipeline.md
      (둘 다 output 을 인용하면서 source_backed 이며, 이는 결함이 아니다)
      raw/ 경로가 아닌 출처도 포함한다 — 외부 URL 직접 인용(bff-pattern.md → samnewman.io),
      스크립트·규칙 파일 인용(vector-db-less-knowledge-base.md, 이미 source_backed 로 부착됨),
      다른 wiki 개념 집합 인용(error-handling.md) 이 실제로 존재한다.
  - sources 없음/빈 배열            → **건드리지 않는다**
      없는 출처를 근거로 source_backed 를 찍을 수 없다. 사람이 개별 판단한다.

  last_verified / review_due 는 null 로 채운다 — 기존 부착분 51/54 가 null 인 관행을 따른다.

evidence_level 은 **sources 구성만으로 파생할 수 없다** — 규칙이 그 값을 *본문 주장의 근거 강도*에
묶어놨기 때문이다(우선순위 규칙: "어긋나면 낮은 쪽에 맞춘다"). 도메인 맵은 본문을 못 본다.

따라서 이 스크립트는 **기본값 secondary + 본문 판독으로 확정된 예외 표**를 쓴다:

  - PRIMARY / AI_SYNTHESIS 집합은 2026-07-27 에 `primary` 후보 34건(공식문서 도메인 15 + github 21)을
    서브에이전트 3배치로 본문 전량 판독해 확정한 결과다. 근거는 계획서
    `.claude/reports/plan/2026-07-27-003-claim-evidence-attach.md` §실측 결과 — T2 에 개념별로 기재돼 있다.
  - 나머지는 secondary. 우선순위 규칙이 지시하는 보수적 선택이며 기존 부착분 분포(75% secondary)와도 맞는다.
  - youtube·wikipedia·기술블로그는 사전 확정으로 secondary (계획서 §사전 확정 판정).

  이 표를 늘리려면 **반드시 본문을 읽고** 계획서나 후속 문서에 근거를 남긴 뒤 추가한다.
  도메인만 보고 primary 를 추가하지 말 것 — 실측에서 aws.amazon.com 인용 8건 중 primary 는 0건이었다
  (전부 레퍼런스가 아니라 블로그 해설글이었다).

이미 claim_status 를 가진 파일은 절대 수정하지 않는다 — 이 스크립트는 미부착분 전용이다.

사용:
    scripts/graphify-py.sh scripts/attach-claim-metadata.py            # dry-run (기본)
    scripts/graphify-py.sh scripts/attach-claim-metadata.py --apply    # 실제 쓰기
"""
import os, re, glob, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wiki_scan import claim_enums  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIKI = os.path.join(ROOT, "wiki")

# 이 스크립트가 **방출하는** 값들. 파생 규칙(어느 것을 낼지)은 아래 함수들이 정하고,
# 여기서는 그 값들이 정본 열거값의 원소인지만 확인한다.
_EMITS = {
    "claim_status": {"inferred", "source_backed"},
    "evidence_level": {"primary", "ai_synthesis", "secondary"},
}


def _assert_enums_match_canon():
    """방출 리터럴이 정본을 벗어나면 **쓰기 전에** 멈춘다 (원장 #64-b).

    🔴 이 스크립트는 열거값을 하드코딩해 방출한다. 그것 자체는 결함이 아니다 —
    「셋 중 어느 것을 낼지」가 파생 규칙이라 조회로 바꿀 수 없다. 결함이 되는 조건은
    **정본이 바뀌었는데 여기가 안 바뀌는 것**이고, 그때 이 도구는 규격 위반 값을
    322파일에 소급 부착한다. 필요한 결합은 「정본과 갈리면 멈춘다」 하나뿐이다.
    """
    spec = os.path.join(ROOT, ".claude/rules/wiki-concepts.md")
    with open(spec, encoding="utf-8") as f:
        canon = claim_enums(f.read())
    for field, emitted in _EMITS.items():
        stray = emitted - set(canon[field])
        if stray:
            sys.exit(f"[attach-claim-metadata] 중단 — 방출값이 정본에 없다: "
                     f"{field} {sorted(stray)} (정본 {sorted(canon[field])}). "
                     f"{os.path.relpath(spec, ROOT)} 를 보고 이 파일을 맞춰라.")

FM = re.compile(r"^---\n(.*?)\n---\n", re.S)
# sources 는 두 YAML 표기가 실제로 섞여 있다 — 인라인만 보면 블록 리스트를 "출처 없음" 으로 오판한다.
#   인라인:      sources: [raw/a.md, raw/b.md]
#   블록 리스트: sources:
#                  - raw/a.md
# 2026-07-27: 이 누락 때문에 envelope-encryption.md·spring-date-format.md 가 여러 회차 동안
# lint 의 "출처 누락" 으로 오보됐다. 두 파일 모두 실제로는 raw 출처를 3~4건씩 갖고 있다.
SOURCES_INLINE = re.compile(r"^sources:\s*\[(.*?)\]", re.M | re.S)
SOURCES_BLOCK = re.compile(r"^sources:\s*\n((?:[ \t]+-[ \t]*\S.*\n?)+)", re.M)

# claim_status 를 넣을 위치: 이 필드 바로 뒤 (없으면 frontmatter 끝)
ANCHOR = "confidence"

# --- evidence_level 판정표 (2026-07-27 본문 판독 확정) ---
# 후보 34건을 전량 본문 판독한 결과. 개념별 근거는 계획서 §실측 결과 — T2.
PRIMARY = {
    # 2026-07-27 독립 검증 후 재확인: 후보 필터에 따옴표 처리 버그가 있어 12건이 판독을 건너뛰었으나
    # (arxiv.org 미포함, `source_url: "https://..."` 의 따옴표로 파싱 실패), 재판독 결과 12건 전부
    # secondary 유지였다 — 필터 버그가 결과를 바꾸지 않았다. 근거는 계획서 §실측 결과 — T4.
    "llm-kg-tools-comparison",      # sources 8건 전부 공식문서·repo README 원문
    "notification-pattern",         # martinfowler.com 본인 원문 2건, 본문이 범위를 벗어나지 않음
    "ai-dlc-interaction-patterns",  # awslabs/aidlc-workflows README·docs 원문 캡처
    "claude-code-harness",          # revfactory/harness repo 자신의 README·SKILL.md 캡처
    "claude-code-agent-teams",      # 위와 동일 캡처, 6패턴·전제조건이 원문에서 확인됨
    "rfc9457-problem-details",      # zalando/problem README 캡처 + RFC 9457 원문
    "secall",                       # hang-in/seCall repo README 원문 캡처
}
AI_SYNTHESIS = {
    "strangler-fig-pattern",             # 본문 4·5절이 output/answer-20260412-1800.md 와 문장 단위 일치
    "claude-code-configuration-strategy",# MSA 전파 로드맵 절이 output/answer-20260710-0054.md 유래
    "lightrag-nano-graphrag",            # graphify-kb 비교표가 출처 어디에도 없는 자체 종합
    # 아래 3건은 sources 가 전부 output/ 이라 claim_status 도 inferred 다
    "graph-visualization-guide",
    "msa-error-design-guide",
    "toon-format",
}


def evidence_for(slug):
    if slug in PRIMARY:
        return "primary"
    if slug in AI_SYNTHESIS:
        return "ai_synthesis"
    return "secondary"


def targets():
    return sorted(
        glob.glob(os.path.join(WIKI, "concepts", "*.md"))
        + glob.glob(os.path.join(WIKI, "topics", "*.md"))
    )


def parse_sources(front):
    m = SOURCES_INLINE.search(front)
    if m:
        return [p.strip().strip('"').strip("'") for p in m.group(1).split(",") if p.strip()]
    m = SOURCES_BLOCK.search(front)
    if m:
        return [
            ln.strip().lstrip("-").strip().strip('"').strip("'")
            for ln in m.group(1).splitlines()
            if ln.strip()
        ]
    if re.search(r"^sources:\s*$", front, re.M):
        return []  # 필드는 있으나 값이 없음
    return None  # 필드 자체가 없음


def verdict(paths):
    """(claim_status, 사유) 또는 (None, 사유) — None 이면 건드리지 않는다."""
    if paths is None:
        return None, "sources 필드 없음"
    if not paths:
        return None, "sources 빈 배열"
    if all(p.startswith("output/") for p in paths):
        return "inferred", "output 전용"
    return "source_backed", "출처 있음 (output 전용 아님)"


def insert_fields(front, status, evidence):
    """frontmatter 문자열에 **없는 필드만** 삽입한다.

    필드 단위로 검사하는 이유: 일부 파일은 수동 리뷰로 last_verified 만 먼저 갖고 있다.
    4필드를 통째로 넣으면 last_verified 가 두 번 들어가고, YAML 파서는 뒤엣값을,
    regex 판독은 앞엣값(null)을 읽어 서로 다른 답을 낸다.
    2026-07-27 에 mattpocock-skills.md 에서 실제로 발생했다(verified: true 인데 last_verified 가 null 로 읽혔다).
    """
    want = [
        ("claim_status", status),
        ("evidence_level", evidence),
        ("last_verified", "null"),
        ("review_due", "null"),
    ]
    add = [f"{k}: {v}" for k, v in want if not re.search(rf"^{k}:", front, re.M)]
    if not add:
        return front
    lines = front.split("\n")
    at = None
    for i, ln in enumerate(lines):
        if ln.startswith(ANCHOR + ":"):
            at = i + 1
            break
    if at is None:
        at = len(lines)
    return "\n".join(lines[:at] + add + lines[at:])


def main():
    _assert_enums_match_canon()   # 정본과 갈리면 여기서 멈춘다 (원장 #64-b)
    apply = "--apply" in sys.argv
    stats = {}
    changed = []
    for path in targets():
        with open(path, encoding="utf-8") as f:
            text = f.read()
        m = FM.match(text)
        if not m:
            stats["frontmatter 없음"] = stats.get("frontmatter 없음", 0) + 1
            continue
        front = m.group(1)
        if re.search(r"^claim_status:", front, re.M) and re.search(
            r"^evidence_level:", front, re.M
        ):
            stats["이미 부착 (건드리지 않음)"] = stats.get("이미 부착 (건드리지 않음)", 0) + 1
            continue
        status, why = verdict(parse_sources(front))
        if status is None:
            stats[f"스킵 — {why}"] = stats.get(f"스킵 — {why}", 0) + 1
            print(f"  SKIP {os.path.relpath(path, ROOT)} — {why}", file=sys.stderr)
            continue
        slug = os.path.basename(path)[:-3]
        evidence = evidence_for(slug)
        stats[f"{status} + {evidence}"] = stats.get(f"{status} + {evidence}", 0) + 1
        changed.append((path, status, evidence))
        if apply:
            new = "---\n" + insert_fields(front, status, evidence) + "\n---\n" + text[m.end():]
            with open(path, "w", encoding="utf-8") as f:
                f.write(new)

    mode = "APPLIED" if apply else "DRY-RUN (쓰기 없음 — --apply 로 실행)"
    print(f"\n[attach-claim-metadata] {mode}", file=sys.stderr)
    for k, v in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"  {v:4}  {k}", file=sys.stderr)
    print(f"  ---- 대상 {len(changed)}건", file=sys.stderr)


if __name__ == "__main__":
    main()
