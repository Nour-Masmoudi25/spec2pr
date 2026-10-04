"""Ordered, in-memory task storage with transactional batch operations.

Each store owns its own dictionary and next-ID counter. Python dictionaries
preserve insertion order, which defines the public task order. Mutations are
synchronous; the class does not provide thread or process synchronization.
"""

from .models import Task
from .validation import (
    validate_fields,
    validate_id,
    validate_priority,
    validate_title,
)


class TaskStore:
    """Manage tasks while keeping their identities and insertion order.

    The returned Task objects are live references, not snapshots. A list
    returned by list_tasks is independent, but the tasks inside it are the
    same objects returned by add and get. Prefer store methods for edits.
    """

    def __init__(self) -> None:
        """Create an empty store whose first task will have ID 1."""
        self._tasks: dict[int, Task] = {}
        self._next_id = 1

    def add(self, title: str, priority: str = "medium") -> Task:
        """Validate and append one task, returning the stored object.

        Duplicate titles are allowed. Validation happens before either the
        dictionary or counter changes, so failed adds do not consume IDs.
        """
        task = Task(self._next_id, title, priority)
        self._tasks[task.id] = task
        self._next_id += 1
        return task

    def get(self, task_id: int) -> Task:
        """Return the stored task, raising KeyError when it does not exist.

        Invalid identifiers raise ValueError before the dictionary lookup.
        For example, True must never resolve to the task with integer ID 1.
        """
        return self._tasks[validate_id(task_id)]

    def list_tasks(self) -> list[Task]:
        """Return a fresh list of live task references in creation order.

        Clearing or reversing this list does not alter the store. Editing an
        object in it does affect that task, matching get's reference semantics.
        """
        return list(self._tasks.values())

    def complete(self, task_id: int) -> Task:
        """Mark a task complete and return it.

        Repeating completion is harmless. Unknown and invalid IDs follow
        get's error rules, and leave every existing task unchanged.
        """
        task = self.get(task_id)
        task.completed = True
        return task

    def reopen(self, task_id: int) -> Task:
        """Mark a task incomplete and return it.

        Reopening an already incomplete task is also a valid operation.
        The task's position, title and priority do not change.
        """
        task = self.get(task_id)
        task.completed = False
        return task

    def update(
        self,
        task_id: int,
        *,
        title: str | None = None,
        priority: str | None = None,
    ) -> Task:
        """Update supplied fields after validating the whole request.

        None means leave a field unchanged. Omitting both fields is a no-op
        for an existing task. Invalid requests cannot partially update a task:
        a valid title with an invalid priority leaves both old values intact.
        """
        task = self.get(task_id)
        new_title = validate_title(title) if title is not None else task.title
        new_priority = (
            validate_priority(priority) if priority is not None else task.priority
        )
        task.title = new_title
        task.priority = new_priority
        return task

    def add_many(self, items: list[dict]) -> list[Task]:
        """Append a batch atomically with respect to input validation.

        Each entry requires title and may provide priority. IDs and completed
        status cannot be supplied by the caller. An empty list is valid.
        Invalid entries leave both the store and its next-ID counter intact.
        The input dictionaries themselves are never modified.
        """
        if not isinstance(items, list):
            raise ValueError("Items must be a list of dictionaries")
        pending = []
        for offset, item in enumerate(items):
            record = validate_fields(
                item, {"title"}, {"priority"}, name=f"Batch entry {offset}"
            )
            pending.append(
                Task(
                    self._next_id + offset,
                    record["title"],
                    record.get("priority", "medium"),
                )
            )
        for task in pending:
            self._tasks[task.id] = task
        self._next_id += len(pending)
        return pending

    def _snapshot(self) -> dict:
        """Create a validated persistence document without mutating the store.

        This private boundary centralizes checks that involve store identity,
        beyond the field checks performed by Task.to_dict. Persistence must
        reject direct ID edits instead of quietly changing lookup behavior.
        """
        next_id = validate_id(self._next_id, "Next ID")
        records = []
        for key, task in self._tasks.items():
            record = task.to_dict()
            if validate_id(key) != record["id"]:
                raise ValueError("Task ID does not match its store key")
            if record["id"] >= next_id:
                raise ValueError("Next ID must exceed every stored task ID")
            records.append(record)
        return {"version": 1, "next_id": next_id, "tasks": records}

    @classmethod
    def _restore(cls, tasks: list[Task], next_id: int) -> "TaskStore":
        """Construct an independent store from validated persistence values.

        Duplicate IDs are rejected rather than overwritten. The ordered list
        can contain gaps or nonascending IDs; its order is retained exactly.
        No existing store is involved in or affected by restoration.
        """
        counter = validate_id(next_id, "Next ID")
        store = cls()
        for task in tasks:
            if task.id in store._tasks:
                raise ValueError(f"Duplicate task ID: {task.id}")
            if task.id >= counter:
                raise ValueError("Next ID must exceed every stored task ID")
            store._tasks[task.id] = task
        store._next_id = counter
        return store

    def filter_by_priority(self, priority):
        """Return tasks matching the given priority in creation order."""
        priority = validate_priority(priority)
        return [t for t in self.list_tasks() if t.priority == priority]

    def filter_by_priority(self, priority: str) -> list[Task]:
        """Return tasks matching the given priority in creation order.

        Args:
            priority: One of "low", "medium", or "high".

        Returns:
            A new list of Task objects whose priority equals the given value.
            The list preserves the store's insertion order. If no tasks match,
            an empty list is returned.

        Raises:
            ValueError: If *priority* is not one of the accepted values.
        """
        priority = validate_priority(priority)
        return [t for t in self.list_tasks() if t.priority == priority]
