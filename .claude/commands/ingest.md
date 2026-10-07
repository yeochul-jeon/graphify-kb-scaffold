원본 자료를 `raw/` 폴더에 수집합니다. Triggers: ingest, save article, collect, add source, clip, URL 저장, 수집, 원본 추가

## 사용법

```
/ingest [URL | Notion URL | 텍스트 설명]
```

## 처리 규칙

### 입력 유형 판별

`$ARGUMENTS`를 분석해 다음 중 하나로 처리:

1. **Notion URL** (`notion.so` 포함): `mcp__claude_ai_Notion__notion-fetch`로 가져오기
2. **GitHub URL** (`github.com/` 포함): 아래 GitHub 처리 규칙 적용
3. **YouTube URL** (`youtube.com/watch`, `youtu.be/`, `youtube.com/shorts/` 포함): 아래 YouTube URL 처리 규칙 적용
4. **일반 URL** (`http://` 또는 `https://` 시작, 위 항목에 해당 없음): 아래 일반 URL 처리 규칙 적용
5. **로컬 파일 경로**: `raw/Clippings/` 안의 파일(Web Clipper 캡처)이면 `raw/`로 **이동**(추적 중이면 `git mv`, 미추적이면 `mv`), 그 외 로컬 경로는 `raw/`로 **복사**. 어느 쪽이든 아래 §저장 처리(중복 검사 → kebab-case 파일명 → 이미지 핸들링)와 frontmatter 보강을 그대로 거친다
   - 왜 이동인지·`verbatim` 판정·레거시 예외는 `.claude/rules/raw-ingest.md` §Web Clipper 인박스 가 단일 출처다. 🔴 `git mv` 를 무조건문으로 쓰지 마라 — 방금 캡처된 클립은 미추적이라 `fatal: not under version control` 로 실패한다
6. **텍스트/없음**: 사용자에게 내용 직접 입력 요청

### GitHub URL 처리 규칙

URL 형식 예시:
- 저장소: `https://github.com/owner/repo`
- 특정 파일: `https://github.com/owner/repo/blob/main/path/to/file.md`
- 특정 디렉토리: `https://github.com/owner/repo/tree/main/docs/`

**처리 순서:**

1. **URL 파싱**: `owner`, `repo`, 경로(있으면) 추출
2. **콘텐츠 수집** (우선순위 순):
   - 특정 파일 URL인 경우: 해당 파일만 `WebFetch`로 가져오기
     - GitHub raw URL로 변환: `https://raw.githubusercontent.com/owner/repo/main/path`
   - 저장소 또는 디렉토리 URL인 경우:
     a. `README.md` 가져오기 (raw URL 사용)
     b. `WebFetch`로 저장소 메인 페이지를 가져와 docs/, wiki/ 등 문서 디렉토리 탐지
     c. 탐지된 핵심 문서 파일 최대 5개 추가 수집 (CONTRIBUTING.md, docs/index.md 등)
3. **통합 마크다운 생성**: 수집한 파일들을 하나의 raw 파일로 병합
   - 각 파일 내용 앞에 `## [파일명]` 헤더 추가
   - 파일 간 `---` 구분선 삽입
4. **파일명 결정**: `owner-repo` 형식 (예: `anthropics-claude-code.md`)

**YAML Frontmatter 추가 필드:**
```yaml
github_repo: https://github.com/owner/repo
github_files: [README.md, docs/index.md, ...]
```

### YouTube URL 처리 규칙

**대상**: `youtube.com/watch?v=`, `youtu.be/`, `youtube.com/shorts/` 형식 URL

**처리 순서:**

1. `scripts/ingest-youtube.sh "<URL>"` 실행 (자막을 `youtube-transcript-api`로 직접 수집, 로그인/API 키 불필요)
2. **성공 시** (종료 코드 0): stdout이 자막 전문(텍스트). 이를 본문으로 raw 파일 생성
   - 자막은 영상 원어(stderr `orig_lang=`)를 1순위로 고르고, 실제로 받은 자막 코드를 stderr `transcript_lang=` 으로 알린다. stderr 가 `orig_lang=unknown` 이면 원어 조회가 실패해 `ko en` 순서로 골랐다는 뜻이다 — frontmatter `note` 에 「원어 미확인」을 적는다 (AI 더빙 영상이면 더빙 음성의 전사일 수 있다)
   - stderr 에 `orig_asr=missing` 이 있으면 원어 표시 언어의 자막 트랙(수동·자동 모두 — 코드가 `orig_lang=` 값 또는 그 하이픈 앞부분과 정확히 같은 것)이 없어 다른 언어 트랙을 받았다는 뜻이다 — `note` 에 `원어(<orig_lang>) ASR 없음 — 받은 트랙 <transcript_lang>` 을 적는다. 업로더가 원본 오디오를 실제 발화와 다른 언어로 표시한 영상(예: `wi3tZ-c48YU` — `ko` 표시, 영어 발화)에서 나온다. 받은 트랙이 실제 발화의 인식인지 더빙 음성의 인식인지는 이 키로 가릴 수 없다. 반대로 이 키가 없어도 받은 트랙이 자동 자막이라는 보장은 없다(수동 자막이 먼저 골라진다)
3. **실패 시** (종료 코드 0이 아님, 예: 자막 비활성·비공개 영상): 기존 방식대로 스텁 생성
   - 본문: 영상 제목(추정 가능하면) + URL만 기록, `<!-- 자막 수집 실패: 수동 입력 필요 -->` 주석 추가
   - 사용자에게 자막 수동 입력 또는 요약 붙여넣기 가능 여부 확인

#### 화면 보조 수집 (claude-video, 선택)

**언제**: 전사만으로는 내용이 닫히지 않는 영상 — 발표자가 슬라이드·화면을 가리키며 말하거나(«as you can see», «이 슬라이드», «여기 보시면»),
고유명사·경로·수치가 화면에만 있을 때. 수집자가 판단하고 그 이유를 `note` 에 적는다.

**전제**: claude-video 가 설치된 PC 에서만. `WATCH=$(find ~/.claude/plugins/cache/claude-video/watch -maxdepth 5 -name watch.py 2>/dev/null | sort | tail -1)`
가 비면 이 절을 건너뛴다 — 수집 실패가 아니다(`ls <glob>` 은 zsh 에서 미설치 시 `no matches found` 를 출력하므로 `find` 를 쓴다). `/watch` 스킬이 아니라 스크립트를 직접 부른다(스킬의 설정 마법사·엔진 안내가 끼어들지 않게).
URL 은 항상 `"<URL>"` 로 따옴표를 친다 — zsh 는 `?` 를 glob 으로 읽어 `no matches found` 로 멈춘다.

**구간 선정** (전제를 통과한 뒤, 아래 1단계로 raw 를 만든 직후 2단계와 함께): raw 본문(frontmatter 제외)에서 화면 지시 표현이 있는 줄을 줄번호와 함께 뽑는다.
```bash
P='그림과 같|그림에서|오른쪽|왼쪽|아래 그래프|아래 그림|보시는|보이시는|화면|슬라이드|as you can see|this slide|on the screen|looks like this|here we have|you can see'
awk '/^---$/{n++;next} n>=2{print FNR": "$0}' raw/youtube-<id>.md | grep -iE "$P"
```
- 가리키는 대상은 다음 줄에 이어지는 경우가 많다(«…컨슈하고 오른쪽 / 코드처럼»). 각 줄을 `sed -n <N-3>,<N+3>p` 로 열어 무엇을 가리키는지 본다
- 글자·수치·코드·표가 있을 것으로 보이는 대상은 모두 추출 대상에 넣는다. 넣지 않아도 되는 것은 **읽을 글자가 없는** 그림(사진·로고만 있는 화면)뿐이다 — 도식이라도 이름·수치가 적혀 있을 수 있어 «언제»의 고유명사·수치 조건에 걸린다. 확신이 없으면 프레임을 뽑아 보고 정한다(토스 영상에서 «도식»으로 보고 뺐던 구간이 필드 표였다)
- 줄 → 시각: 그 줄의 문구를 2단계 `--detail transcript` 출력에서 찾아 시각을 얻는다. 3단계 구간은 그 시각 5초 전부터 20초 정도로 잡고, 슬라이드가 바뀌는 지점이 근처면 넓힌다. 2단계가 `--detail efficient` 폴백이면 전사 시각이 없으므로 프레임 시각을 보고 해당 슬라이드 구간을 잡는다
- grep 결과가 0줄이면(«다음 표», «이 그래프» 처럼 패턴 밖 표현) 위 «언제»의 판단으로 돌아가 전사를 읽고 구간을 직접 고른다
- 화면 하단에 **발화 언어와 같은 언어의** 번인 자막(영상에 박힌 자막)이 있으면, `note` 에 «원음 미확인»으로 적을 오인식 표현도 그 시각 프레임의 번인 자막과 대조한다. 번역 자막(발화와 다른 언어)은 무엇을 말했는지의 근거가 아니므로 쓰지 않는다. 이 대조는 위 슬라이드 구간(5초 전~20초)과 **별도로** 3단계를 한 번 더 부르는 것이다 — claude-video 는 직전에 남긴 프레임과 픽셀 차이가 작은 프레임을 버리므로(자막만 바뀐 프레임이 여기에 걸린다) 구간 시작이 곧 남는 프레임 시각이 된다. 그래서 `--start` 를 2단계 `--detail transcript` 에서 그 표현이 나온 줄 시각 +1초로, `--end` 를 `--start` 의 1초 뒤로 둔다. 자막이 빠졌거나 다른 문장이면 `--start`·`--end` 를 함께 1초씩 뒤로 옮겨 다시 부르되 줄 시각 +4초까지만 본다. 그때까지 번인 자막이 안 나오면(인트로·슬라이드 전체 화면 등) «번인 자막 없음»이라 적고 «원음 미확인»을 유지한다. 프레임 복사·`note`·`images:` 는 아래 4~6단계를 그대로 따른다 — 예: 토스 `mdmZr2QERP4` «강로드»(전사 줄 04:27)는 줄 시각 앞뒤로 넓게 잡은 `--start 04:25 --end 04:33` 에서 04:25 프레임 1장만 남아 자막이 빠졌고, `--start 04:28 --end 04:29` 에서 «k8s의 각 node에 agent를 배포»가 나왔다
- 넣지 않은 지시 줄은 `note` 에 `미추출 구간: 줄 N(«<지시 문구>» — <넣지 않은 이유>)` 형식으로 남긴다. `note` 를 늘리면 본문 줄번호가 밀리므로, 이 줄번호는 `note` 를 다 쓴 뒤 같은 명령을 다시 돌려 얻은 값을 적는다
- 🔴 **이미 컴파일된 raw**(`compiled: true`)에 나중에 이 절을 적용하면, 늘어난 `note` 줄 수 k 만큼 그 raw 를 `:N` 으로 인용하는 위키 페이지의 줄번호가 모두 밀린다. 인용을 일괄 +k 하고, 보정 전 raw 와 보정 후 raw 에서 같은 범위의 내용이 같은지 스크립트로 대조한다. 그 페이지 §출처의 대조 범위 줄에 «줄번호 +k 보정(날짜)» 을 적는다

1. 전사는 위 1~3 그대로 `ingest-youtube.sh` 로 받는다. claude-video 의 전사를 raw 본문에 넣지 않는다. 3번(스텁)이어도 이 절은 적용할 수 있다 — `orig_lang=` 은 실패 시에도 stderr 에 먼저 찍힌다
2. 시각 찾기 — 원어 자막 트랙 이름을 목록에서 그대로 가져와 넘긴다:
   ```bash
   ORIG_TRACK=$(yt-dlp --list-subs "<URL>" 2>/dev/null \
     | awk '/^\[info\] Available automatic captions/{a=1;next} /^\[info\] Available subtitles/{a=0} a{print $1}' \
     | grep -E "^<기본형>(-[A-Za-z]+)*-orig\$" | head -1)
   python3 "$WATCH" "<URL>" --engine local --detail transcript --sub-lang "${ORIG_TRACK:-<기본형>}" --out-dir <scratchpad>
   ```
   - `orig_lang=unknown` 이면 이 절을 건너뛴다(`transcript_lang=` 이 찍혔어도 — 원어를 모르면 `-orig` 트랙을 고를 근거가 없다). 그 밖에는 `<기본형>` 이 `ingest-youtube.sh` stderr `transcript_lang=` 값의 하이픈 앞부분이다(`en-US` → `en`). 보통 `orig_lang=` 과 같고, `orig_asr=missing` 인 영상에서는 원어 표시 언어의 `-orig` 트랙이 없으므로 실제로 받은 언어로 찾아야 한다. 자막 수집이 실패해(3번 스텁) `transcript_lang=` 이 없으면 `orig_lang=` 값의 하이픈 앞부분을 쓴다
   - 트랙 이름은 짐작하지 않는다 — `orig_lang=en-US` 인 영상의 원어 트랙이 `en-orig` 이기도 하고(`fZH97QHHYjY`), 다른 영상의 영어 원어 트랙은 `en-US-orig` 다(`lbRdRKU93EA`).
     `--sub-lang` 에 `-` 가 든 값은 정확히 일치하는 트랙만 고르므로 `en-orig` 로는 `en-US-orig` 를 못 받는다(2026-09-29 실측)
   - `-orig` 를 쓰는 이유: `--sub-lang en` 은 수동 자막 `en` 이 없으면 자동 자막 중 **번역** 트랙 `en` 을 원어 트랙보다 먼저 고르는데(claude-video `download.py` `select_caption`),
     번역 트랙은 `HTTP Error 429` 로 막혔다(2026-09-28~29, `--sub-lang en` 7회 전부 · yt-dlp 직접 `en`·`ar` 각 1회). 원어 자동 자막 `en-orig` 는 같은 시각에 받아졌다.
     `ORIG_TRACK` 이 비면(원어 자동 자막 없음 — 수동 자막만 있는 영상 등, 또는 `--list-subs` 자체 실패) `<기본형>` 으로 돈다 — 이때는 수동 자막이 먼저 골라진다(`select_caption` manual 우선).
     awk 는 자동 자막 표만 읽는다. 원어 트랙이 둘 이상 매치되면 목록 첫 줄을 쓴다(실측 사례 없음)
   - 성공 판정은 exit code 가 아니라 보고서 `Transcript:` 줄로 한다 — 자막을 못 받아도 exit 0 이 나온다
     - `Transcript:` 줄이 `<기본형>` 이 아닌 언어의 자막이면 멈추고 보고한다
     - `no captions available`(예: stderr `HTTP Error 429`) 이면 `--detail transcript` 대신 `--detail efficient` 로 영상 전체를 한 번 돌려 프레임 시각에서 구간을 찾는다.
       자막 요청이 막혀도 프레임 추출은 된다. `ingest-youtube.sh` 전사는 `--format text` 라 시각이 없다.
       이 실행은 `--sub-lang` 없이 돌므로 보고서 전사가 다른 언어일 수 있다 — 프레임 시각만 쓰고 전사는 무시한다
3. 구간 추출: `python3 "$WATCH" "<URL>" --engine local --start <MM:SS> --end <MM:SS> --resolution 1024 --out-dir <scratchpad>`
4. `<scratchpad>` 의 프레임을 보고, **근거로 남길 사실이 담긴 프레임만** `raw/attachments/youtube-<id>/frame-<MMSS>-<NN>.jpg` 로 복사한다
   (`NN` 은 claude-video 프레임 번호 끝 두 자리 — 같은 초에 여러 장이 나온다. 번호는 실행마다 1부터 다시 매겨지므로 이미 같은 이름이 있으면 복사하지 않는다)
5. 프레임에서 읽은 사실은 **지금** frontmatter `note` 에 프레임별로 적는다 — compile 은 `raw/attachments/` 를 열지 못한다(`.claudeignore`).
   버전은 `$WATCH` 경로의 `watch/<버전>/` 에서 읽는다. 예: `화면 보조 수집(claude-video 0.3.2 local, 2026-09-28): frame-0651-01.jpg t=06:51 슬라이드 08 «Retrieval quality changes answer accuracy.» 55.9% / 70.1% / 93%`
6. `images:` 에 복사한 프레임을 raw 기준 상대경로로 적는다 — 예: `images: [attachments/youtube-<id>/frame-0651-01.jpg]`. raw 본문(전사)은 고치지 않는다

**파일명 규칙**: `youtube-[video_id].md` (제목 kebab-case 규칙의 예외 — 자막 API로 영상 제목을 얻을 수 없어 ID 기반 고정)
**frontmatter `source_url`**: 원본 시청 URL 전체

### 일반 URL 처리 규칙

**처리 순서 (우선순위):**

1. `scripts/ingest-fetch.sh "<URL>"` 실행 (Jina AI Reader 1차 시도 → 실패 시 raw HTML로 자동 폴백)
2. **종료 코드 0** (성공): stdout이 본문. stderr 첫 줄의 `tier=` 표기로 어느 티어가 성공했는지 확인
   - `tier=1 (jina-reader)`: 이미 정제된 마크다운 — 사용 전 로그인월·페이월 미리보기·쿠키 동의 문구가 아닌 실제 기사 본문인지 확인할 것 (Jina는 대상 페이지를 그대로 렌더링하므로 페이월 미리보기도 "깔끔한 마크다운"으로 반환될 수 있음)
   - `tier=2 (raw-html)`: 원시 HTML — 본문을 추출해 마크다운으로 변환 (스크립트는 변환하지 않음). 로그인 페이지·빈 SPA 셸이 200으로 반환될 수 있으니 내용이 실제 기사인지 확인할 것
3. **종료 코드 1** (양쪽 티어 모두 실패): `WebFetch`로 마지막 시도
   - `WebFetch`도 실패(로그인월, 403/402 차단, 빈 셸 등)하면 사용자에게 URL 접근 불가를 알리고 내용 직접 붙여넣기 요청

**주의**: `WebFetch`는 결과를 소형 모델로 요약할 수 있어(내용이 크면 손실 발생) 원문 보존이 필요한 이 파이프라인에서는 최후의 수단으로만 사용한다.

### 저장 처리

1. **`source_url` 중복 검사** (파일명 변환보다 **먼저**) — 아래 §중복 `source_url` 검사
2. 제목을 kebab-case 파일명으로 변환 (예: "Attention Is All You Need" → `attention-is-all-you-need.md`)
3. 파일명 중복 시 `-2`, `-3` 등 suffix 추가
4. 이미지가 포함된 경우 아래 이미지 핸들링 규칙 적용

### 중복 `source_url` 검사

파일명 중복 검사만으로는 **같은 글을 다른 파일명으로 두 번 저장하는 것**을 막지 못한다. 저장 전에 URL 층위에서 확인한다.

**1) 정규화 후 비교** — 아래를 모두 무시하고 비교한다:

| 항목 | 예 |
|---|---|
| 스킴·`www.` | `http://www.a.com/x` ≡ `https://a.com/x` |
| 대소문자 (호스트만) | `A.COM` ≡ `a.com` |
| 끝 슬래시 | `/x/` ≡ `/x` |
| 퍼센트 인코딩 | `%EC%A7%88...` ≡ 디코딩된 한글 경로 |
| YouTube 표기 | `youtube.com/watch?v=ID` ≡ `youtu.be/ID` → **비디오 ID 로만 비교** |
| 모바일 서브도메인 | `m.blog.naver.com/x` ≡ `blog.naver.com/x` |
| AMP 경로 | `/amp/x`·`/x/amp` ≡ `/x` |
| 추적 파라미터 | `utm_*`·`fbclid`·`gclid`·`ref` 는 제거 후 비교 |
| 프래그먼트 | `#section` 은 제거 후 비교 |

경로 대소문자와 위에 열거되지 않은 쿼리스트링은 **구분한다** — `?tl=ko`·`?hl=ko`·`?id=N` 처럼 실제로 다른 문서를 가리키는 경우가 있다.

**2) 일치가 없으면 — 🔴 여기서 끝내지 마라. `source_url` 이 URL 이 아니면 위 비교는 성립조차 하지 않았다** (2026-08-11 신설, 원장 #55)

`source_url` 이 `직접 입력`·`manual (…)`·로컬 경로거나 **필드 자체가 없으면**, 같은 리터럴이 수십 건에 붙어 있어 **1) 의 «일치 없음» 은 무의미한 통과**다. 실제로 2026-08-10 에 같은 발표 2건이 이 경로로 들어왔고 **컴파일 단계에서 우연히** 발견됐다. 그 구간은 **제목 축**으로 본다:

```bash
# 저장 전에 돌리려면 임시 경로로 쓴 뒤 그 경로를 넘긴다 — 말뭉치 밖 경로도 읽는다.
scripts/graphify-py.sh scripts/check-title-dup.py --new /tmp/<새파일>.md
# 이미 raw/ 에 썼다면 그 경로를 그대로 넘긴다.
scripts/graphify-py.sh scripts/check-title-dup.py --new raw/<새파일>.md
```

⚠️ **1) 은 「저장 전」 검사인데 이 검사기는 파일이 있어야 읽는다.** 둘 중 하나로 맞춘다 — **ⓐ 임시 경로에 먼저 쓰고 대조**하거나, **ⓑ `raw/` 에 쓴 뒤 대조하고 3) 의 «중단» 판정이 나면 그 파일을 지운다.** ⓑ 를 택했으면 **지웠다는 사실까지 보고**한다. 어느 쪽이든 **`title` frontmatter 가 이미 채워져 있어야** 대조가 성립한다.

- 후보가 나오면 **3) 의 3분기를 그대로 적용**한다 — 새 분기·새 필드를 만들지 않는다.
- 🔴 **이 검사기는 판정하지 않는다. 순위만 매긴다.** 실측상 진양성 최저 **0.444** 가 위양성 최고 **0.545** 보다 낮아 **어떤 문턱도 두 집단을 가르지 못한다.** 점수가 높다고 중복이 아니고 낮다고 아닌 것도 아니다 — **판정은 본문 대조로만** 내린다(아래 §병합·삭제 판정 규율과 같다).
- ⚠️ **종료 코드 `2` 는 실패가 아니라 «후보 있음»** 이다. 하드 블록이 아니므로 이것으로 인제스트를 중단시키지 않는다.
- ⚠️ **`author` 가 같아도 다른 자료일 수 있다** — `Grace (InfoGrab)` 5건이 실례다. 저자는 **순위 가중치**이지 판별자가 아니다.

**2') 위 둘 다 후보가 없으면** 그대로 저장 — 이하 절차 생략.

**3) 일치가 있으면 저장을 멈추고 보고한다.** 기존 파일의 `duplicate_url_verdict` 를 먼저 확인:

- **필드가 있으면** — 이미 판정된 그룹이다. 그 판정과 사유를 보여주고 신규 파일도 같은 `duplicate_url_group` 으로 편입할지 묻는다.
- **필드가 없으면** — 미판정이다. 기존 파일의 `title`·줄 수·`ingested_date` 를 제시하고 아래 3분기 중 사용자 선택을 받는다:

| 분기 | 조건 | 조치 | 기재할 `duplicate_url_verdict` |
|---|---|---|---|
| **중단** | 같은 글의 재수집이고 새로 얻는 내용이 없다 | 저장하지 않는다 | — (파일이 생기지 않음) |
| **공존** | 같은 출처를 소재로 한 다른 정리물이거나, 한쪽에만 있는 내용이 있다 | 저장하고 **그룹 전원**에 판정 3필드 기재 | `coexist` |
| **혼합 출처** | 신규 파일 내용이 `source_url` **하나로 대표되지 않는다** (다른 출처 내용이 섞여 URL 이 우연히 겹친 것) | 저장하고 판정 3필드 + `additional_sources` 기재. URL 을 모르면 **추정하지 말고** 확인 필요 상태로 적는다 | `mixed-origin` |
| **병합** | 한쪽이 다른 쪽의 상위집합이다 | 내용을 합치고 남길 파일을 정한다. **흡수된 파일을 삭제하면 `wiki/` 의 `sources:` 와 `[[raw/...]]` 인용을 반드시 함께 재매핑**하고, 삭제 대신 이력용으로 남길 경우 그 파일에 `merged` 를 기재한다 | `merged` (남길 때만) |

열거값 정의는 `.claude/rules/raw-ingest.md` §중복 `source_url` 판정 필드 가 단일 출처다.

> **혼합 출처 분기를 빠뜨리기 쉽다.** 겉보기엔 "같은 URL 의 두 정리물" 이라 공존으로 분류되지만, 실제로는 한쪽 파일의 `source_url` 이 그 내용을 대표하지 못하는 **메타데이터 결함**이다. 공존으로 적으면 원장에 틀린 사실이 남는다 — `youtube-karpathy-claude-md-secret.md` 가 이 케이스였다.

> **자동 거부·자동 suffix 금지.** 같은 URL 을 소재로 서로 다른 정리물을 만드는 것은 이 저장소의 정상 워크플로다. 2026-07-27 실측에서 중복 5쌍 전부가 양쪽에 고유 내용을 가진 `partial-overlap` 이었고 삭제가 정당한 쌍은 **0건**이었다. 하드 블록이었다면 정당한 인제스트를 막았을 것이다.

> **병합·삭제 판정은 본문 대조 없이 내리지 않는다.** 제목과 URL 이 문자 단위로 같아도 한쪽에만 있는 내용이 있을 수 있다 — 실제로 무신사 쌍이 그랬다(전문 캡처본이 원문의 규칙 1건을 누락, 요약본에만 남아 있었다).

### 이미지 핸들링

원본 자료에 이미지가 포함된 경우:

1. **이미지 저장 경로**: `raw/attachments/[article-name]/` 디렉토리 생성
   - `[article-name]`은 raw 파일명에서 `.md` 제외한 부분 (예: `attention-is-all-you-need`)
2. **이미지 다운로드**: 본문에 포함된 이미지 URL을 `curl`로 로컬 다운로드
   - 파일명: 원본 파일명 유지, 불명확하면 `img-01.png`, `img-02.png` 순번
   - 지원 형식: `.png`, `.jpg`, `.jpeg`, `.gif`, `.svg`, `.webp`
3. **마크다운 참조 변환**: 원본 URL을 상대 경로로 교체
   - 변환 전: `![alt](https://example.com/image.png)`
   - 변환 후: `![alt](attachments/article-name/image.png)`
4. **다운로드 실패 시**: 원본 URL 유지 + 주석 추가 `<!-- 이미지 다운로드 실패: URL -->`
   - 🔴 **단, 실패 URL 이 `blob:http://localhost/…` 이면 4번으로 내려가지 않고 5번을 먼저 한다.**
5. **`blob:` 이미지 (jina-reader 변환 결과)**: 본문에 `![…](blob:http://localhost/…)` 줄이 있거나, 캡션(`그림 N.`)은 있는데 이미지 줄이 없으면 그 blob 은 실제 이미지가 아니라 **변환 산출물**이다 — 원문 HTML 에는 `data:image/…;base64` 로 들어 있다. `python3 scripts/extract-inline-images.py <원문 URL> <raw 슬러그>` (dry-run) 로 개수·캡션 정합을 확인한 뒤 `--apply` 한다. 이미지 0개이거나 캡션 수가 어긋나면 스크립트가 멈춘다 — 그때만 4번으로 내려간다. `note:` 에 blob 이 나왔던 사실과 복원 사실을 적는다. (2026-09-29 실측: 삼성 기술 블로그 raw 6건이 이 경로로 이미지를 잃은 채 «실제 이미지 파일이 아님» 으로 기록돼 있었다 — 원장 #103)
6. **이미지 없는 자료**: attachments 디렉토리 미생성

### YAML Frontmatter 추가

🔴 **먼저 `raw/_templates/raw-template.md` 를 Read 로 열어라. 그 파일의 frontmatter 를 복사해 채운다.**

**여기에 스키마를 다시 적지 않는다.** 사본을 두면 낡기 때문이다 — 2026-08-16 실측에서 이 문서의 사본과 정본(`.claude/rules/raw-ingest.md`)이 실제로 갈려 있었고, 여기 붙어 있던 *"정본은 규칙 파일이다"* 라는 안내문은 **컨텍스트에 전달됐는데도 규칙 파일로 이어지지 않았다**(근거: `docs/plan/plans/2026-08-15-system-review.md` §9-a).

**템플릿을 여는 것이 안내문보다 확실한 이유**는 그 파일이 `raw/` 아래에 있다는 데 있다. `.claude/rules/raw-ingest.md` 는 `paths: raw/**` 스코프라 **그 파일을 여는 순간 규칙 전문이 함께 주입된다** — 같은 실측에서 실제로 작동한 유일한 전달 경로다. 안내문은 읽고 넘어갈 수 있지만, 템플릿은 열지 않으면 채울 내용이 없다.

기억으로 필드를 채우지 마라. 템플릿에 없는 필드가 필요해 보이면 그때 `.claude/rules/raw-ingest.md` 를 보고, 그래도 없으면 **새로 만들지 말고 사람에게 묻는다**(§새 필드 금지).

#### `verbatim` — 수집 시점에 판정한다 (2026-08-09 신설, 원장 #50)

**받은 것이 곧 원본인 순간이므로 판정에 대조 비용이 들지 않는다.** 방금 저장한 본문이 가져온 것 그대로면 `true`, 요약·발췌·재서술이 섞였으면 `false` 를 적고 **무엇이 빠졌는지 `note:` 에 적는다**(규격: `.claude/rules/raw-ingest.md` §`verbatim`).

🔴 **이 순간을 놓치면 되돌릴 수 없다.** http 출처에는 `github_ref` 같은 시점 고정 수단이 없어, 나중에 다시 받으면 **인제스트 시점 판이 아니라 그날 판**이 온다. 수집기가 차단되면(실례: `cncf.co.kr` 이 jina-reader 에 403) **수집 경로조차 재현되지 않는다.** 그 파일은 영구히 승인 체크리스트 0번 **(d) 고정 불가** 로 떨어진다 — **1회 비용이 영구 비용으로 바뀐다.**

⚠️ **`compiled: false` 처럼 고정 기본값을 주지 않는다.** 대조 없이 `true` 가 찍히면 이 필드가 신설된 이유가 그대로 사라진다(원장 #47 조치안 ③). **판단이 서지 않으면 필드를 비우지 말고 `false` + `note:` 로 사유를 적는다.**

### 완료 후 보고

- 저장된 파일 경로
- 파일 크기 (대략적인 단어/줄 수)
- 다음 단계 안내: `/compile [파일명]`

### 작업 로그 업데이트

`log.md` (프로젝트 루트) 파일 끝에 다음 형식으로 append:

```
## [YYYY-MM-DD] ingest | [자료 제목]
- source: [원본 URL 또는 "직접 입력"]
- saved: raw/[파일명].md
- size: [줄 수]줄
```
