# T07 — Stable priority ordering

## Acceptance criteria

- AC-1: Task.priority_rank() returns the integer 0, 1 or 2 for low, medium or high respectively. Invalid directly mutated priorities raise ValueError.
- AC-2: TaskStore.list_by_priority() returns tasks from high to low priority with stable creation order for ties, including completed tasks and the empty store.
- AC-3: Return a fresh list of the stored objects, without changing tasks, creation order or the next ID.
- AC-4: Existing public behavior must continue to work.

## Allowed changes

Only src/tasklib/. Do not modify tests or test configuration.
