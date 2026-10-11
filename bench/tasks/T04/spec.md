# T04 — Summarize task counts

## Required interface

Add `TaskStore.summary() -> dict[str, int]`.

## Acceptance criteria

- AC-1: Return a dictionary with exactly total, completed and pending keys, containing integer counts. Empty stores return three zeros.
- AC-2: Count each task once regardless of title or priority; pending means completed is False, and total equals completed plus pending.
- AC-3: Reflect the current task state on every call, including completion, repeated completion, reopening and newly added tasks.
- AC-4: Return a new dictionary on every call. Editing it must not change the store; summary must not mutate tasks, order or ID allocation. Existing behavior must keep working.

## Allowed changes

Only files under `src/tasklib/` may change. Do not modify tests or test configuration. This task is independent of the other benchmark tasks.
