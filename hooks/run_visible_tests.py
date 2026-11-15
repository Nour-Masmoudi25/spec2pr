"""Trusted runner: runs the library's visible tests and writes
.pipeline/visible-test-report.json at the repository root.

If a target_repo/ folder exists, the tests run there (the library's own visible
tests). Otherwise they run in the current folder.
"""
import json
import re
import subprocess
import sys
from pathlib import Path


def main():
    root = Path.cwd()
    test_dir = root / "target_repo" if (root / "target_repo").is_dir() else root
    done = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                          cwd=test_dir, capture_output=True, text=True)
    output = done.stdout + done.stderr

    def count(word):
        found = re.findall(r"(\d+) " + word, output)
        return int(found[-1]) if found else 0

    report = {"exit_code": done.returncode, "passed": count("passed"),
              "failed": count("failed") + count("error")}
    (root / ".pipeline").mkdir(exist_ok=True)
    (root / ".pipeline" / "visible-test-report.json").write_text(json.dumps(report), encoding="utf-8")
    print(output[-1500:])
    print("report:", report)
    return done.returncode


if __name__ == "__main__":
    sys.exit(main())