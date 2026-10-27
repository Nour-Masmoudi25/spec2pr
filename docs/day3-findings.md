\# Day 3 findings — Agent + Sandbox (T01)



\## Context

First real run of the single-agent loop against benchmark task T01

(`filter\_by\_priority` on `TaskStore`). Multiple failures occurred before

a successful, verified fix was produced. Documented here for RESULTS.md

and the final post-mortem.



Model used for the successful run: `openai/gpt-oss-120b` (Groq).

Earlier attempts also used `openai/gpt-oss-20b`.



\## Outcome

\- Agent successfully appended a correct `filter\_by\_priority` method to

&#x20; `src/tasklib/store.py`.

\- Existing visible test suite: 127/127 passed after the fix (no regressions).

\- Manual sanity check confirmed correct filtering behavior and correct

&#x20; `ValueError` on an invalid priority string.

\- Hidden tests (AC-1 to AC-6) not run yet — pending partner's `validate.py`.



\## Failure modes encountered



\### 1. Docker not running

\*\*Symptom:\*\* every tool call returned

`failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine`.

\*\*Cause:\*\* Docker Desktop was not running / had stopped.

\*\*Fix:\*\* restart Docker Desktop before running the agent.

\*\*Lesson:\*\* the agent has no pre-flight check for sandbox availability.

It burned real API calls hitting a dead sandbox instead of failing fast.

Worth adding a startup check in `agent.py`.



\### 2. Channel-token leak in tool name (intermittent)

\*\*Symptom:\*\* `400 Tool call validation failed: attempted to call tool

'bash<|channel|>analysis'` / `'functions<|channel|>bash'`, not in request.tools.

\*\*Cause:\*\* `openai/gpt-oss-20b`'s internal reasoning-channel formatting

(`<|channel|>analysis`/`final`) occasionally leaked into the tool name field.

\*\*Fix attempted:\*\* added a retry loop (up to 3 attempts per step). Did not

help — the error was reproducible across all 3 retries in the same step,

meaning it is systematic for this model, not random noise.

\*\*Resolution:\*\* switched away from `gpt-oss-20b` for this task.

\*\*Lesson:\*\* small/fast open-weight models can produce malformed tool calls

from internal formatting artifacts, independent of task complexity or

prompt wording.



\### 3. Strong bias toward patch/diff syntax

\*\*Symptom:\*\* model repeatedly generated `apply\_patch <<'PATCH' \*\*\* Begin

Patch ...` inside the `command` argument. The heavy escaping (patch syntax

nested inside a JSON string) broke JSON parsing: `Failed to parse tool call

arguments as JSON`.

\*\*Cause:\*\* likely a strong prior from code-model training data favoring

diff/patch-style edits.

\*\*Fix attempted (partial):\*\* added an instruction discouraging "patch

syntax" generally — not enough, the model still used `apply\_patch` by name.

\*\*Fix that worked:\*\* explicitly named and banned `apply\_patch` and

`\*\*\* Begin Patch` by name in the prompt, and gave a concrete alternative

pattern (Python heredoc writing a file directly).

\*\*Lesson:\*\* vague prohibitions ("avoid patch-style edits") are not reliable;

naming the exact disallowed pattern is necessary.



\### 4. Exploration loops / stalling before writing

\*\*Symptom:\*\* agent spent many steps re-reading the same file ranges

(`sed -n '200,400p' store.py` etc.) and re-running the same `grep` search

for `filter\_by\_priority`, without ever attempting a write, until it hit

the step limit (15, later raised to 20).

\*\*Cause:\*\* model repeatedly re-verified the absence of the method and

misjudged file length from truncated reads, looping instead of concluding

it should proceed to write.

\*\*Fix attempted:\*\* added explicit instructions to limit exploration to a

few commands then write. Helped partially but did not fully resolve it.

\*\*Fix that worked:\*\* stopped relying on the agent to explore at all —

the first agent message now includes the full contents of every file in

`src/tasklib/` directly, so no exploration step is needed.

\*\*Lesson:\*\* for small, well-scoped tasks, giving full file context up

front is more reliable than letting the agent discover it step by step.



\### 5. Full-file rewrite breaks JSON parsing (payload size)

\*\*Symptom:\*\* even with file context provided and patch syntax banned, a

tool call that rewrote the \*entire\* \~110-line `store.py` file (correct

content, including a correctly implemented `filter\_by\_priority`) still

failed with `Failed to parse tool call arguments as JSON`.

\*\*Cause:\*\* deeply nested quote escaping in a long embedded string argument

becomes unreliable for this model at this length, regardless of correctness

of content.

\*\*Fix that worked:\*\* changed the instruction from "rewrite the whole file"

to "append only the new method, in file-append mode (`'a'`)". This reduced

the payload to \~15 lines and the write succeeded on the first attempt.

\*\*Lesson:\*\* tool-call-based file edits are fragile for this model once

payload exceeds roughly 50-80 lines. Prefer small, targeted writes

(append / single-function insertion) over full-file rewrites where possible.



\### 6. Invalid extra tool argument

\*\*Symptom:\*\* `400 Failed to parse tool call arguments as JSON` with

`{"command": "python -m pytest -q"], "timeout": 100000}` — malformed JSON

caused by the model inventing a `"timeout"` argument not defined in the

tool schema.

\*\*Cause:\*\* model attempted to self-limit command runtime by adding a

parameter the `bash` tool does not accept.

\*\*Status:\*\* not fixed, low priority — happened after the actual fix had

already succeeded. Noted for awareness; the tool schema could explicitly

state "no other arguments are accepted" if it recurs.



\## Other operational notes

\- \*\*PYTHONPATH / src layout:\*\* running pytest inside the sandbox against

&#x20; `task-1-workspace` initially failed with `ModuleNotFoundError: No module

&#x20; named 'tasklib'`, because `tasklib` lives under `src/` and nothing tells

&#x20; Python to look there. Fixed locally by passing

&#x20; `-e PYTHONPATH=/workspace/src` to `docker run`. \*\*This needs to be built

&#x20; into the real benchmark sandbox setup\*\* (or declared via a src-layout

&#x20; config file) so `validate.py` and `run.py` don't hit the same error on

&#x20; hidden tests.

\- \*\*T01's `base\_commit: null`:\*\* `task.json` shows

&#x20; `"baseline\_status": "provisional local content snapshot; Git commit and

&#x20; Python 3.12 pending"`. The task is not fully finalized — needs a proper

&#x20; committed baseline before `validate.py` can reliably check fail-before/

&#x20; pass-after on the hidden tests.

\- \*\*Daily token quota (free tier):\*\* hit Groq's 200,000 tokens/day limit

&#x20; on `openai/gpt-oss-20b` partway through debugging. Free-tier budgets are

&#x20; tight enough that several iterative debugging runs on a single task can

&#x20; exhaust a full day's quota — a real constraint when planning the 15-run

&#x20; benchmark (5 tasks × 3 runs) for the week-1 deliverable.



\## Open items for Day 4+

\- \[ ] Confirm hidden tests (AC-1–AC-6) pass once `validate.py` exists.

\- \[ ] Ask partner to fix `base\_commit`/baseline status on T01.

\- \[ ] Ask partner to bake `PYTHONPATH=/workspace/src` (or equivalent) into

&#x20;     the shared sandbox/benchmark setup.

\- \[ ] Decide final model choice for the week-1 baseline run

&#x20;     (`gpt-oss-120b` currently most promising; consider re-testing

&#x20;     `gpt-oss-20b` once appended-write pattern is standard, since its

&#x20;     failures were partly payload-size related, not purely model quality).

\- \[ ] Add a Docker availability pre-flight check to `agent.py`.

