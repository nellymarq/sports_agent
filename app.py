import os
from dotenv import load_dotenv

# Force-load .env from the directory where app.py lives
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH)

print("DEBUG: Loaded .env from:", ENV_PATH)
print("DEBUG: GROQ_API_KEY =", os.getenv("GROQ_API_KEY"))

import streamlit as st
import asyncio

from llm import llm
from tools import TOOL_REGISTRY
from orchestrator import run_agent_orchestrator
from router_agent import router_agent
from state_manager import clear_task_queue, reset_state, load_history, append_to_history


# -------------------------
# PAGE CONFIG
# -------------------------
st.set_page_config(
    page_title="UFC Analytics Engine",
    page_icon="🥊",
    layout="centered",
)


# -------------------------
# INITIALIZE SESSION STATE
# -------------------------
def init_state():
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []


# -------------------------
# ASYNC PIPELINE
# -------------------------
async def _run_full_pipeline(user_input: str) -> str:
    """
    Full multi-agent pipeline:
    - load history
    - route to specialists
    - build task plan
    - run orchestrator
    """
    history = load_history()

    routing = await router_agent(llm, user_input)
    specialists = routing.get("specialists", [])

    tasks = [
        {
            "name": f"{spec}_analysis",
            "specialist": spec,
        }
        for spec in specialists
    ]

    task_plan = {
        "user_input": user_input,
        "history": history,
        "retrieved_context": "",
        "tasks": tasks,
    }

    result = await run_agent_orchestrator(llm, TOOL_REGISTRY, task_plan)
    return result


def run_orchestrator_sync(user_input: str) -> str:
    """
    Run the async multi-agent pipeline inside Streamlit's sync environment.
    Always clear the task queue so the pipeline runs fresh.
    """
    clear_task_queue()
    return asyncio.run(_run_full_pipeline(user_input))


# -------------------------
# HEADER + SIDEBAR
# -------------------------
def render_header():
    st.title("UFC Analytics Engine")
    st.caption(
        "UFC-only narrative, form, style, and market sentiment — "
        "no betting, no wagering, no odds."
    )

    with st.sidebar:
        st.subheader("Session Controls")
        st.write("Conversation is stored locally in this session.")

        if st.button("Clear Conversation"):
            reset_state()
            st.session_state.chat_history = []
            st.experimental_rerun()

        st.markdown("---")
        st.subheader("About")
        st.write(
            "This engine analyzes UFC fighters, matchups, styles, form, "
            "and market sentiment using structured tools and a multi-agent system."
        )


# -------------------------
# MAIN APP
# -------------------------
def main():
    init_state()
    render_header()

    user_input = st.chat_input(
        "Ask about a fighter, matchup, style, recent form, or market sentiment..."
    )

    if user_input:
        st.session_state.chat_history.append(("user", user_input))
        append_to_history("user", user_input)

        with st.spinner("Analyzing with multi-agent system..."):
            try:
                result = run_orchestrator_sync(user_input)
            except Exception as e:
                result = (
                    "I ran into an internal error while processing that.\n\n"
                    f"Details: {e}"
                )

        st.session_state.chat_history.append(("assistant", result))
        append_to_history("assistant", result)

    for role, msg in st.session_state.chat_history:
        with st.chat_message("user" if role == "user" else "assistant"):
            st.markdown(msg)


# -------------------------
# ENTRY POINT
# -------------------------
if __name__ == "__main__":
    main()
