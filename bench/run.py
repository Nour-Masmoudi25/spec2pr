"""Score independent spec-to-code attempts with evaluator-only hidden tests."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import uuid

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(PROJECT / "bench"))
from runtime import docker_command, install_changes, preflight, source_changes
from validate import apply_patch, copy_baseline, prepare_baseline, run_tests
from prompt import build_prompt


def trace_metrics(path):
    """Unknown usage stays unknown instead of being silently counted as free."""
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    costs = [row["cost_usd"] for row in rows]
    return {"steps": len(rows),
            "cost_usd": sum(costs) if all(cost is not None for cost in costs) else None,
            "tokens_in": sum(r["tokens_in"] for r in rows) if all(r["tokens_in"] is not None for r in rows) else None,
            "tokens_out": sum(r["tokens_out"] for r in rows) if all(r["tokens_out"] is not None for r in rows) else None,
            # Lower bound: failed API calls report no usage, so they add nothing here.
            "known_cost_usd": sum(cost for cost in costs if cost is not None),
            "api_error_calls": sum(cost is None for cost in costs)}


def run_attempt(task, directory, *, agent, backend, timeout=60, image="sandbox:py312", steps=20):
    if agent == "single" and backend != "docker":
        raise ValueError("Agent-generated code may only run in Docker")
    metadata = json.loads((task / "task.json").read_text(encoding="utf-8"))
    directory.mkdir(parents=True)
    result = {"task_id": metadata["task_id"], "run_id": directory.name,
              "agent": agent, "backend": backend, "base_commit": metadata["base_commit"],
              "passed": False, "status": "error", "steps": 0, "cost_usd": None}
    try:
        with tempfile.TemporaryDirectory(prefix="spec2pr-run-") as temporary:
            root = Path(temporary)
            baseline, workspace, evaluator = [root / name for name in ("base", "workspace", "evaluator")]
            prepare_baseline(metadata, PROJECT / "target_repo", baseline)
            copy_baseline(baseline, workspace)
            if agent == "single":
                from agent.agent import run_agent

                def shell(command, workdir):
                    try:
                        completed = docker_command(workdir, ["sh", "-c", command], timeout, image)
                        output = completed.stdout + completed.stderr
                        return {"exit_code": completed.returncode, "output": output[:4000],
                                "truncated": len(output) > 4000}
                    except subprocess.TimeoutExpired:
                        return {"exit_code": -1, "output": "Command timed out", "truncated": False}

                spec = build_prompt((task / "spec.md").read_text(encoding="utf-8"), workspace,
                                    forbidden_names=[p.name for p in (task / "hidden_tests").glob("*.py")])
                outcome = run_agent(spec, str(workspace), run_dir=directory,
                                    command_runner=shell, step_limit=steps)
                result["agent_status"] = outcome["status"]
            else:
                # Controls make no model calls, so their trace is empty.
                (directory / "trace.jsonl").write_text("", encoding="utf-8")
                if agent == "reference":
                    apply_patch(workspace, task / "reference.patch")
                result["agent_status"] = "control_no_model"
            result.update(trace_metrics(directory / "trace.jsonl"))
            changes = source_changes(baseline, workspace)
            (directory / "submission.json").write_text(json.dumps(
                {name: content.decode("utf-8") if content is not None else None
                 for name, content in changes.items()}, indent=2, ensure_ascii=False), encoding="utf-8")
            copy_baseline(baseline, evaluator)
            install_changes(evaluator, changes)
            outcomes = run_tests(evaluator, task / "hidden_tests", timeout, backend, image)
            expected = set(metadata["fail_to_pass"]) | set(metadata["pass_to_pass"])
            if set(outcomes) != expected:
                raise ValueError("Evaluation cases differ from task metadata")
            result["fail_to_pass"] = {"passed": sum(outcomes[n] == "passed" for n in metadata["fail_to_pass"]),
                                      "total": len(metadata["fail_to_pass"])}
            result["pass_to_pass"] = {"passed": sum(outcomes[n] == "passed" for n in metadata["pass_to_pass"]),
                                      "total": len(metadata["pass_to_pass"])}
            result["passed"] = all(value == "passed" for value in outcomes.values())
            result["status"] = "passed" if result["passed"] else "failed_tests"
    except (ValueError, KeyError, OSError, subprocess.SubprocessError, ImportError) as error:
        result["error"] = str(error)[-3000:]
    finally:
        trace = directory / "trace.jsonl"
        if trace.exists():
            result.update(trace_metrics(trace))
        else:
            trace.write_text("", encoding="utf-8")
        (directory / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def summarize(results):
    costs = [r["cost_usd"] for r in results if r["cost_usd"] is not None]
    tasks = {r["task_id"] for r in results}
    solved = sum(any(r["passed"] for r in results if r["task_id"] == task) for task in tasks)
    consistent = sum(all(r["passed"] for r in results if r["task_id"] == task) for task in tasks)
    return {"runs": len(results), "passed": sum(r["passed"] for r in results),
            "pass_rate": sum(r["passed"] for r in results) / len(results),
            "tasks_solved_at_least_once": solved,
            "all_repetitions_pass_rate": consistent / len(tasks),
            "median_cost_usd": statistics.median(costs) if len(costs) == len(results) else None,
            "runs_with_known_cost": len(costs),
            "median_known_cost_usd_lower_bound": statistics.median(r.get("known_cost_usd", 0) for r in results),
            "total_api_error_calls": sum(r.get("api_error_calls", 0) for r in results),
            "median_steps": statistics.median(r["steps"] for r in results)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", choices=["single", "reference", "noop"], default="single")
    parser.add_argument("--tasks", type=Path, default=PROJECT / "bench/tasks")
    parser.add_argument("--n", type=int, default=3)
    parser.add_argument("--backend", choices=["docker", "local"], default="docker")
    parser.add_argument("--image", default="sandbox:py312")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--output", type=Path, default=PROJECT / "runs/benchmarks")
    args = parser.parse_args(argv)
    if min(args.n, args.timeout, args.steps) < 1:
        parser.error("n, timeout and steps must be positive")
    if args.agent == "single" and args.backend != "docker":
        parser.error("--agent single requires --backend docker")
    tasks = args.tasks.resolve()
    directories = [tasks] if (tasks / "task.json").is_file() else sorted(tasks.glob("*/task.json"))
    directories = [p.parent if p.is_file() else p for p in directories]
    if not directories:
        parser.error("No tasks found")
    if args.backend == "docker":
        try:
            preflight(args.image)
        except (OSError, subprocess.SubprocessError):
            parser.error("Docker engine/image unavailable. Start Docker and build sandbox:py312 first.")
    if args.agent == "single":
        try:
            from dotenv import load_dotenv
            from groq import Groq
            load_dotenv(PROJECT / ".env")
            Groq(timeout=60, max_retries=0)
        except Exception as error:
            parser.error("Model setup failed (" + type(error).__name__ + "). Install requirements.txt and set GROQ_API_KEY.")
    batch = args.output.resolve() / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8])
    batch.mkdir(parents=True)
    results = []
    for task in directories:
        for repetition in range(1, args.n + 1):
            result = run_attempt(task, batch / f"{task.name}-{repetition}", agent=args.agent,
                                 backend=args.backend, timeout=args.timeout, image=args.image, steps=args.steps)
            results.append(result)
            print(f"{task.name} run {repetition}: {result['status']}", flush=True)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT, capture_output=True, text=True, check=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=PROJECT, capture_output=True, text=True, check=True).stdout.strip())
    summary = {"agent": args.agent, "backend": args.backend, "repetitions": args.n,
               "evaluation_commit": commit, "working_tree_dirty": dirty,
               "created_at": datetime.now(timezone.utc).isoformat(),
               "host_python": sys.version.split()[0], "image": args.image if args.backend == "docker" else None,
               **summarize(results), "results": results}
    (batch / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"Pass rate: {summary['passed']}/{summary['runs']} ({summary['pass_rate']:.1%}); "
          f"median cost USD (configured estimate): {summary['median_cost_usd']}; median steps: {summary['median_steps']}")
    print(f"Median known cost USD (lower bound): {summary['median_known_cost_usd_lower_bound']:.5f}; "
          f"failed API calls: {summary['total_api_error_calls']}")
    print(f"All {args.n} repetitions pass: {summary['all_repetitions_pass_rate']:.1%}")
    print(f"Report: {batch / 'summary.json'}")
    return 1 if any(r["status"] == "error" for r in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())