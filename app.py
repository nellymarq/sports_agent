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

from llm import llm as REAL_LLM
from tests.mock_llm import MockLLM  # S-tier mock for instant responses

from tools import TOOL_REGISTRY
from orchestrator import orchestrator
from router_agent import router_agent
from state_manager import clear_task_queue, reset_state, load_history, append_to_history


# ============================================================
# CONFIG: Choose between LIVE (Groq) and TEST (MockLLM)
# ============================================================

USE_TEST_MODE = False   # <—— CHANGE THIS TO False when you want real Groq calls

if USE_TEST_MODE:
    ACTIVE_LLM = MockLLM()
else:
    ACTIVE_LLM = REAL_LLM


# ============================================================
# STREAMLIT PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="UFC Analytics Engine",
    page_icon="🥊",
    layout="centered",
)


# ============================================================
# INITIALIZE SESSION STATE
# ============================================================

def init_state():
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []


# ============================================================
# FULL MULTI-AGENT PIPELINE
# ============================================================

async def _run_full_pipeline(user_input: str) -> str:
    """
    Full multi-agent pipeline:
    - load history
    - route to specialists
    - build task plan
    - run orchestrator
    """

    # Load raw history as (role, content) tuples
    history_pairs = load_history()

    # Convert to strings for agents that expect text, not tuples
    history = [f"{role}: {content}" for role, content in history_pairs]

    # Episodic memory as a single text block (router-friendly)
    episodic_memory_text = "\n".join(history) if history else ""

    # 1. ROUTER
    routing = await router_agent(
        llm=ACTIVE_LLM,
        user_input=user_input,
        semantic_memory="",          # hook for future semantic memory
        episodic_memory=episodic_memory_text,
    )

    specialists = routing.get("specialists", [])

    # Safety: In LIVE mode, limit specialists to avoid 429 rate-limit hell
    if not USE_TEST_MODE:
        specialists = specialists[:6]  # run only 6 specialists max

    # 2. BUILD TASK PLAN
    tasks = [
        {
            "name": f"{spec}_analysis",
            "specialist": spec,
        }
        for spec in specialists
    ]

    task_plan = {
        "user_input": user_input,
        "history": history,          # list of "role: content" strings
        "retrieved_context": "",
        "tasks": tasks,
    }

    # 3. ORCHESTRATOR
    result = await orchestrator(
        llm=ACTIVE_LLM,
        tool_registry=TOOL_REGISTRY,
        task_plan=task_plan,
        test_mode=USE_TEST_MODE,
    )

    return result


def run_orchestrator_sync(user_input: str) -> str:
    """
    Run the async multi-agent pipeline inside Streamlit's sync environment.
    Always clear the task queue so the pipeline runs fresh.
    """
    clear_task_queue()
    return asyncio.run(_run_full_pipeline(user_input))


# ============================================================
# HEADER + SIDEBAR
# ============================================================

def render_header():
    st.title("UFC Analytics Engine")

    mode_label = "🧪 TEST MODE (MockLLM)" if USE_TEST_MODE else "⚡ LIVE MODE (Groq API)"
    st.caption(f"{mode_label} — UFC-only narrative, form, style, and market sentiment.")

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


# ============================================================
# MAIN APP
# ============================================================

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


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
