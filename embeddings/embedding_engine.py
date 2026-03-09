# embeddings/embedding_engine.py

from typing import List
import hashlib
import math
from functools import lru_cache

# --- Lazy model loading ---
_model = None
_USE_REAL_EMBEDDINGS = True


def _get_model():
    global _model, _USE_REAL_EMBEDDINGS
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception:
            _USE_REAL_EMBEDDINGS = False
            _model = "FALLBACK"
    return _model


# --- Fallback hash-based embedding (original) ---
def _hash_to_vector(text: str, dim: int = 384) -> List[float]:
    h = hashlib.sha256(text.encode("utf-8")).digest()
    vals = list(h) * (dim // len(h) + 1)
    vals = vals[:dim]
    vec = [float(v) - 128.0 for v in vals]
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


# --- Cache for embeddings ---
@lru_cache(maxsize=2048)
def _cached_embed(text: str) -> tuple:
    """Returns tuple (hashable) for caching; convert back to list at call site."""
    model = _get_model()
    if _USE_REAL_EMBEDDINGS and model != "FALLBACK":
        vec = model.encode(text, normalize_embeddings=True).tolist()
        return tuple(vec)
    return tuple(_hash_to_vector(text, dim=384))


def get_embedding(text: str) -> List[float]:
    return list(_cached_embed(text))


class EmbeddingEngine:
    """Wrapper class expected by the test suite and memory_agent."""
    def embed(self, text: str) -> List[float]:
        return get_embedding(text)
