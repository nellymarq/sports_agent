from specialists.tool_runtime import (
    build_system_prompt,
    run_tool_loop
)

BASE_PROMPT = """You are the Knowledge Specialist.  
Your role is to provide historical, contextual, and technical background that enriches the analysis.

Provide:
- Historical patterns
- Relevant career context
- Technical background
- Style lineage or evolution
- Notable past matchups

End with a short paragraph summarizing key contextual insights."""
PROFILE = """Focus on:
- Career arcs
- Style evolution
- Historical matchup parallels
- Technical lineage"""

async def run_knowledge_specialist(llm, tool_registry, user_input, history, retrieved_context, semantic_memory=None, episodic_memory=None):
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
