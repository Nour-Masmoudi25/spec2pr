# T08 — JSON strings without filesystem access

## Acceptance criteria

- AC-1: Expose dumps_store(store) and loads_store(text) in both tasklib.storage and tasklib. dumps_store returns a Unicode JSON string in the existing version-1 format; loads_store constructs an independent store, preserving IDs, order, values and next_id, including an empty store.
- AC-2: loads_store accepts only str and rejects malformed JSON, duplicate keys, nonstandard constants, invalid fields, duplicate IDs and unsupported versions with ValueError, using the existing file-loading rules.
- AC-3: dumps_store rejects non-TaskStore values and invalid directly mutated tasks with ValueError before any filesystem access. Neither function reads or writes files.
- AC-4: Existing public behavior must continue to work.

## Allowed changes

Only src/tasklib/. Do not modify tests or test configuration.
