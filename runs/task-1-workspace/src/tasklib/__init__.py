"""Public entry points for the task-management benchmark library.

Only the standard library is required at runtime. The baseline intentionally
omits filtering, searching, deletion, statistics and CSV export: these are
independent exercises for the agent, not baseline capabilities.

Typical in-memory use::

    from tasklib import TaskStore

    store = TaskStore()
    task = store.add("Read the guide", priority="high")
    store.update(task.id, title="Read the Week 1 guide")
    store.complete(task.id)
    assert store.get(task.id) is task
    assert task.completed

Persistence uses explicit paths and never creates missing parent folders::

    from tasklib import save_store, load_store

    save_store(store, "tasks.json")
    restored = load_store("tasks.json")
    assert restored.get(task.id) == task
    assert restored.get(task.id) is not task

Public input validation raises ValueError, while lookup of an absent valid
ID raises KeyError. Filesystem exceptions propagate from persistence so a
caller can distinguish inaccessible files from invalid saved documents.
The library is synchronous and intended for a single writer at a time.
"""

from .models import Task
from .store import TaskStore
from .storage import load_store, save_store

__all__ = ["Task", "TaskStore", "load_store", "save_store"]
