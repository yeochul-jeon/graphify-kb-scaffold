#!/usr/bin/env python3
"""마크다운 스캔 공통 정의 — **코드 스팬·펜스 마스킹의 단일 출처**.

이 모듈이 생긴 이유는 같은 정규식이 세 곳에 복제돼 있었기 때문이다
(`rebuild-backlinks.py` · `rebuild-cross-edges.py` · `lint-registry.py`).
원장 #24 가 정한 규율 — *"정본이 코드에 있는 상수는 `import` 한다"* — 의 적용이며,
복제본은 한쪽만 고쳐지면 검사기끼리 다른 값을 낸다.

## 왜 정규식 하나로는 안 되는가 (원장 #43)

이전 정본은 이랬다:

    CODE = re.compile(r"```.*?```|`[^`\\n]*`", re.S)
    text = CODE.sub(" ", raw)

두 가지가 틀렸다.

1. **펜스가 짝을 이룬다고 가정한다.** `re.S` 라 짝이 안 맞으면 **첫 열림부터
   다음 ``` 까지를 통째로 삼킨다.** 산문에 끼어든 ` ```yaml 예시 ` 같은 표기가
   실재하며(실측 2026-08-07: `_meta/*` 2파일이 이미 그 조건이고 `weather.md` 는
   ``` 5회 중 줄머리가 **0회**다), 그 상태로 적용하면 문서의 큰 구간이 사라지고
   **그 안의 `[[링크]]` 가 함께 사라진다.** island 판정과 `backlinks.md` 가
   조용히 움직이는데 **종료코드도 stderr 도 없다** — 원장 #35 와 같은 실패 계열이다.
   마크다운에서 펜스는 **줄머리(들여쓰기 3칸 이내)에서만** 성립한다. 그 규칙을
   지키면 산문 중간의 ``` 은 애초에 펜스가 아니다.

2. **백틱 1개만 가정한다.** `` `x` `` 는 잡지만 ``` ``x`` ``` 는 새어나간다.
   백틱 런 길이를 맞춰야 한다.

덤으로, 통째 치환(`sub(" ", text)`)은 펜스 블록이 줄을 삼켜 **줄 수가 줄어든다.**
줄 번호로 보고하는 소비자(`lint-registry.py` 의 depth 누적)가 전부 어긋나므로
마스킹은 **줄 수와 개행을 보존**해야 한다.

⚠️ `~~~` 는 펜스로 취급하지 않는다. 이 저장소는 ``` 만 쓰고 원장 종결 표기가
`~~` 를 쓰므로, `~~~` 를 펜스로 해석하면 이득 없이 오탐 경로만 생긴다.
"""
import difflib
import re
import sys

FENCE_RE = re.compile(r"^\s{0,3}```")        # 펜스는 줄머리에서만 성립한다
INLINE_CODE_RE = re.compile(r"(`+)[^\n]*?\1")  # 백틱 런을 맞춰 `x` 와 ``x`` 를 함께 잡는다

# 위키 문법 설명용 더미 링크 — 실제 개념이 아니다.
PLACEHOLDER = {"wikilink", "개념명", "링크", "concept-name", "concept-a", "concept-b"}

# `index.md` 등재 링크는 본문의 `[[슬러그]]` 가 아니라 **표시 텍스트가 붙은 마크다운 링크**다.
INDEX_LINK_RE = re.compile(r"\[[^\]\n]*\]\(((?:concepts|topics)/[^)\s]+?\.md)\)")
ISO_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")

TAGS_INLINE_RE = re.compile(r"^tags:[ \t]*\[(.*?)\]", re.M | re.S)
TAGS_BLOCK_RE = re.compile(r"^tags:[ \t]*$\n((?:[ \t]+-[ \t]*\S.*\n?)+)", re.M)

# `#12` (AI/LLM 소스 갱신) 의 대상 태그. **부분 문자열이 아니라 집합 원소로 비교한다.**
FAST_MOVING_TAGS = frozenset({"llm", "ai", "claude-code", "agent"})

# `#3` (오래된 콘텐츠) 의 frontmatter `updated` 파서. `sync-index-dates.py:64` 에서 끌어올렸다.
# `(\S+)` 가 핵심이다 — **선두 토큰만** 잡아야 `updated: 2026-04-10 (설명)` 이 살아남는다.
UPDATED_RE = re.compile(r"^updated:[ \t]*(\S+)", re.M)

# `#3` 의 경과일수 임계값. ⚠️ `#12` 의 90일과 **다르다** — 둘을 섞어 재면 이월 항목을
# "틀렸다" 고 오판한다(`/lint` §재측정 규율 2항의 실제 사례). 90일 상수는 여기 두지 않는다.
STALE_DAYS = 30

# `#4` (중복 개념) 파일명 축의 임계값. 실측상 0.81 → 6쌍 · 0.82 → 5쌍 · 0.83 → 4쌍 이라
# **고정값이며 조정 손잡이가 아니다**(§측정 정의 「중복 개념」 행).
DUP_NAME_THRESHOLD = 0.82

# `island` (인바운드 0) 판정. `wiki/backlinks.md` 의 **개념 블록 헤딩**이다 — 그 파일이
# 이미 결정론적 strict-inbound 역인덱스라 코퍼스를 다시 스캔할 이유가 없다.
# 🔴 **`grep <슬러그> backlinks.md` 의 히트 수로 판정하면 방향이 뒤집힌다** — 히트 대부분은
#   *다른 개념 블록 안의 referrer 항목*, 즉 그 슬러그의 **아웃바운드**다. 인바운드는
#   `## [[슬러그]]` 블록의 **존재**로만 성립한다 (lint 41회차가 이 오독으로 인바운드 0인
#   `unlazy-skill` 을 «4곳 이상» 이라 보고했다).
BACKLINK_BLOCK_RE = re.compile(r"^##[ \t]+\[\[([^\]|#\n]+)\]\]", re.M)

# `#14` (enum 위반) 정본 절의 구조. 절 안에서 `**\`필드\`**` 라벨을 만나면 그 아래
# 표의 **첫 열 백틱 값**만 걷는다. 표 헤더(`| 값 |`)·구분선은 백틱이 없어 자연히 빠진다.
ENUM_FIELDS = ("claim_status", "evidence_level")
ENUM_SECTION_RE = re.compile(r"^###\s+.*열거값")
ENUM_LABEL_RE = re.compile(r"^\*\*`(" + "|".join(ENUM_FIELDS) + r")`")
ENUM_ROW_RE = re.compile(r"^\|\s*`([a-z_]+)`\s*\|")


def mask_lines(lines, source=None):
    """줄 리스트의 코드 스팬·펜스를 공백으로 덮는다. **줄 수와 개행을 보존**한다.

    `source` 를 주면 펜스가 닫히지 않은 채 끝났을 때 stderr 로 경고한다 —
    조용히 큰 구간을 지우는 것이 #43 의 실패 양상이므로, 남은 위험은 보이게 만든다.
    치명적으로 다루지 않는 이유는 호출 사슬 때문이다: `graphify-build.sh` 가
    `set -euo pipefail` 이라 비정상 종료하면 뒤따르는 패스가 함께 멈춘다.
    표기 문제 하나로 빌드를 세우는 것은 과잉 대책이다(원장 #35 조치 때의 판단과 대칭).
    """
    blank = lambda s: re.sub(r"[^\n]", " ", s)
    out, in_fence = [], False
    for line in lines:
        if FENCE_RE.match(line):
            in_fence = not in_fence
            out.append(blank(line))
        elif in_fence:
            out.append(blank(line))
        else:
            out.append(INLINE_CODE_RE.sub(lambda m: blank(m.group(0)), line))
    if in_fence and source:
        sys.stderr.write(
            f"[wiki_scan] 경고: {source} 의 코드 펜스가 닫히지 않았다. "
            "파일 끝까지 마스킹됐으므로 그 구간의 [[링크]] 는 집계되지 않는다.\n")
    return out


def mask_text(text, source=None):
    """문자열 버전. 줄 수를 보존하므로 `text.count('\\n')` 이 유지된다."""
    return "".join(mask_lines(text.splitlines(keepends=True), source))


def index_links(text, source=None):
    """`wiki/index.md` 의 **등재 링크**를 `{"concepts/x.md", "topics/y.md"}` 로 돌려준다.

    ## 왜 별도 함수인가 (원장 #60)

    `index.md` 는 본문과 **링크 표기가 다르다.** 본문은 `[[슬러그]]` 인데 `index.md` 의
    개념·주제 목록은 **표시 텍스트가 붙은 마크다운 링크** `[x.md](concepts/x.md)` 다.
    그 사실이 어느 문서에도 없어서 `index.md` 를 점검할 때마다 본문용 정규식을 그대로
    가져다 쓰게 됐고, **lint 30회차에서 미등재 305건이라는 오탐**이 나왔다(실제 0). 306
    파일 중 306 이 "미등재" 로 잡힌 것이며 **전건 오탐**이었다.

    ⚠️ **`grep 'concepts/[^ ]*\\.md'` 로 대신하면 반대 방향으로 틀린다** — `## 최근 변경
    이력` 표가 대상 파일을 **산문으로**(`concepts/mcp-server.md`, 링크 아님) 적으므로
    등재되지 않은 파일까지 등재로 세게 된다. 그래서 **마크다운 링크 형태만** 센다.

    ## 이 함수가 보지 못하는 것 — 「없다」로 보고하지 말 것

    - **`## 태그 빠른 탐색` 프리페이스 행.** 개념명을 **평문**으로 적으므로(`| \\`#retrieval\\` |
      aws-graphrag-toolkit, knowledge-graph |`) 여기 잡히지 않는다. **그것이 맞다** —
      프리페이스는 파생물이 아니라 **큐레이션**이고(`.claude/rules/wiki-concepts.md`
      §프리페이스의 성격) 등재 의무는 `## 개념 목록`·`## 주제 목록` 표가 진다.
    - **`[[슬러그]]` 위키링크.** `index.md` 에도 5건 있으나 전부 `## 최근 변경 이력`
      **산문** 안이며 등재가 아니다. 등재 표기가 언젠가 위키링크로 바뀌면 이 함수는
      **조용히 0 을 돌려준다** — 표기를 바꾸는 안은 #60 등재 시 배제됐지만(표시 텍스트가
      파일명과 다르고 과거 회차 수치와 어긋난다) 바꾼다면 여기를 함께 고쳐야 한다.
    - **절 경계를 보지 않는다.** 파일 전체에서 찾으므로, 위 두 목록 밖에 마크다운 링크가
      새로 생기면 등재로 센다. 현재 실측은 `## 개념 목록`·`## 주제 목록` 밖 **0건**이다.

    코드 스팬·펜스는 `mask_text` 로 먼저 덮는다 — 문서가 예시로 적은 링크를 등재로
    세지 않기 위해서다.
    """
    return set(index_rows(text, source))


def index_rows(text, source=None):
    """등재 링크에 **날짜 열**을 붙여 `{"concepts/x.md": "2026-08-05" | None}` 으로 돌려준다.

    `index_links` 의 상위 함수다 — 같은 줄을 두 번 파싱하지 않기 위해 여기가 정본이고
    `index_links` 는 이 결과의 키 집합이다.

    ## 왜 날짜를 따로 돌려주는가 (원장 #61)

    `## 개념 목록` 표의 마지막 열은 *최종 업데이트* 인데 **frontmatter `updated` 와
    독립적으로 손으로 관리된다.** 30회차 실측에서 **76건이 어긋나 있었고 그중 71건이
    선재**였다. 이 열을 보는 검사가 하나도 없어서(#6 은 **등재 여부만** 본다) 언제부터
    어긋났는지도 알 수 없었다.

    🔴 **이 함수는 판정하지 않는다.** 사람 결정(2026-08-11)이 택한 것은 ③ *"`/lint` 에
    대조만 추가해 수치를 노출한다"* 이며, ①(빌드 주입)·②(열 삭제)는 **이 열의 독자가
    누구인지 확인된 뒤**로 미뤄졌다 — 사람이 탐색에 쓰는지 스크립트가 파싱하는지 모르는
    채 지우면 되돌리기 어렵다. 노출된 수치가 그 확인의 재료가 된다.

    ⚠️ **날짜가 없거나 형식이 다르면 `None` 이다.** `None` 을 *"불일치"* 로 세지 말 것 —
    *"열이 비었다"* 와 *"열이 틀렸다"* 는 다른 상태이며, 합치면 조치 대상이 부풀려진다.

    ⚠️ **`index_links` 가 못 보는 것은 이 함수도 못 본다** — 위 docstring 의 3항 그대로다.

    ⚠️ **한 줄에 링크가 둘이면 첫 번째만 센다.** 날짜 열을 붙이려면 줄 단위로 봐야 하고
    한 줄은 한 등재라는 표 구조를 전제하기 때문이다. **현재 실측으로 그런 줄은 0건**이라
    `index_links` 의 기존 계약(전문 `findall`)과 결과가 같지만, **전제이지 보장이 아니다** —
    목록 표에 링크가 둘인 행이 생기면 조용히 하나를 놓친다.
    """
    rows = {}
    for line in mask_text(text, source).splitlines():
        m = INDEX_LINK_RE.search(line)
        if not m:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        date = next((c for c in reversed(cells) if ISO_DATE_RE.fullmatch(c)), None)
        rows[m.group(1)] = date
    return rows


def tags(text, source=None):
    """frontmatter `tags:` 를 **값 집합** `{"claude-code", "SKILL.md", ...}` 으로 돌려준다.

    ## 왜 별도 함수인가 (원장 #64) — 같은 오분해가 **세 번** 났다

    `tags:` 를 `[a-z0-9-]+` / `[\\w-]+` 같은 **토큰 정규식**으로 훑으면 `.` 에서 쪼개져
    **존재하지 않는 태그가 생긴다** — `CLAUDE.md` → `CLAUDE` + `md`. 실사용에 `CLAUDE.md`
    2건 · `AGENTS.md` 2건 · `SKILL.md` 1건이 있어 `md` 가 **5회 쓰인 태그로** 집계되고,
    `/lint` #6b 는 *"3회 이상 쓰이는데 프리페이스에 행이 없는 태그"* 를 보므로 **위반 1건**이
    된다. 17회차 · 26회차 · 32회차에 **세 번** 났다.

    26회차가 `weather.md` §측정 정의에 「태그 파싱」 행을 만들어 **증상·원인·걸릴 파일명까지
    실명으로** 적어뒀고, `lint.md` 머리말도 그 절을 단일 출처로 지목하며 이 항목을 이름으로
    열거한다. 🔴 **그럼에도 32회차가 또 틀렸다 — 문서 공백이 아니라 산문이 세 번 실패한
    것이며, 그래서 조치가 문서가 아니라 함수다.** 읽기를 신뢰하지 않는 수단으로 옮긴다.

    ⚠️ **`#60`(`index_links`) 과 성격이 반대다.** 그쪽은 어디에도 안 적혀 있어서 났고
    이쪽은 적혀 있는데 안 읽혀서 났다. **조치가 같아 보이는 것은 우연이 아니라 수렴이다.**

    ## 두 표기를 모두 파싱한다

        tags: [a, b]        # 인라인 — 현재 전건이 이 표기
        tags:               # 블록 리스트 — 현재 0건
          - a
          - b

    블록 표기가 지금 0건인데도 넣는 이유는 `sources` 가 정확히 그 함정으로 여러 회차
    오보됐기 때문이다(`envelope-encryption`·`spring-date-format` — 인라인만 파싱해
    *"출처 없음"* 으로 잡혔다). **표기가 하나뿐인 것은 현재 사실이지 계약이 아니다.**

    ## 이 함수가 보지 못하는 것 — 「없다」로 보고하지 말 것

    - **`## 태그 빠른 탐색` 프리페이스 행은 대상이 아니다.** 그쪽은 `` | `#tag` | `` 형식이라
      **백틱이 데이터가 아니라 문법**이며, 마스킹을 적용하면 529행이 전부 사라진다(원장 #31).
      프리페이스 추출은 `^\\|\\s*`+백틱 형태로 따로 하고 **마스킹하지 않는다.**
    - **frontmatter 밖의 `tags:`.** 본문이 예시로 적은 것은 세지 않으려고 첫 블록만 본다.
    - **값의 타당성.** 오타 태그인지 정당한 태그인지는 판정하지 않는다 — 개수만 센다.

    ⚠️ **frontmatter 는 마스킹하지 않는다** — §측정 정의 「코드 스팬 제외」 행이
    *"링크 스캔 한정"* 으로 범위를 좁혀 놨다.
    """
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    fm = m.group(1) if m else text
    out = set()
    im = TAGS_INLINE_RE.search(fm)
    if im:
        raw = im.group(1).split(",")
    else:
        bm = TAGS_BLOCK_RE.search(fm + "\n")
        raw = [l.strip().lstrip("-").strip() for l in bm.group(1).splitlines()] if bm else []
    for t in raw:
        t = t.strip().strip("'\"").strip()
        if t:
            out.add(t)
    return out


def is_fast_moving(text, source=None):
    """`#12` 대상인가 — `tags` 와 {llm, ai, claude-code, agent} 의 **교집합이 비지 않는가**.

    🔴 **부분 문자열 매칭이 아니다.** `re.search(r"\\b(llm|ai|...)\\b", tags_line)` 은
    **`-` 를 단어 경계로 보므로** `ai-engineering-evolution`·`engineering-culture`·
    `enterprise-ai-agent-architecture` 의 태그 **내부**에 적중한다. 32회차 실측에서 이 오탐이
    7건을 **10건**으로 부풀렸고, 세 파일 모두 `tags` 에 해당 값 자체는 없다.

    §측정 정의 「AI/LLM 소스 갱신」 행이 `tags` **∩** {…} **≠ ∅** 로 이미 규정한 것이며,
    이 함수는 그 정의를 **구현으로 못박아** 부분 문자열 매칭을 원리적으로 불가능하게 만든다.

    ⚠️ **경과일수 판정(≥90일)은 여기 넣지 않는다** — 그쪽은 관측일에 의존해 회차마다 값이
    달라지므로 호출자가 자기 기준일로 계산한다. 이 함수는 **시점 무관한 축**만 담당한다.
    """
    return bool(tags(text, source) & FAST_MOVING_TAGS)


def updated_date(text, source=None):
    """frontmatter `updated` 의 **선두 토큰**을 ISO 문자열로. 없거나 ISO 가 아니면 `None`.

    ## 왜 별도 함수인가 (원장 #64-b) — 파서 회귀가 「개선」으로 읽혔다

    실사용에 `updated: 2026-04-10 (설명)` 처럼 **날짜 뒤에 괄호 주석이 붙은 형태**가 있다.
    줄 전체를 파싱하면 `2026-04-10 (설명)` 이 ISO 검사에 걸려 **그 파일이 통째로 스킵되고
    수치가 낮게 나온다.** §측정 정의 「오래된 콘텐츠」 행이 이 함정을 **경고했는데도**
    36회차가 밟았다 — 정본 168 을 **165** 로 보고했고, 🔴 **그 −3 이 *"컷 이동(2일)의
    순효과"* 라는 개선으로 해석돼 실렸다.** 실제로는 콘텐츠도 컷도 아니고 파서 회귀다.

    차이가 나는 파일은 추정이 아니라 특정된다 — `error-message-management` ·
    `spring-messagesource` · `stripe-api-errors` 셋이며 전부 `2026-04-10 (…)` 형태다.
    현 트리 실측(2026-08-19): 정본 **167** / 전체라인 파서 **164**.

    ⚠️ **`#40`·`#48` 의 두 값 규율(`−N(조치)/+M(경계 통과)`)은 파서가 정본과 같다는 전제
    위에서만 작동한다.** 전제가 깨지면 규율이 오히려 잘못된 해석에 근거를 준다.

    ## `tags()` 와 다른 점 — frontmatter 가 없으면 `None` 이다

    `tags()` 는 frontmatter 부재 시 전문으로 폴백한다(`fm = m.group(1) if m else text`).
    태그는 본문에 안 쓰이므로 그쪽은 안전하지만 **`updated:` 는 본문에 실재한다** —
    `/lint` §재측정 규율 4항이 기록한 2026-07-27 오탐이 정확히 그것이다(`markdown-wiki.md`
    가 `created: YYYY-MM-DD` 미치환으로 보고됐으나 매칭된 것은 형식을 설명하는 ```yaml
    예시였다). 그래서 **이 함수는 폴백하지 않는다.**

    ⚠️ 현 코퍼스 322파일은 **전건이 frontmatter 를 갖고 있어 이 분기는 도달 불가**다.
    실데이터로 검증되지 않았고 합성 케이스로만 확인했다 — `tags()` 의 블록 표기와 같은
    상태이며, **표기가 하나뿐인 것은 현재 사실이지 계약이 아니다.**

    ## 이 함수가 보지 못하는 것 — 「없다」로 보고하지 말 것

    - **따옴표 값.** `updated: "2026-04-10"` 은 `\\S+` 가 따옴표째 잡아 `None` 이 된다.
      **현행 동작이며 이번에 고치지 않았다** — 실사용 0건이고, 고치면 행위 보존 증명이
      깨진다. 실사용이 생기면 여기를 고쳐야 한다.
    - **경과일수.** 관측일 의존이라 담지 않는다 — `is_fast_moving` 과 같은 판단이다.
      임계값 상수 `STALE_DAYS`(30) 만 여기 두고 **산술은 호출자**(`lint-metrics.py`)가 한다.
    """
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return None
    um = UPDATED_RE.search(m.group(1))
    if not um:
        return None
    tok = um.group(1)
    return tok if ISO_DATE_RE.fullmatch(tok) else None


def name_similarity(base1, base2):
    """두 **파일명 base**(확장자 뗀 슬러그)의 `SequenceMatcher` 비율.

    ## 왜 별도 함수인가 (원장 #64-b) — 수치가 데이터가 아니라 정의를 따라갔다

    §측정 정의는 `difflib.SequenceMatcher(None, base1, base2).ratio() >= 0.82` 로
    못박혀 있는데, 회차들이 **다른 측도**를 썼다. 정본을 쓴 회차(30·32·34)는 전부 **4쌍**,
    다른 정의를 쓴 회차(33·35·36)는 전부 **0** 이다. 🔴 **그 사이 「중복 개념 0」이 두 회차
    연속 무결의 근거로 실렸다.**

    🔴 **원인이 부주의가 아니다 — `lint.md` §4 본문이 *"편집 거리 기준"* 이라 적혀 있었다.**
    36회차는 검사 지시서를 성실히 따랐고, 그래서 정본에서 벗어났다. 실측: 편집거리 ≤3 은
    이 코퍼스의 정본 5쌍을 **전부** 놓친다(Levenshtein 6·5·4·9·6). 같은 커밋에서
    `lint.md:58` 을 정본 문면으로 교체했다.

    ## 정규화하지 않는다

    🔴 **`check-title-dup.py` 의 `normalize()` + 하한 0.40 을 가져오지 말 것.** 그쪽은
    `raw/` **제목**을 대상으로 선행 대괄호 태그를 떼고 문장부호를 지우는 **다른 측도**다.
    끌어오면 `#24`(정본을 사본으로 베끼면 오탐) 재발이다. 이쪽 피연산자는 **`.md` 를 뗀
    파일명 그대로**이며, 그 사실은 §측정 정의가 기록한 비율과의 일치로 확정됐다 —
    `weather.md` 가 남긴 `0.864`·`0.844`·`0.839`·`0.821` 이 이 함수 산출과 자릿수까지 같다.

    ⚠️ **임계값은 `DUP_NAME_THRESHOLD` 하나뿐이고 인자로 열지 않았다.** 실측상 0.81 은
    6쌍, 0.83 은 4쌍을 내므로 **손잡이를 열면 회차마다 다른 값이 나온다** — 이 항목이
    정확히 그렇게 어긋났다.
    """
    return difflib.SequenceMatcher(None, base1, base2).ratio()


def is_dup_name(base1, base2):
    """`#4` 파일명 축 — 유사도가 `DUP_NAME_THRESHOLD` **이상**인가."""
    return name_similarity(base1, base2) >= DUP_NAME_THRESHOLD


def is_dup_tags(tags1, tags2):
    """`#4` 태그셋 축 — 두 태그셋이 **비어있지 않고** 완전히 같은가.

    🔴 **빈 집합끼리를 일치로 세지 않는다.** `frozenset() == frozenset()` 은 참이므로
    가드가 없으면 **태그 없는 파일이 전부 서로 짝**이 되어 쌍 수가 조합 폭발한다.
    §측정 정의가 요구하는 것은 *"태그가 완전히 동일한 파일 쌍"* 이고, 태그가 아예 없는
    것은 *"같다"* 가 아니라 **미기재**다.

    ⚠️ 두 축은 **OR 로 각각 보고한다** — 14회차에 태그셋 일치 쌍이 처음 나왔을 때
    파일명 유사도는 0.82 미만이었다. 한 축으로 접으면 그런 쌍을 놓친다.
    """
    return bool(tags1) and bool(tags2) and set(tags1) == set(tags2)


def claim_enums(rules_text):
    """`.claude/rules/wiki-concepts.md` **본문을 읽어** `#14` 열거값을 돌려준다.

    반환: `{"claim_status": frozenset({...}), "evidence_level": frozenset({...})}`

    ## 왜 별도 함수인가 (원장 #64-b) — 지어낸 열거값이 오탐 333건을 냈다

    37회차가 정본을 **열지 않고** `claim_status ∈ {verified, reported, hypothesis,
    deprecated}` · `evidence_level ∈ {tertiary, anecdotal}` 를 **발명**해 오탐 **333건**을
    냈다. 정본으로 교체하니 **0**. `lint.md` §14 가 *"판정 기준은 이 파일 하나뿐이다.
    **이 파일을 열어 대조할 것**"* 이라고 이름까지 적어뒀는데 열지 않았다.

    🔴 **오탐이 「그럴듯한 신호」로 보인다** — 333건은 *"심각한 문제를 발견했다"* 로 읽히지
    *"내 검사기가 틀렸다"* 로 읽히지 않는다. **반대 방향도 같다: 정의를 좁게 지어내면 0 이
    나오고 그것은 무결로 읽힌다.** 그래서 조치는 「더 강한 경고문」이 아니라 **읽는 함수**다.

    ⚠️ 그 회차의 술어가 scratchpad 와 함께 소실돼 **「333」은 재현되지 않는다.** 재현을
    시도하지 말 것 — 그 재현 불가가 이 함수와 `lint-metrics.py` 를 만든 이유다.

    ## 파싱 규약

    절은 `### … 열거값 …` 부터 **다음 `### ` 직전**까지다(중간의 `####`·`#####` 는 안쪽).
    그 안에서 `**\\`필드\\`**` 라벨을 만나면 이후 표의 **첫 열 백틱 값**만 걷는다.
    표 헤더(`| 값 | 사용 조건 |`)와 구분선은 백틱이 없어 자연히 빠진다.

    🔴 **`mask_text` 를 태우지 않는다.** 이 파일은 frontmatter 규격을 ```yaml 펜스로 싣고
    있어 마스킹하면 대상이 통째로 사라진다 — 프리페이스(#31) 와 같은 계열의 예외다.

    🔴 **산문을 긁지 않는 것이 요점이다.** 같은 절의 서술이 `claim_status: source_backed`
    같은 값을 문장 안에 그대로 쓴다(2026-07-27·2026-08-09 결정 문단). 「파이프 있는 아무
    `키: a | b` 줄」로 훑으면 `confidence`·`last_verified`·`review_due` 까지 **5키**를 집는다.

    ## fail-closed

    두 필드가 각각 정확히 한 번 라벨되고 값이 하나 이상이어야 한다. 아니면 `ValueError` 다 —
    `lint-registry.load_enum_set` 이 세운 *"하드코딩 기본값이 없어 파싱 실패는 곧
    fail-closed"* 규율의 계승이다. ⚠️ 다만 **여기는 라이브러리라 `sys.exit` 이 아니라
    `raise`** 이고, 종료코드로의 변환은 호출자(`lint-metrics.py` → exit 2)가 한다.
    """
    lines = rules_text.splitlines()
    start = next((i for i, l in enumerate(lines) if ENUM_SECTION_RE.match(l)), None)
    if start is None:
        raise ValueError("wiki-concepts.md 에서 열거값 절(`### … 열거값 …`)을 찾지 못했다")
    end = next((i for i in range(start + 1, len(lines))
                if lines[i].startswith("### ")), len(lines))

    found, cur = {}, None
    for line in lines[start:end]:
        lm = ENUM_LABEL_RE.match(line)
        if lm:
            cur = lm.group(1)
            if cur in found:
                raise ValueError(f"열거값 절에 `{cur}` 라벨이 두 번 나온다")
            found[cur] = set()
            continue
        rm = ENUM_ROW_RE.match(line)
        if rm and cur:
            found[cur].add(rm.group(1))

    missing = [f for f in ENUM_FIELDS if not found.get(f)]
    if missing:
        raise ValueError(f"열거값 절에서 값을 얻지 못한 필드: {missing}")
    return {f: frozenset(found[f]) for f in ENUM_FIELDS}


def island_slugs(backlinks_text, slugs):
    """`wiki/backlinks.md` 에 블록이 없는 슬러그 = **island(인바운드 0)** 를 돌려준다.

    `slugs` 는 `concepts`+`topics` 의 슬러그 iterable 이고, 반환은 정렬된 `list` 다.

    ## 왜 별도 함수인가 (원장 #81) — 정의는 있었고 **러너가 없었다**

    `wiki/_meta/weather.md` §측정 정의의 `Islands(inbound 0)` 행이 정확한 정의를 이미
    담고 있었다. 그런데 **그 값을 내는 코드가 저장소에 없어서** 매 회차가 정의를
    재실행하는 대신 원장 항목(`#68`·`#69`)의 존재만 재확인했고, 그 사이 새로 생긴
    island 4건이 **39·40·41회차 3회차 연속** 누락됐다(실측 6 / 보고 2).

    🔴 **`#64-b` 계열과 방향이 반대다** — 그쪽은 정본을 *안 읽어서*, 이쪽은 정본이
    있는데 *아무도 실행하지 않아서* 났다. 그래서 조치가 「더 강한 경고문」이 아니라
    **러너에 물린 함수**다(`lint-metrics.py` 가 매 회차 출력한다).

    ## `#2` orphan 과 **다른 지표**다 — 정의를 합치지 않는다

    `#2` 는 *"index.md 미등재 **AND** 인바운드 0"* 이라 **index 에 정상 등재된 island 을
    논리곱에서 걸러낸다.** 3회차 오보의 4건이 전부 그 상태였다(`## 개념 목록` 표에
    등재돼 있고 인바운드만 0). 두 지표를 하나로 합치면 편해 보이지만 **회차 간 수치
    비교가 깨진다**(`/lint` §재측정 규율 3항).

    ## 마스킹 규약

    `mask_text` 를 **태운다.** 큐레이션 주석이 예시로 적은 ```` ``` ```` 안의
    `## [[x]]` 를 실제 블록으로 세지 않기 위해서다 — 링크 스캔과 같은 판단이다.
    ⚠️ 프리페이스(원장 `#31`)와 열거값 절(`claim_enums`)이 **마스킹 예외**인 것과
    혼동하지 말 것: 그 둘은 백틱·펜스가 **데이터**지만 여기서는 **문법**이다.
    실측(2026-08-24, backlinks 330블록)에서 마스킹 유무가 결과를 바꾸지 않는다 —
    바뀌는 날은 큐레이션 주석이 블록 헤딩을 예시로 실은 날이며 그때는 마스킹이 맞다.
    """
    have = set(BACKLINK_BLOCK_RE.findall(mask_text(backlinks_text)))
    return sorted(s for s in slugs if s not in have)
