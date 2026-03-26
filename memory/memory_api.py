# memory/memory_api.py

from __future__ import annotations
from typing import List, Dict, Any
from data.metadata import Evidence, SCHEMA_VERSION
import math
import time
import hashlib


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a)) or 1.0
    norm_b = math.sqrt(sum(x * x for x in b)) or 1.0
    return dot / (norm_a * norm_b)


def _get_embedding_fn():
    """Lazy import of embedding engine; returns None if only hash fallback."""
    try:
        import embeddings.embedding_engine as _ee
        _ee._get_model()  # trigger lazy init
        if not _ee._USE_REAL_EMBEDDINGS:
            return None
        return _ee.get_embedding
    except Exception:
        return None


class MemoryStore:
    def __init__(self):
        self.long_term: List[Dict[str, Any]] = []
        self.short_term: List[Dict[str, Any]] = []
        self.evidence: List[Evidence] = []
        self.specialist_notes: Dict[str, List[Dict[str, Any]]] = {}

    def write_long_term(self, item: Dict[str, Any]):
        item["timestamp"] = time.time()
        item["schema_version"] = SCHEMA_VERSION
        item["hash"] = _hash(str(item))
        self.long_term.append(item)

    def write_short_term(self, item: Dict[str, Any]):
        item["timestamp"] = time.time()
        item["schema_version"] = SCHEMA_VERSION
        self.short_term.append(item)

    def write_evidence(self, ev: Evidence):
        self.evidence.append(ev)

    def write_specialist_note(self, specialist: str, note: Dict[str, Any]):
        note["timestamp"] = time.time()
        note["schema_version"] = SCHEMA_VERSION
        if specialist not in self.specialist_notes:
            self.specialist_notes[specialist] = []
        self.specialist_notes[specialist].append(note)

    def get_recent_short_term(self, limit: int = 10) -> List[Dict[str, Any]]:
        return sorted(self.short_term, key=lambda x: x["timestamp"], reverse=True)[:limit]

    def get_long_term(self) -> List[Dict[str, Any]]:
        return self.long_term

    def get_evidence(self) -> List[Evidence]:
        return self.evidence

    def get_specialist_history(self, specialist: str) -> List[Dict[str, Any]]:
        return self.specialist_notes.get(specialist, [])

    def find_similar(self, text: str, threshold: float = 0.8) -> List[Dict[str, Any]]:
        """Return long-term entries whose content is semantically similar to *text*.

        Uses cosine similarity over embeddings when the embedding engine is
        available; falls back to substring overlap otherwise.
        """
        if not self.long_term:
            return []

        embed = _get_embedding_fn()
        if embed is None:
            # Fallback: simple case-insensitive substring matching
            lower = text.lower()
            return [
                item for item in self.long_term
                if lower in str(item.get("content", item.get("text", ""))).lower()
            ]

        query_vec = embed(text)
        results = []
        for item in self.long_term:
            item_text = str(item.get("content", item.get("text", "")))
            if not item_text:
                continue
            item_vec = embed(item_text)
            score = _cosine_similarity(query_vec, item_vec)
            if score >= threshold:
                results.append({**item, "_similarity": round(score, 4)})

        results.sort(key=lambda x: x.get("_similarity", 0), reverse=True)
        return results

    def cluster_topics(self) -> Dict[str, List[Dict[str, Any]]]:
        """Group long-term memories by their metadata type or inferred topic."""
        clusters: Dict[str, List[Dict[str, Any]]] = {}
        for item in self.long_term:
            topic = item.get("type") or item.get("topic") or "general"
            clusters.setdefault(topic, []).append(item)
        return clusters

    def dedupe_long_term(self):
        seen = set()
        unique = []
        for item in self.long_term:
            if item["hash"] not in seen:
                seen.add(item["hash"])
                unique.append(item)
        self.long_term = unique

    def decay_long_term(self, threshold_seconds: float):
        now = time.time()
        self.long_term = [
            item for item in self.long_term
            if now - item["timestamp"] < threshold_seconds
        ]

    def decay_short_term(self, threshold_seconds: float = 86400):
        """Remove short-term memories older than threshold (default 24h)."""
        now = time.time()
        self.short_term = [
            item for item in self.short_term
            if now - item.get("timestamp", 0) < threshold_seconds
        ]

    def cap_long_term(self, max_entries: int = 500):
        """Keep only the most recent N long-term entries."""
        if len(self.long_term) > max_entries:
            self.long_term.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
            self.long_term = self.long_term[:max_entries]
