# T05 — Export tasks as CSV

## Required interface

Add `TaskStore.to_csv() -> str`.

## Acceptance criteria

- AC-1: Return CSV text, not a file. The header is exactly id,title,priority,completed in that order. An empty store returns only the header followed by a newline.
- AC-2: Export one row per task in creation order with its current ID, title, priority and completion state. Write booleans as lowercase true and false.
- AC-3: Use commas as separators, double quotes for quoting, doubled embedded quotes and a newline (\n) record terminator, including after the final record. Quote fields containing commas, double quotes, carriage returns or newlines; preserve Unicode and embedded newlines exactly.
- AC-4: Do not mutate tasks, order or ID allocation. Repeated calls reflect current state and return identical text when state is unchanged. Existing public behavior must keep working.

## Allowed changes

Only files under `src/tasklib/` may change. Do not modify tests or test configuration. This task is independent of the other benchmark tasks.
