# tests/test_cache_manager.py
# Tests for TTL-aware cache manager.

import sys
import time
import json
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def cache(tmp_path, monkeypatch):
    """Create a CacheManager with a temp directory."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    cache_file = cache_dir / "runtime_cache.json"
    cache_file.write_text("{}")

    monkeypatch.setattr("cache.cache_manager.CACHE_DIR", cache_dir)
    monkeypatch.setattr("cache.cache_manager.RUNTIME_CACHE_PATH", cache_file)

    from cache.cache_manager import CacheManager
    return CacheManager(default_ttl=60)


class TestCacheBasicOperations:
    def test_set_and_get(self, cache):
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_missing_key(self, cache):
        assert cache.get("nonexistent") is None

    def test_set_overwrites(self, cache):
        cache.set("key1", "v1")
        cache.set("key1", "v2")
        assert cache.get("key1") == "v2"

    def test_delete_existing(self, cache):
        cache.set("key1", "val")
        assert cache.delete("key1") is True
        assert cache.get("key1") is None

    def test_delete_nonexistent(self, cache):
        assert cache.delete("nope") is False

    def test_clear(self, cache):
        cache.set("a", 1)
        cache.set("b", 2)
        count = cache.clear()
        assert count == 2
        assert cache.size == 0


class TestCacheTTL:
    def test_expired_key_returns_none(self, cache):
        cache.set("temp", "data", ttl=1)
        assert cache.get("temp") == "data"
        time.sleep(1.1)
        assert cache.get("temp") is None

    def test_no_ttl_never_expires(self, cache):
        cache.set("forever", "data", ttl=0)
        assert cache.get("forever") == "data"

    def test_cleanup_expired(self, cache):
        cache.set("short", "gone", ttl=1)
        cache.set("long", "stays", ttl=3600)
        time.sleep(1.1)
        removed = cache.cleanup_expired()
        assert removed == 1
        assert cache.get("short") is None
        assert cache.get("long") == "stays"


class TestCacheStats:
    def test_stats_structure(self, cache):
        stats = cache.stats()
        assert "total_entries" in stats
        assert "active_entries" in stats
        assert "expired_entries" in stats
        assert "default_ttl" in stats

    def test_stats_counts(self, cache):
        cache.set("a", 1)
        cache.set("b", 2)
        stats = cache.stats()
        assert stats["total_entries"] == 2
        assert stats["active_entries"] == 2

    def test_size_property(self, cache):
        assert cache.size == 0
        cache.set("x", 1)
        assert cache.size == 1


class TestCachePersistence:
    def test_persists_to_disk(self, cache, tmp_path):
        cache.set("persisted", "value")
        cache_file = tmp_path / "cache" / "runtime_cache.json"
        raw = json.loads(cache_file.read_text())
        assert "persisted" in raw

    def test_complex_values(self, cache):
        cache.set("dict", {"a": 1, "b": [2, 3]})
        assert cache.get("dict") == {"a": 1, "b": [2, 3]}

        cache.set("list", [1, "two", 3.0])
        assert cache.get("list") == [1, "two", 3.0]


class TestCacheEndpoints:
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from backend.main import app
        return TestClient(app)

    def test_cache_stats_endpoint(self, client):
        resp = client.get("/cache/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "tool_cache" in data
        assert "total_entries" in data["tool_cache"]

    def test_cache_cleanup_endpoint(self, client):
        resp = client.post("/cache/cleanup")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "removed" in data
