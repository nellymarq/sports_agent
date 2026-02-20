import json
import os
import threading
from typing import Any, Dict, List, Optional, Tuple

STATE_DIR = os.path.join(os.path.dirname(__file__), "state")

PROJECT_STATE_PATH = os.path.join(STATE_DIR, "project_state.json")
TASK_QUEUE_PATH = os.path.join(STATE_DIR, "task_queue.json")
HISTORY_PATH = os.path.join(STATE_DIR, "history.json")
TOOL_CACHE_PATH = os.path.join(STATE_DIR, "tool_cache.json")

os.makedirs(STATE_DIR, exist_ok=True)

_file_lock = threading.Lock()


# ---------- INTERNAL SAFE IO ---------- #

def _safe_read_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _safe_write_json(path: str, data: Any) -> None:
    tmp_path = f"{path}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


# ---------- PROJECT STATE ---------- #

def load_project_state() -> Dict[str, Any]:
    with _file_lock:
        return _safe_read_json(PROJECT_STATE_PATH, default={})


def save_project_state(state: Dict[str, Any]) -> None:
    with _file_lock:
        _safe_write_json(PROJECT_STATE_PATH, state)


def update_project_state(updates: Dict[str, Any]) -> Dict[str, Any]:
    with _file_lock:
        state = _safe_read_json(PROJECT_STATE_PATH, default={})
        state.update(updates)
        _safe_write_json(PROJECT_STATE_PATH, state)
        return state


# ---------- TASK QUEUE ---------- #

Task = Dict[str, Any]


def load_task_queue() -> List[Task]:
    with _file_lock:
        return _safe_read_json(TASK_QUEUE_PATH, default=[])


def save_task_queue(tasks: List[Task]) -> None:
    with _file_lock:
        _safe_write_json(TASK_QUEUE_PATH, tasks)


def clear_task_queue() -> None:
    with _file_lock:
        _safe_write_json(TASK_QUEUE_PATH, [])


def add_tasks(new_tasks: List[Task]) -> List[Task]:
    with _file_lock:
        tasks = _safe_read_json(TASK_QUEUE_PATH, default=[])
        existing_by_id = {t["id"]: t for t in tasks}

        for t in new_tasks:
            if "id" not in t:
                raise ValueError("Task missing 'id' field")
            t.setdefault("type", "generic")
            t.setdefault("description", "")
            t.setdefault("status", "pending")
            t.setdefault("depends_on", [])
            t.setdefault("metadata", {})
            existing_by_id[t["id"]] = t

        merged = list(existing_by_id.values())
        _safe_write_json(TASK_QUEUE_PATH, merged)
        return merged


def update_task_status(task_id: str, status: str) -> Optional[Task]:
    with _file_lock:
        tasks = _safe_read_json(TASK_QUEUE_PATH, default=[])
        updated_task = None
        for t in tasks:
            if t.get("id") == task_id:
                t["status"] = status
                updated_task = t
                break
        _safe_write_json(TASK_QUEUE_PATH, tasks)
        return updated_task


def get_task_by_id(task_id: str) -> Optional[Task]:
    with _file_lock:
        tasks = _safe_read_json(TASK_QUEUE_PATH, default=[])
        for t in tasks:
            if t.get("id") == task_id:
                return t
        return None


def _dependencies_satisfied(task: Task, tasks_by_id: Dict[str, Task]) -> bool:
    deps = task.get("depends_on") or []
    for dep_id in deps:
        dep_task = tasks_by_id.get(dep_id)
        if not dep_task or dep_task.get("status") != "done":
            return False
    return True


def get_next_eligible_task() -> Optional[Task]:
    with _file_lock:
        tasks = _safe_read_json(TASK_QUEUE_PATH, default=[])
        tasks_by_id = {t["id"]: t for t in tasks if "id" in t}

        eligible: List[Task] = []
        for t in tasks:
            if t.get("status") != "pending":
                continue
            if _dependencies_satisfied(t, tasks_by_id):
                eligible.append(t)

        if not eligible:
            return None

        def _priority(task: Task) -> int:
            meta = task.get("metadata") or {}
            return int(meta.get("priority", 9999))

        eligible.sort(key=_priority)
        return eligible[0]


def all_tasks_completed() -> bool:
    with _file_lock:
        tasks = _safe_read_json(TASK_QUEUE_PATH, default=[])
        if not tasks:
            return True
        return all(t.get("status") in ("done", "failed") for t in tasks)


# ---------- CHAT HISTORY ---------- #

def load_history() -> List[Tuple[str, str]]:
    with _file_lock:
        raw = _safe_read_json(HISTORY_PATH, default=[])
        history: List[Tuple[str, str]] = []
        for item in raw:
            if (
                isinstance(item, list)
                and len(item) == 2
                and isinstance(item[0], str)
                and isinstance(item[1], str)
            ):
                history.append((item[0], item[1]))
        return history


def save_history(history: List[Tuple[str, str]]) -> None:
    with _file_lock:
        raw = [[role, content] for role, content in history]
        _safe_write_json(HISTORY_PATH, raw)


def append_to_history(role: str, content: str, max_len: int = 100) -> None:
    with _file_lock:
        history = _safe_read_json(HISTORY_PATH, default=[])
        history.append([role, content])
        if len(history) > max_len:
            history = history[-max_len:]
        _safe_write_json(HISTORY_PATH, history)


# ---------- TOOL CACHE ---------- #

def load_tool_cache() -> Dict[str, Any]:
    with _file_lock:
        return _safe_read_json(TOOL_CACHE_PATH, default={})


def save_tool_cache(cache: Dict[str, Any]) -> None:
    with _file_lock:
        _safe_write_json(TOOL_CACHE_PATH, cache)


def get_tool_cache_entry(key: str) -> Optional[Any]:
    with _file_lock:
        cache = _safe_read_json(TOOL_CACHE_PATH, default={})
        return cache.get(key)


def set_tool_cache_entry(key: str, value: Any) -> None:
    with _file_lock:
        cache = _safe_read_json(TOOL_CACHE_PATH, default={})
        cache[key] = value
        _safe_write_json(TOOL_CACHE_PATH, cache)


# ---------- GLOBAL RESET (for devtools / smoke tests) ---------- #

def reset_state() -> None:
    """
    Reset all persisted state so devtools smoke tests always start clean.
    """
    with _file_lock:
        _safe_write_json(PROJECT_STATE_PATH, {})
        _safe_write_json(TASK_QUEUE_PATH, [])
        _safe_write_json(HISTORY_PATH, [])
        _safe_write_json(TOOL_CACHE_PATH, {})
