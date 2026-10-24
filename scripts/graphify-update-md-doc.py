#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""`graphify update` 런처 — `.md` 의 논문 판정만 끄고 graphify CLI 를 부른다.

사용 (graphify venv 로 돌아야 한다 — `scripts/graphify-build.sh` 가 이렇게 부른다):
    scripts/graphify-py.sh scripts/graphify-update-md-doc.py update .

## 왜 있는가 (계획 `docs/plan/plans/2026-10-25-graphify-paper-misclassification.md`)

graphify 는 `.md` 앞 3,000자에서 논문 신호 정규식 13개 중 3개 이상이 맞으면
`paper` 로 분류한다(`graphify/detect.py` `_looks_like_paper`·`classify_file`).
`graphify update` 는 LLM 없이 `code` 와 `document` 버킷만 다시 추출하고 `paper` 는
읽지 않는다. 그래서 arXiv 원문을 담은 md 6건이 **경고 없이** 그래프에서 빠져 있었다.
분류를 바꾸는 환경변수·설정은 없다.

## 범위

패치는 **이 프로세스 안에서만** 걸린다. `graphify query`·`/graphify` 스킬·
`rebuild-graph-report.py` 등 다른 `graphify-py.sh` 호출은 원래 판정을 그대로 쓴다.
환경변수·`sitecustomize` 방식을 쓰지 않은 이유가 이것이다 — 모든 호출에 끼어든다.
모듈 속성 교체로 충분한 근거: `classify_file` 이 `_looks_like_paper` 를 모듈 전역
이름으로 부르고, `update` 경로(`graphify/watch.py` `_rebuild_code`)가 `detect` 를
함수 안에서 늦게 import 한다 (graphifyy 0.9.68 에서 확인).

## 업그레이드로 깨질 때

비공개 함수 몽키패치다. 함수가 없어지거나 `detect()` 가 그 이름을 거쳐 분류하지
않으면 **exit 3 으로 멈춘다** — 조용히 원래 판정으로 돌면 6건이 다시 빠진다.
그때는 새 버전의 `classify_file` 을 읽고 이 파일을 고친다. 자세한 절차는
`docs/guide/graphify.md` §.md 논문 판정과 빌드 경로.
"""
import os
import sys
import tempfile
from pathlib import Path

# `PYTHONHASHSEED` 가 없으면 graphify `main()` 이 `update` 를 `-m graphify` 로 다시 실행한다
# (`graphify/__main__.py` `_pin_hash_seed_if_needed`). 새 프로세스에는 패치가 없어서
# 논문 판정이 조용히 돌아온다. `scripts/graphify-py.sh` 가 `=0` 을 export 하므로 그 경유를 강제한다.
if "PYTHONHASHSEED" not in os.environ:
    sys.stderr.write("[graphify-update-md-doc] PYTHONHASHSEED 미설정 — graphify 가 프로세스를 다시 띄워 "
                     "패치가 사라진다. scripts/graphify-py.sh 로 부를 것.\n")
    sys.exit(3)

import graphify.detect as detect  # noqa: E402

_orig = getattr(detect, "_looks_like_paper", None)
if _orig is None:
    sys.stderr.write("[graphify-update-md-doc] graphify.detect._looks_like_paper 가 없다 — "
                     "graphify 업그레이드로 패치 대상이 사라졌다. 이 런처를 고칠 것.\n")
    sys.exit(3)


def _md_never_paper(path):
    if Path(path).suffix.lower() == ".md":
        return False
    return _orig(path)


detect._looks_like_paper = _md_never_paper

# 자기 시험 — 논문 신호 3개(arxiv · abstract · arXiv ID)를 가진 md 가 `update` 와 같은
# 진입점 `detect()` 에서 `document` 버킷에 들어가는지 본다. 이름은 남았는데 분류가 그 이름을
# 거치지 않게 바뀐 경우를 잡는다.
with tempfile.TemporaryDirectory() as d:
    probe = Path(d) / "probe.md"
    probe.write_text("# t\n\narXiv 2501.00001\n\nAbstract\n", encoding="utf-8")
    buckets = detect.detect(Path(d))["files"]
    ok = any(Path(f).name == "probe.md" for f in buckets.get("document", []))
if not ok:
    where = [k for k, v in buckets.items() if any(Path(f).name == "probe.md" for f in v)]
    sys.stderr.write(f"[graphify-update-md-doc] 패치 후에도 논문 신호 md 가 document 가 아니다(버킷 {where}) — "
                     "detect() 가 _looks_like_paper 를 거치지 않는다. 이 런처를 고칠 것.\n")
    sys.exit(3)

from graphify.__main__ import main  # noqa: E402

sys.argv = ["graphify", *sys.argv[1:]]
main()
