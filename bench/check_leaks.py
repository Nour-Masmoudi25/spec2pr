"""Search selected JSONL traces for hidden-test filenames without printing secrets."""
import argparse
import json
from pathlib import Path
import re
import sys

FORBIDDEN_NAMES = ("test_filter_priority.py", "test_acceptance.py")
PATTERN = re.compile("|".join(re.escape(name) for name in FORBIDDEN_NAMES), re.IGNORECASE)


def scan_traces(paths):
    files, errors = set(), []
    for raw_path in paths:
        path = Path(raw_path).resolve()
        try:
            if not path.exists():
                raise ValueError("path does not exist")
            if path.is_dir():
                found = list(path.rglob("trace.jsonl"))
                if not found:
                    raise ValueError("directory contains no trace.jsonl files")
                files.update(p.resolve() for p in found)
            elif path.name == "trace.jsonl":
                files.add(path)
            else:
                raise ValueError("select a directory or a file named trace.jsonl")
        except (OSError, ValueError) as error:
            errors.append({"path": str(path), "error": str(error)})
    if not files:
        errors.append({"path": None, "error": "no traces selected; zero hits would be inconclusive"})
    matches, rows = [], 0
    for path in sorted(files):
        nonempty = 0
        try:
            with path.open(encoding="utf-8-sig") as stream:
                for number, line in enumerate(stream, 1):
                    if not line.strip():
                        continue
                    nonempty += 1
                    try:
                        row = json.loads(line)
                        if not isinstance(row, dict):
                            raise ValueError("trace record must be a JSON object")
                        # Decoding first also finds JSON-escaped filenames.
                        text = json.dumps(row, ensure_ascii=False)
                        rows += 1
                    except ValueError:
                        errors.append({"path": str(path), "line": number, "error": "invalid JSON object"})
                        text = line
                    for match in PATTERN.finditer(text):
                        matches.append({"path": str(path), "line": number, "filename": match.group().lower()})
            if not nonempty:
                errors.append({"path": str(path), "error": "empty trace; no model evidence to check"})
        except (OSError, UnicodeError) as error:
            errors.append({"path": str(path), "error": type(error).__name__})
    return {"status": "incomplete" if errors else ("leak_found" if matches else "clean"),
            "trace_files": len(files), "valid_json_rows": rows,
            "occurrences": len(matches), "matches": matches, "errors": errors,
            "checked_files": [str(path) for path in sorted(files)],
            "forbidden_names": list(FORBIDDEN_NAMES)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, default=[Path("runs/benchmarks")])
    parser.add_argument("--report", type=Path, help="new JSON evidence file; never overwrites an existing file")
    args = parser.parse_args(argv)
    result = scan_traces(args.paths)
    print(f"{result['status']}: {result['occurrences']} occurrence(s), "
          f"{result['trace_files']} trace file(s), {result['valid_json_rows']} valid JSON row(s)")
    for match in result["matches"]:
        print(f"{match['path']}:{match['line']}: {match['filename']}")
    for error in result["errors"]:
        print(f"Incomplete check: {error['path']}: {error['error']}", file=sys.stderr)
    if args.report:
        try:
            with args.report.open("x", encoding="utf-8", newline="\n") as stream:
                json.dump(result, stream, indent=2, ensure_ascii=False)
                stream.write("\n")
        except OSError as error:
            print(f"Cannot create report: {error}", file=sys.stderr)
            return 2
    return 2 if result["errors"] else (1 if result["matches"] else 0)


if __name__ == "__main__":
    raise SystemExit(main())
