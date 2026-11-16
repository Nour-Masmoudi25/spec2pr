# Team run on T01-T05: hand-off notes

Runs made on 2026-11-15 by `pipeline/run_team.py`: tester, implementer and reviewer in
turn, in a clean workspace per task (library copy only, no hidden tests), after the
plans of `runs/week2/plans/`. Evidence: `runs/week2/team/Txx/` (`result.json`, the
transcript of each role as `.jsonl`, `diff.patch`, `submission.json`, `test-report.json`).
Notes marked (automatic) come from the orchestrator's checks; notes marked (by hand)
come from comparing a role's words with measured numbers. We have not yet read every
tool call of the transcripts line by line.

## What happened

| Task | Hidden f2p | Hidden p2p | Review | Cost (USD) | Orchestrator notes |
|---|---|---|---|---|---|
| T01 | 16/16 | 127/127 | approve | 0.1663 | none |
| T02 | 14/14 | 127/127 | approve | 0.1513 | tester put prose before its JSON |
| T03 | 16/16 | 127/127 | approve | 0.1612 | none |
| T04 | 8/8 | 127/127 | approve | 0.1344 | none |
| T05 | 11/11 | 127/127 | approve | 0.1631 | report claims 18 added lines, real diff has 19 |

Total cost 0.7762 USD for five tasks. Visible tests after the tester failed in T01
(20 failed, 128 passed), so the tester's new tests do test a missing feature; after the
implementer all passed (148). One run per task, one model.

## Hand-off problems observed

1. **Prose around the JSON (automatic, T01 first attempt and T02).** The tester wrote a
   sentence before the JSON object. The first version of the orchestrator rejected the
   reply and stopped. Rule now: the JSON object must end the reply and is still
   validated against the schema; each case is logged as an observation.
2. **The hook self-test passed for the wrong reason (T01 first attempt).** The probe was
   refused by the permission system, not by our guard, so "file not written" proved
   nothing. The hooks were not active in the clean workspace. Fix: hooks are passed
   with `--settings`, the probe is allowed so only the guard can refuse it, and the test
   passes only if the guard's "Blocked:" message is seen.
3. **Path prefix (planner, T01).** The spec's `allowed_paths` is `src/tasklib/` but in the
   repository the library sits in `target_repo/`. The planner flagged it. Plans are now
   written relative to the library root; the guard accepts `src/` and `target_repo/src/`.
4. **The tester's claim differs from the measured result (by hand, T01).** It said 16 new
   tests fail and listed 17 test ids; 20 failed and 21 new tests exist, because
   parametrized tests were listed by function name, not one id per case.
5. **The implementer's diff statistics are not exact (automatic, T05).** It reported
   18 added lines; the real diff has 19. The orchestrator compares every report with the
   real diff, which is why this was caught.
6. **The reviewer approved all five patches.** All five were correct, so this says
   nothing about its quality. Its recall must be measured on planted defects.

## Limits of this evidence

- Not comparable with row 0: different model, one run per task.
- The team ran with the working tree uncommitted (`working_tree_dirty: true` in each
  `result.json`); the files were committed unchanged afterwards.
- Hooks: the stop gate is proven in a normal session, not in a subagent
  (`docs/live-hook-proof.md`). Here the implementer ran as a normal session.
## Added after reading two transcripts (2026-11-16)

- **Model:** every role ran on `claude-sonnet-5-5` (the `init` line of each transcript).
- **T05 implementer: why its numbers are guesses.** It read the code, added the method
  and the imports with the Edit tool, ran the visible tests once (138 passed) and replied.
  Its report says 18 added lines, the real diff has 19. It could not have measured the
  diff: the workspace has no git and its only allowed shell command is the test runner.
  A number a role cannot measure will be guessed. Consequence for the contracts:
  `diff_stat` should be computed by the orchestrator (it already is) and treated as
  informational when a role writes it.
- **T05 here versus T05 in Week 1.** The implementer put `lineterminator='\n'` into the
  file with the Edit tool and it arrived intact. In Week 1 the single agent had only a
  shell and wrote its code through a heredoc, where the `\n` became a real line break and
  broke all three runs. So part of the Week 1 failure came from the tool interface, not
  only from the model. This is an inference from one run, not a measured result.
- **T02 tester: first attempt to write its test file through a shell heredoc was refused
  by Claude Code's own safety check** ("brace with quote character"). The tester then used
  the Write tool. One turn wasted. To do: tell the tester in `tester.md` to create files
  with the Write tool, not the shell (not changed yet, so the evidence matches what ran).
- **T02 tester: the prose before the JSON** was a status sentence ("Tests are written, and
  the visible run shows 7 failing tests... I'm finalizing the plan now."), not content the
  next role needs. The contract asks for the JSON object only, which is why it is logged.
