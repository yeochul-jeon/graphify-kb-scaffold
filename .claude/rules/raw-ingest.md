---
paths:
  - "raw/**"
---

# Raw 인제스트 규칙

**Scope**: `raw/**` 하위 파일 추가/편집 시 참조.

## 디렉터리 구조

- `raw/*.md` — 직접 수집한 노트·정리 문서 (편집 가능)
- `raw/Clippings/**` — 웹 클리핑 원본 (**읽기 전용, 수정 금지**)
- `raw/attachments/**` — 이미지·PDF 등 첨부의 **단일 저장 위치** (원천소스 보존용). LLM 자동 읽기 대상 아님(`.claudeignore` 차단). 사용자가 경로를 지정해 명시적으로 요청할 때만 읽는다. `wiki/attachments/` 는 사용하지 않는다 — 첨부는 항상 `raw/attachments/<소스명>/` 에 두고, wiki 문서는 상대경로(`../../raw/attachments/...`)로 참조
- `raw/_templates/**` — 템플릿
- `raw/sessions/**` — 세션 로그 (미트/스터디)

## frontmatter 필수

새 `raw/*.md` 추가 시:
```yaml
---
title: <Title>
source_url: <URL or "manual">
ingested_date: YYYY-MM-DD
compiled: false
tags: [tag1, tag2]
images: []
author: <선택>
published: <선택, YYYY-MM-DD>
---
```

> **2026-07-27 정정**: 이 절은 원래 `source:` / `captured:` 를 규정했으나 실제 사용은 `source_url:` 279건(96%) · `ingested_date:` 279건(96%) 대 `source:` 12건(4%) 였다 (`raw/*.md` frontmatter 보유 291건 기준). 규격을 실사용에 맞춰 정정했다. 기존 12건은 소급 변경하지 않는다.

### `verbatim` — 원문 보존 여부 (2026-08-04 신설)

`raw/` 는 **원본 보관 위치**다. 그런데 여러 파일이 원본이 아니라 요약·재서술본이었고, 그 사실이 frontmatter 어디에도 없어 **읽는 쪽이 구별할 방법이 없었다.**

```yaml
verbatim: true | false
verbatim_checked: YYYY-MM-DD     # verbatim 을 기재한 날 (필수)
```

| 값 | 의미 |
|---|---|
| `true` | 본문이 출처 원문 **그대로**다. 한국어 주석·사용자 노트를 덧붙이는 것은 허용되나, **원문에서 빼는 것은 허용되지 않는다** |
| `false` | 요약·발췌·재서술이 섞였다. **무엇이 빠졌는지 `note:` 에 적는다** |

##### 고정(pinning) — `github_ref` 가 있으면 `verbatim` 은 그 SHA 기준이다

```yaml
github_ref: <commit SHA>
github_ref_note: "인제스트 시점(YYYY-MM-DD) 고정 SHA. 현재 main 과 다르다 — 왜 고정했는가"
```

**`github_ref` 가 SHA 를 고정하면 `verbatim: true` 는 최신 `main` 이 아니라 그 SHA 에 대한 주장이다.** 검사기는 `main` 이 아니라 `github_ref` 로 받아 대조해야 한다 — 그러지 않으면 고정된 파일이 전부 오탐으로 뒤집힌다.

**왜 고정하는가**: `raw/` 는 **위키가 컴파일된 시점의 증거**다. 업스트림이 바뀐 뒤 최신본으로 갱신하면 `verbatim` 은 만족하지만 **위키 주장의 근거가 사라진다.**

> 2026-08-04 실측: `wiki/concepts/secall.md` 의 주장 3건(`graph_query` 의 "BFS, 최대 3홉" 등)이 현재 README 에 없어 한때 위키가 틀린 것처럼 보였다. 인제스트 시점 README 에는 셋 다 있었다 — **위키는 맞았고 업스트림이 30,559자 → 18,261자로 축소된 것**이다. 최신본으로 덮었다면 저장소가 스스로 근거를 지우고 위키를 오류로 판정했을 것이다.

**따라서 업스트림 변경이 확인된 파일은 최신본이 아니라 인제스트 시점 커밋으로 받는다.** 현재 판과의 차이는 `note:` 에 적는다.

**`verbatim_checked` 가 필수인 이유**: 이 필드는 **시점 의존 주장**이다. 2026-04 수집분에 `verbatim: true` 를 붙이는 것은 "*어느 시점의* 원문과 일치하는가" 를 말하지 않으면 무의미하고, 업스트림이 바뀐 뒤엔 값이 조용히 거짓이 된다. 저장소 규율 *"시점 의존 수치는 실측 시점을 함께 적는다"* 가 그대로 적용된다.

##### `verbatim: true` 가 구조적으로 잡지 못하는 것 — 자막 출처의 고유명사 (2026-08-05 신설)

`verbatim` 은 **저장분이 원문과 일치하는가**만 묻는다. 그런데 **음성 인식 자막**이 출처인 파일에서는 원문 자체가 이미 오류를 담고 있을 수 있고, 그 경우 일치할수록 오류가 충실히 보존된다.

**특히 고유명사(인명·저장소명·제품명)가 취약하다.** 산문은 문맥이 오탈자를 드러내지만 이름은 대조할 문맥이 없다 — 자막 안에서는 그것이 곧 "원문" 이다.

> **2026-08-05 실측**: `wiki/concepts/unknowns-framework-agentic-coding.md` 가 `grill-me` 스킬의 제작자를 **"퍼커"** 로 4주간 실었다. 출처 `raw/youtube-NhuAdy8EsRQ.md:41` 의 자막 그대로였고 `verbatim` 관점에서는 문제가 없었다. 실제 제작자는 **Matt Pocock** 이며, **정정 재료(`raw/mattpocock-skills.md`)는 같은 날 인제스트돼 저장소 안에 있었다.**

**탐지 신호 — 같은 이름이 한 파일 안에서 갈린다.** 위 파일은 `:41` "퍼커" · `:136` "몇 퍼" 로 같은 사람을 다르게 적었다. 자막 전사는 등장할 때마다 독립적으로 실패하므로 **표기 분산 자체가 전사 오류의 지표**다.

**따라서 자막 출처(`youtube-*.md` 등) 문서를 컴파일할 때, 본문에 옮기는 고유명사는 자막 밖에서 한 번 확인한다.**

| 확인 경로 | 예 |
|---|---|
| 저장소가 이미 가진 1차 자료와 대조 | `raw/mattpocock-skills.md` README 의 스킬 **경로·설명 문구** |
| 자막이 말한 **탐색 경로**를 그대로 따라가기 | *"grill me 검색 → productivity 아래"* → 실제 파일 경로 확인 |
| `gh api` 등으로 저장소·계정 실재 확인 | ⚠️ **인기 지표는 귀속 근거가 아니다** — 동시기 `obra/superpowers` 266,663 · `anthropics/skills` 166,304 로 자릿수가 겹쳐 저장소를 가르지 못한다 |

확인이 안 되면 **이름을 단정하지 말고 자막 표기임을 명시한다** — 틀린 이름을 확정형으로 적으면 다음 회차가 그것을 사실로 인용한다.

#### 판정 방법 — 분량비 하나로는 못 가른다

2026-08-04 전수 확인(23건)에서 **분량비 1.02 인 파일과 0.82 인 파일이 둘 다 문제**였다. 세 지표를 함께 본다:

| 지표 | 무엇을 잡는가 |
|---|---|
| **cov** (저장분 40자+ 라인 중 원문에 그대로 있는 비율) | 저장분이 원문에서 왔는가 — **재서술 탐지** |
| **ocov** (원문 40자+ 라인 중 저장분에 있는 비율) | 원문이 다 들어왔는가 — **누락 탐지**. `verbatim: true` 의 서명은 **ocov ≈ 1.00** |
| **펜스·헤딩 카운트 대조** | 구조 유실(OT-10 ③) — **산문이 멀쩡해 cov 로도 안 잡힌다** |

> `rest-assured-usage-guide` 는 cov 0.73 으로 준수한데 **펜스가 0개 대 원문 247개**였다. 구조 카운트가 아니면 못 잡는다. 펜스는 **총 라인 ÷ 2** 로 센다(언어 태그를 요구하면 과소집계).

**업스트림 커밋 이력이 "요약본" 과 "저장소가 커진 것" 을 가른다** — 둘은 조치가 정반대다. `gh api "repos/<slug>/commits?path=<p>&since=<ingested_date>T00:00:00Z"` 가 0건인데 ocov 가 낮으면, 빠진 내용은 **수집 당시 이미 있었다**.

#### 수집 경로

```bash
curl -sL https://raw.githubusercontent.com/<owner>/<repo>/<branch>/<path>   # 일반 파일
curl -sL https://raw.githubusercontent.com/wiki/<owner>/<repo>/<Page>.md   # GitHub wiki (별도 경로)
```

파일 자체를 반환하므로 HTML→마크다운 변환이 없다 — **OT-10 유실이 구조적으로 발생하지 않는다.**

⚠️ 함정 3가지: ①기본 브랜치가 `main`/`master` 가 아닐 수 있다(`develop` 실례) ②확장자를 확인하라(`README.adoc` 인데 `README.md` 로 기재된 실례) ③한글 파일명은 URL 인코딩이 필요하다.

> **`github_files` 는 실제로 받아지는 경로여야 한다.** 2026-08-04 확인에서 2건이 존재하지 않는 경로였고, 그중 하나는 **엉뚱한 파일과 대조돼 원문을 요약본으로 오판하게 만들었다.**

### 중복 `source_url` 판정 필드 (선택)

같은 `source_url` 을 가진 `raw/` 파일이 이미 있는데도 새 파일을 남기기로 판정했다면, **그룹의 모든 파일에** 아래 3필드를 기재한다. `/ingest` 의 중복 검사는 이 필드의 **존재 여부로 "판정 완료" 를 판별**하므로, 산문 메모만 남기면 다음 인제스트에서 같은 질문을 다시 받는다.

```yaml
duplicate_url_group: <그룹 슬러그>          # 같은 URL 을 공유하는 파일들이 동일 값을 가진다
duplicate_url_verdict: coexist              # coexist | mixed-origin | merged
duplicate_url_note: "<왜 공존하는지 + 판정 근거·일자>"
```

| `duplicate_url_verdict` | 사용 조건 |
|---|---|
| `coexist` | 같은 출처를 소재로 한 **서로 다른 정리물**. 각자 고유 내용이 있어 어느 쪽을 지워도 정보가 손실된다 |
| `mixed-origin` | 이 파일의 내용이 `source_url` **하나로 대표되지 않는다** (다른 출처 내용이 섞임). `additional_sources` 를 함께 기재한다 |
| `merged` | 내용이 다른 파일로 흡수됐고, **이 파일은 삭제하지 않고 이력용으로 남긴다**. 삭제하기로 했다면 이 값을 쓰지 말고 파일을 지운 뒤 `wiki/` 의 `sources:` 와 `[[raw/...]]` 인용을 재매핑한다 (지운 파일에는 필드를 달 곳이 없다) |

`additional_sources: [<출처1>, ...]` — `mixed-origin` 일 때 필수. URL 을 모르면 **추정해 적지 말고** 확인 필요 상태 그대로 기재한다.

> 판정 근거는 **본문 대조**에 기반해야 한다. 제목·URL 만 보고 "같은 글" 로 단정하지 말 것 — 2026-07-27 실측에서 중복 5쌍 전부가 `partial-overlap`(양쪽에 고유 내용 존재)으로, 삭제가 정당한 쌍은 **0건**이었다.

## 인제스트 워크플로

1. `raw/` 에 새 파일 드롭
2. 프론트매터 보강
3. 그래프 갱신: `graphify build --update` 또는 `scripts/graphify-py.sh -c "..._rebuild_code..."`
4. 새 concept 파일 생성 여부 확인 → `wiki/concepts/` 업데이트는 `.claude/rules/wiki-concepts.md` 규칙 따름

## 금지 사항

- `raw/Clippings/` 내용 수정 — 원본 무결성 보존
- 첨부 바이너리를 LLM 에 직접 읽히기 시도 (대용량)
- frontmatter 없는 `.md` 신규 생성

## graphify 와 연동

- 이 디렉터리 변경 후 그래프가 낡을 수 있음 → 세션 끝에 재빌드 권장
- 재빌드 상세는 `.claude/rules/graphify-pipeline.md` 참조
