from specialists.tool_runtime import (
    build_system_prompt,
    run_tool_loop
)

BASE_PROMPT = """You are the {NAME} Specialist..."""
PROFILE = """(Your fighter profile block here)"""

async def run_{NAME}_specialist(llm, tool_registry, user_input, history, retrieved_context):
    messages = build_system_prompt(
        BASE_PROMPT,
        PROFILE,
        retrieved_context,
        tool_registry.keys()
    )

    for h in history:
        if isinstance(h, dict) and "role" in h and "content" in h:
            messages.append(h)
        else:
            messages.append({
                "role": "user",
                "content": str(h)
            })

    messages.append({"role": "user", "content": user_input})

    return await run_tool_loop(llm, messages, tool_registry)
