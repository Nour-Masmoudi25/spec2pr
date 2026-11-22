"""One Claude agent alone on a task: the fair baseline for the team (row 2).

    python -m pipeline.run_single bench/tasks/T01 bench/tasks/T02 --runs 3 [--out runs/week3/solo]
    python -m pipeline.run_single --summary runs/week3/solo

Same spec, same model alias, same tools, same hooks, same clean workspace and same
hidden-test grader as the team's implementer. What it does NOT have: the planner's
plan, the tester's tests and the reviewer. Runs that already have a result.json are skipped.
"""
import argparse
import json
import statistics
import sys
from datetime import datetime
from pathlib import Path

from pipeline import run_team as rt


def solo_prompt(spec):
    return ("You are a single software engineer working alone. Work in this folder, a clean copy of the library.\n"
            "Spec:\n" + json.dumps(spec, indent=2) + "\n"
            "Implement the feature so that every acceptance criterion holds. Edit only files under the allowed "
            "paths. Never create or edit test files. Run the visible tests, on their own line, with: "
            "python hooks/run_visible_tests.py\nWhen you are done, reply with one short paragraph saying what you changed.")


def run_one(task_dir, index, out_root, work_parent):
    task_id = task_dir.name
    out = out_root / ("%s-%d" % (task_id, index))
    if (out / "result.json").exists():
        print("%s-%d: already done, skipped" % (task_id, index))
        return json.loads((out / "result.json").read_text(encoding="utf-8"))
    out.mkdir(parents=True, exist_ok=True)
    spec = rt.load_json(task_dir / "spec.json")
    rt.validate_contract("spec", spec)
    metadata = json.loads((task_dir / "task.json").read_text(encoding="utf-8"))
    work_root = work_parent / ("%s-solo%d-%s" % (task_id, index, datetime.now().strftime("%Y%m%dT%H%M%S")))
    work_root.mkdir(parents=True)
    head, dirty = rt.git_state()
    result = {"task": task_id, "run": index, "agent": "solo", "commit": head, "working_tree_dirty": dirty,
              "status": "error", "workspace": str(work_root), "budget_usd": spec["budget_usd"], "observations": []}
    costs = {}
    notes = result["observations"]

    def spend(name, record):
        costs[name] = round(costs.get(name, 0) + (record.get("cost_usd") or 0), 6)
        print("%s-%d %s: %s ($%s, %ss)" % (task_id, index, name, "ok" if not record.get("error") else record["error"],
                                          costs[name], record.get("seconds")))

    try:
        rt.preflight(rt.IMAGE)
        base, workspace = rt.build_workspace(metadata, work_root)
        text = (rt.ROOT / ".claude" / "agents" / "solo.md").read_text(encoding="utf-8")
        (workspace / ".claude" / "agents" / "solo.md").write_text(text, encoding="utf-8", newline="\n")
        settings_path = work_root / "solo-hooks.json"
        settings_path.write_text(json.dumps(rt.HOOK_SETTINGS, indent=2), encoding="utf-8")
        base_tree = rt.tree(base)
        result["visible_baseline"] = rt.run_visible(workspace)

        probe = rt.call_role("solo", rt.PROBE_PROMPT, workspace, rt.PROBE_TOOLS, out / "00-hook-selftest.jsonl",
                             settings=settings_path)
        spend("hook_selftest", probe)
        log = out / "00-hook-selftest.jsonl"
        written = (workspace / "tests" / "hook_probe.py").exists()
        refused = log.exists() and "Blocked:" in log.read_text(encoding="utf-8")
        result["hook_selftest"] = {"file_written": written, "refusal_seen": refused}
        if written or not refused or probe.get("error"):
            result.update(status="stopped", reason="the hooks are not active (or the probe failed)")
            return result

        prompt = solo_prompt(spec)
        record = rt.call_role("solo", prompt, workspace, rt.IMPLEMENTER_TOOLS, out / "01-solo.jsonl",
                              edits=True, settings=settings_path)
        spend("solo", record)
        rt.save_role(out, "01-solo", prompt, record)
        result["turns"] = record.get("turns")
        result["seconds"] = record.get("seconds")
        if record.get("error") or record.get("is_error"):
            notes.append("The agent call failed: %s" % (record.get("error") or record.get("result")))
        outside = [n for n in rt.changed(base_tree, rt.tree(workspace)) if not n.startswith("src/tasklib/")]
        if outside:
            notes.append("The agent changed files outside src/tasklib/ (ignored by the grader): %s" % outside)
        result["visible_after"] = rt.run_visible(workspace)
        if result["visible_after"].get("exit_code") != 0:
            notes.append("The visible tests still fail at the end.")

        changes, test_report = rt.grade(task_dir, metadata, base, workspace, work_root)
        result.update(f2p=test_report["f2p"], p2p=test_report["p2p"])
        diff_text = "\n".join(rt.diff_of(n, base_tree.get(n), c)[2] for n, c in sorted(changes.items()) if c is not None)
        (out / "diff.patch").write_text(diff_text + "\n", encoding="utf-8")
        all_pass = test_report["f2p"]["fail"] == 0 and test_report["p2p"]["fail"] == 0
        result["status"] = "passed" if all_pass else "failed_tests"
        return result
    except Exception as error:  # keep the failure in result.json instead of losing the run
        notes.append("Run stopped by an exception: %r" % error)
        return result
    finally:
        result["costs_usd"] = costs
        result["total_cost_usd"] = round(sum(costs.values()), 6)
        (out / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print("%s-%d: %s | cost $%s" % (task_id, index, result["status"], result["total_cost_usd"]))


def summary(folder):
    rows = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("T*-*/result.json"))]
    if not rows:
        print("no results in", folder)
        return 1
    tasks = sorted({r["task"] for r in rows})
    passed = [r for r in rows if r["status"] == "passed"]
    print("| Task | Runs | Passed |")
    print("|---|---|---|")
    full = 0
    for t in tasks:
        mine = [r for r in rows if r["task"] == t]
        ok = sum(r["status"] == "passed" for r in mine)
        full += ok == len(mine)
        print("| %s | %d | %d |" % (t, len(mine), ok))
    costs = [r["total_cost_usd"] for r in rows]
    turns = [r["turns"] for r in rows if r.get("turns")]
    print()
    print("runs: %d | passed: %d (%.0f %%)" % (len(rows), len(passed), 100 * len(passed) / len(rows)))
    print("tasks solved in every run: %d of %d" % (full, len(tasks)))
    print("median cost per run: $%.4f | total: $%.4f" % (statistics.median(costs), sum(costs)))
    if turns:
        print("median turns: %s" % statistics.median(turns))
    if any(r.get("working_tree_dirty") for r in rows):
        print("note: some runs started from a modified working tree")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tasks", nargs="*", type=Path)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--out", type=Path, default=Path("runs/week3/solo"))
    parser.add_argument("--workspaces", type=Path, default=Path.home() / "spec2pr-workspaces")
    parser.add_argument("--summary", type=Path, help="print the summary of an output folder and exit")
    args = parser.parse_args(argv)
    if args.summary:
        return summary(args.summary)
    if not args.tasks:
        parser.error("give at least one task folder, or --summary")
    args.out.mkdir(parents=True, exist_ok=True)
    for task_dir in args.tasks:
        for index in range(1, args.runs + 1):
            run_one(task_dir, index, args.out, args.workspaces)
    return summary(args.out)


if __name__ == "__main__":
    sys.exit(main())
