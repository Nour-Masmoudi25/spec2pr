"""Trusted runner: runs the visible tests and writes .pipeline/visible-test-report.json."""
import json
import re
import subprocess
import sys
from pathlib import Path


def main():
    cwd = Path.cwd()
    done = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                          cwd=cwd, capture_output=True, text=True)
    output = done.stdout + done.stderr

    def count(word):
        found = re.findall(r"(\d+) " + word, output)
        return int(found[-1]) if found else 0

    report = {"exit_code": done.returncode, "passed": count("passed"),
              "failed": count("failed") + count("error")}
    (cwd / ".pipeline").mkdir(exist_ok=True)
    (cwd / ".pipeline" / "visible-test-report.json").write_text(json.dumps(report), encoding="utf-8")
    print(output[-1500:])
    print("report:", report)
    return done.returncode


if __name__ == "__main__":
    sys.exit(main())