from __future__ import annotations

from devcard_mcp.cache import DevCardCache


def test_get_returns_none_on_miss():
    cache = DevCardCache(ttl_seconds=60)
    assert cache.get("unknown") is None


def test_get_returns_cached_value():
    cache = DevCardCache(ttl_seconds=60)
    cache.set("user1", {"identity": {"username": "user1"}})
    result = cache.get("user1")
    assert result is not None
    assert result["identity"]["username"] == "user1"


def test_expired_entry_returns_none():
    cache = DevCardCache(ttl_seconds=0)
    cache.set("user1", {"data": True})
    assert cache.get("user1") is None


def test_clear_removes_all():
    cache = DevCardCache(ttl_seconds=60)
    cache.set("a", {})
    cache.set("b", {})
    cache.clear()
    assert cache.get("a") is None
    assert cache.get("b") is None
