# devtools/inspect_embeddings.py

# --- Universal project root bootstrap ---
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
# ----------------------------------------

from embeddings.embedding_engine import EmbeddingEngine
from embeddings.vector_store import VectorStore
import sys


def main():
    engine = EmbeddingEngine()
    store = VectorStore()

    print(f"Vector store entries: {len(store.store)}")

    if len(sys.argv) == 1:
        for i, entry in enumerate(store.store[:5]):
            print(f"\n[{i}] text: {entry['text'][:120]}...")
            print(f"    metadata: {entry.get('metadata', {})}")
        return

    query = " ".join(sys.argv[1:])
    print(f"\nQuery: {query}")

    query_embedding = engine.embed(query)
    results = store.search(query_embedding, top_k=5)

    for i, (entry, score) in enumerate(results):
        print(f"\nResult {i} (score={score:.4f}):")
        print(f"  text: {entry['text'][:200]}...")
        print(f"  metadata: {entry.get('metadata', {})}")


if __name__ == "__main__":
    main()
