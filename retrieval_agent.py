# retrieval_agent.py

from typing import List, Tuple
from logger import info, debug, error
from retrieval_store import load_documents


async def retrieval_agent(
    llm,
    user_input: str,
    history: List[Tuple[str, str]],
    semantic_memory=None,
    episodic_memory=None,
) -> str:
    """
    Retrieval agent that looks at:
    - recent conversation history
    - external knowledge documents in data/knowledge
    """

    info("Retrieval agent invoked")

    # ---- HISTORY SLICE ----
    if not history:
        debug("Retrieval agent: no history available")
        history_text = ""
    else:
        recent = history[-20:]
        history_text = "\n".join(f"{role}: {content}" for role, content in recent)

    # ---- DOCUMENTS FROM DISK ----
    docs = load_documents()
    if not docs:
        debug("Retrieval agent: no external documents loaded")
        docs_text = ""
    else:
        docs_text = "\n\n".join(
            f"FILE: {name}\n{content}" for name, content in docs
        )

    system_prompt = """
You are a retrieval helper for a UFC analytics system.

You are given:
- The current user question
- A recent slice of conversation history (may be empty)
- A set of external knowledge documents (may be empty)

Your job:
- Identify any prior messages or document snippets that seem directly relevant
  to answering the current question.
- Summarize that relevant context in 3–6 concise bullet points.
- If nothing is clearly relevant, return an empty summary.

Respond with plain text only.
"""

    user_prompt = f"""
Current user question:
{user_input}

Recent history:
{history_text}

External knowledge documents:
{docs_text}
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        reply = await llm.chat(messages)
        summary = reply.strip()
        debug(f"Retrieval agent summary preview: {summary[:200]}...")
        return summary
    except Exception as e:
        error(f"Retrieval agent LLM error: {e}")
        return ""
