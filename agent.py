# agent.py
# Clean, async, tool-calling agent (single-agent mode)

import json
import logging
import asyncio
from typing import List, Dict, Any, Tuple, Optional

from llm import llm
from tools import TOOL_REGISTRY

logger = logging.getLogger("ufc_agent")
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )


SYSTEM_PROMPT = """
You are a gambling prediction UFC assistant.

You:
- Use ONLY the provided tools (UFCStats, ESPN UFC, DraftKings Marketplace, Polymarket).
- Focus on style, tendencies, context, recent form, matchup dynamics, collectibles/market sentiment, and narrative.
- Treat DraftKings Marketplace and Polymarket data as indicators of interest, popularity, and sentiment — NOT as betting or trading advice.

TOOL CALLING PROTOCOL:

When you need external data, respond ONLY with JSON:

{
  "tool_call": {
    "name": "<tool_name>",
    "args": {}
  }
}

When you are ready to answer the user, DO NOT use JSON.
Just answer normally.

Never invent tool names.
"""


def _safe_parse_tool_call(model_reply: str) -> Optional[Dict[str, Any]]:
    try:
        parsed = json.loads(model_reply)
    except json.JSONDecodeError:
        return None

    if not isinstance(parsed, dict):
        return None

    tool_call = parsed.get("tool_call")
    if not isinstance(tool_call, dict):
        return None

    name = tool_call.get("name")
    if not isinstance(name, str) or not name:
        return None

    args = tool_call.get("args", {}) or {}
    if not isinstance(args, dict):
        args = {}

    return {"name": name, "args": args}


async def _call_tool(name: str, args: Dict[str, Any]) -> Any:
    logger.info("Tool call requested: %s with args=%s", name, args)

    tool = TOOL_REGISTRY.get(name)
    if not tool:
        return {"error": f"Unknown tool: {name}"}

    try:
        if hasattr(tool, "invoke") and callable(tool.invoke):
            if asyncio.iscoroutinefunction(tool.invoke):
                return await tool.invoke(args)
            return tool.invoke(args)
        return {"error": f"Tool {name} has no invoke() method"}

    except Exception as e:
        logger.exception("Tool %s failed", name)
        return {"error": f"Tool {name} failed", "details": str(e)}


async def agent_executor(
    user_input: str,
    chat_history: List[Tuple[str, str]] | None = None,
) -> str:
    tool_names = ", ".join(TOOL_REGISTRY.keys())
    logger.info("New user query: %s", user_input)

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": f"Available tools: {tool_names}"},
    ]

    if chat_history:
        for role, msg in chat_history:
            if role in ("user", "assistant"):
                messages.append({"role": role, "content": msg})

    messages.append({"role": "user", "content": user_input})

    for step in range(4):
        logger.info("Agent loop step %d", step + 1)

        try:
            model_reply = await llm.chat(messages)
            model_reply = model_reply.strip()
        except Exception:
            return "I couldn’t complete the analysis due to an LLM error."

        tool_call = _safe_parse_tool_call(model_reply)
        if not tool_call:
            return model_reply

        name = tool_call["name"]
        args = tool_call["args"]

        tool_result = await _call_tool(name, args)

        messages.append({"role": "assistant", "content": model_reply})
        messages.append(
            {
                "role": "tool",
                "content": json.dumps(
                    {
                        "tool_name": name,
                        "tool_args": args,
                        "tool_result": tool_result,
                    },
                    ensure_ascii=False,
                ),
            }
        )
        messages.append(
            {
                "role": "user",
                "content": "Use the tool_result above to answer the original question.",
            }
        )

    return "I had trouble completing the analysis. Try rephrasing your question."
