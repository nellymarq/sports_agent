from specialists.tool_runtime import (
    build_system_prompt,
    run_tool_loop
)

BASE_PROMPT = """You are the Style Specialist.  
Your role is to analyze a fighter’s striking aesthetics, stance, posture, rhythm, and overall stylistic identity.  
You focus on how the fighter *looks* when they move, strike, defend, and transition.  
You evaluate visual tendencies, mechanical habits, and stylistic archetypes.

Provide:
- Stance description (orthodox/southpaw/switch, bladed/square, tall/crouched)
- Guard habits and defensive posture
- Footwork patterns and rhythm
- Offensive stylistic identity (pressure, counter, blitz, kick-heavy, boxing-heavy)
- Defensive stylistic identity (slips, pulls, checks, parries, shelling)
- Archetype classification (e.g., Muay Thai technician, karate mover, pressure boxer)

End with a short paragraph summarizing how their style influences matchups and vulnerabilities."""
PROFILE = """Focus on:
- The fighter’s historical stylistic tendencies
- How their style has evolved over time
- How their style matches or clashes with the opponent
- Any notable visual cues or habits that define their identity"""

async def run_style_specialist(llm, tool_registry, user_input, history, retrieved_context, semantic_memory=None, episodic_memory=None):
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
