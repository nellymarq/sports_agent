from specialists.tool_runtime import (
    build_system_prompt,
    run_tool_loop
)

BASE_PROMPT = """You are the Weightcut Specialist.  
Your role is to analyze a fighter’s weight‑cutting history, physical durability during cuts, and any patterns of struggle or success.

Provide:
- Historical weight‑cut performance
- Signs of difficult or easy cuts
- Durability and cardio impact from cuts
- Division suitability (too big, too small, optimal)
- Any red flags from past weigh‑ins

End with a short paragraph summarizing how the weight cut may affect performance."""
PROFILE = """Focus on:
- Past weigh‑in footage and outcomes
- Reported issues or smooth cuts
- Body composition and frame size
- Division changes and their effects"""

async def run_weightcut_specialist(llm, tool_registry, user_input, history, retrieved_context, semantic_memory=None, episodic_memory=None):
    memory_block = ""
    if semantic_memory:
        memory_block += f"\n\nLong-term fighter knowledge:\n{semantic_memory}"
    if episodic_memory:
        memory_block += "\n\nRecent session summaries:\n" + "\n".join(episodic_memory)

    messages = build_system_prompt(
        BASE_PROMPT + memory_block,
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
