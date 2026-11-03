# Person B verification evidence — 2026-11-03

These are deterministic validation results, not model performance.

- `validation-local.json`: 10/10 tasks valid under host Python 3.13.1.
- `validation-docker.json`: 10/10 tasks valid in `sandbox:py312`; the
  `host_runtime` field describes the harness, not the container interpreter.
- The container reports Python **3.12.16**. Its inspected image ID is
  `sha256:f84cc98820a1b954d1f1553d5750f646b9e6ef4a4093bff7db83b14f34a257c5`.
- `tests.xml`: **311 passed**, zero failures/errors, for the library, benchmark tools and contract
  checks. Contract and hook fixtures are synthetic, clearly labeled in the tests.
- `verification.json`: source/report hashes and the commands used. Text hashes
  normalize CRLF to LF so checkout line endings do not change the identity.

The checks run on the `codex/person-b-weeks1-2` working tree based on main
`17f0e8d`, before the delivery commit. They do not claim a clean-commit model
campaign. The immutable target baseline remains
`dd0519be0d15a7b370dadb342319b982b2bfcaef`; the target source and existing tests
are unchanged.

No actual Week 2 planner outputs, model traces or installed-hook evidence were
available to check. Those remain integration work with A. Do not treat fixture
plans or hooks as completion evidence for the live multi-agent milestone.
