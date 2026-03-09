# llm.py
# Global GroqLLM with lazy client, async-safe concurrency,
# token-bucket rate limiting, and retry with exponential backoff.

import os
import time
import logging
import asyncio
from typing import List, Dict, Optional
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

# ----------------------------------------------------------------------
# ENV LOADING
# ----------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent
ENV_PATH = PROJECT_ROOT / ".env"

if not ENV_PATH.exists():
    ENV_PATH = Path.cwd() / ".env"

load_dotenv(ENV_PATH)

# ----------------------------------------------------------------------

logger = logging.getLogger("ufc_llm")
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )


class _TokenBucketRateLimiter:
    """Simple token-bucket rate limiter for API calls."""

    def __init__(self, rate: float = 25.0, burst: int = 5):
        """
        rate: requests per minute allowed
        burst: max burst tokens (extra requests allowed above rate)
        """
        self._rate = rate / 60.0  # convert to per-second
        self._burst = burst
        self._tokens = float(burst)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(
                self._burst, self._tokens + elapsed * self._rate
            )
            self._last_refill = now

            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return

            # Wait for a token to become available
            wait = (1.0 - self._tokens) / self._rate
            self._tokens = 0.0

        await asyncio.sleep(wait)


# Shared rate limiter: 25 RPM with burst of 5
_RATE_LIMITER = _TokenBucketRateLimiter(
    rate=float(os.getenv("GROQ_RATE_LIMIT_RPM", "25")),
    burst=int(os.getenv("GROQ_RATE_LIMIT_BURST", "5")),
)

# Concurrency semaphore: max parallel in-flight requests
GROQ_SEMAPHORE = asyncio.Semaphore(
    int(os.getenv("GROQ_MAX_CONCURRENT", "6"))
)


class GroqLLM:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return super().__new__(cls)

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        if (
            getattr(self, "_initialized", False)
            and model is None
            and temperature is None
            and max_tokens is None
        ):
            return

        env_model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        env_temp = float(os.getenv("GROQ_TEMPERATURE", "0.2"))
        env_max = int(os.getenv("GROQ_MAX_TOKENS", "1024"))

        self.model = model or env_model
        self.temperature = float(
            temperature if temperature is not None else env_temp
        )
        self.max_tokens = int(
            max_tokens if max_tokens is not None else env_max
        )

        self.client = None
        self._call_count = 0
        self._total_tokens = 0

        logger.info(
            f"GroqLLM configured: model={self.model}, "
            f"temperature={self.temperature}, max_tokens={self.max_tokens}"
        )

        self._initialized = True

    def get_client(self):
        if self.client is None:
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError(
                    "GROQ_API_KEY is not set in environment variables."
                )

            self.client = Groq(api_key=api_key)
            logger.info("Groq client initialized lazily (first use).")

        return self.client

    @property
    def stats(self) -> Dict:
        return {
            "model": self.model,
            "call_count": self._call_count,
            "total_tokens": self._total_tokens,
        }

    async def _create_completion(self, messages: List[Dict[str, str]]):
        client = self.get_client()

        def _call():
            return client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

        return await asyncio.to_thread(_call)

    async def chat(self, messages: List[Dict[str, str]], retries: int = 2):
        """
        Core chat method. Returns the full message object.
        Uses rate limiting + concurrency control + retry with backoff.
        """
        last_err = None
        for attempt in range(1 + retries):
            try:
                await _RATE_LIMITER.acquire()
                async with GROQ_SEMAPHORE:
                    t0 = time.monotonic()
                    resp = await self._create_completion(messages)
                    elapsed = time.monotonic() - t0

                self._call_count += 1
                usage = getattr(resp, "usage", None)
                if usage:
                    tokens = getattr(usage, "total_tokens", 0)
                    self._total_tokens += tokens
                    logger.debug(
                        f"LLM call: model={self.model} tokens={tokens} "
                        f"elapsed={elapsed:.2f}s"
                    )

                return resp.choices[0].message

            except Exception as e:
                last_err = e
                err_str = str(e).lower()
                is_transient = any(
                    k in err_str
                    for k in [
                        "rate_limit",
                        "429",
                        "timeout",
                        "503",
                        "overloaded",
                        "connection",
                        "temporarily",
                    ]
                )
                if is_transient and attempt < retries:
                    wait = 2 ** (attempt + 1)  # 2s, 4s
                    logger.warning(
                        f"Transient LLM error (attempt {attempt + 1}/{1 + retries}), "
                        f"retrying in {wait}s: {e}"
                    )
                    await asyncio.sleep(wait)
                    continue
                break

        logger.exception("GroqLLM.chat failed after retries")
        raise RuntimeError(
            f"Groq LLM error (model={self.model}): {last_err}"
        ) from last_err


# Global singleton instance (legacy usage)
llm = GroqLLM()
