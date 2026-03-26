# retrieval_agent.py
# Retrieval layer that now surfaces next UFC event + main event fighters
# while remaining 100% backward-compatible (returns a plain string summary).

from typing import List, Tuple, Optional, Any

from logger import info, error, debug
from event_utils import get_unified_next_event, get_event_fighters
from fighter_utils import extract_fighters


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
    main_event = event.get("main_event") or {}
    co_main = event.get("co_main_event") or {}

    lines: List[str] = []
    lines.append(f"Next scheduled UFC event: {name}")
    lines.append(f"Date: {date}")
    lines.append(f"Location: {location}")

    # Format main event
    if isinstance(main_event, dict) and main_event.get("fighters"):
        me_fighters = main_event["fighters"]
        if isinstance(me_fighters, list) and len(me_fighters) >= 2:
            lines.append(f"Main event: {me_fighters[0]} vs {me_fighters[1]}")
            wc = main_event.get("weight_class", "")
            if wc:
                lines.append(f"  Weight class: {wc}")
            if main_event.get("is_title_fight"):
                lines.append("  Title fight: Yes")
    elif isinstance(main_event, str) and main_event:
        lines.append(f"Main event: {main_event}")

    if isinstance(co_main, dict) and co_main.get("fighters"):
        cm_fighters = co_main["fighters"]
        if isinstance(cm_fighters, list) and len(cm_fighters) >= 2:
            lines.append(f"Co-main event: {cm_fighters[0]} vs {cm_fighters[1]}")
    elif isinstance(co_main, str) and co_main:
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
    fighters, primary = extract_fighters(user_input)
    debug(f"retrieval_agent: extracted fighters={fighters}, primary={primary}")

    # 1b) If no fighters found in text, try to derive from event mention
    if not fighters:
        import re
        m = re.search(r"ufc[\s_\-]*([0-9]{2,4})", user_input.lower())
        if m:
            event_id = f"ufc_{m.group(1)}"
            event_fighters = get_event_fighters(event_id)
            if event_fighters:
                fighters = event_fighters
                primary = fighters[0]
                debug(f"retrieval_agent: derived fighters from event {event_id}: {fighters}")

    # 2) Fetch next scheduled UFC event
    event, event_block = await _build_event_context()

    # 1c) If still no fighters, derive from the next event's main event
    if not fighters and event:
        main_ev = event.get("main_event") or {}
        if isinstance(main_ev, dict):
            me_fighters = main_ev.get("fighters", [])
            derived = [
                (f if isinstance(f, str) else f.get("name", ""))
                for f in me_fighters
            ]
            derived = [n for n in derived if n]
            if len(derived) >= 2:
                fighters = derived
                primary = derived[0]
                debug(f"retrieval_agent: derived fighters from next event: {fighters}")

    fighter_lines: List[str] = []
    if fighters:
        fighter_lines.append("Fighters identified:")
        for f in fighters:
            fighter_lines.append(f"- {f}")
    else:
        fighter_lines.append("No clear fighters extracted from the question.")

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
