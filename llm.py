# llm.py
# Global GroqLLM singleton with correct .env loading and full message return

import os
import logging
import asyncio
from typing import List, Dict
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

# ---------------------------------------------------------
# Load .env BEFORE creating the singleton
# ---------------------------------------------------------
ROOT_ENV = Path(__file__).resolve().parent / ".env"
load_dotenv(ROOT_ENV)

logger = logging.getLogger("ufc_llm")
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )

# ---------------------------------------------------------
# Global semaphore to prevent Groq 429 rate limits
# ---------------------------------------------------------
GROQ_SEMAPHORE = asyncio.Semaphore(1)


class GroqLLM:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Prevent reinitialization on Streamlit reload
        if getattr(self, "_initialized", False):
            return

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is not set in environment variables.")

        self.model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self.temperature = float(os.getenv("GROQ_TEMPERATURE", "0.2"))
        self.client = Groq(api_key=api_key)

        logger.info(
            f"GroqLLM initialized with model={self.model}, temperature={self.temperature}"
        )

        self._initialized = True

    # ---------------------------------------------------------
    # FIXED: Direct synchronous call + semaphore for rate limiting
    # ---------------------------------------------------------
    async def chat(self, messages: List[Dict[str, str]]):
        try:
            # Prevent multiple concurrent Groq requests
            async with GROQ_SEMAPHORE:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                )

            # Return the full message object:
            # {
            #   "role": "assistant",
            #   "content": "...",
            #   "tool_calls": [...]
            # }
            return resp.choices[0].message

        except Exception as e:
            logger.exception("GroqLLM.chat failed")
            raise RuntimeError(f"Groq LLM error (model={self.model}): {e}") from e


# ---------------------------------------------------------
# Create the global singleton AFTER .env is loaded
# ---------------------------------------------------------
llm = GroqLLM()
