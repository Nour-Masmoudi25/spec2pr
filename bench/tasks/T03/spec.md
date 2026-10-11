# T03 — Delete a task

## Required interface

Add `TaskStore.delete(task_id: int) -> Task`.

## Acceptance criteria

- AC-1: Delete exactly the task with the supplied ID and return the original removed Task object. Other tasks keep their order and values.
- AC-2: Validate IDs as positive integers excluding bool. Invalid IDs raise ValueError; valid absent IDs (including a second deletion) raise KeyError. Errors do not mutate the store.
- AC-3: Never reuse a deleted ID or lower the next-ID counter, including after deleting all tasks.
- AC-4: JSON save/load preserves remaining tasks, their order and the next-ID counter after deletion. Existing public behavior must keep working.

## Allowed changes

Only files under `src/tasklib/` may change. Do not modify tests or test configuration. This task is independent of the other benchmark tasks.
