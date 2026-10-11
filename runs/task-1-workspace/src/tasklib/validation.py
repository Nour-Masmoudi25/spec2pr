"""Shared value validation for the public API and persisted documents.

Validation raises ValueError rather than silently converting values. In
particular, JSON booleans must not be accepted as integer identifiers, even
though bool is a subclass of int in Python. Titles are the one normalized
value: surrounding whitespace is removed without changing interior text.
"""

from typing import Any


PRIORITIES = ("low", "medium", "high")


def validate_title(value: object) -> str:
    """Return a stripped, nonempty title.

    Unicode and internal whitespace are preserved. Duplicate titles are
    legitimate: a task is identified by its ID, not by its text.
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Title must be a non-empty string")
    return value.strip()


def validate_priority(value: object) -> str:
    """Accept only the three lowercase priority names.

    No case conversion or whitespace stripping is performed for priorities,
    so a misspelled value cannot be silently stored as a different priority.
    """
    if not isinstance(value, str) or value not in PRIORITIES:
        raise ValueError("Priority must be low, medium, or high")
    return value


def validate_id(value: object, name: str = "Task ID") -> int:
    """Return a strictly positive integer, excluding booleans.

    The optional name provides context for errors about the next-ID counter.
    Numeric strings and floats are rejected rather than coerced.
    """
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def validate_completed(value: object) -> bool:
    """Return a real boolean; reject 0, 1 and truthy strings."""
    if not isinstance(value, bool):
        raise ValueError("Completed must be a boolean")
    return value


def validate_fields(
    value: object,
    required: set[str],
    optional: set[str] | None = None,
    *,
    name: str = "Record",
) -> dict[str, Any]:
    """Check the keys of a dictionary without copying or modifying it.

    This is used for both exact persisted records and batch-add entries
    where priority is optional. Unknown keys are rejected so misspellings
    do not disappear unnoticed. Field values are checked by the caller.
    """
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a dictionary")
    if any(not isinstance(key, str) for key in value):
        raise ValueError(f"{name} keys must be strings")
    keys = set(value)
    missing = required - keys
    unexpected = keys - required - (optional or set())
    if missing:
        raise ValueError(f"{name} is missing fields: {', '.join(sorted(missing))}")
    if unexpected:
        raise ValueError(
            f"{name} has unexpected fields: {', '.join(sorted(unexpected))}"
        )
    return value
