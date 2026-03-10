# cache/cache_manager.py
# TTL-aware cache with disk persistence and memory-first reads.

import json
import time
import threading
from pathlib import Path
from typing import Any, Optional

from config import TOOL_CACHE_TTL_SECONDS

CACHE_DIR = Path("cache/")
CACHE_DIR.mkdir(exist_ok=True)

RUNTIME_CACHE_PATH = CACHE_DIR / "runtime_cache.json"


class CacheManager:
    """
    Thread-safe cache with per-key TTL support.
    Reads from memory first, persists to disk on writes.
    """

    def __init__(self, default_ttl: int = TOOL_CACHE_TTL_SECONDS):
        self._lock = threading.Lock()
        self._default_ttl = default_ttl
        self._cache: dict[str, dict[str, Any]] = {}
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        if RUNTIME_CACHE_PATH.exists():
            try:
                raw = json.loads(RUNTIME_CACHE_PATH.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    # Support both old format (flat dict) and new format (with metadata)
                    for k, v in raw.items():
                        if isinstance(v, dict) and "value" in v and "expires_at" in v:
                            self._cache[k] = v
                        else:
                            # Legacy entry — no TTL, keep forever
                            self._cache[k] = {
                                "value": v,
                                "expires_at": 0,  # 0 = never expires
                                "created_at": 0,
                            }
            except (json.JSONDecodeError, OSError):
                self._cache = {}
        else:
            RUNTIME_CACHE_PATH.write_text("{}", encoding="utf-8")

    def _persist(self) -> None:
        try:
            tmp = str(RUNTIME_CACHE_PATH) + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2, ensure_ascii=False, default=str)
            Path(tmp).replace(RUNTIME_CACHE_PATH)
        except OSError:
            pass

    def get(self, key: str) -> Any:
        """Get a cached value. Returns None if missing or expired."""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None

            expires_at = entry.get("expires_at", 0)
            if expires_at and time.time() > expires_at:
                del self._cache[key]
                return None

            return entry["value"]

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Store a value with optional TTL (seconds). Default TTL from config."""
        ttl = ttl if ttl is not None else self._default_ttl
        now = time.time()

        with self._lock:
            self._cache[key] = {
                "value": value,
                "expires_at": now + ttl if ttl > 0 else 0,
                "created_at": now,
            }
            self._persist()

    def delete(self, key: str) -> bool:
        """Remove a specific key. Returns True if key existed."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._persist()
                return True
            return False

    def clear(self) -> int:
        """Clear all entries. Returns count of removed entries."""
        with self._lock:
            count = len(self._cache)
            self._cache = {}
            self._persist()
            return count

    def cleanup_expired(self) -> int:
        """Remove all expired entries. Returns count of removed entries."""
        now = time.time()
        with self._lock:
            expired_keys = [
                k for k, v in self._cache.items()
                if v.get("expires_at", 0) and now > v["expires_at"]
            ]
            for k in expired_keys:
                del self._cache[k]
            if expired_keys:
                self._persist()
            return len(expired_keys)

    @property
    def size(self) -> int:
        """Number of entries (including potentially expired)."""
        return len(self._cache)

    def stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        now = time.time()
        total = len(self._cache)
        expired = sum(
            1 for v in self._cache.values()
            if v.get("expires_at", 0) and now > v["expires_at"]
        )
        return {
            "total_entries": total,
            "expired_entries": expired,
            "active_entries": total - expired,
            "default_ttl": self._default_ttl,
        }
