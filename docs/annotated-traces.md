# Week 1 annotated model traces

Status: template only. Fill this document after selecting and checking the real
evidence. No reference/noop control or synthetic test fixture is an agent run.
Keep the original trace.jsonl, result.json and summary.json unchanged.

## Evidence selection

- The handoff dated 27 October reports T01 at 3/3 in
  `runs/benchmarks/20261027T192036Z-a2cd78af`. Those files are not tracked in this
  checkout; obtain the original batch before filling in the successful example.
- The same handoff excludes the entire T02 batch
  `runs/benchmarks/20261027T200253Z-f2998abb` because quota exhaustion interrupted
  its execution. Do not count only its successful attempt in the official row.
- Prefer a failed attempt from a completed official batch for the failure
  example. If every official attempt passes, a historical debugging trace may
  illustrate failure, but label it separately and exclude it from row 0.
- The suggested historical directory `docs/evidence-T02-before-timeout-fix` is
  also absent here. Do not invent its contents or its commit.

## Successful trace

Evidence status: **not yet inspected**.

| Item | Fill from the original evidence |
|---|---|
| Task and acceptance criteria | TODO |
| Batch directory / run ID | TODO |
| summary.json / result.json / trace.jsonl | TODO |
| evaluation_commit / base_commit | TODO |
| working_tree_dirty | Must be false for an official batch |
| Official result or historical example | TODO |
| Hidden / visible tests passed | TODO; read result.json |
| Logged steps / known cost lower bound / unknown-usage rows | TODO |
| Leak-check evidence | TODO; include the selected directory and check result |

| Trace line(s) | Observed action and tool exit code | Interpretation supported by the evidence |
|---|---|---|
| TODO | How the model receives or inspects the target code | Explain which requirements it addresses |
| TODO | The command that changes source code | Explain the implementation choice |
| TODO | Visible test execution and output | Distinguish visible tests from later hidden grading |
| TODO | Final response or step-limit exit | Compare the model's claim with result.json |

Write a short explanation of why the submitted code passed, citing exact trace
line numbers. A final message saying "done" does not prove the hidden tests pass.
Mention unknown billed usage rather than replacing it with zero.

## Failed trace

Evidence status: **not yet inspected**.

| Item | Fill from the original evidence |
|---|---|
| Task / batch / run ID | TODO |
| summary.json / result.json / trace.jsonl | TODO |
| evaluation_commit / base_commit | TODO |
| Official attempt or excluded debugging example | TODO; explain any exclusion |
| Failure category | Wrong implementation, API rejection, quota, timeout or evaluator error |
| Hidden / visible results and agent_status | TODO |
| Logged steps / known cost lower bound / unknown-usage rows | TODO |
| Leak-check evidence | TODO |

| Trace line(s) | Observed event | Consequence and supported explanation |
|---|---|---|
| TODO | First sign of the failure | State what the trace actually shows |
| TODO | Attempted repair or API error | Distinguish model behavior from infrastructure |
| TODO | Final status and evaluator result | Explain why the attempt was not successful |

Conclude with one evidence-based lesson and a possible later experiment. Do not
modify the frozen agent to apply that experiment until the official campaign is
complete. An exhausted-quota run in which no code was written is not evidence
that the model could not implement the feature.

## Measurement limits in the frozen runner

`steps` counts trace rows. `api_error_calls` counts rows whose cost is unknown;
it is not a complete count of HTTP requests or exclusively malformed tool calls.
The rate-limit retry loop can make several HTTP attempts inside one logged step.
Its intermediate retries are not separate trace records. A successful recovery
can record `rate_limit_wait_s`; a failed retry sequence does not preserve every
intermediate wait. Do not reconstruct missing events or claim a one-to-one
relationship between trace lines and all API requests from these files alone.
