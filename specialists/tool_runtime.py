# specialists/tool_runtime.py
# Shared runtime utilities for all specialists:
# - token-safe truncation
# - system prompt builder
# - tool-call loop with Groq-compatible tool_call_id handling

import json
import traceback
from logger import error, info


# ---------------------------------------------------------
# Token-safe truncation utilities
# ---------------------------------------------------------

def estimate_tokens(text: str) -> int:
    """Very rough token estimator: ~4 chars per token."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def truncate_text(text: str, max_tokens: int) -> str:
    """Truncate text to a maximum token count."""
    if estimate_tokens(text) <= max_tokens:
        return text
    approx_chars = max_tokens * 4
    return text[:approx_chars] + "\n...[TRUNCATED]..."


def truncate_messages(messages, max_tokens: int):
    """
    Truncate the messages array from the *oldest* entries first
    until the total estimated tokens fit under max_tokens.
    """
    def total_tokens(msgs):
        return sum(estimate_tokens(m.get("content", "")) for m in msgs)

    msgs = list(messages)
    while msgs and total_tokens(msgs) > max_tokens:
        msgs.pop(0)  # drop oldest message first
    return msgs


# ---------------------------------------------------------
# System prompt builder (REQUIRED by specialists + tests)
# ---------------------------------------------------------

def build_system_prompt(base_prompt: str, profile: str, retrieved_context: str, tool_names):
    """
    Build the system prompt with consistent formatting.
    """
    tools_list = ", ".join(tool_names) if tool_names else "None"

    system_msg = (
        f"{base_prompt}\n\n"
        f"Fighter Profile:\n{profile}\n\n"
        f"Retrieved Context:\n{truncate_text(str(retrieved_context), 1500)}\n\n"
        f"Available Tools: {tools_list}\n"
        f"You MUST return JSON when calling tools. "
        f"If no tool is needed, answer normally."
    )

    return [{"role": "system", "content": system_msg}]


# ---------------------------------------------------------
# Tool call parsing
# ---------------------------------------------------------

def parse_tool_call(reply):
    """
    Extract tool call info from the model reply.
    Must include the tool_call_id for Groq.
    """
    try:
        tool_calls = getattr(reply, "tool_calls", None)
        if not tool_calls:
            return None
        tool_call = tool_calls[0]  # Groq/OpenAI format
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments or "{}")
        call_id = tool_call.id  # REQUIRED by Groq
        return {"name": name, "args": args, "id": call_id}
    except Exception:
        return None


def append_tool_message(messages, tool_call, result):
    """
    Append a tool result message with the REQUIRED tool_call_id.
    """
    messages.append(
        {
            "role": "tool",
            "tool_call_id": tool_call["id"],  # REQUIRED
            "content": json.dumps(
                {
                    "tool_name": tool_call["name"],
                    "tool_args": tool_call["args"],
                    "tool_result": result,
                },
                ensure_ascii=False,
            ),
        }
    )


# ---------------------------------------------------------
# Main tool loop (with token truncation)
# ---------------------------------------------------------

async def run_tool_loop(llm, messages, tool_registry, max_iters: int = 4):
    """
    Universal tool-call loop used by ALL specialists.
    JSON-first, natural-language fallback.
    """

    # -----------------------------------------------------
    # Enforce token budget BEFORE sending to Groq
    # -----------------------------------------------------
    MAX_INPUT_TOKENS = 4500  # safe for llama-3.1-8b-instant

    # Truncate messages array
    messages = truncate_messages(messages, MAX_INPUT_TOKENS)

    # Also truncate individual message content (safety)
    for m in messages:
        m["content"] = truncate_text(m.get("content", ""), 2000)

    # -----------------------------------------------------
    # Tool loop
    # -----------------------------------------------------
    for _ in range(max_iters):
        try:
            reply = await llm.chat(messages)
        except Exception as e:
            tb = traceback.format_exc()
            error(f"LLM error in tool loop:\n{tb}")
            return f"LLM error: {e}"

        # If the model returns normal text, we're done
        if not getattr(reply, "tool_calls", None):
            return reply.content

        # Otherwise, handle tool call
        tool_call = parse_tool_call(reply)
        if not tool_call:
            # If parsing fails, fall back to the raw content
            return reply.content

        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        if tool_name not in tool_registry:
            return f"Unknown tool: {tool_name}"

        try:
            tool = tool_registry[tool_name]
            # Support both callable tools and class instances with .invoke()
            if hasattr(tool, "invoke"):
                result = tool.invoke(tool_args)
            elif callable(tool):
                import asyncio
                if asyncio.iscoroutinefunction(tool):
                    result = await tool(**tool_args)
                else:
                    result = tool(**tool_args)
            else:
                result = f"Tool '{tool_name}' is not callable"
        except Exception as e:
            tb = traceback.format_exc()
            error(f"Tool execution error ({tool_name}):\n{tb}")
            result = f"Tool error: {e}"

        append_tool_message(messages, tool_call, result)

    return "Tool loop exceeded maximum iterations."
