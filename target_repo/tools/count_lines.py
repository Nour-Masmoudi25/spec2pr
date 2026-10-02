"""Count documented source and tests separately, without third-party tools."""

import ast
import io
from pathlib import Path
import tokenize


def counts(path):
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    docstrings = set()
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if (node.body and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)):
                doc = node.body[0]
                docstrings.update(range(doc.lineno, doc.end_lineno + 1))
    code = set()
    ignored = {tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE,
               tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER, tokenize.ENCODING}
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type not in ignored and token.start[0] not in docstrings:
            code.update(range(token.start[0], token.end[0] + 1))
    nonblank = {i for i, line in enumerate(lines, 1) if line.strip()}
    return (len(lines), len(nonblank & code), len(nonblank - code), len(lines) - len(nonblank))


def report(label, paths, root):
    totals = [0, 0, 0, 0]
    print(f"\n{label}: physical | code | comments/docstrings | blank")
    for path in sorted(paths):
        values = counts(path)
        totals = [a + b for a, b in zip(totals, values)]
        print(f"{path.relative_to(root)}: " + " | ".join(map(str, values)))
    print("TOTAL: " + " | ".join(map(str, totals)))


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    report("LIBRARY", (root / "src" / "tasklib").glob("*.py"), root)
    report("TESTS", (root / "tests").glob("test_*.py"), root)
