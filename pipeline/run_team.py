"""Run the four-role team on one task and log every handoff.

    python -m pipeline.run_team bench/tasks/T01 [--plans runs/week2/plans] [--out runs/week2/team]

The workspace is a clean copy of the library at the task's base commit, built OUTSIDE
this repository, with only the role files, hooks and contract schemas added. Hidden
tests and reference patches never enter it. The plan comes from pipeline.plan_all.
Roles run here: tester, implementer, reviewer. The orchestrator validates every
handoff, checks who changed which files, runs the visible tests in Docker, grades only
src/tasklib/ with the hidden tests once the implementer is done, and stops on the
first invalid handoff or when the spec budget is used up.
"""
import argparse
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline.plan_all import ContractError, load_json, strip_fence, validate_contract  # noqa: E402

sys.path.insert(0, str(ROOT / "bench"))
from runtime import install_changes, preflight, source_changes  # noqa: E402
from validate import copy_baseline, prepare_baseline, run_tests  # noqa: E402

IMAGE = "sandbox:py312"
RUNNER = "Bash(python hooks/run_visible_tests.py)"
TESTER_TOOLS = "Read,Grep,Glob,Write,Edit," + RUNNER
IMPLEMENTER_TOOLS = "Read,Grep,Glob,Write,Edit," + RUNNER
REVIEWER_TOOLS = "Read,Grep,Glob"
PROBE_TOOLS = "Bash"
PROBE_PROMPT = ('This is an automatic hook self-test. Run this exact Bash command once: '
                'echo "# probe" >> tests/hook_probe.py\n'
                'Then reply with one line saying whether it was allowed or refused. Do nothing else.')


HOOK_SETTINGS = {"hooks": {
    "PreToolUse": [{"matcher": "Edit|Write|MultiEdit|NotebookEdit|Bash",
                    "hooks": [{"type": "command", "command": "python hooks/pre_tool_guard.py"}]}],
    "Stop": [{"hooks": [{"type": "command", "command": "python hooks/stop_gate.py"}]}]}}


def call_role(agent, prompt, cwd, allowed, log_path, edits=False, timeout=1500, settings=None):
    exe = shutil.which("claude")
    if not exe:
        return {"error": "claude was not found on PATH"}
    cmd = [exe, "-p", "--agent", agent, "--output-format", "stream-json", "--verbose"]
    if settings:
        cmd += ["--settings", str(settings)]
    if edits:
        cmd += ["--permission-mode", "acceptEdits"]
    cmd += ["--allowedTools", allowed]
    env = dict(os.environ, SPEC2PR_VISIBLE_BACKEND="docker")
    started = time.time()
    try:
        done = subprocess.run(cmd, input=prompt, text=True, encoding="utf-8", errors="replace",
                              capture_output=True, timeout=timeout, cwd=cwd, env=env)
    except subprocess.TimeoutExpired:
        return {"error": "role call timed out", "seconds": round(time.time() - started, 1)}
    log_path.write_text(done.stdout, encoding="utf-8")
    final = None
    for line in done.stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and event.get("type") == "result":
            final = event
    record = {"exit_code": done.returncode, "seconds": round(time.time() - started, 1),
              "stderr": done.stderr[-800:], "transcript": log_path.name}
    if final is None:
        record["error"] = "no result event in the transcript"
        return record
    record.update(result=final.get("result", ""), is_error=bool(final.get("is_error")),
                  cost_usd=final.get("total_cost_usd") or 0, turns=final.get("num_turns"))
    return record


def parse_reply(text):
    """Return (data, wrapped). The JSON object must end the reply; wrapped is True if prose precedes it."""
    text = strip_fence(text)
    try:
        return json.loads(text), False
    except ValueError as first:
        decoder = json.JSONDecoder()
        for start in [i for i, ch in enumerate(text) if ch == "{"]:
            try:
                data, end = decoder.raw_decode(text, start)
            except ValueError:
                continue
            if isinstance(data, dict) and not text[end:].strip():
                return data, True
        raise first


def handoff(kind, record, spec, plan=None, notes=None, role="role"):
    """Return (data, None) if the role's reply is a valid contract, else (None, reason)."""
    if record.get("error") or record.get("is_error") or record.get("exit_code"):
        return None, "role call failed: %s" % (record.get("error") or record.get("result") or record.get("stderr"))
    try:
        data, wrapped = parse_reply(record.get("result", ""))
    except ValueError as exc:
        return None, "the reply is not valid JSON: %s" % exc
    if wrapped and notes is not None:
        notes.append("The %s put prose before its JSON reply; the JSON itself was validated as usual." % role)
    try:
        validate_contract(kind, data, spec=spec, plan=plan)
    except ContractError as exc:
        return None, str(exc)
    return data, None


def tree(root):
    found = {}
    for top in ("src", "tests"):
        folder = root / top
        if not folder.is_dir():
            continue
        for path in folder.rglob("*"):
            if path.is_file() and "__pycache__" not in path.parts and ".pytest_cache" not in path.parts:
                found[path.relative_to(root).as_posix()] = path.read_bytes().replace(b"\r\n", b"\n")
    return found


def changed(before, after):
    return sorted(n for n in before.keys() | after.keys() if before.get(n) != after.get(n))


def diff_of(name, old, new):
    lines = list(difflib.unified_diff(
        old.decode("utf-8", "replace").splitlines() if old else [],
        new.decode("utf-8", "replace").splitlines() if new else [],
        fromfile="a/" + name, tofile="b/" + name, lineterm="", n=2))
    added = sum(1 for x in lines if x.startswith("+") and not x.startswith("+++"))
    removed = sum(1 for x in lines if x.startswith("-") and not x.startswith("---"))
    return added, removed, "\n".join(lines)


def build_workspace(metadata, work_root):
    base, workspace = work_root / "base", work_root / "workspace"
    prepare_baseline(metadata, ROOT / "target_repo", base)
    copy_baseline(base, workspace)
    (workspace / ".claude" / "agents").mkdir(parents=True)
    for name in ("planner", "tester", "implementer", "reviewer", "probe"):
        text = (ROOT / ".claude" / "agents" / (name + ".md")).read_text(encoding="utf-8")
        if name == "implementer":
            text = re.sub(r"^hooks:\n(?:[ \t]+.*\n)+", "", text, flags=re.M)
        (workspace / ".claude" / "agents" / (name + ".md")).write_text(text, encoding="utf-8", newline="\n")
    shutil.copytree(ROOT / "hooks", workspace / "hooks", ignore=shutil.ignore_patterns("__pycache__"))
    (workspace / "contracts").mkdir()
    for schema in (ROOT / "contracts").glob("*.schema.json"):
        shutil.copy2(schema, workspace / "contracts" / schema.name)
    return base, workspace


def run_visible(workspace):
    report_file = workspace / ".pipeline" / "visible-test-report.json"
    report_file.unlink(missing_ok=True)
    env = dict(os.environ, SPEC2PR_VISIBLE_BACKEND="docker")
    try:
        subprocess.run([sys.executable, "hooks/run_visible_tests.py"], cwd=workspace, env=env,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=400)
        return json.loads(report_file.read_text(encoding="utf-8"))
    except (subprocess.TimeoutExpired, OSError, ValueError) as error:
        return {"exit_code": 125, "passed": 0, "failed": 0, "error": str(error)}


def grade(task_dir, metadata, base, workspace, work_root):
    candidate = work_root / "candidate"
    copy_baseline(base, candidate)
    shutil.rmtree(candidate / "src" / "tasklib")
    shutil.copytree(workspace / "src" / "tasklib", candidate / "src" / "tasklib",
                    ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    changes = source_changes(base, candidate)
    evaluator = work_root / "evaluator"
    copy_baseline(base, evaluator)
    install_changes(evaluator, changes)
    outcomes = run_tests(evaluator, task_dir / "hidden_tests", 120, "docker", IMAGE)
    f2p, p2p = metadata["fail_to_pass"], metadata["pass_to_pass"]
    if set(outcomes) != set(f2p) | set(p2p):
        raise ValueError("Evaluation cases differ from task metadata")

    def tally(names):
        passed = sum(outcomes[n] == "passed" for n in names)
        return {"pass": passed, "fail": len(names) - passed}

    return changes, {"f2p": tally(f2p), "p2p": tally(p2p)}


def tester_prompt(spec, plan):
    return ("You are the tester. Work in this folder, a clean copy of the library.\n"
            "Spec:\n" + json.dumps(spec, indent=2) + "\nAccepted plan:\n" + json.dumps(plan, indent=2) +
            "\nWrite new tests ONLY under tests/agent_generated/ (create the folder). Map every AC to tests. "
            "Use pytest node ids relative to this folder, like tests/agent_generated/test_x.py::test_name, "
            "in test_ids and ac_map. Run the visible tests, on their own line, with: "
            "python hooks/run_visible_tests.py\nYour final message must be only the test_plan JSON object: it starts with { and ends with }, with no sentence before it.")


def implementer_prompt(spec, plan, task):
    return ("You are the implementer. Work in this folder, a clean copy of the library. The tester's "
            "tests are in tests/agent_generated/.\nSpec:\n" + json.dumps(spec, indent=2) +
            "\nAccepted plan:\n" + json.dumps(plan, indent=2) +
            "\nYou implement ONLY plan task " + task["id"] + " (files: " + ", ".join(task["files"]) +
            "). Run the visible tests, on their own line, with: python hooks/run_visible_tests.py\n"
            "Your final message must be only the implementation_report JSON object: it starts with { and ends with }, with no sentence before it.")


def reviewer_prompt(spec, plan, diff_text, test_report):
    return ("You are the reviewer. Work in this folder, a clean copy of the library with the "
            "implementation applied.\nSpec:\n" + json.dumps(spec, indent=2) +
            "\nAccepted plan:\n" + json.dumps(plan, indent=2) +
            "\nDiff of the implementation:\n" + diff_text[:20000] +
            "\nIndependent test report:\n" + json.dumps(test_report, indent=2) +
            "\nCheck each AC against the code. Cite real files and line numbers, an AC id from the spec "
            "for each finding, and use severity error only for real defects. Your final message must be only the review JSON object: it starts with { and ends with }, with no sentence before it.")


def save_role(out, name, prompt, record):
    (out / (name + ".json")).write_text(
        json.dumps({"prompt": prompt, "record": record}, indent=2) + "\n", encoding="utf-8")


def git_state():
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT,
                                capture_output=True, text=True).stdout.strip())
    return head, dirty


def run_team(task_dir, plans_dir, out_root, work_parent):
    task_id = task_dir.name
    out = out_root / task_id
    if out.exists():
        raise SystemExit("%s already exists; choose another --out or move it" % out)
    out.mkdir(parents=True)
    spec = load_json(task_dir / "spec.json")
    validate_contract("spec", spec)
    plan = load_json(plans_dir / (task_id + ".json"))
    validate_contract("plan", plan, spec=spec)
    metadata = json.loads((task_dir / "task.json").read_text(encoding="utf-8"))
    work_root = work_parent / (task_id + "-" + datetime.now().strftime("%Y%m%dT%H%M%S"))
    work_root.mkdir(parents=True)
    head, dirty = git_state()
    result = {"task": task_id, "commit": head, "working_tree_dirty": dirty, "status": "stopped",
              "workspace": str(work_root), "budget_usd": spec["budget_usd"], "observations": []}
    costs = {}
    notes = result["observations"]

    def spend(role, record):
        costs[role] = round(costs.get(role, 0) + (record.get("cost_usd") or 0), 6)
        print("%s: %s ($%s, %ss)" % (role, "ok" if not record.get("error") else record["error"],
                                     costs[role], record.get("seconds")))

    def stop(stage, reason):
        result.update(status="stopped", stopped_at=stage, reason=reason)
        print("STOPPED at %s: %s" % (stage, reason))
        return result

    def over_budget():
        return sum(costs.values()) >= spec["budget_usd"]

    try:
        preflight(IMAGE)
        base, workspace = build_workspace(metadata, work_root)
        settings_path = work_root / "implementer-hooks.json"
        settings_path.write_text(json.dumps(HOOK_SETTINGS, indent=2), encoding="utf-8")
        base_tree = tree(base)
        result["visible_baseline"] = run_visible(workspace)

        probe = call_role("probe", PROBE_PROMPT, workspace, PROBE_TOOLS, out / "00-hook-selftest.jsonl",
                          settings=settings_path)
        spend("hook_selftest", probe)
        written = (workspace / "tests" / "hook_probe.py").exists()
        log = out / "00-hook-selftest.jsonl"
        result["hook_selftest"] = {"file_written": written,
                                   "refusal_seen": log.exists() and "Blocked:" in log.read_text(encoding="utf-8")}
        if written or not result["hook_selftest"]["refusal_seen"] or probe.get("error"):
            return stop("hook_selftest", "the hooks are not active (or the probe failed): "
                                         "the guard did not refuse the probe command")

        if over_budget():
            return stop("tester", "budget used up")
        before = tree(workspace)
        prompt = tester_prompt(spec, plan)
        record = call_role("tester", prompt, workspace, TESTER_TOOLS, out / "01-tester.jsonl", edits=True)
        spend("tester", record)
        save_role(out, "01-tester", prompt, record)
        test_plan, error = handoff("test_plan", record, spec, plan, notes, "tester")
        if error:
            return stop("tester", error)
        after = tree(workspace)
        touched = changed(before, after)
        outside = [n for n in touched if not n.startswith("tests/agent_generated/")]
        if outside:
            return stop("tester", "the tester changed files outside tests/agent_generated/: %s" % outside)
        if not touched:
            notes.append("The tester wrote no test files.")
        for test_id in test_plan["test_ids"]:
            if test_id.split("::")[0] not in after:
                notes.append("test_plan lists a test file that does not exist: %s" % test_id)
        result["visible_after_tester"] = run_visible(workspace)
        shown = result["visible_after_tester"]
        if shown.get("exit_code") == 0 and shown.get("failed") == 0:
            notes.append("The tester's tests all pass before any implementation, so they may not test the new feature.")

        for task in plan["tasks"]:
            if over_budget():
                return stop("implementer", "budget used up")
            snapshot = tree(workspace)
            prompt = implementer_prompt(spec, plan, task)
            name = "02-implementer-" + task["id"]
            record = call_role("implementer", prompt, workspace, IMPLEMENTER_TOOLS, out / (name + ".jsonl"),
                               edits=True, settings=settings_path)
            spend("implementer", record)
            save_role(out, name, prompt, record)
            report, error = handoff("implementation_report", record, spec, plan, notes, "implementer")
            if error:
                return stop("implementer", error)
            outside = [n for n in changed(snapshot, tree(workspace)) if not n.startswith("src/tasklib/")]
            if outside:
                return stop("implementer", "the implementer changed files outside src/tasklib/: %s" % outside)
            now = tree(workspace)
            actual = {}
            for file_name in changed(snapshot, now):
                if file_name.startswith("src/tasklib/"):
                    added, removed, _ = diff_of(file_name, snapshot.get(file_name), now.get(file_name))
                    actual[file_name] = (added, removed)
            claimed = {d["file"]: (d["added"], d["removed"]) for d in report["diff_stat"]}
            if claimed != actual:
                notes.append("Task %s: the implementation report does not match the real diff. claimed=%s actual=%s"
                             % (task["id"], claimed, actual))
        result["visible_after_implementer"] = run_visible(workspace)
        if result["visible_after_implementer"].get("exit_code") != 0:
            notes.append("The visible tests still fail after the implementer finished.")

        changes, test_report = grade(task_dir, metadata, base, workspace, work_root)
        test_report = dict(spec_id=spec["spec_id"], lint="not_run", **test_report)
        validate_contract("test_report", test_report, spec=spec)
        result.update(f2p=test_report["f2p"], p2p=test_report["p2p"])
        (out / "submission.json").write_text(json.dumps(
            {n: c.decode("utf-8") if c is not None else None for n, c in changes.items()},
            indent=2, ensure_ascii=False), encoding="utf-8")
        diff_text = "\n".join(diff_of(n, base_tree.get(n), c)[2] for n, c in sorted(changes.items()) if c is not None)
        (out / "diff.patch").write_text(diff_text + "\n", encoding="utf-8")
        (out / "test-report.json").write_text(json.dumps(test_report, indent=2) + "\n", encoding="utf-8")
        all_pass = test_report["f2p"]["fail"] == 0 and test_report["p2p"]["fail"] == 0
        result["status"] = "passed" if all_pass else "failed_tests"

        if over_budget():
            notes.append("The budget was used up before the review.")
            return result
        prompt = reviewer_prompt(spec, plan, diff_text, test_report)
        record = call_role("reviewer", prompt, workspace, REVIEWER_TOOLS, out / "03-reviewer.jsonl")
        spend("reviewer", record)
        save_role(out, "03-reviewer", prompt, record)
        review, error = handoff("review", record, spec, plan, notes, "reviewer")
        if error:
            notes.append("The review was rejected: %s" % error)
        else:
            result["review_verdict"] = review["verdict"]
            if review["verdict"] == "approve" and not all_pass:
                notes.append("The reviewer approved although hidden tests fail.")
            if review["verdict"] == "request_changes" and all_pass:
                notes.append("The reviewer asked for changes although all hidden tests pass.")
        return result
    finally:
        result["costs_usd"] = costs
        result["total_cost_usd"] = round(sum(costs.values()), 6)
        (out / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", type=Path)
    parser.add_argument("--plans", type=Path, default=Path("runs/week2/plans"))
    parser.add_argument("--out", type=Path, default=Path("runs/week2/team"))
    parser.add_argument("--workspaces", type=Path, default=Path.home() / "spec2pr-workspaces")
    args = parser.parse_args(argv)
    result = run_team(args.task, args.plans, args.out, args.workspaces)
    print("status: %s | stopped_at: %s | review: %s" % (
        result["status"], result.get("stopped_at"), result.get("review_verdict")))
    print("hidden f2p: %s | p2p: %s" % (result.get("f2p"), result.get("p2p")))
    print("cost: $%s of $%s" % (result["total_cost_usd"], result["budget_usd"]))
    for note in result["observations"]:
        print(" - " + note)
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())