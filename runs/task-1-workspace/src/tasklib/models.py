"""Task values and their explicit dictionary representation.

Tasks remain mutable to preserve the original library's object semantics.
Construction and serialization validate values; ordinary attribute assignment
does not. Store.update is the preferred way to change a title or priority.
"""

from dataclasses import dataclass
from typing import Any

from .validation import (
    validate_completed,
    validate_fields,
    validate_id,
    validate_priority,
    validate_title,
)


@dataclass
class Task:
    """A single task with an identity, title, priority and completion state.

    IDs are positive integers. Titles are stripped at construction; priorities
    default to medium and new tasks default to incomplete. ID assignment is
    normally handled by TaskStore rather than by application code.

    An existing task's ID should not be changed: the store indexes tasks by
    that ID and saving detects a mismatch between the index and the object.
    """

    id: int
    title: str
    priority: str = "medium"
    completed: bool = False

    def __post_init__(self) -> None:
        """Validate construction before normalizing the title."""
        validate_id(self.id)
        title = validate_title(self.title)
        validate_priority(self.priority)
        validate_completed(self.completed)
        self.title = title

    def to_dict(self) -> dict[str, Any]:
        """Return a fresh validated record containing all four fields.

        Revalidation matters because callers retain mutable references to
        tasks. A corrupted value must not make it into a saved document.
        Normalizing the returned title does not mutate the original object.
        """
        return {
            "id": validate_id(self.id),
            "title": validate_title(self.title),
            "priority": validate_priority(self.priority),
            "completed": validate_completed(self.completed),
        }

    @classmethod
    def from_dict(cls, data: object) -> "Task":
        """Build a task from an exact four-field record.

        All fields are mandatory in serialized data, even those that have
        constructor defaults. Missing fields can indicate a damaged file,
        so loading does not silently invent replacement values.
        """
        record = validate_fields(
            data,
            {"id", "title", "priority", "completed"},
            name="Task record",
        )
        return cls(
            id=record["id"],
            title=record["title"],
            priority=record["priority"],
            completed=record["completed"],
        )
