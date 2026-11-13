# Results

## Row 0: single agent baseline (Week 1)

| Row | Agent | Tasks × runs | Pass rate | Median known cost (USD, lower bound) | Median logged steps | Tasks solved at least once | pass^3 | Commit |
|---|---|---|---|---|---|---|---|---|
| 0 | Single agent (one `bash` tool) | 5 × 3 | **12/15 (80.0%)** | 0.004149 | 6 | 4/5 | 80.0% | `834104fcf4b11b687a336b0e633daa1b6948be83` |

Runs were made between 2026-10-27 and 2026-10-30 on Windows with Docker Desktop,
model `openai/gpt-oss-120b` through the Groq API, sandbox image `sandbox:py312`.
All five official batches were run from the same commit with a clean working tree
(`working_tree_dirty: false`). The numbers come from `bench/aggregate.py`, which
refuses mixed commits, dirty trees and incomplete batches.

How to read the columns:

- **Cost** is a lower bound. Model calls that Groq refused report no token usage,
  so their cost is unknown and left out; the full billed cost is unknown. The
  configured rates are $0.15 per million input tokens and $0.60 per million output
  tokens. They are estimates, not invoices.
- **Steps** count trace rows (one per model request, including refused requests).
  Across the 15 runs, 15 rows had no usage because the request was refused. The
  frozen agent does not log each internal rate-limit wait as a separate row.
- **pass^3** is the share of tasks that passed in all three repetitions. It is not
  pass@3.

### Per task

| Task | Feature | Passed | Batch | Notes |
|---|---|---:|---|---|
| T01 | `filter_by_priority` | 3/3 | `20261027T192036Z-a2cd78af` | |
| T02 | `search` | 3/3 | `20261028T222638Z-7615e9d3` | Rerun of a discarded batch (see below) |
| T03 | `delete` | 3/3 | `20261028T224535Z-63183b8d` | |
| T04 | `summary` | 3/3 | `20261029T121733Z-d3d08b2b` | Rerun of a discarded batch (see below) |
| T05 | `to_csv` | **0/3** | `20261030T143136Z-973a4f26` | All three submissions failed to import |

Raw `summary.json`, `result.json`, `trace.jsonl` and `submission.json` files for
these batches are kept unchanged in `evals/week1/`.

### Why T05 failed

All three T05 attempts wrote `lineterminator='\n'` inside a Python string that the
agent passed to a heredoc. The `\n` became a real line break in `store.py`, which
left an unterminated string literal. Pytest could not import `tasklib`, so the
runner reported `error` (collection failure) rather than `failed_tests`. Both
statuses count as unsuccessful attempts in the pass rate.

This failure is partly caused by the working rules in `bench/prompt.py`, which show
the agent a normal triple-quoted string for the appended method. That worked for
T01 to T04 but not for the one task that needs escape sequences. The prompt is not
changed for row 0: the baseline stays frozen so all 15 runs are comparable.

## Batches not counted

| Batch | Task | Reason for exclusion |
|---|---|---|
| `20261027T200253Z-f2998abb` | T02 | Daily Groq token quota ran out during runs 2 and 3 (every wait was capped at 60 s). Rerun in full, not only the failed attempts. |
| `20261029T095634Z-4d3fb0a2` | T04 | Grading of run 2 hit a host timeout of about 6 minutes. The submitted `summary()` passed all 8 hidden cases when checked separately, so the failure was in the grading environment. Rerun in full. |
| `20261029T122721Z-30a4dd31` | T05 | Daily quota ran out; runs ended after about 2 steps. Rerun in full. |

Earlier batches from 2026-10-27 were made while the prompt, retry and cost logging
were still being fixed, from uncommitted or older code. They are debugging runs and
are not part of row 0.

## Checks

| Check | Result | Evidence |
|---|---|---|
| Task validator, Python 3.12 Docker image | 5/5 tasks valid | [report](docs/benchmark-validation-docker.json) |
| Task validator, local Python 3.13.1 | 5/5 tasks valid | [report](docs/benchmark-validation-local.json) |
| Hidden test that already passes is rejected | Covered by a self-test (`test_trap_rejects_hidden_case_already_passing`) | `bench/tests/test_validator.py` |
| Hidden-test file names in the 15 traces | 0 occurrences, 15 trace files, 79 JSON rows | `evals/week1/official-leak-check.json` |
| Sandbox: no network, not root, read-only system, writes only in `/workspace` | All four checks held | [sandbox proof](docs/sandbox-proof.md) |
| Scorer controls, no model (reference patches 15/15, unchanged baseline 0/5) | Passed | [reference](docs/scorer-reference-local.json), [noop](docs/scorer-noop-local.json) |

The scorer controls make no model calls and are not agent performance. The leak
check is a text search; it does not by itself prove isolation of every file.

## Trace analysis

The [annotated official traces](docs/annotated-traces.md) explain T01-1 (solved)
and T05-1 (syntax failure followed by an API limit), with exact JSONL line
references. The original evidence is unchanged. Internal API retries are not
logged individually in the frozen agent; the annotations document this limit.

Week 2 benchmark and contract checks are recorded separately in
[the Person B handoff](docs/person-b-weeks1-2.md); they are not new agent scores.

See [the benchmark guide](bench/README.md) for commands and metric definitions.

## Known limit: 8,000 tokens per minute

On the Groq plan used here, `openai/gpt-oss-120b` accepts at most 8,000 tokens per
minute. The conversation grows at every step (the prompt alone is about 4,600
tokens), so a request that would exceed 8,000 tokens is refused with HTTP 413
("Request too large"). Waiting does not help, because the request itself is too
big, and the agent stops with `api_error`.

| Measure over the 15 official runs | Count |
|---|---:|
| Runs with a request refused as too large | 8 |
| of which still passed (code was already correct) | 6 |
| of which failed (both are T05 runs) | 2 |
| Runs that ended with `api_error` instead of the model finishing | 9 |

Consequences for reading row 0:

- The runner grades the code left on disk, so a run cut off after a correct edit
  still counts as passed. The pass rate does not depend on the model finishing.
- A task that needs several repair steps can run out of room before it succeeds.
  The results therefore measure the agent together with this plan's limit, and the
  limit probably lowers the pass rate on harder tasks.
- Any later comparison between agents (for example a multi-agent pipeline, which
  sends more tokens) must be run under the same limit or on a plan with a higher
  one, or the comparison will not be fair.

Possible mitigations, none applied to row 0: shorter tool output (currently up to
4,000 characters per command), dropping old tool output from the conversation, or
a plan or model with a higher per-minute limit.
