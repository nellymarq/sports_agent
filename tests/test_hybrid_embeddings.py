
# --- Ensure project root is on sys.path ---
import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
# ------------------------------------------

# tests/test_hybrid_embeddings.py

from embeddings.embedding_engine import EmbeddingEngine
from embeddings.vector_store import VectorStore


def test_hybrid_embedding_engine():
    engine = EmbeddingEngine()
    vec = engine.embed("Test embedding for UFC engine.")
    assert isinstance(vec, list)
    assert len(vec) > 0


def test_vector_store_roundtrip():
    store = VectorStore()
    engine = EmbeddingEngine()

    text = "Hybrid embedding test entry."
    emb = engine.embed(text)

    store.add(text=text, embedding=emb, metadata={"test": True})
    results = store.search(emb, top_k=1)

    assert results
    entry, score = results[0]
    assert "text" in entry
    assert score <= 1.0
