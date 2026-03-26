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

    def test_ttl_actual_expiry(self):
        """Verify entries actually expire after TTL elapses."""
        cache = ResponseCache(default_ttl=60)
        # Manually set an entry that's already expired
        key = cache._make_key("/expire_test", None)
        cache._cache[key] = {"value": "old", "expires_at": time.time() - 1}
        assert cache.get("/expire_test", None) is None

    def test_custom_ttl_overrides_default(self):
        cache = ResponseCache(default_ttl=1)
        # Set with a longer TTL
        cache.set("/long", None, "value", ttl=3600)
        key = cache._make_key("/long", None)
        # Verify the expiry is well in the future
        assert cache._cache[key]["expires_at"] > time.time() + 3500

    def test_overwrite_existing_key(self):
        cache = ResponseCache(default_ttl=60)
        cache.set("/test", {"k": 1}, "first")
        cache.set("/test", {"k": 1}, "second")
        assert cache.get("/test", {"k": 1}) == "second"

    def test_clear_resets_stats(self):
        cache = ResponseCache(default_ttl=60)
        cache.set("/a", None, 1)
        cache.get("/a", None)  # hit
        cache.get("/b", None)  # miss
        cache.clear()
        stats = cache.stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0

    def test_invalidate_nonexistent_is_noop(self):
        cache = ResponseCache(default_ttl=60)
        cache.invalidate("/nonexistent", {"x": 1})  # should not raise
        assert cache.get("/nonexistent", {"x": 1}) is None

    def test_param_order_independence(self):
        """Same params in different order should produce same cache key."""
        cache = ResponseCache(default_ttl=60)
        cache.set("/test", {"a": 1, "b": 2}, "value")
        # json.dumps with sort_keys=True ensures order-independence
        assert cache.get("/test", {"b": 2, "a": 1}) == "value"

    def test_different_endpoints_same_params(self):
        cache = ResponseCache(default_ttl=60)
        cache.set("/ep1", {"x": 1}, "result_1")
        cache.set("/ep2", {"x": 1}, "result_2")
        assert cache.get("/ep1", {"x": 1}) == "result_1"
        assert cache.get("/ep2", {"x": 1}) == "result_2"

    def test_concurrent_access(self):
        """Verify thread safety with concurrent reads/writes."""
        import threading

        cache = ResponseCache(default_ttl=60)
        errors = []

        def writer(i):
            try:
                for j in range(50):
                    cache.set(f"/ep_{i}", {"j": j}, f"val_{i}_{j}")
            except Exception as e:
                errors.append(e)

        def reader(i):
            try:
                for j in range(50):
                    cache.get(f"/ep_{i}", {"j": j})
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(4):
            threads.append(threading.Thread(target=writer, args=(i,)))
            threads.append(threading.Thread(target=reader, args=(i,)))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
