# tests/test_embeddings.py
# Unit tests for embedding engine and vector store.

import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import uuid
import numpy as np
from embeddings.embedding_engine import get_embedding, EmbeddingEngine, _hash_to_vector
from embeddings.vector_store import VectorStore


class TestEmbeddingEngine:
    def test_returns_list_of_floats(self):
        emb = get_embedding("test")
        assert isinstance(emb, list)
        assert all(isinstance(x, float) for x in emb)

    def test_dimension_384(self):
        emb = get_embedding("test query")
        assert len(emb) == 384

    def test_normalized(self):
        emb = get_embedding("normalize test")
        norm = np.linalg.norm(emb)
        assert abs(norm - 1.0) < 0.05  # approximately unit norm

    def test_deterministic(self):
        emb1 = get_embedding("same text")
        emb2 = get_embedding("same text")
        assert emb1 == emb2

    def test_different_texts_different_embeddings(self):
        emb1 = get_embedding("Alex Pereira striking")
        emb2 = get_embedding("best pizza recipe")
        assert emb1 != emb2

    def test_semantic_similarity(self):
        emb1 = get_embedding("UFC fighter knockout power")
        emb2 = get_embedding("MMA striking knockout ability")
        emb3 = get_embedding("chocolate cake recipe baking")

        def cosine(a, b):
            a, b = np.array(a), np.array(b)
            return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

        sim_related = cosine(emb1, emb2)
        sim_unrelated = cosine(emb1, emb3)
        assert sim_related > sim_unrelated

    def test_engine_class_interface(self):
        engine = EmbeddingEngine()
        emb = engine.embed("test")
        assert len(emb) == 384

    def test_hash_fallback_works(self):
        vec = _hash_to_vector("test", dim=384)
        assert len(vec) == 384
        norm = np.linalg.norm(vec)
        assert abs(norm - 1.0) < 0.01


class TestVectorStore:
    def _fresh_store(self):
        """Return a vector store (shared across tests via cache file)."""
        return VectorStore()

    def test_add_and_search(self):
        store = self._fresh_store()
        text = f"vector store test {uuid.uuid4().hex[:8]}"
        emb = get_embedding(text)
        store.add(text, emb, {"test": True})
        results = store.search(emb, top_k=1)
        assert len(results) >= 1
        entry, score = results[0]
        assert score > 0.9

    def test_deduplication(self):
        store = self._fresh_store()
        text = f"dedup test {uuid.uuid4().hex[:8]}"
        emb = get_embedding(text)
        initial_count = store.count()
        store.add(text, emb, {"v": 1})
        store.add(text, emb, {"v": 2})  # duplicate
        assert store.count() == initial_count + 1

    def test_dimension_mismatch_skipped(self):
        store = self._fresh_store()
        text = f"dim test {uuid.uuid4().hex[:8]}"
        # Add with wrong dimension
        store.store.append({"text": text, "embedding": [0.1] * 128, "metadata": {}})
        store._text_index.add(text)
        # Search with 384-dim
        query = get_embedding("dim test")
        results = store.search(query, top_k=100)
        # The 128-dim entry should not appear
        for entry, score in results:
            assert len(entry["embedding"]) == 384

    def test_min_score_filter(self):
        store = self._fresh_store()
        text = f"min score test {uuid.uuid4().hex[:8]}"
        emb = get_embedding(text)
        store.add(text, emb, {})
        results = store.search(emb, top_k=10, min_score=0.99)
        # Perfect match should still appear
        assert len(results) >= 1

    def test_batch_add(self):
        store = self._fresh_store()
        initial = store.count()
        items = []
        for i in range(3):
            text = f"batch item {uuid.uuid4().hex[:8]}"
            emb = get_embedding(text)
            items.append({"text": text, "embedding": emb, "metadata": {"batch": i}})
        store.add_batch(items)
        assert store.count() == initial + 3

    def test_count(self):
        store = self._fresh_store()
        assert isinstance(store.count(), int)
        assert store.count() >= 0

    def test_empty_search(self):
        # Search on store with potentially no matching dimension
        store = VectorStore()
        results = store.search([0.0] * 999, top_k=5)
        # Should return empty (no 999-dim entries)
        assert results == []
