"""Generate Week 1 row 0 from five explicitly selected official task batches.

This offline tool never launches an agent, selects a best attempt, or edits an
existing report. Metrics are recomputed over all 15 individual run records.
"""
import argparse
import json
import math
from pathlib import Path
import re
import statistics
import sys

TASKS = ("T01", "T02", "T03", "T04", "T05")
REPETITIONS = 3


def require(condition, message):
    if not condition:
        raise ValueError(message)


def integer(value, name, minimum=0):
    require(type(value) is int and value >= minimum, f"{name} must be an integer >= {minimum}")
    return value


def money(value, name):
    require(type(value) in (int, float) and math.isfinite(value) and value >= 0,
            f"{name} must be a finite nonnegative number")
    return value


def commit(value, name):
    require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value),
            f"{name} must be a full 40-character Git commit")
    return value


def load_batch(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        require(isinstance(data, dict), "summary must be a JSON object")
        require(data["working_tree_dirty"] is False, "working_tree_dirty must be false")
        require(data["agent"] == "single", "only single-agent batches are official")
        require(data["backend"] == "docker", "official batches must use Docker")
        commit(data["evaluation_commit"], "evaluation_commit")
        require(isinstance(data["image"], str) and data["image"].strip(), "image is required")
        require(integer(data["repetitions"], "repetitions") == REPETITIONS,
                "each batch must have exactly 3 repetitions")
        records = data["results"]
        require(isinstance(records, list) and len(records) == REPETITIONS,
                "each summary must contain exactly 3 individual runs of one task")
        task_ids = set()
        for record in records:
            require(isinstance(record, dict), "run must be a JSON object")
            task = record["task_id"]
            require(isinstance(task, str) and task in TASKS, "unknown task_id")
            task_ids.add(task)
            require(record["agent"] == "single" and record["backend"] == "docker",
                    "run agent/backend differs from official batch")
            commit(record["base_commit"], "base_commit")
            require(type(record["passed"]) is bool, "passed must be a boolean")
            require(record["status"] in ("passed", "failed_tests", "error"), "unknown run status")
            require(record["passed"] == (record["status"] == "passed"), "passed/status mismatch")
            steps = integer(record["steps"], "steps", minimum=1)
            errors = integer(record["api_error_calls"], "api_error_calls")
            require(errors <= steps, "api_error_calls cannot exceed logged steps")
            known = money(record["known_cost_usd"], "known_cost_usd")
            if record["cost_usd"] is None:
                require(errors > 0, "unknown cost requires at least one unknown-usage call")
            else:
                total = money(record["cost_usd"], "cost_usd")
                require(errors == 0 and math.isclose(total, known, rel_tol=1e-9, abs_tol=1e-12),
                        "known cost and total cost are inconsistent")
        require(len(task_ids) == 1, "each input summary must contain a single task")
        task = next(iter(task_ids))
        require({record["run_id"] for record in records} == {f"{task}-{i}" for i in range(1, 4)},
                "run IDs must contain repetitions 1, 2 and 3 exactly once")
        require(integer(data["runs"], "runs") == 3, "summary runs count does not match its records")
        require(integer(data["passed"], "passed count") == sum(r["passed"] for r in records),
                "summary passed count does not match its records")
        return data
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"{path}: invalid batch: {error}") from error


def aggregate(paths):
    """Fail closed for dirty, mixed-commit, duplicate or incomplete batches."""
    paths = [Path(path).resolve() for path in paths]
    require(len(paths) == 5, "select exactly 5 summary.json files, one per task")
    require(len(set(paths)) == 5, "duplicate summary path")
    batches = [load_batch(path) for path in paths]
    require(len({b["evaluation_commit"] for b in batches}) == 1, "evaluation commits differ")
    require(len({b["image"] for b in batches}) == 1, "Docker image tags differ")
    task_ids = [b["results"][0]["task_id"] for b in batches]
    require(sorted(task_ids) == list(TASKS), "need exactly one batch for each of T01-T05")
    records = [record for batch in batches for record in batch["results"]]
    require(len({r["base_commit"] for r in records}) == 1, "baseline commits differ")
    per_task = {task: sum(r["passed"] for r in records if r["task_id"] == task) for task in TASKS}
    costs = [r["cost_usd"] for r in records]
    return {
        "agent": "single", "backend": "docker", "runs": len(records),
        "evaluation_commit": batches[0]["evaluation_commit"],
        "base_commit": records[0]["base_commit"], "working_tree_dirty": False,
        "image": batches[0]["image"], "passed": sum(per_task.values()),
        "pass_rate": sum(per_task.values()) / len(records),
        "median_steps": statistics.median(r["steps"] for r in records),
        "median_cost_usd": statistics.median(costs) if all(c is not None for c in costs) else None,
        "median_known_cost_usd_lower_bound": statistics.median(r["known_cost_usd"] for r in records),
        "total_api_error_calls": sum(r["api_error_calls"] for r in records),
        "tasks_solved_at_least_once": sum(count > 0 for count in per_task.values()),
        "pass_cubed": sum(count == REPETITIONS for count in per_task.values()) / len(TASKS),
        "per_task_passed": per_task,
        "sources": [{"task_id": batch["results"][0]["task_id"], "summary": str(path)}
                    for path, batch in sorted(zip(paths, batches), key=lambda pair: pair[1]["results"][0]["task_id"])],
        "run_records": records,
        "measurement_note": "Steps count trace rows; api_error_calls counts rows with unknown usage. "
                            "The frozen agent does not log each internal rate-limit retry separately.",
    }


def markdown(result):
    """Render a replacement table and supporting metrics for RESULTS.md."""
    return (
        "| Row | Agent | Tasks × runs | Pass rate | Median known cost (USD, lower bound) | "
        "Median logged steps | API error rows | Tasks solved at least once | Commit |\n"
        "|---|---|---|---|---|---|---|---|---|\n"
        f"| 0 | Single agent | 5 × 3 | {result['passed']}/15 ({result['pass_rate']:.1%}) | "
        f"{result['median_known_cost_usd_lower_bound']:.6f} | {result['median_steps']:g} | "
        f"{result['total_api_error_calls']} | {result['tasks_solved_at_least_once']}/5 | "
        f"`{result['evaluation_commit']}` |\n\n"
        f"pass^3: {result['pass_cubed']:.1%} (tasks passing all three repetitions).\n\n"
        "The cost column is a lower bound, not the full billed cost. "
        + ("The median full cost is unknown.\n\n" if result["median_cost_usd"] is None else
           f"Median configured total cost: ${result['median_cost_usd']:.6f}.\n\n")
        + result["measurement_note"] + "\n"
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summaries", nargs="+", type=Path, help="five approved task summary.json files")
    parser.add_argument("--output", type=Path, help="new Markdown file; existing files are never overwritten")
    parser.add_argument("--json-output", type=Path, help="new machine-readable aggregate file")
    args = parser.parse_args(argv)
    try:
        result = aggregate(args.summaries)
        outputs = [(args.output, markdown(result)),
                   (args.json_output, json.dumps(result, indent=2, ensure_ascii=False) + "\n")]
        selected = [path.resolve() for path, _ in outputs if path]
        require(len(selected) == len(set(selected)), "output paths must be different")
        for path in selected:
            require(not path.exists(), f"output already exists: {path}")
        for path, content in outputs:
            if path:
                with path.open("x", encoding="utf-8", newline="\n") as stream:
                    stream.write(content)
        print(markdown(result), end="")
        return 0
    except (ValueError, OSError) as error:
        print(f"Aggregation refused: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
