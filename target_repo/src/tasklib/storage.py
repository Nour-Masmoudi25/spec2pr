"""Versioned UTF-8 JSON persistence with replacement after successful writing.

Saving prepares a complete validated document before opening a temporary file.
The temporary file lives beside the destination so os.replace does not cross
filesystems. It is closed before replacement, which is required on Windows.
No parent directories are created implicitly and filesystem errors propagate.
"""

import json
import os
from pathlib import Path
import tempfile
from typing import Any

from .models import Task
from .store import TaskStore
from .validation import validate_fields, validate_id


FORMAT_VERSION = 1


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject duplicate JSON keys instead of accepting the last occurrence.

    json.load calls this hook for every object, including nested task records.
    Without the hook a document could contain contradictory IDs or versions
    and lose evidence of the contradiction before schema validation begins.
    """
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON field: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    """Reject nonstandard JSON constants such as NaN and Infinity."""
    raise ValueError(f"Invalid JSON constant: {value}")


def _decode_document(document: object) -> TaskStore:
    """Validate the complete document before returning a new store.

    Version 1 has exactly version, next_id and tasks at the top level. Tasks
    must be an ordered list of complete records. An empty store still needs
    a positive next_id; gaps in the counter are allowed and preserved.
    """
    record = validate_fields(
        document,
        {"version", "next_id", "tasks"},
        name="Store document",
    )
    version = record["version"]
    if type(version) is not int or version != FORMAT_VERSION:
        raise ValueError(f"Unsupported store version: {version!r}")
    next_id = validate_id(record["next_id"], "Next ID")
    if not isinstance(record["tasks"], list):
        raise ValueError("Tasks must be a list")
    tasks = [Task.from_dict(item) for item in record["tasks"]]
    return TaskStore._restore(tasks, next_id)


def _write_temporary(destination: Path, text: str) -> Path:
    """Write, flush and close a sibling file, removing it on write failure.

    The caller owns the returned file and must replace or remove it. The
    destination remains unopened here, so a serialization or write failure
    cannot truncate a previous save. fsync flushes the file before replacement;
    it is not a guarantee against all filesystem or power-loss failures.
    """
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        return temporary
    except BaseException:
        if temporary is not None:
            _remove_temporary(temporary)
        raise


def _remove_temporary(path: Path) -> None:
    """Attempt cleanup without hiding the original write or replace error.

    A locked temporary file may survive a failed cleanup on Windows. This
    helper deliberately preserves the actionable original exception rather
    than replacing it with an unrelated deletion error.
    """
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def save_store(store: TaskStore, path: str | os.PathLike[str]) -> None:
    """Save a validated store as UTF-8 JSON, replacing an existing file.

    Validation and serialization finish before any output file is created.
    Invalid mutable task values, inconsistent IDs or counters raise ValueError.
    Permission errors and missing parent directories remain ordinary OSErrors.

    A sibling temporary file is used for replacement. Concurrent writers are
    not coordinated: the last successful replacement wins. Saving does not
    change the store, and it does not create missing parent directories.
    """
    if not isinstance(store, TaskStore):
        raise ValueError("Store must be a TaskStore")
    document = store._snapshot()
    text = json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False)
    destination = Path(path)
    temporary = _write_temporary(destination, text + "\n")
    try:
        os.replace(temporary, destination)
    finally:
        _remove_temporary(temporary)


def load_store(path: str | os.PathLike[str]) -> TaskStore:
    """Load and validate a version-1 document into an independent store.

    IDs, task order, priorities, completion flags and the next-ID counter are
    preserved. Titles follow the same whitespace normalization as construction.
    Every record must be valid; there is no partial import or silent skipping.

    Invalid JSON, non-UTF-8 input and invalid document values raise ValueError.
    FileNotFoundError, PermissionError and other filesystem exceptions remain
    unchanged so applications can handle missing files separately from bad data.
    """
    with Path(path).open("r", encoding="utf-8") as stream:
        document = json.load(
            stream,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    return _decode_document(document)
