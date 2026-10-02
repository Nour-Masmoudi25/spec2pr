# tasklib — Week 1 target library

A small Python library for the Spec → PR benchmark. It manages tasks in memory
and saves or loads versioned JSON files. Runtime code uses only the standard
library; tests require pytest. The code targets Python 3.12 and 3.13.

## Run the visible tests

From the parent project directory on Windows:

```powershell
.\.venv\Scripts\python.exe -m pytest -c target_repo\pytest.ini target_repo\tests -q
```

From this `target_repo` directory in a Python environment with pytest installed:

```bash
python -m pytest -q
```

These are baseline regression tests, not hidden benchmark tests. The original
nine cases remain in `tests/test_store.py`.

## Try the library

When using a standalone script or interpreter, make `src` importable. From
this directory in PowerShell:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
..\.venv\Scripts\python.exe
```

Then run:

```python
from tasklib import Task, TaskStore, load_store, save_store

store = TaskStore()
task = store.add("Read the guide", priority="high")
store.update(task.id, title="Read the Week 1 guide")
store.complete(task.id)
store.reopen(task.id)
store.add_many([{"title": "Write tests"}, {"title": "Review", "priority": "low"}])
print(store.list_tasks())

save_store(store, "tasks.json")
restored = load_store("tasks.json")
assert restored.list_tasks() == store.list_tasks()
```

## Public API and behavior

| API | Result |
|---|---|
| `Task(id, title, priority="medium", completed=False)` | A validated, mutable task |
| `Task.to_dict()` / `Task.from_dict(data)` | Independent dictionary / task conversion |
| `TaskStore.add(title, priority="medium")` | Append and return a task with a fresh ID |
| `get(task_id)` | Return the live stored object |
| `list_tasks()` | New list of live objects in creation order |
| `complete(task_id)` / `reopen(task_id)` | Set completion and return the task; idempotent |
| `update(task_id, *, title=None, priority=None)` | Validate supplied fields, then update atomically |
| `add_many(items)` | Validate the entire list, then append and return all new tasks |
| `save_store(store, path)` | Write a validated UTF-8 JSON document; return `None` |
| `load_store(path)` | Return a new, independently allocated store |

- Titles must be nonempty strings after stripping outer whitespace. Unicode,
  interior whitespace and duplicate titles are supported.
- Priorities are exactly `low`, `medium`, or `high` (case sensitive).
- IDs are positive integers; booleans, strings and floats are not accepted.
- Completion flags must be booleans.
- Invalid public values raise `ValueError`; a valid but absent ID raises
  `KeyError`. Filesystem errors such as `FileNotFoundError` propagate.
- `None` in `update` means unchanged. Omitting both fields is a no-op for an
  existing task. Invalid updates and batches leave data and ID allocation intact.
- Batch entries require `title` and optionally `priority`; other keys are errors.
- Returned tasks are live references. Prefer store methods for changes. Direct
  attribute edits bypass immediate validation but are checked at serialization.
  Changing a stored task's ID causes saving to fail because its index differs.

## JSON format and guarantees

```json
{
  "version": 1,
  "next_id": 2,
  "tasks": [
    {"id": 1, "title": "Read the guide", "priority": "high", "completed": false}
  ]
}
```

Every shown field is mandatory; extra fields, duplicate JSON keys, duplicate
task IDs and unknown versions are rejected. `next_id` must be a positive integer
larger than every saved ID. Array order and gaps in IDs are preserved. Titles
are normalized using the same rules as task construction.

Saving validates and serializes before opening any output, writes and flushes
a sibling temporary file, closes it, then replaces the destination. Failure
before replacement preserves an existing save. Temporary-file cleanup is best
effort if the operating system prevents deletion. Parent directories must
already exist. This is single-writer persistence, not a transaction system for
concurrent processes or a guarantee against every power-loss scenario.

## Deliberately missing benchmark features

1. T01: `filter_by_priority(priority)`
2. T02: `search(query)`
3. T03: `delete(task_id)`
4. T04: `summary()`
5. T05: `to_csv()`

Do not add these to the baseline or write visible tests that require them.
The evaluator's hidden tests and reference fixes belong outside this directory.
Mount only the target checkout into the agent sandbox, never the full project.

## Reproduce the size report

From this directory, run `python tools/count_lines.py`. It reports physical
lines, blank lines, code-bearing lines and comment/docstring-only lines for
the five library modules and tests separately. Tests are not counted toward
the library's 500–800 documented source-line target.

See `../docs/tasklib-validation.md` for observed test results and compatibility
checks. The library alone does not complete the five-task benchmark or Week 1.
