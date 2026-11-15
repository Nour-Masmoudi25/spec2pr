"""Trusted runner: runs the library's visible tests and writes
.pipeline/visible-test-report.json at the repository root.

If a target_repo/ folder exists, the tests run there (the library's own visible
tests). Otherwise they run in the current folder. With the environment variable
SPEC2PR_VISIBLE_BACKEND=docker the tests run in the sandbox image (no network,
read-only mount) instead of on the host, because the code under test was written
by a model.
"""
import json
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path

IMAGE = "sandbox:py312"
PYTEST = ["python", "-m", "pytest", "-q", "-p", "no:cacheprovider"]


def run_pytest(test_dir):
    if os.environ.get("SPEC2PR_VISIBLE_BACKEND") != "docker":
        return subprocess.run([sys.executable] + PYTEST[1:], cwd=test_dir,
                              capture_output=True, text=True)
    name = "spec2pr-visible-" + uuid.uuid4().hex
    args = ["docker", "run", "--rm", "--name", name, "--network", "none", "--read-only",
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
            "--pids-limit", "128", "--memory", "512m", "--cpus", "1",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m", "--user", "1000:1000",
            "-v", str(test_dir.resolve()) + ":/workspace:ro", "-w", "/workspace",
            "-e", "PYTHONDONTWRITEBYTECODE=1", "-e", "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1",
            "-e", "PYTHONPATH=/workspace/src:/workspace", IMAGE] + PYTEST
    try:
        return subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=300)
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True, timeout=15)


def main():
    root = Path.cwd()
    test_dir = root / "target_repo" if (root / "target_repo").is_dir() else root
    try:
        done = run_pytest(test_dir)
        code, output = done.returncode, done.stdout + done.stderr
    except subprocess.TimeoutExpired:
        code, output = 124, "The visible tests timed out."
    except OSError as error:
        code, output = 125, "The visible tests could not be started: %s" % error

    def count(word):
        found = re.findall(r"(\d+) " + word, output)
        return int(found[-1]) if found else 0

    report = {"exit_code": code, "passed": count("passed"),
              "failed": count("failed") + count("error")}
    (root / ".pipeline").mkdir(exist_ok=True)
    (root / ".pipeline" / "visible-test-report.json").write_text(json.dumps(report), encoding="utf-8")
    print(output[-1500:])
    print("report:", report)
    return code


if __name__ == "__main__":
    sys.exit(main())