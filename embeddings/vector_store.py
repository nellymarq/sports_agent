# embeddings/vector_store.py

import json
from pathlib import Path
from typing import List, Dict, Any
import numpy as np

VECTOR_STORE_PATH = Path("cache/vector_store.json")


class VectorStore:
    def __init__(self):
        VECTOR_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not VECTOR_STORE_PATH.exists():
            VECTOR_STORE_PATH.write_text(json.dumps([]))
        self.store = json.loads(VECTOR_STORE_PATH.read_text())
        self._text_index = {entry["text"] for entry in self.store if "text" in entry}

    def _persist(self):
        VECTOR_STORE_PATH.write_text(json.dumps(self.store, indent=2))

    def add(self, text: str, embedding: List[float], metadata: Dict[str, Any]):
        if text in self._text_index:
            return  # skip duplicates
        entry = {
            "text": text,
            "embedding": embedding,
            "metadata": metadata,
        }
        self.store.append(entry)
        self._text_index.add(text)
        self._persist()

    def add_batch(self, items: List[Dict[str, Any]]):
        added = False
        for item in items:
            text = item.get("text", "")
            if text in self._text_index:
                continue
            self.store.append(item)
            self._text_index.add(text)
            added = True
        if added:
            self._persist()

    def search(self, query_embedding: List[float], top_k: int = 5, min_score: float = 0.0) -> List:
        if not self.store:
            return []

        q = np.array(query_embedding, dtype=np.float32)
        q_dim = len(q)
        q_norm = float(np.linalg.norm(q)) or 1.0

        scored = []
        for entry in self.store:
            emb = entry.get("embedding", [])
            if len(emb) != q_dim:
                continue  # skip dimension-mismatched entries (e.g. old 128-dim)
            e = np.array(emb, dtype=np.float32)
            e_norm = float(np.linalg.norm(e)) or 1.0
            score = float(np.dot(q, e) / (q_norm * e_norm))
            if score >= min_score:
                scored.append((entry, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def count(self) -> int:
        return len(self.store)
