# Proposed Week 2 multi-agent experiment

Status: design only. Implement after the Week 1 campaign and its evidence are
complete. The Week 1 agent, prompt and evaluator remain frozen meanwhile.

## Roles and information boundaries

| Role | Inputs it may see | Output | Write access |
|---|---|---|---|
| Planner | Specification, target source, visible tests | Ordered implementation plan tied to acceptance criteria | None |
| Tester | Specification, target source, visible tests, plan | Proposed tests and observed failures | Separate visible-test workspace |
| Implementer | Specification, source, plan, tester feedback | Source-only changes | src/tasklib in the task checkout |
| Reviewer | Specification, plan, submitted source diff, visible-test results | Concrete findings or recommendation to submit | None |

The orchestrator controls scheduling, shared budgets and handoffs. Hidden tests,
reference fixes, task metadata containing hidden node IDs, Git history and API
credentials are never sent to any role or mounted in its shell container.
Hidden evaluation happens only after the final submission and cannot feed back
into another repair attempt within that run.

Tester-generated tests are additional diagnostics. They do not replace or
modify the committed visible suite used for final grading. Keep them outside
the submitted source diff. The existing grader still evaluates a clean baseline
plus allowed source changes and its original visible/hidden tests.

## Initial sequence

1. Export the same baseline and provide the same task specification.
2. Planner proposes a short plan; tester proposes tests against that plan.
3. Implementer edits source and runs available visible diagnostics.
4. Reviewer examines the diff and reports specific issues.
5. If the shared budget allows, implementer makes one repair and submits.
6. The trusted evaluator grades once in a separate checkout.

Begin sequentially so attribution and budget accounting are easy to verify.
Parallel calls, if later introduced, need an atomic shared budget reservation
before dispatch; simultaneous roles must not each assume the whole remaining
budget is available.

## Fair comparison

Use the same task baseline, model/version, Docker limits and final grading rules
for both systems. Give each entire pipeline the same limits on total model
requests, input/output tokens, configured cost and wall time. Planner, tester,
reviewer, retries and repeated context all consume the shared allowance; do not
give every role the single-agent allowance independently. Reserve enough for
implementation rather than spending all of it on planning.

Week 1 traces count logged steps and known cost. Some internal API retries have
no separate usage record, so those values cannot establish equality of actual
request counts or billed costs. After Week 1, instrument the orchestrator and
rerun both the single-agent and multi-agent variants with the same accounting
version. Report unknown usage explicitly; never treat a lower bound as a proven
hard spending cap. Keep the original Week 1 results as their own historical row.

Run three attempts per task for both variants, keep all attempts and record the
code/configuration commits. Compare pass rate, tasks solved at least once,
pass^3, known-cost lower bounds, logged/actual requests where measurable, and
elapsed time. With only five tasks, treat differences as exploratory rather
than strong evidence of general superiority.

## Proposed deliverables

- An orchestrator with one shared budget and role-specific input construction.
- Tests that no role receives hidden material and that budget checks include
  handoffs, retries and concurrent reservations if concurrency is enabled.
- Trace records identifying role, request, tool calls, usage and handoff.
- Matched single-agent and multi-agent evaluation batches, plus a limitations
  statement for unknown provider usage and the small task set.
