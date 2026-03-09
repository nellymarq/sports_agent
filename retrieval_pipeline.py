# retrieval_pipeline.py
# Vector-store retrieval for UFC agent, with fighter-aware filtering.

from typing import Optional, List
from embeddings.embedding_engine import get_embedding
from embeddings.vector_store import VectorStore


def get_retrieved_context(
    user_input: str,
    fighter: Optional[str] = None,
    top_k: int = 5,
) -> str:
    """
    Retrieve relevant context from the vector store for a given query.

    - If fighter is provided, we prefer entries whose metadata matches that fighter.
    - Falls back gracefully if no results or embeddings are available.
    """
    user_input = (user_input or "").strip()
    if not user_input:
        return ""

    try:
        store = VectorStore()
        query_emb = get_embedding(user_input)
        results = store.search(query_emb, top_k=top_k) or []
    except Exception:
        return ""

    if not results:
        return ""

    fighter_norm = fighter.lower().strip() if fighter else None
    lines: List[str] = []

    for entry, score in results:
        meta = entry.get("metadata", {}) or {}

        # Align with memory_agent semantic metadata: "fighter" / "primary_fighter"
        if fighter_norm:
            meta_fighter = (meta.get("fighter") or meta.get("primary_fighter") or "").lower().strip()
            if meta_fighter and meta_fighter != fighter_norm:
                continue

        text = (entry.get("text") or "").strip()
        if not text:
            continue

        lines.append(f"[score={score:.3f}] {text}")

    return "\n".join(lines)
