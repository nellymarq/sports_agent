# === UNIVERSAL DEVTOOLS HEADER ===
import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
# === END UNIVERSAL DEVTOOLS HEADER ===

import subprocess
import importlib
import traceback
from tools import TOOL_REGISTRY
from specialists import *
from orchestrator import orchestrator
from tests.mock_llm import MockLLM


def banner(title: str):
    print("\n" + "=" * 80)
    print(f"=== {title}")
    print("=" * 80 + "\n")


def run_shell(cmd: str):
    print(f"→ {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"✖ Command failed: {cmd}")
    else:
        print(f"✔ OK\n")
    return result.returncode == 0


def check_imports():
    banner("IMPORT VALIDATION")

    modules = [
        "router_agent",
        "supervisor",
        "orchestrator",
        "coordinator_agent",
        "critic_agent",
        "memory_agent",
        "tools",
        "specialists",
    ]

    for m in modules:
        try:
            importlib.import_module(m)
            print(f"✔ Imported: {m}")
        except Exception as e:
            print(f"✖ FAILED: {m}")
            traceback.print_exc()
    print()


def check_specialists():
    banner("SPECIALIST REGISTRY CHECK")

    try:
        from specialists import __all__ as names
    except Exception:
        # fallback: inspect globals
        names = [n for n in globals().keys() if n.startswith("run_")]

    print(f"Found {len(names)} specialists")

    for name in names:
        fn = globals().get(name)
        if not callable(fn):
            print(f"✖ {name} is not callable")
            continue
        print(f"✔ {name} loaded")

    print()


async def check_orchestrator_test_mode():
    banner("ORCHESTRATOR TEST MODE CHECK")

    llm = MockLLM()
    dummy_plan = {
        "user_input": "test",
        "history": [],
        "retrieved_context": "",
        "tasks": [],
    }

    try:
        result = await orchestrator(
            llm=llm,
            tool_registry=TOOL_REGISTRY,
            task_plan=dummy_plan,
            test_mode=True,
        )
        if isinstance(result, dict) and result.get("final") == "[MOCK FINAL OUTPUT]":
            print("✔ Orchestrator test mode OK\n")
        else:
            print("✖ Orchestrator test mode returned unexpected output\n")
    except Exception:
        print("✖ Orchestrator test mode FAILED")
        traceback.print_exc()
        print()


def run_pytest():
    banner("RUNNING PYTEST SUITE")
    run_shell("pytest -q")


def run_tree_check():
    banner("TREE STRUCTURE CHECK")
    run_shell("python3 devtools/check_tree.py")


def run_import_validation():
    banner("IMPORT VALIDATION SCRIPT")
    run_shell("python3 devtools/validate_imports.py")


if __name__ == "__main__":
    banner("PROJECT DOCTOR")

    run_tree_check()
    run_import_validation()
    check_imports()
    check_specialists()

    import asyncio
    asyncio.run(check_orchestrator_test_mode())

    run_pytest()

    banner("PROJECT DOCTOR COMPLETE")
