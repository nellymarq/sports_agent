# tests/test_state_manager.py
# Unit tests for state manager: JSON persistence, task queue, history.

import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from state_manager import (
    load_project_state,
    update_project_state,
    load_task_queue,
    clear_task_queue,
    add_tasks,
    update_task_status,
    get_task_by_id,
    get_next_eligible_task,
    all_tasks_completed,
    load_history,
    append_to_history,
    load_tool_cache,
    set_tool_cache_entry,
    get_tool_cache_entry,
)


class TestProjectState:
    def test_load_returns_dict(self):
        state = load_project_state()
        assert isinstance(state, dict)

    def test_update_merges(self):
        state = update_project_state({"test_key": "test_value"})
        assert state["test_key"] == "test_value"


class TestTaskQueue:
    def test_clear_and_load(self):
        clear_task_queue()
        tasks = load_task_queue()
        assert tasks == []

    def test_add_tasks(self):
        clear_task_queue()
        new_tasks = [
            {"id": "t1", "description": "task 1"},
            {"id": "t2", "description": "task 2"},
        ]
        result = add_tasks(new_tasks)
        assert len(result) == 2

    def test_update_status(self):
        clear_task_queue()
        add_tasks([{"id": "t1"}])
        updated = update_task_status("t1", "done")
        assert updated["status"] == "done"

    def test_get_by_id(self):
        clear_task_queue()
        add_tasks([{"id": "t1", "description": "find me"}])
        task = get_task_by_id("t1")
        assert task is not None
        assert task["description"] == "find me"

    def test_get_nonexistent(self):
        task = get_task_by_id("nonexistent_id_xyz")
        assert task is None

    def test_all_completed(self):
        clear_task_queue()
        assert all_tasks_completed() is True

    def test_not_all_completed(self):
        clear_task_queue()
        add_tasks([{"id": "t1"}])
        assert all_tasks_completed() is False


class TestHistory:
    def test_append_and_load(self):
        # Save current history
        append_to_history("user", "test question")
        history = load_history()
        assert len(history) >= 1
        assert history[-1] == ("user", "test question")

    def test_max_length(self):
        for i in range(110):
            append_to_history("user", f"q{i}")
        history = load_history()
        assert len(history) <= 100


class TestToolCache:
    def test_set_and_get(self):
        set_tool_cache_entry("test_key", {"data": 42})
        result = get_tool_cache_entry("test_key")
        assert result == {"data": 42}

    def test_missing_key(self):
        result = get_tool_cache_entry("missing_key_xyz")
        assert result is None
