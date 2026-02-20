# specialists/tool_runtime.py

import json
import traceback
from logger import error, info


def build_system_prompt(base_prompt: str, profile: str, retrieved_context: str, tool_names):
    """
    Build the system prompt with consistent formatting.
    """
    tools_list = ", ".join(tool_names) if tool_names else "None"

    system_msg = (
        f"{base_prompt}\n\n"
        f"Fighter Profile:\n{profile}\n\n"
        f"Retrieved Context:\n{retrieved_context}\n\n"
        f"Available Tools: {tools_list}\n"
        f"You MUST return JSON when calling tools. "
        f"If no tool is needed, answer normally."
    )

    return [{"role": "system", "content": system_msg}]


def parse_tool_call(reply):
    """
    Extract tool call info from the model reply.
    Must include the tool_call_id for Groq.
    """
    try:
        tool_call = reply.tool_calls[0]  # Groq/OpenAI format
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)
        call_id = tool_call.id  # REQUIRED by Groq
        return {"name": name, "args": args, "id": call_id}
    except Exception:
        return None


def append_tool_message(messages, tool_call, result):
    """
    Append a tool result message with the REQUIRED tool_call_id.
    """
    messages.append({
        "role": "tool",
        "tool_call_id": tool_call["id"],  # REQUIRED
        "content": json.dumps({
            "tool_name": tool_call["name"],
            "tool_args": tool_call["args"],
            "tool_result": result
        }, ensure_ascii=False)
    })


async def run_tool_loop(llm, messages, tool_registry, max_iters=4):
    """
    Universal tool-call loop used by ALL specialists.
    JSON-first, natural-language fallback.
    """
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
            return reply.content  # fallback

        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        if tool_name not in tool_registry:
            return f"Unknown tool: {tool_name}"

        try:
            result = await tool_registry[tool_name](**tool_args)
        except Exception as e:
            tb = traceback.format_exc()
            error(f"Tool execution error ({tool_name}):\n{tb}")
            result = f"Tool error: {e}"

        append_tool_message(messages, tool_call, result)

    return "Tool loop exceeded maximum iterations."
