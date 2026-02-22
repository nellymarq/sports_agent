# cache/cache_manager.py

import json
from pathlib import Path
from functools import lru_cache
from typing import Any

CACHE_DIR = Path("cache/")
CACHE_DIR.mkdir(exist_ok=True)

RUNTIME_CACHE_PATH = CACHE_DIR / "runtime_cache.json"


class CacheManager:
    def __init__(self):
        if not RUNTIME_CACHE_PATH.exists():
            RUNTIME_CACHE_PATH.write_text(json.dumps({}))
        self.cache = json.loads(RUNTIME_CACHE_PATH.read_text())

    def get(self, key: str) -> Any:
        return self.cache.get(key)

    def set(self, key: str, value: Any):
        self.cache[key] = value
        RUNTIME_CACHE_PATH.write_text(json.dumps(self.cache, indent=2))

    @staticmethod
    @lru_cache(maxsize=256)
    def memoize(func):
        return func
