# T02 — Search task titles

## Required interface

Add `TaskStore.search(query: str) -> list[Task]`.

## Acceptance criteria

- AC-1: Match a substring anywhere in the title, using Unicode str.casefold() on both title and query.
- AC-2: An empty query matches all tasks; preserve query whitespace (do not strip it). Return [] for an empty store or no matches.
- AC-3: Reject any non-string query with ValueError, including None, numbers, booleans, lists and dictionaries.
- AC-4: Return a fresh list of the original Task objects in creation order, including completed tasks and duplicate titles.
- AC-5: Do not mutate tasks, their order or ID allocation. Existing public behavior must keep working.

## Allowed changes

Only files under `src/tasklib/` may change. Do not modify tests or test configuration. This task is independent of the other benchmark tasks.
