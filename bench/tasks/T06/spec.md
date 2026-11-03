# T06 — Independent task and store copies

## Acceptance criteria

- AC-1: Task.copy() returns a new Task with the same four validated values; changing the copy cannot change the original.
- AC-2: TaskStore.clone() returns an independent TaskStore preserving IDs, creation order, all values and the next-ID counter, including gaps and an empty store.
- AC-3: copy and clone reject invalid directly mutated task values with ValueError and leave the original untouched.
- AC-4: Existing public behavior must continue to work.

## Allowed changes

Only src/tasklib/. Do not modify tests or test configuration.
