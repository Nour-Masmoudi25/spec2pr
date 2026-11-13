# Spec → PR Pipeline — Weeks 1 and 2

A single agent implements a specification in a small Python library. The
benchmark checks its submitted code against existing tests and evaluator-only
acceptance tests. This repository contains Person A's agent and sandbox and
Person B's target library, ten-task benchmark and Week 2 contract checks.

## Setup

Use Python 3.13 locally, Git, and Docker Desktop running Linux containers.
The sandbox uses Python 3.12.

Week 1 evidence is archived in `evals/week1`. The Week 2 B work is on
`codex/person-b-weeks1-2` until its pull request is merged.

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
builds the sandbox, validates the tasks in Docker and starts 30 runs (10 tasks × 3).
The historical Week 1 row remains the original five tasks × three runs.
The key stays on the host; the agent's shell container has no network and
receives only a fresh target checkout. Keep keys out of commits and screenshots.

Generated runs are saved under `runs/benchmarks/<batch>/<task-repeat>/`.
The batch summary records the Git commit, dirty-worktree status, pass rate,
median configured cost estimate, median logged steps and consistency across
repetitions. [RESULTS.md](RESULTS.md) distinguishes checks from real agent results.

## Team handoff

- **Person B:** target library, task specifications, hidden tests, reference
  patches, validator, scorer, contract tests and evidence analysis.
- **Person A:** model/API configuration, agent behavior and sandbox operation.
- **Week 2 integration:** A supplies actual planner outputs, hooks and team
  transcripts; B validates them using [the contracts](ARCHITECTURE.md).

The baseline deliberately lacks filtering, search, deletion, statistics and CSV.
Their reference solutions belong only in `bench/tasks/*/reference.patch`.
Do not add these features to `target_repo` before the benchmark.

## Week 2 checks without a model

```bash
python -m pytest tests/contracts -q
python bench/validate.py bench/tasks
python bench/validate.py bench/tasks --backend docker
```

Both validators should report **10/10 tasks valid**. Once A supplies ten real
planner outputs named `T01.json` through `T10.json`:

```bash
python bench/check_plans.py bench/tasks runs/week2/plans --report runs/week2/plan-check.json
```

The report destination must be new; create its parent folder first. Tests use
synthetic fixtures and do not claim ten actual plans exist. See the
[Person B status and handoff](docs/person-b-weeks1-2.md) for verified checks and
remaining integration work.
