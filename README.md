# Spec → PR Pipeline — Week 1

A single agent implements a specification in a small Python library. The
benchmark checks its submitted code against existing tests and evaluator-only
acceptance tests. This repository contains Person A's agent and sandbox and
Person B's target library and five-task benchmark.

## Setup

Use Python 3.13 locally, Git, and Docker Desktop running Linux containers.
The sandbox uses Python 3.12.

Until PR #1 is merged, check out `codex/person-b-day2` after cloning to use
the complete benchmark described here.

```powershell
git clone https://github.com/Nour-Masmoudi25/spec2pr.git
cd spec2pr
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe bench/validate.py bench/tasks
```

Local checks do not need an API key. See [tasklib usage](target_repo/README.md)
and the [benchmark guide](bench/README.md).

## Run the real benchmark

```powershell
docker build -t sandbox:py312 .
$env:GROQ_API_KEY = "<your key>"
.\.venv\Scripts\python.exe bench/validate.py bench/tasks --backend docker
.\.venv\Scripts\python.exe bench/run.py --agent single --tasks bench/tasks --n 3
```

On systems with Make and the virtual environment activated, `make bench`
builds the sandbox, validates the tasks in Docker and starts these 15 runs.
The key stays on the host; the agent's shell container has no network and
receives only a fresh target checkout. Keep keys out of commits and screenshots.

Generated runs are saved under `runs/benchmarks/<batch>/<task-repeat>/`.
The batch summary records the Git commit, dirty-worktree status, pass rate,
median configured cost estimate, median model calls and consistency across
repetitions. [RESULTS.md](RESULTS.md) distinguishes checks from real agent results.

## Team handoff

- **Person B:** target library, task specifications, hidden tests, reference
  patches, validator and scorer.
- **Person A:** model/API configuration, agent behavior and sandbox operation.
- **Together:** Python 3.12 verification, 15 actual agent runs, two annotated
  traces and the final baseline decision.

The baseline deliberately lacks filtering, search, deletion, statistics and CSV.
Their reference solutions belong only in `bench/tasks/*/reference.patch`.
Do not add these features to `target_repo` before the benchmark.
