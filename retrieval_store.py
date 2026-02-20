# retrieval_store.py

import os
from typing import List, Tuple
from logger import info, debug, error

# Path: sports_agent/data/knowledge
DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "knowledge")


def load_documents() -> List[Tuple[str, str]]:
    """
    Load all text-like documents from data/knowledge.

    Returns a list of (filename, content).
    """
    docs: List[Tuple[str, str]] = []

    # Ensure the directory exists
    if not os.path.isdir(DATA_DIR):
        info(f"[RetrievalStore] DATA_DIR does not exist: {DATA_DIR}")
        return docs

    # Iterate through all files in the folder
    for fname in os.listdir(DATA_DIR):
        path = os.path.join(DATA_DIR, fname)

        # Skip non-files (e.g., subfolders)
        if not os.path.isfile(path):
            continue

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            docs.append((fname, content))
        except Exception as e:
            error(f"[RetrievalStore] Error reading document {path}: {e}")

    # Logging for visibility
    info(f"[RetrievalStore] Loaded {len(docs)} documents from {DATA_DIR}")
    debug(f"[RetrievalStore] Document names: {[name for name, _ in docs]}")

    return docs
