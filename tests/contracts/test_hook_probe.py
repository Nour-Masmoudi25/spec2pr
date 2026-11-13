"""Probe self-tests use deliberately synthetic hooks, not Person A's hooks."""
import json
import subprocess

import pytest

from bench.check_hooks import decision, probe


@pytest.mark.parametrize("event,code,out,err,expected", [
    ("PreToolUse", 2, "", "Denied", "block"),
    ("Stop", 2, "", "Tests failed", "block"),
    ("PreToolUse", 1, "", "Traceback", "error"),
    ("PreToolUse", 0, "not JSON", "", "error"),
    ("PreToolUse", 0, "[]", "", "error"),
    ("PreToolUse", 0, '{"hookSpecificOutput":null}', "", "error"),
    ("PreToolUse", 0, '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Tests are readonly"}}', "", "block"),
    ("PreToolUse", 0, '{"hookSpecificOutput":{"permissionDecision":"deny"}}', "", "error"),
    ("Stop", 0, '{"decision":"block","reason":"Tests failed"}', "", "block"),
    ("Stop", 0, '{"decision":"block"}', "", "error"),
    ("Stop", 0, '{"continue":false}', "", "error"),
    ("Stop", 0, "", "", "continue"),
])
def test_response_interpretation(event, code, out, err, expected):
    assert decision(event, subprocess.CompletedProcess([], code, out, err)) == expected


def test_noop_hook_cannot_count_as_working_protection(tmp_path):
    hook = tmp_path/"noop.py"; hook.write_text("pass\n")
    result = probe(hook, hook)
    assert result["passed"] == 4 and result["total"] == 10
    assert not next(r for r in result["results"] if r["case"] == "deny_push")["passed"]


def test_controlled_fixture_exercises_both_decisions(tmp_path):
    # This intentionally simple fixture is not shipped as a security policy.
    hook = tmp_path/"fixture.py"
    hook.write_text('''import json, sys
from pathlib import Path
event = json.load(sys.stdin)
if event['hook_event_name'] == 'Stop':
    report = json.loads((Path(event['cwd'])/'.pipeline/visible-test-report.json').read_text())
    if report['exit_code']:
        print(json.dumps({'decision':'block','reason':'Tests failed'}))
else:
    inputs = event['tool_input']
    blocked = (event['tool_name'] in ('Edit','Write') and 'tests' in inputs.get('file_path',''))
    blocked = blocked or (event['tool_name'] == 'Bash' and
                          ('push' in inputs['command'] or '>' in inputs['command']))
    if blocked:
        print(json.dumps({'hookSpecificOutput':{'hookEventName':'PreToolUse',
            'permissionDecision':'deny','permissionDecisionReason':'Controlled fixture'}}))
''', encoding="utf-8")
    result = probe(hook, hook)
    assert result["passed"] == result["total"] == 10
    assert result["kind"] == "controlled_hook_probe"
    assert len(result["hook_sha256"]["Stop"]) == 64
