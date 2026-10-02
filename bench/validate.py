"""Validate trusted benchmark tasks locally, without running an agent.

Every declared FAIL_TO_PASS case must fail normally on the baseline and pass
with the reference patch. All visible cases must pass both times. Collection,
setup, teardown errors and skipped cases do not count as legitimate failures.
Uncommitted baselines are supported provisionally via a content fingerprint;
this does not claim a Git baseline or a Docker execution has been verified.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


PROJECT = Path(__file__).resolve().parents[1]
BENCH = Path(__file__).resolve().parent
IGNORED = {".git", ".venv", "__pycache__", ".pytest_cache"}
TEXT_SUFFIXES = {".py", ".md", ".ini", ".txt", ".toml", ".json"}


def baseline_files(repo):
    return sorted(path for path in repo.rglob("*") if path.is_file()
                  and not any(part in IGNORED for part in path.relative_to(repo).parts)
                  and path.suffix != ".pyc")


def fingerprint(repo):
    """Hash names and content; normalize text newlines across Windows/Linux."""
    digest = hashlib.sha256()
    for path in baseline_files(repo):
        relative = path.relative_to(repo).as_posix().encode("utf-8")
        content = path.read_bytes()
        if path.suffix in TEXT_SUFFIXES:
            content = content.replace(b"\r\n", b"\n")
        digest.update(len(relative).to_bytes(8, "big") + relative)
        digest.update(len(content).to_bytes(8, "big") + content)
    return digest.hexdigest()


def copy_baseline(repo, destination):
    destination.mkdir()
    for source in baseline_files(repo):
        if source.is_symlink() or any(p.is_symlink() for p in source.parents if p != repo.parent):
            raise ValueError("Symlinked baseline files are not supported")
        target = destination / source.relative_to(repo)
        target.parent.mkdir(parents=True, exist_ok=True)
        content = source.read_bytes()
        if source.suffix in TEXT_SUFFIXES:
            content = content.replace(b"\r\n", b"\n")
        target.write_bytes(content)


def run_tests(checkout, hidden, timeout):
    """Run source and tests in a disposable trusted evaluator checkout."""
    shutil.copytree(hidden, checkout / "hidden_tests")
    report = checkout / "case-report.json"
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(checkout / "src"), str(BENCH)])
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("PYTEST_ADDOPTS", None)
    env.pop("PYTEST_PLUGINS", None)
    command = [sys.executable, "-m", "pytest", "-c", "pytest.ini",
               "-p", "_pytest_report", "-p", "no:cacheprovider",
               "--case-report", str(report), "tests", "hidden_tests", "-q"]
    completed = subprocess.run(command, cwd=checkout, env=env, capture_output=True,
                               text=True, encoding="utf-8", errors="replace", timeout=timeout)
    if completed.returncode not in (0, 1) or not report.exists():
        raise ValueError("pytest infrastructure/collection error: " +
                         (completed.stdout + completed.stderr)[-3000:])
    result = json.loads(report.read_text(encoding="utf-8"))
    if result["collection_errors"]:
        raise ValueError("pytest collection failed")
    if len(result["collected"]) != len(set(result["collected"])):
        raise ValueError("Duplicate collected test IDs")
    outcomes = {}
    for node in result["collected"]:
        phases = result["cases"].get(node, {})
        if phases.get("setup") != "passed" or phases.get("teardown") != "passed":
            raise ValueError(f"Setup/teardown error or skipped case: {node}")
        if phases.get("call") not in ("passed", "failed"):
            raise ValueError(f"Missing or skipped test call: {node}")
        outcomes[node] = phases["call"]
    if not outcomes:
        raise ValueError("No test cases collected")
    return outcomes


def apply_patch(checkout, patch_path):
    # Windows editors/Git checkouts may use CRLF. Match the normalized copies
    # and content fingerprint without modifying the submitted reference file.
    normalized_patch = checkout / ".reference.patch"
    normalized_patch.write_text(patch_path.read_text(encoding="utf-8"),
                                encoding="utf-8", newline="\n")
    patch_path = normalized_patch.resolve()
    command = ["git", "apply", "--numstat", "-z", str(patch_path)]
    stat = subprocess.run(command, cwd=checkout, capture_output=True, check=True, timeout=30)
    entries = stat.stdout.decode("utf-8").strip("\0").split("\0")
    for entry in entries:
        fields = entry.split("\t", 2)
        if len(fields) != 3 or not fields[2].startswith("src/tasklib/"):
            raise ValueError("Reference patch must change only src/tasklib/ files")
        if ".." in fields[2].split("/") or fields[0] == "-":
            raise ValueError("Unsafe or binary reference patch")
    subprocess.run(["git", "apply", "--check", str(patch_path)], cwd=checkout,
                   capture_output=True, check=True, timeout=30)
    subprocess.run(["git", "apply", str(patch_path)], cwd=checkout,
                   capture_output=True, check=True, timeout=30)


def validate_task(task_dir, repo, timeout=60):
    metadata = json.loads((task_dir / "task.json").read_text(encoding="utf-8"))
    expected = metadata["fail_to_pass"]
    if not expected or len(expected) != len(set(expected)):
        raise ValueError("FAIL_TO_PASS must contain unique explicit test IDs")
    if metadata["base_tree_sha256"] != fingerprint(repo):
        raise ValueError("Baseline content differs from task.json fingerprint")
    if metadata.get("base_commit") is not None:
        raise ValueError("This provisional validator does not yet validate Git commit baselines")
    with tempfile.TemporaryDirectory(prefix="spec2pr-validate-") as temporary:
        base = Path(temporary) / "base"
        fixed = Path(temporary) / "fixed"
        copy_baseline(repo, base)
        copy_baseline(repo, fixed)
        before = run_tests(base, task_dir / "hidden_tests", timeout)
        f2p = set(expected)
        hidden_ids = {node for node in before if node.startswith("hidden_tests/")}
        if hidden_ids != f2p:
            raise ValueError("Collected hidden tests do not match declared FAIL_TO_PASS IDs")
        visible_ids = {node for node in before if node.startswith("tests/")}
        if not visible_ids or set(before) != hidden_ids | visible_ids:
            raise ValueError("Expected visible and hidden tests only")
        already_pass = sorted(node for node in f2p if before[node] != "failed")
        if already_pass:
            raise ValueError("Hidden tests already pass on baseline: " + ", ".join(already_pass))
        if any(before[node] != "passed" for node in visible_ids):
            raise ValueError("Visible regression tests fail on baseline")
        apply_patch(fixed, task_dir / "reference.patch")
        after = run_tests(fixed, task_dir / "hidden_tests", timeout)
        if set(after) != set(before) or any(state != "passed" for state in after.values()):
            raise ValueError("Reference patch does not pass the same complete test suite")
        return {"task_id": metadata["task_id"], "valid": True,
                "fail_to_pass": len(f2p), "pass_to_pass": len(visible_ids),
                "base_tree_sha256": metadata["base_tree_sha256"],
                "base_commit": None, "runtime": sys.version.split()[0],
                "baseline_results": {"hidden_failed": len(f2p), "visible_passed": len(visible_ids)},
                "reference_results": {"hidden_passed": len(f2p), "visible_passed": len(visible_ids)},
                "execution": "local, provisional (not Docker)"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tasks", type=Path)
    parser.add_argument("--repo", type=Path, default=PROJECT / "target_repo")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    tasks = args.tasks.resolve()
    task_dirs = [tasks] if (tasks / "task.json").exists() else sorted(p for p in tasks.iterdir() if p.is_dir())
    if not task_dirs:
        parser.error("No task directories found")
    results = []
    for task in task_dirs:
        try:
            result = validate_task(task, args.repo.resolve(), args.timeout)
        except (ValueError, KeyError, OSError, subprocess.SubprocessError) as error:
            result = {"task_id": task.name, "valid": False, "reason": str(error)}
        results.append(result)
        print(f"{result['task_id']}: " + ("VALID" if result["valid"] else "INVALID: " + result["reason"]))
    valid = sum(result["valid"] for result in results)
    print(f"{valid}/{len(results)} tasks valid (local provisional validation)")
    if args.report:
        args.report.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    return 0 if valid == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
