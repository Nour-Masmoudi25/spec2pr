# Week 1 results

## Real agent benchmark

| Row | Agent | Tasks × runs | Pass rate | Median cost (USD estimate) | Median model calls | Commit |
|---|---|---|---|---|---|---|
| 0 | Single agent | 5 × 3 planned | Not run | Not measured | Not measured | Pending |

No complete 15-run model batch has been executed here. Docker Desktop was
started on 2026-10-11, but the Linux engine returned HTTP 500 on its info
endpoint. The local environment also lacks the Groq/dotenv packages and project
API configuration. Reference solutions are not evidence of agent performance.

## Verified locally

- Python 3.13.1: **153 tests pass** (127 library tests and 26 harness checks).
- **5/5 tasks valid**: each of the 65 hidden cases fails before its reference
  fix and passes afterward; all 127 visible cases pass in both states.
- Baseline: `dd0519be0d15a7b370dadb342319b982b2bfcaef:target_repo`.
- [Validation evidence](docs/benchmark-validation-local.json).
- The validator rejects a hidden case that already passes on the baseline.
- Offline tests verify a fresh agent workspace without hidden tests/reference
  patches and one trace line per model request, including multiple-tool replies.

## Scorer controls (no model)

Verified on clean evaluation commit `3f2df171ed97dd8cbae4fd48b2de78d903ee9c7e`,
Python 3.13.1, local backend:

| Control | Attempts | Passed | Median model calls | API cost |
|---|---:|---:|---:|---:|
| Reference patches | 15 | 15 | 0 | $0 |
| Unchanged baseline (noop) | 5 | 0 | 0 | $0 |

Evidence: [reference report](docs/scorer-reference-local.json) and
[noop report](docs/scorer-noop-local.json). The reference control passes all
three repetitions for all five tasks. These rows verify the scorer; they do
not fill the real-agent row 0.

## Pending joint checks

- Validate all five tasks in the Python 3.12 Docker image.
- Run the single agent 5 × 3 times and record its actual summary and Git commit.
- Demonstrate at least two tasks solved at least once.
- Search real traces for hidden-test filenames and annotate one solved and one
  failed run. Historical prototype traces are not the new benchmark's row 0.

See [the benchmark guide](bench/README.md) for exact commands and metric definitions.
