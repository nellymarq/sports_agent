# critic_agent.py
# Chunked critic pipeline for large multi-specialist outputs

from logger import info, debug, error

CRITIC_SYSTEM_PROMPT = """
You are the final-stage critic for a multi-specialist UFC analytics engine.
Your job is to refine clarity, cohesion, and flow without changing meaning.
Do not add new facts. Do not remove meaningful analysis.
"""

CHUNK_SIZE = 3500  # safe for Groq 8B models


def chunk_text(text: str, size: int = CHUNK_SIZE):
    """Split text into safe-sized chunks."""
    return [text[i:i + size] for i in range(0, len(text), size)]


async def _critic_pass(llm, text: str) -> str:
    """Run a single critic pass on a chunk or full text."""
    messages = [
        {"role": "system", "content": CRITIC_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Refine the following analysis. Improve clarity, flow, and transitions "
                "without changing meaning:\n\n" + text
            ),
        },
    ]

    msg = await llm.chat(messages)
    return msg.content.strip()


async def critic_review(
    llm,
    coordinator_output: str,
    semantic_memory=None,
    episodic_memory=None,
) -> str:
    """
    Chunked critic pipeline:
    1. Split merged output into chunks
    2. Critic-polish each chunk
    3. Merge polished chunks
    4. Final critic pass on the combined text
    """

    info("Critic agent invoked")

    if not coordinator_output or not coordinator_output.strip():
        error("Critic received empty coordinator output")
        return "No content available for final review."

    # Step 1: Chunk the merged output
    chunks = chunk_text(coordinator_output)
    debug(f"Critic: splitting into {len(chunks)} chunks")

    polished_chunks = []

    # Step 2: Critic each chunk individually
    for idx, chunk in enumerate(chunks):
        info(f"Critic: refining chunk {idx + 1}/{len(chunks)}")
        try:
            refined = await _critic_pass(llm, chunk)
            polished_chunks.append(refined)
        except Exception as e:
            error(f"Critic chunk {idx + 1} failed: {e}")
            polished_chunks.append(chunk)

    # Step 3: Merge polished chunks
    merged_polished = "\n\n".join(polished_chunks)

    # Step 4: Final critic pass for cohesion
    info("Critic: running final cohesion pass")
    try:
        final_output = await _critic_pass(llm, merged_polished)
        return final_output
    except Exception as e:
        error(f"Final critic pass failed: {e}")
        return merged_polished
