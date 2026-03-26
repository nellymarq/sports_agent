# backend/response_cache.py
# Simple in-memory response cache for expensive API endpoints.
# Uses TTL-based expiry with thread-safe access.

from __future__ import annotations
import time
import threading
import hashlib
import json
from typing import Any, Dict, Optional

try:
    from config import RESPONSE_CACHE_TTL
except ImportError:
    RESPONSE_CACHE_TTL = 120


class ResponseCache:
    """
    In-memory response cache for API endpoints.
    Keyed by endpoint + request hash.
    """

    def __init__(self, default_ttl: int = 60):
        self._lock = threading.Lock()
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._default_ttl = default_ttl
        self._hits = 0
        self._misses = 0

    def _make_key(self, endpoint: str, params: Any = None) -> str:
        raw = f"{endpoint}:{json.dumps(params, sort_keys=True, default=str)}"
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, endpoint: str, params: Any = None) -> Optional[Any]:
        key = self._make_key(endpoint, params)
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None
            if time.time() > entry["expires_at"]:
                del self._cache[key]
                self._misses += 1
                return None
            self._hits += 1
            return entry["value"]

    def set(self, endpoint: str, params: Any, value: Any, ttl: Optional[int] = None) -> None:
        key = self._make_key(endpoint, params)
        ttl = ttl if ttl is not None else self._default_ttl
        with self._lock:
            self._cache[key] = {
                "value": value,
                "expires_at": time.time() + ttl,
            }

    def invalidate(self, endpoint: str, params: Any = None) -> None:
        key = self._make_key(endpoint, params)
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> int:
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            return count

    def evict_expired(self) -> int:
        """Remove all expired entries. Returns count of evicted entries."""
        now = time.time()
        with self._lock:
            expired = [k for k, v in self._cache.items() if now > v["expires_at"]]
            for k in expired:
                del self._cache[k]
            return len(expired)

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            total = self._hits + self._misses
            return {
                "entries": len(self._cache),
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(self._hits / total * 100, 1) if total > 0 else 0,
            }

    def start_background_eviction(self, interval_seconds: int = 60):
        """Start a daemon thread that periodically evicts expired entries."""
        def _evict_loop():
            while True:
                time.sleep(interval_seconds)
                self.evict_expired()

        t = threading.Thread(target=_evict_loop, daemon=True, name="cache-evictor")
        t.start()


# Shared instance for the backend
response_cache = ResponseCache(default_ttl=RESPONSE_CACHE_TTL)
response_cache.start_background_eviction(interval_seconds=60)
