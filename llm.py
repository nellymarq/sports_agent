# llm.py
# Global GroqLLM singleton with lazy client initialization,
# correct .env loading, concurrency-safe async usage,
# and full message return.

import os
import logging
import asyncio
from typing import List, Dict, Optional
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

# ----------------------------------------------------------------------
# FIXED ENV LOADING (robust across Streamlit, FastAPI, CLI, tests)
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

GROQ_SEMAPHORE = asyncio.Semaphore(5)


class GroqLLM:
    _instance = None

    def __new__(cls, *args, **kwargs):
        # Allow multiple configured instances (routing vs prediction),
        # but keep the original singleton as a default when used as `llm = GroqLLM()`.
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return super().__new__(cls)

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        # Avoid re‑initializing when used as a global singleton
        if getattr(self, "_initialized", False) and model is None and temperature is None and max_tokens is None:
            return

        # Base config from env
        env_model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        env_temp = float(os.getenv("GROQ_TEMPERATURE", "0.2"))
        env_max = int(os.getenv("GROQ_MAX_TOKENS", "1024"))

        # Allow explicit overrides
        self.model = model or env_model
        self.temperature = float(temperature if temperature is not None else env_temp)
        self.max_tokens = int(max_tokens if max_tokens is not None else env_max)

        # Lazy client
        self.client = None

        logger.info(
            f"GroqLLM configured with model={self.model}, "
            f"temperature={self.temperature}, max_tokens={self.max_tokens}"
        )

        self._initialized = True

    # --------------------------------------------------------------
    # Lazy client creation (safe for FastAPI, Streamlit, uvicorn reload)
    # --------------------------------------------------------------
    def get_client(self):
        if self.client is None:
            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError("GROQ_API_KEY is not set in environment variables.")

            self.client = Groq(api_key=api_key)
            logger.info("Groq client initialized lazily (first use).")

        return self.client

    # --------------------------------------------------------------
    # Async completion wrapper
    # --------------------------------------------------------------
    async def _create_completion(self, messages: List[Dict[str, str]]):
        """
        Run the Groq completion in a thread to avoid blocking the event loop.
        """
        client = self.get_client()

        def _call():
            return client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

        return await asyncio.to_thread(_call)

    # --------------------------------------------------------------
    # Public chat method
    # --------------------------------------------------------------
    async def chat(self, messages: List[Dict[str, str]]):
        """
        Core chat method used by the entire system.
        Returns the full message object (with .content, .tool_calls, etc.).
        """
        try:
            async with GROQ_SEMAPHORE:
                resp = await self._create_completion(messages)

            return resp.choices[0].message

        except Exception as e:
            logger.exception("GroqLLM.chat failed")
            raise RuntimeError(f"Groq LLM error (model={self.model}): {e}") from e


# Global singleton instance (legacy usage)
llm = GroqLLM()
