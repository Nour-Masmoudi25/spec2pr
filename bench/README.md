# Person B — provisional local benchmark validation

T01 is the first prepared exercise. Its goal is to add priority filtering to
TaskStore. The target library remains unchanged and does not contain the answer.

## Files and roles

- `tasks/T01/spec.md`: the request that the agent may read.
- `tasks/T01/hidden_tests/test_filter_priority.py`: 16 evaluator-only test cases.
- `tasks/T01/reference.patch`: our known-good implementation, not given to the agent.
- `tasks/T01/task.json`: the baseline fingerprint, explicit FAIL_TO_PASS case IDs
  and acceptance-criterion mapping. All baseline visible tests are PASS_TO_PASS.
- `validate.py`: checks the exercise using two temporary target copies.
- `_pytest_report.py`: distinguishes genuine failed test calls from collection,
  setup, teardown and skipped-test problems.
- `tests/test_validator.py`: seven positive and negative checks of the evaluator.

Only the target checkout and selected specification belong in the agent sandbox.
Keep this entire `bench` directory outside that mount, including Git history
that could expose reference solutions. "Hidden" means inaccessible to the agent
during its run, not necessarily unpublished in the submitted project repository.

## Run from the project root in PowerShell

Prerequisites: Git available on PATH, and pytest installed in the local .venv.
No model API, API key, credits, or additional Python dependency is used.

```powershell
.\.venv\Scripts\python.exe bench\validate.py bench\tasks
```

Expected for the currently prepared task set:

```text
T01: VALID
1/1 tasks valid (local provisional validation)
```

This means one prepared task is valid; it does **not** mean all five Week 1
tasks are complete. To save the report:

```powershell
.\.venv\Scripts\python.exe bench\validate.py bench\tasks --report docs\T01-validation.json
```

Check the validator itself:

```powershell
.\.venv\Scripts\python.exe -m pytest bench\tests -q
```

The tests introduce an already-passing hidden test, an invalid fixture, a skip,
a broken reference implementation, a wrong baseline fingerprint and a patch
touching visible tests. Each must be rejected. All edits are in temporary
copies. The valid-task test also verifies the real baseline is unchanged.

## What VALID means

1. Baseline contents match task.json's SHA-256 fingerprint.
2. Every declared hidden case is collected and fails during its test call.
3. All visible regression cases pass on the baseline.
4. The reference patch touches source files under src/tasklib/ only.
5. The same hidden and visible cases all pass after applying the patch.

Collection/setup/teardown errors, missing cases, skips and timeouts invalidate
the task. Text newlines are normalized in temporary copies and patches to
support Windows and Linux without changing the original target files.

## Current results and limits

On Python 3.13.1, T01 has 16 hidden failures and 127 visible passes before the
fix; afterward all 143 cases pass. The validator's seven self-checks pass.

This script runs **trusted reference code locally**, not agent-generated code
in a security sandbox. It is a development check, not the final scored runner.
Each run creates disposable copies outside the original checkout and never
applies the reference patch to `target_repo`.

`base_commit` is intentionally null: the baseline has not been committed and
verified in the partner's Python 3.12 sandbox. A content fingerprint temporarily
detects changes but does not substitute for that final commit. This validator
explicitly refuses non-null base commits until Git-checkout validation is added.

Do not update the fingerprint merely to suppress a mismatch: review baseline
changes, rerun task validation, then record the agreed baseline. Final integration
must support the agreed immutable Git baseline, Docker evaluation and explicit
PASS_TO_PASS IDs recorded from it before scored agent runs.

T02–T05, the agent scorer, fifteen real runs, and trace/cost reporting remain
future work. No agent performance has been measured by these checks.
