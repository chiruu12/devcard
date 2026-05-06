"""In-memory cache for generated DevCards with TTL."""
from __future__ import annotations

import time
from typing import Any


class DevCardCache:
    def __init__(self, ttl_seconds: int = 1800):
        self._store: dict[str, tuple[Any, float]] = {}
        self._ttl = ttl_seconds

    def get(self, username: str) -> Any | None:
        entry = self._store.get(username)
        if entry is None:
            return None
        value, timestamp = entry
        if time.time() - timestamp > self._ttl:
            del self._store[username]
            return None
        return value

    def set(self, username: str, value: Any) -> None:
        self._store[username] = (value, time.time())

    def clear(self) -> None:
        self._store.clear()
