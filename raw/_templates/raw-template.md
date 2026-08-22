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
# note — 조건부 필드 (실측 93/356 이 사용 중, 2026-08-17). 아래에 해당하면 반드시 적는다.
#   · verbatim: false        → 무엇이 빠졌는지
#   · 수집 범위가 URL 이 가리키는 것의 일부일 때 → 무엇을 못 담았는지, 전문이 필요하면 어디로
#     가야 하는지. verbatim 은 '저장한 것' 에 대한 주장이므로 그 대상 범위를 여기서 못박는다
#   · 핀 없는 http 출처      → 대조일과 '오늘 판' 임을 명시
#   해당 없으면 아래 두 줄을 지운다. 여러 줄이면 아래처럼 블록 스칼라(|) 를 쓴다.
#   ⚠️ | 아래의 # 는 주석이 아니라 값이다. 안내를 그 안에 남기지 말 것.
#   규격: .claude/rules/raw-ingest.md §verbatim · §핀이 없는 출처
note: |
  (조건부 — 해당 없으면 이 필드를 지운다)
---

# 제목

원본 내용을 여기에 붙여넣기.
