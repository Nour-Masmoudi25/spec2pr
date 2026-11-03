"""Probe trusted Python hook scripts with controlled events, without a model.

No proposed tool command is executed. The scripts themselves execute on the
host, so use only reviewed hooks. This checks their protocol and selected cases;
it does not prove Claude Code loaded them or replace container isolation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def decision(event, completed):
    """Interpret documented blocking responses; crashes are test failures."""
    if completed.returncode == 2 and completed.stderr.strip():
        return "block"
    if completed.returncode != 0:
        return "error"
    try:
        output = json.loads(completed.stdout) if completed.stdout.strip() else {}
        if not isinstance(output, dict):
            return "error"
        if event == "PreToolUse":
            specific = output.get("hookSpecificOutput", {})
            if not isinstance(specific, dict):
                return "error"
            value = specific.get("permissionDecision")
            if value is not None:
                if specific.get("hookEventName") != event:
                    return "error"
                if value == "deny" and specific.get("permissionDecisionReason"):
                    return "block"
                if value == "allow":
                    return "continue"
                return "error"
        elif output.get("decision") == "block":
            return "block" if output.get("reason") else "error"
        # Asking the whole agent to stop is not continuing to repair tests.
        if output.get("continue") is False or "decision" in output:
            return "error"
        return "continue"
    except (ValueError, TypeError):
        return "error"


def probe(pre_tool_hook, stop_hook, timeout=15):
    scripts = {"PreToolUse": Path(pre_tool_hook).resolve(), "Stop": Path(stop_hook).resolve()}
    hashes = {event: hashlib.sha256(path.read_bytes()).hexdigest() for event, path in scripts.items()}
    results = []
    with tempfile.TemporaryDirectory(prefix="spec2pr-hook-probe-") as directory:
        workspace = Path(directory)
        (workspace/"tests").mkdir()
        (workspace/"src/tasklib").mkdir(parents=True)
        (workspace/".pipeline").mkdir()
        (workspace/"transcript.jsonl").write_text("", encoding="utf-8")
        cases = [
            ("deny_test_edit", "Edit", {"file_path": str(workspace/"tests/test_example.py"), "old_string": "assert False", "new_string": "assert True"}, "block"),
            ("deny_test_write", "Write", {"file_path": "tests/test_example.py", "content": "pass"}, "block"),
            ("deny_bash_test_write", "Bash", {"command": "printf 'pass' > tests/test_example.py"}, "block"),
            ("deny_push", "Bash", {"command": "git push origin main"}, "block"),
            ("deny_push_with_flag", "Bash", {"command": "git -C . push origin main"}, "block"),
            ("allow_source_edit", "Edit", {"file_path": str(workspace/"src/tasklib/store.py"), "old_string": "pass", "new_string": "return []"}, "continue"),
            ("allow_test_read", "Read", {"file_path": "tests/test_example.py"}, "continue"),
            ("allow_test_run", "Bash", {"command": "python -m pytest -q"}, "continue"),
        ]

        def run(name, event, expected, extra):
            payload = {"session_id": "controlled-hook-probe", "cwd": str(workspace),
                       "transcript_path": str(workspace/"transcript.jsonl"),
                       "permission_mode": "default", "hook_event_name": event,
                       "agent_type": "implementer", **extra}
            row = {"case": name, "event": event, "expected": expected, "input": payload}
            try:
                completed = subprocess.run([sys.executable, str(scripts[event])],
                    input=json.dumps(payload), text=True, encoding="utf-8", capture_output=True,
                    cwd=workspace, timeout=timeout)
                row.update(actual=decision(event, completed), exit_code=completed.returncode,
                           stdout=completed.stdout[:8000], stderr=completed.stderr[:8000])
            except (OSError, subprocess.TimeoutExpired) as error:
                row.update(actual="error", error=str(error))
            row["passed"] = row["actual"] == expected
            results.append(row)

        for name, tool, inputs, expected in cases:
            run(name, "PreToolUse", expected, {"tool_name": tool, "tool_input": inputs, "tool_use_id": name})
        # The stop hook reads a trusted VISIBLE-test result. Held-out grading
        # happens only after submission and must never drive an agent retry.
        for failing in (True, False):
            report = {"exit_code": int(failing), "passed": 127, "failed": int(failing)}
            (workspace/".pipeline/visible-test-report.json").write_text(json.dumps(report), encoding="utf-8")
            run("deny_stop_failed_tests" if failing else "allow_stop_passed_tests", "Stop",
                "block" if failing else "continue", {"stop_hook_active": False, "last_assistant_message": "Done"})
    return {"kind": "controlled_hook_probe", "passed": sum(r["passed"] for r in results),
            "total": len(results), "hook_sha256": hashes, "results": results,
            "limitation": "Synthetic events; live hook registration and team transcripts still required."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pre-tool-hook", type=Path, required=True)
    parser.add_argument("--stop-hook", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.report.exists():
            raise ValueError("Report already exists; choose a new output path")
        report = probe(args.pre_tool_hook, args.stop_hook)
        with args.report.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2)
            stream.write("\n")
        print(f"{report['passed']}/{report['total']} controlled hook checks passed")
        return 0 if report["passed"] == report["total"] else 1
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
