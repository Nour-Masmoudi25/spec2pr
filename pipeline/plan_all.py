"""Run the planner role on every spec, validate each plan, retry once, log it all.

    python -m pipeline.plan_all bench/tasks [--only T01,T02] [--force] [--out runs/week2]

For each spec: ask the planner (Claude Code subagent in .claude/agents/planner.md),
validate the plan with contracts, and on rejection retry ONCE with the validator's
error. Both attempts are logged in <out>/plan-traces/Txx.json. An accepted plan is
saved without any wrapper as <out>/plans/Txx.json. A second rejection stops that
spec: no plan is saved and nothing is repaired silently.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from contracts import validate as contract_checks

ROOT = Path(__file__).resolve().parent.parent
validate_contract = contract_checks.validate_contract
load_json = contract_checks.load_json
ContractError = getattr(contract_checks, "ContractError", ValueError)

INSTRUCTIONS = (
    "Plan this spec. Reply with ONLY the JSON plan, no other text.\n"
    "File paths in the plan are relative to the library root, exactly like "
    "allowed_paths in the spec (for example src/tasklib/store.py), even though in "
    "this checkout the library sits in target_repo/.\n"
    "Spec JSON:\n"
)


def strip_fence(text):
    text = text.strip()
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    return match.group(1) if match else text


def call_planner(prompt, timeout=900):
    exe = shutil.which("claude")
    if not exe:
        return {"error": "claude was not found on PATH"}
    started = time.time()
    try:
        done = subprocess.run([exe, "-p", "--agent", "planner", "--output-format", "json"],
                              input=prompt, text=True, encoding="utf-8",
                              capture_output=True, timeout=timeout, cwd=ROOT)
    except subprocess.TimeoutExpired:
        return {"error": "planner call timed out", "seconds": round(time.time() - started, 1)}
    record = {"exit_code": done.returncode, "seconds": round(time.time() - started, 1),
              "stderr": done.stderr[-1000:]}
    try:
        out = json.loads(done.stdout)
    except ValueError:
        record["error"] = "claude output was not JSON"
        record["stdout"] = done.stdout[:2000]
        return record
    record.update(result=out.get("result", ""), is_error=bool(out.get("is_error")),
                  cost_usd=out.get("total_cost_usd"), turns=out.get("num_turns"),
                  usage=out.get("usage"))
    return record


def check(record, spec):
    """Return (plan, None) if accepted, else (None, reason)."""
    if record.get("error") or record.get("is_error") or record.get("exit_code"):
        reason = record.get("error") or record.get("result") or record.get("stderr")
        return None, "planner call failed: %s" % reason
    try:
        plan = json.loads(strip_fence(record.get("result", "")))
    except ValueError as exc:
        return None, "the reply is not valid JSON: %s" % exc
    try:
        validate_contract("plan", plan, spec=spec)
    except ContractError as exc:
        return None, str(exc)
    return plan, None


def retry_prompt(prompt, record, error):
    return (prompt + "\n\nYour previous reply was rejected by the validator.\n"
            "Previous reply:\n" + str(record.get("result", ""))[:6000] +
            "\nValidator error:\n" + error +
            "\nReply again with the full corrected JSON plan only.")


def plan_one(task_dir, out, force):
    task_id = task_dir.name
    spec = load_json(task_dir / "spec.json")
    validate_contract("spec", spec)
    plan_path = out / "plans" / (task_id + ".json")
    if plan_path.exists() and not force:
        return {"task": task_id, "status": "skipped: plan already saved", "attempts": 0, "cost_usd": 0}
    base = INSTRUCTIONS + json.dumps(spec, indent=2)
    attempts, plan, current = [], None, base
    for number in (1, 2):
        record = call_planner(current)
        plan, error = check(record, spec)
        attempts.append({"attempt": number, "prompt": current, "response": record,
                         "accepted": plan is not None, "error": error})
        if plan is not None:
            break
        current = retry_prompt(base, record, error or "")
    (out / "plan-traces").mkdir(parents=True, exist_ok=True)
    (out / "plan-traces" / (task_id + ".json")).write_text(
        json.dumps({"task": task_id, "attempts": attempts}, indent=2) + "\n", encoding="utf-8")
    if plan is not None:
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    return {"task": task_id, "status": "accepted" if plan is not None else "rejected after retry",
            "attempts": len(attempts),
            "cost_usd": round(sum(a["response"].get("cost_usd") or 0 for a in attempts), 6),
            "last_error": attempts[-1]["error"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tasks", type=Path)
    parser.add_argument("--out", type=Path, default=Path("runs/week2"))
    parser.add_argument("--only", default="")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    only = {x.strip() for x in args.only.split(",") if x.strip()}
    dirs = [d for d in sorted(args.tasks.iterdir())
            if (d / "spec.json").exists() and (not only or d.name in only)]
    results = []
    for task_dir in dirs:
        result = plan_one(task_dir, args.out, args.force)
        results.append(result)
        print("%s: %s (attempts: %s, cost: $%s)" % (
            result["task"], result["status"], result["attempts"], result["cost_usd"]))
    report = {"kind": "planner_run", "finished": datetime.now(timezone.utc).isoformat(),
              "results": results,
              "total_cost_usd": round(sum(r["cost_usd"] or 0 for r in results), 6)}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "plan-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("total cost: $%s" % report["total_cost_usd"])
    return 0 if all(r["status"].startswith(("accepted", "skipped")) for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())