# Person B — ten-task benchmark

| Task | Required method | Hidden cases |
|---|---|---:|
| T01 | filter_by_priority(priority) | 16 |
| T02 | search(query) | 14 |
| T03 | delete(task_id) | 16 |
| T04 | summary() | 8 |
| T05 | to_csv() | 11 |
| T06 | Task.copy(), TaskStore.clone() | 11 |
| T07 | Task.priority_rank(), TaskStore.list_by_priority() | 10 |
| T08 | dumps_store(store), loads_store(text) | 18 |
| T09 | rename_many(updates) | 13 |
| T10 | paginate(offset=0, limit=10) | 18 |

Each directory contains a spec, hidden tests, a reference patch and task.json.
The metadata records explicit FAIL_TO_PASS and PASS_TO_PASS IDs, acceptance
mappings, a Git baseline and a normalized content fingerprint. Every task is
independent and starts from `dd0519be0d15a7b370dadb342319b982b2bfcaef:target_repo`.
The exported tree has 127 visible tests. It includes no Git history or benchmark
answers. This baseline is fixed for reproducibility. All ten tasks were checked
under local Python 3.13.1 and Docker Python 3.12 on 2026-11-03; see
`evals/week2/validation-local.json` and `evals/week2/validation-docker.json`.
T06, T07 and T08 each require two source files in their reference fix.

## Validate the exercises

From the repository root, with pytest installed:

```bash
python bench/validate.py bench/tasks --report validation-local.json
python bench/validate.py bench/tasks --backend docker --report validation-docker.json
python -m pytest -q
```

Expected: **10/10 tasks valid**. For each task, the validator exports the committed
baseline, verifies its hash and checks all 127 visible tests pass. Every hidden
test must fail during its test call; collection errors, fixture failures, skips
and timeouts do not qualify. After applying the reference patch to a separate
copy, every visible and hidden test must pass. Patches may only edit src/tasklib.

The local backend is for trusted reference code. Model-generated code always
uses Docker. Text newlines are normalized for Windows/Linux compatibility.
The self-tests include a hidden test that already passes: the validator must
reject that task. They also reject broken fixes, wrong hashes, fixture errors,
skips, altered visible tests, and unsafe execution choices.

## Score an agent

```bash
python bench/run.py --agent single --tasks bench/tasks --n 3
```

This now selects 30 attempts. The archived Week 1 result uses only T01–T05;
`bench/aggregate.py` deliberately keeps that five-task definition. Do not mix
the new tasks into row 0. Each task also provides a safe planner input
`spec.json` with the full specification and numbered ACs. Its budget is a
configurable proposed ceiling; these validation commands do not call a model.

The runner checks Docker and API configuration before starting. Each attempt
gets a fresh exported checkout and only its specification. After the agent
stops, the runner rejects changes outside src/tasklib, copies the submitted
source onto another clean checkout and introduces hidden tests only there.
The evaluator's test results are never returned to the model.

The Docker command uses no network, UID 1000, a read-only root, dropped
capabilities, a process limit, a memory limit and a temporary /tmp filesystem.
A timeout forcibly removes the named container. /tmp is intentionally writable;
it is ephemeral and does not expose another host directory. Only /workspace is
a writable host mount. This is process isolation, not a proof against malicious
code trying to tamper with its own grading process.

Options: `--steps 20`, `--timeout 60` (seconds per command/evaluation),
`--image sandbox:py312`, `--output runs/benchmarks`. Host API requests have a
60-second timeout and SDK retries are disabled so each attempt is logged.
There is no dollar-budget cap: check available API credits before a full run.

## Offline controls

These exercise grading without a model or API key:

```bash
python bench/run.py --agent reference --backend local --tasks bench/tasks --n 3
python bench/run.py --agent noop --backend local --tasks bench/tasks --n 1
```

The reference control should pass 15/15; the unchanged baseline should pass 0/5.
These are scorer checks, **not agent performance**. They have zero model calls
and empty trace files. Never label them as solved or failed model traces.

## Results and traces

Each attempt writes trace.jsonl, submission.json and result.json.
Each model call contributes one trace line, including failed API attempts.
A line can contain several tool inputs, exit codes and truncated outputs.
Usage is counted once per call. The existing configured input/output rates are
estimates; unknown API usage stays null rather than being counted as free.
A batch with any unknown cost reports median cost as null.

A task passes only when **all** its declared hidden and visible tests pass.
Pass rate counts successful attempts / total attempts, including evaluation
errors as unsuccessful attempts. Median steps uses all attempts. With n=3,
all_repetitions_pass_rate is pass^3: the fraction of tasks passing all three
attempts. It is not pass@3. The summary also counts tasks solved at least once.
An exit code of 1 means an infrastructure/evaluation error; ordinary failed
solutions are valid benchmark results and do not cause a nonzero exit.

For a completed real batch, search only its trace.jsonl files for hidden-test
filenames (test_filter_priority.py and test_acceptance.py); expect zero hits.
Inspect the actual mount list too: zero text matches alone cannot prove isolation.
Select one successful and one failed **real** run for annotated traces.
Keep the original trace files unchanged and place explanations in a separate
Markdown document.

The old `runs/task-1-workspace` is a historical demo, not the benchmark
baseline. Its duplicate method has been removed. The agent entry point now
uses a fresh benchmark checkout on every invocation.
