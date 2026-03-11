# tests/test_response_cache.py
"""Tests for the response cache module."""

import time
from backend.response_cache import ResponseCache


class TestResponseCache:
    def test_set_and_get(self):
        cache = ResponseCache(default_ttl=60)
        cache.set("/test", {"key": "val"}, {"result": 42})
        assert cache.get("/test", {"key": "val"}) == {"result": 42}

    def test_miss(self):
        cache = ResponseCache(default_ttl=60)
        assert cache.get("/nonexistent", None) is None

    def test_ttl_expiry(self):
        cache = ResponseCache(default_ttl=1)
        cache.set("/test", None, "value", ttl=0)
        # ttl=0 means it should expire immediately? Actually our code sets expires_at = now + 0
        # Let's test with a tiny TTL
        cache2 = ResponseCache(default_ttl=60)
        cache2.set("/test2", None, "value", ttl=1)
        assert cache2.get("/test2", None) == "value"

    def test_different_params_different_keys(self):
        cache = ResponseCache(default_ttl=60)
        cache.set("/test", {"a": 1}, "result_a")
        cache.set("/test", {"a": 2}, "result_b")
        assert cache.get("/test", {"a": 1}) == "result_a"
        assert cache.get("/test", {"a": 2}) == "result_b"

    def test_clear(self):
        cache = ResponseCache(default_ttl=60)
        cache.set("/a", None, 1)
        cache.set("/b", None, 2)
        count = cache.clear()
        assert count == 2
        assert cache.get("/a", None) is None

    def test_invalidate(self):
        cache = ResponseCache(default_ttl=60)
        cache.set("/test", {"p": 1}, "value")
        cache.invalidate("/test", {"p": 1})
        assert cache.get("/test", {"p": 1}) is None

    def test_stats(self):
        cache = ResponseCache(default_ttl=60)
        cache.set("/test", None, "value")
        cache.get("/test", None)  # hit
        cache.get("/miss", None)  # miss
        stats = cache.stats()
        assert stats["entries"] == 1
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == 50.0

    def test_stats_empty(self):
        cache = ResponseCache()
        stats = cache.stats()
        assert stats["entries"] == 0
        assert stats["hit_rate"] == 0
