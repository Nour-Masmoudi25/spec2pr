# Week 1 benchmark plan

## Target library

tasklib is a small in-memory task-management library.

The baseline supports:
- Adding a task with a title and priority.
- Retrieving a task by ID.
- Listing tasks in creation order.
- Marking a task as completed.
- Reopening tasks and updating their titles or priorities.
- Adding tasks in validated batches.
- Saving and loading versioned JSON files.

## Proposed benchmark tasks

| ID | Feature | Required method |
|---|---|---|
| T01 | Filter tasks by priority | filter_by_priority(priority) |
| T02 | Search titles, ignoring case | search(query) |
| T03 | Delete a task by ID | delete(task_id) |
| T04 | Count total, completed and pending tasks | summary() |
| T05 | Export tasks as CSV text | to_csv() |

## Evaluation rules

- Each task starts from its recorded baseline commit.
- Tasks are independent: none requires another task's solution.
- The agent receives the specification and target project.
- Hidden tests and reference fixes remain outside the agent workspace.
- Existing visible tests must keep passing.
- Every acceptance criterion must be stated before writing its tests.

## Day 1 status

- Initial library: implemented.
- Initial visible tests: 9 passing.
- Five benchmark tasks: proposed.
- Full specifications, hidden tests and reference fixes: pending.
- Benchmark validation and agent runs: not yet performed.

## Library completion update

- The five-module library now has 504 physical source lines, including
  documentation and blank lines; see `tasklib-validation.md` for the breakdown.
- The original nine test cases are preserved; the full visible suite has
  127 passing cases under Python 3.13.1.
- T01's existing specification has been cleaned up without changing its scope.
- All five benchmark features remain intentionally unimplemented.
- Python 3.12 sandbox verification is pending because the local Docker Linux
  engine was unavailable. No benchmark baseline commit has been frozen.

## Day 2 — first task validated locally

- T01 now has its specification, 16 hidden acceptance cases, a reference patch,
  explicit FAIL_TO_PASS IDs and a baseline content fingerprint.
- Before the reference patch: 16 hidden failures and 127 visible passes.
- After the reference patch: all 143 cases pass.
- `bench/validate.py` reports 1/1 prepared tasks valid under Python 3.13.1.
- Seven validator self-checks pass, including the already-passing hidden-test
  trap, an incorrect reference solution and a patch attempting to edit tests.
- The target library has not been modified or committed. Hidden tests and the
  answer are outside the target checkout.
- These are provisional local checks, not Docker or model-agent executions.
  Python 3.12 verification and a frozen Git baseline remain pending.
- Four other tasks and the agent scorer still need to be prepared. See
  `../bench/README.md` and `T01-validation.json` for commands and evidence.
