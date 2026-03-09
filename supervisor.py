# supervisor.py
# S‑tier Supervisor Agent for UFC Analytics Engine
# Builds a complete, dependency-aware task graph for orchestrator execution.

from logger import info, debug, error


def _build_specialist_task(
    task_id: int,
    specialist: str,
    user_input: str,
    history,
    retrieved_context: str,
):
    """
    Build a single specialist task node.
    """
    return {
        "id": task_id,
        "task_type": "specialist",
        "specialist": specialist,
        "user_input": user_input,
        "history": history,
        "retrieved_context": retrieved_context,
        "depends_on": [],
    }


def _build_coordinator_task(task_id: int, parent_ids):
    """
    Coordinator merges all specialist outputs.
    """
    return {
        "id": task_id,
        "task_type": "coordinator_merge",
        "depends_on": parent_ids,
    }


def _build_critic_task(task_id: int, coordinator_id: int):
    """
    Critic refines the merged coordinator output.
    """
    return {
        "id": task_id,
        "task_type": "critic_review",
        "depends_on": [coordinator_id],
    }


async def supervisor_agent(
    llm,
    router_output: dict,
    user_input: str,
    history,
    retrieved_context: str = "",
    test_mode: bool = False,
) -> dict:
    """
    S‑tier Supervisor Agent:
    - Accepts router output (specialists + mode)
    - Builds a full dependency graph:
        specialists → coordinator → critic
    - Supports debug specialists
    - Supports test_mode (no coordinator/critic if desired)
    - Returns a complete task_plan for the orchestrator
    """

    info("Supervisor agent invoked")

    specialists = router_output.get("specialists", [])
    mode = router_output.get("mode", "autonomous")

    if not specialists:
        error("Supervisor: Router returned no specialists")
        return {
            "tasks": [],
            "mode": mode,
            "specialists": [],
            "user_input": user_input,
            "history": history,
            "retrieved_context": retrieved_context,
            "question_type": router_output.get("question_type"),
            "debug_specialists": router_output.get("debug_specialists", []),
        }

    debug(f"Supervisor received specialists: {specialists}")

    tasks = []
    next_id = 0

    # 1. Specialist tasks
    specialist_task_ids = []
    for spec in specialists:
        t = _build_specialist_task(
            task_id=next_id,
            specialist=spec,
            user_input=user_input,
            history=history,
            retrieved_context=retrieved_context,
        )
        tasks.append(t)
        specialist_task_ids.append(next_id)
        next_id += 1

    # 2. Coordinator task (unless test_mode disables it)
    if not test_mode:
        coordinator_task = _build_coordinator_task(
            task_id=next_id,
            parent_ids=specialist_task_ids,
        )
        coordinator_task_id = next_id
        tasks.append(coordinator_task)
        next_id += 1
    else:
        coordinator_task_id = None

    # 3. Critic task (only if coordinator exists)
    if not test_mode and coordinator_task_id is not None:
        critic_task = _build_critic_task(
            task_id=next_id,
            coordinator_id=coordinator_task_id,
        )
        tasks.append(critic_task)
        next_id += 1

    info("Supervisor: Task plan successfully generated")

    return {
        "tasks": tasks,
        "mode": mode,
        "specialists": specialists,
        "user_input": user_input,
        "history": history,
        "retrieved_context": retrieved_context,
        "question_type": router_output.get("question_type"),
        "debug_specialists": router_output.get("debug_specialists", []),
    }
