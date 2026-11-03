# T10 — Pagination in creation order

## Acceptance criteria

- AC-1: TaskStore.paginate(offset=0, limit=10) returns a fresh list of live stored Task objects in creation order, including completed tasks. Return at most limit tasks starting at offset; zero limit or an offset beyond the end returns [].
- AC-2: Both arguments must be nonnegative integers excluding bool. Invalid arguments raise ValueError. No call changes tasks, creation order or the next-ID counter.
- AC-3: Existing public behavior must continue to work.

## Allowed changes

Only src/tasklib/. Do not modify tests or test configuration.
