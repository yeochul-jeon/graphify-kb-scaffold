---
title: 제목을 여기에
source_url: https://
ingested_date: YYYY-MM-DD
compiled: false
compiled_date: null       # 인제스트 시점엔 항상 null — /compile Step 6 이 채운다
tags: [tag-1, tag-2]      # 채우는 것이 규범이다 — 실측 316/356(89%)가 값을 갖는다 (2026-08-17).
                          #   비울 거면 왜 비우는지 판단이 서야 한다. 습관적 [] 는 누락이다
                          # 🔴 어휘는 원문이 아니라 저장소에서 가져온다. 새 태그를 짓기 전에
                          #   `grep -h '^tags:' raw/*.md | tr ',[]' '\n\n\n' | sort | uniq -c | sort -rn`
                          #   로 기존 어휘를 보고 같은 뜻의 기존 태그가 있으면 그것을 쓴다.
                          #   실측 사례(2026-08-17): 원문 어휘만 따라 `retrieval`(2건)을 골랐는데
                          #   이 영역의 지배 태그는 `rag`(23건)였다 — 태그의 목적이 색인이므로
                          #   원문에 없는 단어라도 저장소 어휘가 우선이다
images: []                # 이미지 있으면 상대 경로 목록 (예: [attachments/<소스명>/img-01.png])
                          #   첨부 실물은 raw/attachments/<소스명>/ 에만 둔다. wiki/attachments/ 는 쓰지 않는다
verbatim: true | false    # 필수 — 수집 직후 판정한다. 기본값을 두지 않는다(대조 없이 true 가 찍히는 것을 막는다)
                          #   true  = 가져온 원문 그대로 (수집자 주석 추가는 허용, 원문에서 빼는 것은 불가)
                          #   false = 요약·발췌·재서술이 섞였다 → 무엇이 빠졌는지 note 에 적는다
verbatim_checked: YYYY-MM-DD
author: 작성자            # 선택 — 알면 적는다 (실측 125/356)
published: YYYY-MM-DD     # 선택 — 원문 발행일. ingested_date 와 다른 축이다 (실측 44/356)
# note — 필수 (2026-11-09 이후 ingested_date). 첫 줄은 항상 `수집 이유: <왜 이 자료를 받는가 한 줄>`.
#   2026-11-08 사용자 결정(ingest 제안 ①) — «ingest 가 무분별했는가» 를 다음 달에 수로 판정하려고.
#   scripts/check-raw-structure.py ⓓ 가 첫 줄을 검사한다. 예: `수집 이유: AWS KMS 페이지의 키 삭제 대기 기간 빈칸을 공식 문서로 채우려고.`
#   둘째 줄부터는 조건부 — 아래에 해당하면 반드시 적는다 (실측 93/356 이 사용 중, 2026-08-17).
#   · verbatim: false        → 무엇이 빠졌는지
#   · 수집 범위가 URL 이 가리키는 것의 일부일 때 → 무엇을 못 담았는지, 전문이 필요하면 어디로
#     가야 하는지. verbatim 은 '저장한 것' 에 대한 주장이므로 그 대상 범위를 여기서 못박는다
#   · 핀 없는 http 출처      → 대조일과 '오늘 판' 임을 명시
#   · images: 에 화면 보조 수집 프레임이 있을 때 → 프레임별로 읽은 사실. compile 은 raw/attachments/ 를
#     열지 못한다 (.claude/commands/ingest.md §화면 보조 수집)
#   해당 없는 조건부 줄은 지운다. 블록 스칼라(|) 를 쓴다.
#   ⚠️ | 아래의 # 는 주석이 아니라 값이다. 안내를 그 안에 남기지 말 것.
#   규격: .claude/rules/raw-ingest.md §수집 이유 · §verbatim · §핀이 없는 출처
note: |
  수집 이유: (왜 이 자료를 받는가 — 한 줄)
  (조건부 줄 — 해당 없으면 이 줄을 지운다)
---

# 제목

원본 내용을 여기에 붙여넣기.
