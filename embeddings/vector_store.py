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

    def add(self, text: str, embedding: List[float], metadata: Dict[str, Any]):
        entry = {
            "text": text,
            "embedding": embedding,
            "metadata": metadata,
        }
        self.store.append(entry)
        VECTOR_STORE_PATH.write_text(json.dumps(self.store, indent=2))

    def search(self, query_embedding: List[float], top_k: int = 5):
        def cosine(a, b):
            a = np.array(a)
            b = np.array(b)
            denom = float(np.linalg.norm(a) * np.linalg.norm(b)) or 1.0
            return float(np.dot(a, b) / denom)

        scored = [
            (entry, cosine(query_embedding, entry["embedding"]))
            for entry in self.store
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]
