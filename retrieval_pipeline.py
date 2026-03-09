# retrieval_pipeline.py
# Vector-store retrieval for UFC agent, with multi-fighter search.

from typing import Optional, List
from embeddings.embedding_engine import get_embedding
from embeddings.vector_store import VectorStore


def get_retrieved_context(
    user_input: str,
    fighter: Optional[str] = None,
    fighters: Optional[List[str]] = None,
    top_k: int = 5,
) -> str:
    """
    Retrieve relevant context from the vector store.

    - Searches for the user query first
    - If multiple fighters provided, searches for each fighter individually
    - Deduplicates and ranks by relevance score
    """
    user_input = (user_input or "").strip()
    if not user_input:
        return ""

    try:
        store = VectorStore()
    except Exception:
        return ""

    all_fighters = list(fighters or [])
    if fighter and fighter not in all_fighters:
        all_fighters.append(fighter)

    # Query 1: the full user input
    seen_texts = set()
    scored_lines: List[tuple] = []  # (score, line)

    try:
        query_emb = get_embedding(user_input)
        results = store.search(query_emb, top_k=top_k) or []
        for entry, score in results:
            text = (entry.get("text") or "").strip()
            if text and text not in seen_texts:
                seen_texts.add(text)
                scored_lines.append((score, f"[score={score:.3f}] {text}"))
    except Exception:
        pass

    # Query 2+: individual fighter name searches
    for f in all_fighters:
        f = (f or "").strip()
        if not f or f == "unknown":
            continue
        try:
            f_emb = get_embedding(f)
            results = store.search(f_emb, top_k=3) or []
            for entry, score in results:
                text = (entry.get("text") or "").strip()
                if text and text not in seen_texts:
                    # Check metadata alignment
                    meta = entry.get("metadata", {}) or {}
                    meta_fighter = (
                        meta.get("fighter") or meta.get("primary_fighter") or ""
                    ).lower().strip()
                    if meta_fighter and meta_fighter != f.lower():
                        continue
                    seen_texts.add(text)
                    scored_lines.append((score, f"[score={score:.3f}] {text}"))
        except Exception:
            continue

    # Sort by score (lower = more similar for cosine distance)
    scored_lines.sort(key=lambda x: x[0])

    return "\n".join(line for _, line in scored_lines[:top_k * 2])
