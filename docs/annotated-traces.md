# Week 1 annotated model traces

Inspected on 2026-11-03 from the official evidence committed by Nour. Both
examples belong to row 0; neither is a reference control or a synthetic fixture.
The original traces, submissions, results and summaries remain unchanged.

All 15 official attempts record evaluation commit
`834104fcf4b11b687a336b0e633daa1b6948be83`, a clean working tree, and target baseline
`dd0519be0d15a7b370dadb342319b982b2bfcaef`. Reaggregating the five summaries gives
12/15 successes, median known cost **$0.004149 (lower bound)** and median **6 logged
steps**. The full median billed cost is unknown. A fresh scan of `evals/week1`
found **0 hidden-test filename occurrences in 15 traces / 79 JSON rows**, matching
[the published check](../evals/week1/official-leak-check.json).

## Successful example: T01-1

Evidence: [trace](../evals/week1/20261027T192036Z-a2cd78af/T01-1/trace.jsonl),
[result](../evals/week1/20261027T192036Z-a2cd78af/T01-1/result.json),
[submission](../evals/week1/20261027T192036Z-a2cd78af/T01-1/submission.json),
[batch](../evals/week1/20261027T192036Z-a2cd78af/summary.json).

Task: add `TaskStore.filter_by_priority(priority)`. It must validate the priority,
preserve creation order and object identity, include completed tasks, and leave
existing behavior intact. See [T01](../bench/tasks/T01/spec.md).

| JSONL line | Observed action | Interpretation |
|---|---|---|
| 1 | A Python heredoc appends the method to `src/tasklib/store.py`; exit 0. It calls `validate_priority` and filters `self._tasks.values()` into a list. | Reuses the existing validation and ordered storage. No new task copies or status filter are introduced. |
| 2 | `python -m pytest -q`; exit 0, `127 passed in 0.42s`. | The visible regression suite passes. The model has not run hidden acceptance tests. |
| 3 | Final answer, no tool call; says the method is implemented and tests pass. | The agent stops itself. Its statement alone is not the grade. |

The separate evaluator result confirms **16/16 hidden cases and 127/127 visible
cases passed**. The original store iteration explains ordering and inclusion;
the list comprehension explains the fresh list containing original objects.
These observations agree with the acceptance tests and the final submitted code.

Metrics: 3 logged steps; 14,336 input tokens; 714 output tokens; configured cost
$0.0025788; zero unknown-usage rows; `agent_status=stopped_by_model`.
Lines 2 and 3 record rate-limit waits of 7 and 31 seconds respectively.

## Failed example: T05-1

Evidence: [trace](../evals/week1/20261030T143136Z-973a4f26/T05-1/trace.jsonl),
[result](../evals/week1/20261030T143136Z-973a4f26/T05-1/result.json),
[submission](../evals/week1/20261030T143136Z-973a4f26/T05-1/submission.json),
[batch](../evals/week1/20261030T143136Z-973a4f26/summary.json).

Task: implement `TaskStore.to_csv()` with the required columns, quoting, booleans
and line endings. See [T05](../bench/tasks/T05/spec.md).

| JSONL line | Observed action | Consequence |
|---|---|---|
| 1 | Appends `to_csv` using a normal triple-quoted Python string in a heredoc; tool exits 0. | Writing the file succeeds, but the embedded `\n` in `lineterminator` becomes a literal newline inside a single-quoted string in the generated source. |
| 2 | `python -m pytest -q`; exit 2. | Test collection fails with `SyntaxError: unterminated string literal`, `store.py:184`. A successful write did not establish valid Python. |
| 3 | `sed -n '150,210p' src/tasklib/store.py`; exit 0. | The output visibly shows the split `lineterminator` string. This is direct evidence of the generated syntax defect. |
| 4 | Repeats pytest; exit 2 with the same syntax error. | No repair appears between inspecting the source and rerunning tests. |
| 5 | No tool executes. API returns HTTP 413: request 8,478 tokens exceeds the 8,000 TPM limit. | The attempt ends with `agent_status=api_error`; usage/cost for this row is unknown. |

Final grading also fails during collection. Its status is **`error`**, not a
normal assertion failure; hidden and visible pass counts are unavailable.
This unsuccessful attempt still belongs in the official 15-run denominator.
It combines a generated-code defect and a later API limit; the evidence does
not establish what the model would have done if another call were possible.

Metrics: 5 logged steps; known cost lower bound $0.0040698; 1 unknown-usage row;
total cost and total tokens are unknown. The other two official T05 attempts
also failed, as recorded in the batch summary; they were not replaced with
successful reruns or controls.

Lesson: verify generated Python before claiming completion. A later experiment
can compare safe source-writing instructions and a syntax check, while keeping
the task, model and budget fixed. No such improvement is applied retroactively
to the frozen Week 1 prompt or results.

## Measurement limits

`steps` counts trace rows. `api_error_calls` counts rows with unknown cost; it is
not a complete count of HTTP requests. Internal rate-limit retries are not
logged individually, so these traces do **not** prove one line per physical API
request. A successful recovery may record `rate_limit_wait_s`. The filename
scan checks textual leakage and cannot alone prove sandbox isolation.
