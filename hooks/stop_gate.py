"""Stop gate for the implementer role.

Reads the visible-test report written by hooks/run_visible_tests.py. The agent
may not stop while visible tests fail, or while the report is missing, empty or
older than the last change in src/. After MAX_BLOCKS refusals the agent may stop,
and .pipeline/stop-gave-up.txt records that, so the loop is bounded and visible.
Only visible tests are used here. Hidden tests never reach this hook.
"""
import json
import sys
from pathlib import Path

MAX_BLOCKS = 5
RUN = "python hooks/run_visible_tests.py"


def problem(cwd, report_path):
    if not report_path.exists():
        return "No visible test report yet. Run: " + RUN
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        code = int(report["exit_code"])
        passed = int(report["passed"])
        failed = int(report["failed"])
    except (OSError, ValueError, KeyError, TypeError):
        return "The visible test report is unreadable. Run: " + RUN
    newest = max((f.stat().st_mtime for f in (cwd / "src").rglob("*.py")), default=0)
    if newest > report_path.stat().st_mtime:
        return "The report is older than your last change in src/. Run: " + RUN
    if code != 0 or failed > 0:
        return "Visible tests are failing (%d failed, exit code %d). Fix src/ and run: %s" % (failed, code, RUN)
    if passed == 0:
        return "No visible test ran, which proves nothing. Run: " + RUN
    return None


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        payload = {}
    cwd = Path(payload.get("cwd") or ".")
    pipeline = cwd / ".pipeline"
    pipeline.mkdir(exist_ok=True)
    counter = pipeline / "stop-blocks.txt"
    why = problem(cwd, pipeline / "visible-test-report.json")
    if why is None:
        counter.unlink(missing_ok=True)
        return 0
    try:
        used = int(counter.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        used = 0
    if used >= MAX_BLOCKS:
        (pipeline / "stop-gave-up.txt").write_text(
            "Stopped after %d refusals. Last problem: %s\n" % (used, why), encoding="utf-8")
        return 0
    counter.write_text(str(used + 1), encoding="utf-8")
    print(json.dumps({"decision": "block", "reason": why}))
    return 0


if __name__ == "__main__":
    sys.exit(main())