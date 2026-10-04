# T01 — Filter tasks by priority

## User story

As a library user, I want to retrieve tasks with a given priority

so that I can focus on the relevant tasks.

## Required interface

Add this method to TaskStore:

filter_by_priority(priority: str) -> list[Task]

## Acceptance criteria

- AC-1: Accept exactly "low", "medium", and "high".

  Any other string must raise ValueError.

- AC-2: Return only tasks whose priority matches the requested value.

- AC-3: Preserve the matching tasks' creation order.

- AC-4: Return an empty list if no tasks match,

  including when the store is empty.

- AC-5: Include both completed and incomplete matching tasks.

- AC-6: Do not change stored tasks or their order.

  Return a new list containing the matching Task objects.

- AC-7: Existing public behavior must continue to work.

## Allowed changes

Only files under src/tasklib/ may be modified.

Do not modify tests or test configuration.
