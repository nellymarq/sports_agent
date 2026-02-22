# embeddings/embedding_engine.py

from typing import List
import hashlib
import math


def _hash_to_vector(text: str, dim: int = 128) -> List[float]:
    h = hashlib.sha256(text.encode("utf-8")).digest()
    vals = list(h) * (dim // len(h) + 1)
    vals = vals[:dim]
    vec = [float(v) - 128.0 for v in vals]
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def get_embedding(text: str) -> List[float]:
    return _hash_to_vector(text, dim=128)


# -------------------------------------------------------------------
# Minimal wrapper class required by the test suite
# -------------------------------------------------------------------
class EmbeddingEngine:
    """
    Minimal wrapper class expected by the test suite.
    Provides a .embed(text) method that returns a 128‑dim embedding.
    """

    def embed(self, text: str) -> List[float]:
        return get_embedding(text)
