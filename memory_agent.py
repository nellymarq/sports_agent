# memory_agent.py
# Upgraded long-term memory system: episodic + semantic + retrieval

import os
import json
from typing import Any, Dict, List

from state_manager import update_project_state

MEMORY_DIR = os.path.join(os.path.dirname(__file__), "memory")
MEMORY_MD = os.path.join(MEMORY_DIR, "memory.md")
MEMORY_JSON = os.path.join(MEMORY_DIR, "memory.json")

os.makedirs(MEMORY_DIR, exist_ok=True)

DEFAULT_MEMORY = {
    "episodic": [],        # chronological summaries
    "semantic": {},        # fighter → long-term knowledge
}


def _ensure_files():
    """Ensure both markdown and JSON memory files exist."""
    if not os.path.exists(MEMORY_MD):
        with open(MEMORY_MD, "w", encoding="utf-8") as f:
            f.write("# UFC Agent Long-Term Memory\n\n")

    if not os.path.exists(MEMORY_JSON):
        with open(MEMORY_JSON, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_MEMORY, f, indent=2)


def _load_json() -> Dict[str, Any]:
    _ensure_files()
    try:
        with open(MEMORY_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_MEMORY.copy()


def _save_json(data: Dict[str, Any]):
    with open(MEMORY_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def append_memory_entry(title: str, content: str) -> None:
    """Append to the human-readable markdown memory."""
    _ensure_files()
    with open(MEMORY_MD, "a", encoding="utf-8") as f:
        f.write(f"## {title}\n\n")
        f.write(content.strip() + "\n\n")


def get_memory_text() -> str:
    """Return the full markdown memory."""
    _ensure_files()
    with open(MEMORY_MD, "r", encoding="utf-8") as f:
        return f.read()


async def add_episodic(summary: str):
    """Store a short episodic memory entry."""
    data = _load_json()
    data["episodic"].append(summary.strip())
    _save_json(data)


async def add_semantic(fighter: str, knowledge: str):
    """Store long-term fighter-specific knowledge."""
    fighter = fighter.lower().strip()
    data = _load_json()
    data["semantic"][fighter] = knowledge.strip()
    _save_json(data)


def get_semantic(fighter: str) -> str:
    """Retrieve long-term fighter knowledge."""
    fighter = fighter.lower().strip()
    data = _load_json()
    return data["semantic"].get(fighter, "")


def get_recent_episodic(n: int = 5) -> List[str]:
    """Retrieve the last N episodic memories."""
    data = _load_json()
    return data["episodic"][-n:]


async def summarize_and_store(llm, summary_prompt: str, context_chunks: List[str]) -> None:
    """
    Summarize the session and store it as episodic memory.
    Also append to markdown for human readability.
    """
    _ensure_files()

    joined = "\n\n---\n\n".join(context_chunks)
    messages = [
        {
            "role": "system",
            "content": (
                "You are a summarization assistant for a UFC analytics agent. "
                "Your job is to create concise, information-dense summaries "
                "that will be stored as long-term memory."
            ),
        },
        {
            "role": "user",
            "content": f"{summary_prompt}\n\nContext:\n{joined}",
        },
    ]

    summary_msg = await llm.chat(messages)
    summary = summary_msg.content.strip()

    # Store in both memory formats
    append_memory_entry("Session Summary", summary)
    await add_episodic(summary)

    update_project_state({"last_memory_update": "ok"})
