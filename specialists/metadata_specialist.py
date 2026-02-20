from specialists.tool_runtime import (
    build_system_prompt,
    run_tool_loop
)

BASE_PROMPT = """You are the Metadata Specialist.  
Your role is to provide factual, structural, and contextual information about the matchup.

Provide:
- Height, reach, age
- Stance, gym, camp changes
- Record, streaks, layoffs
- Fight location, cage size, altitude
- Any logistical or contextual factors

End with a short paragraph summarizing how metadata shapes the matchup."""
PROFILE = """Focus on:
- Verified physical stats
- Training camp context
- Environmental factors
- Career stage and mileage"""

async def run_metadata_specialist(llm, tool_registry, user_input, history, retrieved_context, semantic_memory=None, episodic_memory=None):
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
