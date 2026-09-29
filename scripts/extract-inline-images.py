#!/usr/bin/env python3
"""원문 HTML 의 `data:image/…;base64` 인라인 이미지를 raw 에 복원한다 (원장 #103).

jina-reader(ingest-fetch.sh tier=1)는 인라인 이미지를 `blob:http://localhost/…` 로만 남긴다.
원문 HTML 에는 실제 이미지가 들어 있으므로 `curl` 대신 이 스크립트로 디코드한다.

사용:
  python3 scripts/extract-inline-images.py <원문 URL> <raw 슬러그>            # dry-run (기본)
  python3 scripts/extract-inline-images.py <원문 URL> <raw 슬러그> --apply    # 쓰기

<raw 슬러그> 는 raw/<슬러그>.md 의 파일명(.md 제외)이다. 저장 위치는
raw/attachments/<슬러그>/img-NN.<ext>.

멈추는 조건 (fallback 없음, exit 2):
- 인라인 이미지가 0개 · 디코드 실패 · 매직 바이트가 mime 과 다름
- raw 의 캡션 줄(`그림 N.` / `[그림 N]`)이 이미지 수와 다르거나 번호가 1..N 순서가 아님
- frontmatter `images:` 가 `[]` 가 아님 · 대상 파일이 이미 있음

캡션 N 바로 위(빈 줄·`<!-- 이미지 다운로드 실패 … -->` 주석은 건너뜀)가 `![…](blob:…)` 이면 그 줄을 치환하고
(실패 주석은 삭제 — 더 이상 사실이 아니다), 아니면 캡션 위에 참조 줄을 삽입한다.
raw 본문의 그 밖의 텍스트는 바꾸지 않는다. `note:` 는 바꾸지 않는다(사람이 사유를 적는다).
"""
import base64
import html
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMG_RE = re.compile(r'<img[^>]*?src="data:image/(png|jpeg|jpg|webp|gif);base64,([^"]+)"[^>]*>')
CAPTION_RE = re.compile(r"^\[?그림 ?(\d+)[.\]]")
BLOB_LINE_RE = re.compile(r"^!\[[^\]]*\]\(blob:[^)]*\)\s*$")
FAIL_NOTE_RE = re.compile(r"^<!--\s*이미지 다운로드 실패:.*-->\s*$")  # ingest.md §이미지 핸들링 4항이 blob 줄 아래에 남기는 주석
MAGIC = {"png": b"\x89PNG", "jpg": b"\xff\xd8", "gif": b"GIF8", "webp": b"RIFF"}


def die(msg):
    print(f"[extract-inline-images] 오류: {msg}", file=sys.stderr)
    sys.exit(2)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", errors="replace")


def decode_images(page):
    out = []
    for i, m in enumerate(IMG_RE.finditer(page), 1):
        ext = "jpg" if m.group(1) in ("jpeg", "jpg") else m.group(1)
        b64 = html.unescape(m.group(2))
        try:
            data = base64.b64decode(b64 + "=" * (-len(b64) % 4), validate=True)
        except Exception as e:
            die(f"이미지 {i} base64 디코드 실패: {e}")
        if not data.startswith(MAGIC[ext]):
            die(f"이미지 {i} 매직 바이트가 {ext} 가 아니다: {data[:8]!r}")
        out.append((ext, data))
    if not out:
        die("원문 HTML 에 data: 인라인 이미지가 없다")
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    apply = "--apply" in sys.argv
    if len(args) != 2:
        die("사용법: extract-inline-images.py <원문 URL> <raw 슬러그> [--apply]")
    url, slug = args
    raw_path = ROOT / "raw" / f"{slug}.md"
    if not raw_path.is_file():
        die(f"{raw_path} 가 없다")
    images = decode_images(fetch(url))

    lines = raw_path.read_text(encoding="utf-8").split("\n")
    caps = [(i, int(m.group(1))) for i, l in enumerate(lines) if (m := CAPTION_RE.match(l))]
    if [n for _, n in caps] != list(range(1, len(images) + 1)):
        die(f"캡션 줄 번호 {[n for _, n in caps]} 가 이미지 {len(images)}개(1..N 순서)와 맞지 않는다")
    if "images: []" not in lines[:20]:
        die("frontmatter 에 `images: []` 가 없다 (이미 채워졌거나 형식이 다르다)")

    att = ROOT / "raw" / "attachments" / slug
    names = [f"img-{n:02d}.{ext}" for n, (ext, _) in enumerate(images, 1)]
    for nm in names:
        if (att / nm).exists():
            die(f"{att / nm} 가 이미 있다")

    edits = []  # (캡션 줄 index, 치환할 blob 줄 index 또는 None, 지울 실패 주석 줄 index 또는 None, 참조 줄)
    for (ci, n), nm in zip(caps, names):
        ref = f"![Image {n}: {nm}](attachments/{slug}/{nm})"
        j, note = ci - 1, None
        while j >= 0 and (lines[j].strip() == "" or (note is None and FAIL_NOTE_RE.match(lines[j]))):
            if FAIL_NOTE_RE.match(lines[j]):
                note = j
            j -= 1
        if BLOB_LINE_RE.match(lines[j]):
            edits.append((ci, j, note, ref))
        else:
            edits.append((ci, None, None, ref))

    print(f"이미지 {len(images)}개 · 대상 {raw_path.relative_to(ROOT)} · 모드 {'apply' if apply else 'dry-run'}")
    for (ci, rj, nj, ref), (ext, data) in zip(edits, images):
        how = f"치환(줄 {rj + 1}" + (f", 실패 주석 줄 {nj + 1} 삭제)" if nj is not None else ")") if rj is not None else "삽입"
        print(f"  {ref}  {len(data)}B  캡션 줄 {ci + 1} 위 {how}")
    if not apply:
        return

    for ci, rj, nj, ref in sorted(edits, key=lambda e: -e[0]):
        if rj is not None:
            lines[rj] = ref
            if nj is not None:
                del lines[nj]
        else:
            lines[ci:ci] = [ref, ""]
    lines[lines.index("images: []")] = "images: [" + ", ".join(f"attachments/{slug}/{nm}" for nm in names) + "]"
    att.mkdir(parents=True)
    for nm, (_, data) in zip(names, images):
        (att / nm).write_bytes(data)
    raw_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"저장 완료: {att.relative_to(ROOT)}/ {len(names)}개, raw 본문·images 갱신 (note 는 직접 정정할 것)")


if __name__ == "__main__":
    main()
