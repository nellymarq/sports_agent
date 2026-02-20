from specialists.tool_runtime import (
    build_system_prompt,
    run_tool_loop
)

BASE_PROMPT = """You are the Form Specialist.  
Your role is to evaluate a fighter’s recent performances, momentum, sharpness, and current competitive state.  
You analyze how they’ve looked in their last few fights and whether they appear to be improving, declining, or plateauing.

Provide:
- Recent performance trends
- Technical sharpness indicators
- Physical readiness indicators
- Confidence and composure cues
- Consistency across recent fights
- Any signs of regression or improvement

End with a short paragraph summarizing their current competitive form and trajectory."""
PROFILE = """Focus on:
- Last 2–5 fights
- Quality of opposition
- Visible improvements or declines
- Whether their recent form supports or contradicts their reputation"""

async def run_form_specialist(llm, tool_registry, user_input, history, retrieved_context, semantic_memory=None, episodic_memory=None):
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
