"""
graphify-out/cache/ 에서 meta 파일(index.md, backlinks.md, compile-log.md)의
구버전 캐시를 정리하고 최신 1개만 유지한다.

wiki/index.md, wiki/backlinks.md, wiki/_meta/compile-log.md는 컴파일마다
내용이 바뀌어 버전별 캐시가 누적되고 그래프에 중복 노드가 생긴다.
이 스크립트는 빌드 후 호출되어 각 파일당 최신 캐시 1개만 남긴다.
"""
import json
from pathlib import Path
from collections import defaultdict

META_FILES = [
    "wiki/index.md",
    "wiki/backlinks.md",
    "wiki/_meta/compile-log.md",
]

cache_dir = Path("graphify-out/cache")
if not cache_dir.exists():
    print("cache dir not found, skipping")
    exit(0)

# meta 파일 → [(mtime, cache_path), ...]
buckets: dict[str, list] = defaultdict(list)

for cache_file in cache_dir.glob("*.json"):
    try:
        data = json.loads(cache_file.read_text())
        for node in data.get("nodes", []):
            src = node.get("source_file", "")
            if any(meta in src for meta in META_FILES):
                buckets[src].append((cache_file.stat().st_mtime, cache_file))
                break
    except Exception:
        pass

deleted = 0
for src, entries in buckets.items():
    if len(entries) <= 1:
        continue
    entries.sort(reverse=True)  # 최신 → 구버전 순
    for _mtime, old_cache in entries[1:]:
        old_cache.unlink()
        deleted += 1

print(f"cleanup-meta-caches: {deleted}개 구버전 캐시 삭제 ({len(buckets)}개 meta 파일 처리)")
