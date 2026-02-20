# supervisor.py
# Generates the full task plan for 14-specialist autonomous workflows

from logger import info, debug, error


def build_specialist_task(specialist_name: str, user_input: str, history, retrieved_context: str):
    """
    Helper to build a specialist task dict.
    """
    return {
        "task_type": "specialist",
        "specialist": specialist_name,
        "user_input": user_input,
        "history": history,
        "retrieved_context": retrieved_context,
        "depends_on": [],
    }


async def supervisor_agent(
    llm,
    router_output: dict,
    user_input: str,
    history,
    retrieved_context: str = "",
) -> dict:
    """
    Creates a full task plan:
    - One task per specialist selected by the router.
    - Coordinator merges all specialist outputs.
    - Critic refines the coordinator output.
    """

    info("Supervisor agent invoked")

    specialists = router_output.get("specialists", [])
    if not specialists:
        error("Supervisor: No specialists provided by router")
        return {"tasks": []}

    debug(f"Supervisor received specialists: {specialists}")

    tasks = []

    # 1. Specialist tasks
    for spec in specialists:
        tasks.append(
            build_specialist_task(
                specialist_name=spec,
                user_input=user_input,
                history=history,
                retrieved_context=retrieved_context,
            )
        )

    # Collect IDs for dependency graph
    specialist_task_ids = list(range(len(tasks)))

    # 2. Coordinator task
    coordinator_task = {
        "task_type": "coordinator_merge",
        "depends_on": specialist_task_ids,
    }
    coordinator_task_id = len(tasks)
    tasks.append(coordinator_task)

    # 3. Critic task
    critic_task = {
        "task_type": "critic_review",
        "depends_on": [coordinator_task_id],
    }
    tasks.append(critic_task)

    info("Supervisor: Task plan successfully generated")

    return {
        "tasks": tasks,
        "mode": router_output.get("mode", "autonomous"),
        "specialists": specialists,
    }
