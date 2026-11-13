"""PreToolUse guard for the implementer role.

Allowed: edit files under src/. Blocked: any other edit, shell writes to
protected folders, and git push. Exit code 2 with a message on stderr is the
documented way to block a tool call. This is a handoff check, not an OS
security boundary: indirect shell writes are only partly covered.
"""
import json
import re
import sys
from pathlib import Path

FILE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
PUSH = re.compile(r"\bgit\b[^;&|\n]*\bpush\b")
WRITE = re.compile(
    r">|\btee\b|\bsed\s+-i|\bmv\b|\bcp\b|\brm\b|\btouch\b|\bchmod\b|\bpatch\b"
    r"|\bgit\s+(checkout|restore|apply|stash|reset|clean)\b"
    r"|\b(del|erase|copy|move)\b|Set-Content|Add-Content|Out-File|\bopen\s*\(",
    re.IGNORECASE,
)
PROTECTED = re.compile(
    r"(^|[\s'\"=/\\])(tests|\.pipeline|\.claude|hooks|contracts|bench)([/\\]|\b)"
    r"|conftest\.py|pytest\.ini"
)


def inside_src(cwd, raw):
    base = Path(cwd).resolve()
    path = Path(raw)
    path = (path if path.is_absolute() else base / path).resolve()
    try:
        relative = path.relative_to(base)
    except ValueError:
        return False
    return relative.parts[:1] == ("src",)


def deny(reason):
    print(reason, file=sys.stderr)
    return 2


def main():
    try:
        payload = json.load(sys.stdin)
        tool = payload["tool_name"]
        data = payload.get("tool_input") or {}
        cwd = payload.get("cwd") or "."
    except (ValueError, KeyError, TypeError):
        return deny("Blocked: the hook could not read its input.")
    if tool in FILE_TOOLS:
        raw = data.get("file_path") or data.get("notebook_path")
        if not raw or not inside_src(cwd, raw):
            return deny("Blocked: the implementer may only edit files under src/. "
                        "Tests, hooks and contracts are read-only.")
        return 0
    if tool == "Bash":
        command = re.sub(r"\d*>&\d+|\d*>\s*/dev/null", "", str(data.get("command", "")))
        if PUSH.search(command):
            return deny("Blocked: git push is not allowed for the implementer.")
        if WRITE.search(command) and PROTECTED.search(command):
            return deny("Blocked: this command writes to tests, hooks, contracts or "
                        "pipeline files. Only src/ may change.")
    return 0


if __name__ == "__main__":
    sys.exit(main())