"""Build the agent's first message: spec + library source + working rules.

This reuses the strategy that solved T01 (see docs/day3-findings.md):
give the agent every file under src/tasklib/ up front so it does not explore,
ban patch syntax by name, and ask for a short append instead of a rewrite.
"""
from pathlib import Path

RULES = """\
## How to work

- Your only tool runs a shell command (sh) in /workspace. There is no network.
- The full current source of src/tasklib/ is shown above. Do NOT re-read or grep it.
- Never use `apply_patch`, `*** Begin Patch`, diffs or any patch syntax. They do not exist here.
- Do not rewrite whole files. TaskStore is the last class in src/tasklib/store.py,
  so add the new method by APPENDING it to the end of that file, indented by 4 spaces.
  Put any extra import (for example `import csv, io`) inside the method body.
- Use a short python heredoc like this (keep `EOF` alone at the start of its line):

```
python - <<'EOF'
code = \'\'\'

    def new_method(self, arg):
        return arg
\'\'\'
with open('src/tasklib/store.py', 'a') as f:
    f.write(code)
EOF
```

- Then check your work with: python -m pytest tests -q
- If tests fail, fix only your new method (you may rewrite just that method).
- When all tests pass, reply with a one-line summary and make no tool call.
- Only files under src/tasklib/ may change. Do not edit tests.
"""


def build_prompt(spec_text, workspace, forbidden_names=()):
    """Return the first user message for one attempt.

    forbidden_names: hidden-test file names that must never appear in the
    prompt (a "no peeking" guard). Raises ValueError if one does.
    """
    workspace = Path(workspace)
    parts = [spec_text.strip(), "", "## Current source of src/tasklib/", ""]
    for path in sorted((workspace / "src" / "tasklib").glob("*.py")):
        relative = path.relative_to(workspace).as_posix()
        code = path.read_text(encoding="utf-8")
        parts += [f"### {relative}", "```python", code.rstrip(), "```", ""]
    parts.append(RULES)
    prompt = "\n".join(parts)
    leaked = [name for name in forbidden_names if name in prompt]
    if leaked:
        raise ValueError("Prompt would leak hidden test names: " + ", ".join(leaked))
    return prompt
