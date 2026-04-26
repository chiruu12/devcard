from __future__ import annotations

import logging
from pathlib import Path

from diskcache import Cache

logger = logging.getLogger(__name__)


class GitHubCache:
    def __init__(self, cache_dir: Path, ttl: int = 3600, enabled: bool = True):
        self._ttl = ttl
        self._enabled = enabled
        self._cache: Cache | None = None
        if enabled:
            cache_dir.mkdir(parents=True, exist_ok=True)
            self._cache = Cache(str(cache_dir))

    def get(self, url: str) -> dict | list | None:
        if not self._enabled or self._cache is None:
            return None
        key = f"GET:{url}"
        return self._cache.get(key)

    def set(self, url: str, data: dict | list) -> None:
        if not self._enabled or self._cache is None:
            return
        key = f"GET:{url}"
        self._cache.set(key, data, expire=self._ttl)

    def close(self) -> None:
        if self._cache is not None:
            self._cache.close()
