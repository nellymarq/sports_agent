# memory_agent.py
# Upgraded long-term memory system:
# - episodic memory
# - semantic memory
# - vectorized memory (embeddings + vector store)
# - hybrid JSON + Markdown storage
# - safe fallback if embeddings unavailable
# - light metadata for better retrieval

import os
import json
from typing import Any, Dict, List, Optional

from state_manager import update_project_state

try:
    from embeddings.embedding_engine import EmbeddingEngine
    from embeddings.vector_store import VectorStore

    _embedding_engine = EmbeddingEngine()
    _vector_store = VectorStore()
except Exception as _init_err:
    import logging as _log
    _log.getLogger("memory_agent").debug(f"Embedding init failed: {_init_err}")
    _embedding_engine = None
    _vector_store = None


MEMORY_DIR = os.path.join(os.path.dirname(__file__), "memory")
MEMORY_MD = os.path.join(MEMORY_DIR, "memory.md")
MEMORY_JSON = os.path.join(MEMORY_DIR, "memory.json")

os.makedirs(MEMORY_DIR, exist_ok=True)

DEFAULT_MEMORY: Dict[str, Any] = {
    "episodic": [],
    "semantic": {},
}


def _ensure_files() -> None:
    """Ensure memory files exist with sane defaults."""
    if not os.path.exists(MEMORY_MD):
        with open(MEMORY_MD, "w", encoding="utf-8") as f:
            f.write("# UFC Agent Long-Term Memory\n\n")

    if not os.path.exists(MEMORY_JSON):
        with open(MEMORY_JSON, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_MEMORY, f, indent=2)


def _load_json() -> Dict[str, Any]:
    """Load JSON memory, falling back to a fresh default copy on error."""
    _ensure_files()
    try:
        with open(MEMORY_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return DEFAULT_MEMORY.copy()
            # Ensure required keys exist
            data.setdefault("episodic", [])
            data.setdefault("semantic", {})
            return data
    except Exception as _e:
        from logger import debug
        debug(f"Memory JSON load failed, using defaults: {_e}")
        return DEFAULT_MEMORY.copy()


def _save_json(data: Dict[str, Any]) -> None:
    """Persist JSON memory atomically."""
    tmp_path = f"{MEMORY_JSON}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, MEMORY_JSON)


def append_memory_entry(title: str, content: str) -> None:
    """Append a human-readable memory entry to the Markdown log."""
    _ensure_files()
    content = content.strip()
    if not content:
        return
    with open(MEMORY_MD, "a", encoding="utf-8") as f:
        f.write(f"## {title}\n\n")
        f.write(content + "\n\n")


def get_memory_text() -> str:
    """Return the full Markdown memory log as a string."""
    _ensure_files()
    with open(MEMORY_MD, "r", encoding="utf-8") as f:
        return f.read()


async def add_episodic(summary: str) -> None:
    """Store a short episodic summary and optionally embed it."""
    summary = summary.strip()
    if not summary:
        return

    data = _load_json()
    data["episodic"].append(summary)
    _save_json(data)

    if _embedding_engine and _vector_store:
        try:
            emb = _embedding_engine.embed(summary)
            _vector_store.add(
                text=summary,
                embedding=emb,
                metadata={"type": "episodic"},
            )
        except Exception as _e:
            from logger import debug
            debug(f"Episodic embedding failed (non-fatal): {_e}")


def get_recent_episodic(n: int = 5) -> List[str]:
    """Return the last n episodic summaries."""
    data = _load_json()
    return data.get("episodic", [])[-n:]


async def add_semantic(fighter: str, knowledge: str) -> None:
    """Store semantic knowledge keyed by fighter name and embed it."""
    fighter = fighter.lower().strip()
    knowledge = knowledge.strip()
    if not fighter or not knowledge:
        return

    data = _load_json()
    data["semantic"][fighter] = knowledge
    _save_json(data)

    if _embedding_engine and _vector_store:
        try:
            emb = _embedding_engine.embed(knowledge)
            _vector_store.add(
                text=knowledge,
                embedding=emb,
                metadata={
                    "type": "semantic",
                    "fighter": fighter,
                },
            )
        except Exception as _e:
            from logger import debug
            debug(f"Semantic embedding failed (non-fatal): {_e}")


def get_semantic(fighter: str) -> str:
    """Return stored semantic knowledge for a fighter, if any."""
    fighter = fighter.lower().strip()
    if not fighter:
        return ""
    data = _load_json()
    return data.get("semantic", {}).get(fighter, "")


def store_vectorized_memory(
    text: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Store arbitrary text in the vector store with optional metadata."""
    text = (text or "").strip()
    if not text:
        return

    if _embedding_engine is None or _vector_store is None:
        return

    metadata = metadata or {}

    try:
        emb = _embedding_engine.embed(text)
        _vector_store.add(
            text=text,
            embedding=emb,
            metadata=metadata,
        )
    except Exception as _e:
        from logger import debug
        debug(f"Vector store write failed (non-fatal): {_e}")
        return


async def summarize_and_store(
    llm,
    summary_prompt: str,
    context_chunks: List[str],
) -> None:
    """Summarize context into a compact episodic memory + Markdown entry."""
    _ensure_files()

    chunks = [c.strip() for c in context_chunks if c and c.strip()]
    if not chunks:
        return

    joined = "\n\n---\n\n".join(chunks)
    messages = [
        {
            "role": "system",
            "content": (
                "You are a summarization assistant for a UFC analytics agent. "
                "Your job is to create concise, information-dense summaries "
                "that will be stored as long-term memory. "
                "Avoid speculation; focus on stable, reusable insights."
            ),
        },
        {
            "role": "user",
            "content": f"{summary_prompt}\n\nContext:\n{joined}",
        },
    ]

    summary_msg = await llm.chat(messages)
    summary = (summary_msg.content or "").strip()
    if not summary:
        return

    append_memory_entry("Session Summary", summary)
    await add_episodic(summary)

    update_project_state({"last_memory_update": "ok"})
