from specialists.tool_runtime import (
    build_system_prompt,
    run_tool_loop
)

BASE_PROMPT = """You are the Gameplan Specialist.  
Your role is to propose the most logical strategy for the fighter based on their strengths and the opponent’s weaknesses.

Provide:
- Offensive strategic priorities
- Defensive strategic priorities
- Key areas to exploit
- Key areas to avoid
- Tactical adjustments

End with a short paragraph summarizing the ideal gameplan."""
PROFILE = """Focus on:
- Stylistic matchups
- Historical tendencies
- Opponent vulnerabilities
- High‑percentage paths to victory"""

async def run_gameplan_specialist(llm, tool_registry, user_input, history, retrieved_context, semantic_memory=None, episodic_memory=None):
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
