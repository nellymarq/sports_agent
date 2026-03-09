# retrieval_agent.py
# Retrieval layer that now surfaces next UFC event + main event fighters
# while remaining 100% backward-compatible (returns a plain string summary).

from typing import List, Tuple, Optional, Any

from logger import info, error, debug
from event_utils import get_unified_next_event
from fighter_utils import extract_canonical_fighters


async def _build_event_context() -> Tuple[Optional[dict], str]:
    """
    Fetch the next scheduled UFC event (if any) and build a short textual summary.
    """
    try:
        event = await get_unified_next_event()
    except Exception as e:
        error(f"retrieval_agent: get_unified_next_event failed: {e}")
        return None, ""

    if not event:
        return None, ""

    name = event.get("name") or "Unknown event"
    date = event.get("date") or "Unknown date"
    location = event.get("location") or "Unknown location"
    main_event = event.get("main_event") or ""
    co_main = event.get("co_main_event") or ""

    lines: List[str] = []
    lines.append(f"Next scheduled UFC event: {name}")
    lines.append(f"Date: {date}")
    lines.append(f"Location: {location}")

    if main_event:
        lines.append(f"Main event: {main_event}")
    if co_main:
        lines.append(f"Co-main event: {co_main}")

    return event, "\n".join(lines)


async def retrieval_agent(
    llm: Any,
    user_input: str,
    history,
    semantic_memory,
    episodic_memory,
) -> str:
    """
    Backward-compatible retrieval agent.

    Previously: returned a plain string summary.
    Now: still returns a string, but that string includes:
      - extracted fighters from the question (canonical IDs)
      - next UFC event metadata (if available)
      - main event / co-main event text

    This gives downstream agents enough context to lock onto the
    next main event without changing any call signatures.
    """
    info("Retrieval agent invoked")

    # 1) Extract fighters directly from the user question
    fighters, primary = extract_canonical_fighters(user_input)
    debug(f"retrieval_agent: extracted fighters={fighters}, primary={primary}")

    fighter_lines: List[str] = []
    if fighters:
        fighter_lines.append("Fighters extracted from question (canonical IDs):")
        for f in fighters:
            fighter_lines.append(f"- {f}")
    else:
        fighter_lines.append("No clear fighters extracted from the question.")

    # 2) Fetch next scheduled UFC event
    event, event_block = await _build_event_context()

    # 3) Build final retrieval summary string
    sections: List[str] = []

    sections.append("=== QUERY ===")
    sections.append(user_input.strip())

    sections.append("\n=== FIGHTER EXTRACTION ===")
    sections.append("\n".join(fighter_lines))

    sections.append("\n=== NEXT UFC EVENT CONTEXT ===")
    if event_block:
        sections.append(event_block)
    else:
        sections.append("No upcoming UFC event could be resolved from local data.")

    summary = "\n".join(sections).strip()

    debug(f"retrieval_agent summary preview: {summary[:400]}...")
    return summary
