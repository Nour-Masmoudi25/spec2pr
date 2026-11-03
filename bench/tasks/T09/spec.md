# T09 — Atomic batch rename

## Acceptance criteria

- AC-1: TaskStore.rename_many(updates) accepts a list of dictionaries with exactly id and title. Validate every entry before changing any task. Titles follow existing trimming and validation rules; IDs follow existing validation rules. Duplicate IDs, missing/unexpected fields and invalid inputs raise ValueError; a valid absent ID raises KeyError.
- AC-2: Return the renamed stored Task objects in request order; empty input returns []. Keep creation order, priorities, completion flags and next-ID counter unchanged. Invalid batches leave all existing tasks and the counter unchanged.
- AC-3: Existing public behavior must continue to work.

## Allowed changes

Only src/tasklib/. Do not modify tests or test configuration.
