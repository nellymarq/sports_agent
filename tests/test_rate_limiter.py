# tests/test_rate_limiter.py
# Tests for the token-bucket rate limiter in llm.py

import asyncio
import time
import pytest


class TestTokenBucketRateLimiter:
    """Test the _TokenBucketRateLimiter class."""

    def _make_limiter(self, rate=60.0, burst=3):
        from llm import _TokenBucketRateLimiter
        return _TokenBucketRateLimiter(rate=rate, burst=burst)

    @pytest.mark.asyncio
    async def test_burst_allows_immediate(self):
        """Burst tokens allow immediate acquisition."""
        limiter = self._make_limiter(rate=60.0, burst=3)
        t0 = time.monotonic()
        for _ in range(3):
            await limiter.acquire()
        elapsed = time.monotonic() - t0
        assert elapsed < 0.5, f"Burst should be near-instant, took {elapsed}s"

    @pytest.mark.asyncio
    async def test_rate_limit_throttles(self):
        """After burst is exhausted, acquisition should be throttled."""
        # 60 RPM = 1/sec, burst=1 → second acquire should wait ~1s
        limiter = self._make_limiter(rate=60.0, burst=1)
        await limiter.acquire()  # Use the burst token
        t0 = time.monotonic()
        await limiter.acquire()  # Should wait
        elapsed = time.monotonic() - t0
        assert elapsed >= 0.5, f"Should throttle, but only took {elapsed}s"

    @pytest.mark.asyncio
    async def test_tokens_refill(self):
        """Tokens should refill over time."""
        limiter = self._make_limiter(rate=600.0, burst=2)  # 10/sec
        await limiter.acquire()
        await limiter.acquire()
        # Wait for refill
        await asyncio.sleep(0.3)
        t0 = time.monotonic()
        await limiter.acquire()
        elapsed = time.monotonic() - t0
        assert elapsed < 0.5, "Tokens should have refilled"

    @pytest.mark.asyncio
    async def test_concurrent_acquire(self):
        """Multiple concurrent acquires should not deadlock."""
        limiter = self._make_limiter(rate=600.0, burst=5)
        results = await asyncio.gather(
            *[limiter.acquire() for _ in range(5)]
        )
        assert len(results) == 5

    def test_init_defaults(self):
        """Verify default initialization."""
        limiter = self._make_limiter()
        assert limiter._burst == 3
        assert limiter._rate > 0


class TestGroqLLMConfig:
    """Test GroqLLM configuration and stats."""

    def test_stats_property(self):
        from llm import GroqLLM
        instance = GroqLLM.__new__(GroqLLM)
        instance._initialized = False
        instance.model = "test-model"
        instance._call_count = 5
        instance._total_tokens = 1000
        instance.client = None

        stats = instance.stats
        assert stats["model"] == "test-model"
        assert stats["call_count"] == 5
        assert stats["total_tokens"] == 1000

    def test_model_override(self):
        from llm import GroqLLM
        instance = GroqLLM.__new__(GroqLLM)
        instance._initialized = False
        instance.__init__(model="custom-model", max_tokens=2048)
        assert instance.model == "custom-model"
        assert instance.max_tokens == 2048
