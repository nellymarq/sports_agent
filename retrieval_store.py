# retrieval_store.py
# Simple in-memory retrieval store (used for debugging / local experiments).

from typing import List, Dict, Any, Tuple


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


# Global in-memory store instance
_STORE = RetrievalStore()


def get_store() -> RetrievalStore:
    """
    Return the global in-memory retrieval store.

    Other parts of the system can do:
        from retrieval_store import get_store
        store = get_store()
        store.add_document("some text", {"source": "manual"})
    """
    return _STORE


def load_documents() -> List[Tuple[str, str]]:
    """
    Adapter for retrieval_agent:

    Returns a list of (name, content) tuples.

    Currently, we synthesize simple names like 'doc_0', 'doc_1', ...
    based on the in-memory store contents.
    """
    docs = _STORE.get_all()
    result: List[Tuple[str, str]] = []
    for idx, d in enumerate(docs):
        text = (d.get("text") or "").strip()
        if not text:
            continue
        name = d.get("metadata", {}).get("name") or f"doc_{idx}"
        result.append((name, text))
    return result
