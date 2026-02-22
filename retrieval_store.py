# retrieval_store.py
# Simple in-memory retrieval store (used for debugging / local experiments).

from typing import List, Dict, Any


class RetrievalStore:
    """
    Lightweight in-process document store.

    This is intentionally simple and non-persistent; the real retrieval
    pipeline should use embeddings + VectorStore. This is mainly useful
    for tests, debugging, or small ad-hoc experiments.
    """

    def __init__(self) -> None:
        self.docs: List[Dict[str, Any]] = []

    def add_document(self, text: str, metadata: Dict[str, Any]) -> None:
        text = (text or "").strip()
        if not text:
            return
        self.docs.append({"text": text, "metadata": metadata or {}})

    def get_all(self) -> List[Dict[str, Any]]:
        return list(self.docs)
