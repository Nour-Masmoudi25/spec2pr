"""Validate JSON structure and cross-document references before a handoff."""
import json
import math
from pathlib import Path

from jsonschema import Draft202012Validator

SCHEMAS = Path(__file__).resolve().parent
KINDS = {"spec", "plan", "test_plan", "implementation_report", "test_report", "review"}


class ContractError(ValueError):
    """A handoff must be rejected rather than silently repaired."""


def load_json(path):
    """Reject duplicate keys and nonfinite JSON values at the boundary."""
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ContractError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def bad_constant(value):
        raise ContractError(f"Invalid JSON constant: {value}")

    try:
        return json.loads(Path(path).read_text(encoding="utf-8"),
                          object_pairs_hook=unique, parse_constant=bad_constant)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ContractError(str(error)) from error


def require(condition, message):
    if not condition:
        raise ContractError(message)


def safe_path(path, *, directory=False):
    """Use portable checkout-relative paths; filesystem isolation is separate."""
    candidate = path[:-1] if directory and path.endswith("/") else path
    require(bool(candidate) and not candidate.startswith("/") and "\\" not in candidate
            and ":" not in candidate, f"Unsafe relative path: {path}")
    require(all(part not in {"", ".", "..", ".git"} for part in candidate.split("/")),
            f"Unsafe relative path: {path}")
    return candidate


def allowed_file(path, spec):
    safe_path(path)
    require(any(path.startswith(prefix) if prefix.endswith("/") else path == prefix
                for prefix in spec["allowed_paths"]), f"File outside allowed paths: {path}")


def validate_contract(kind, data, *, spec=None, plan=None, expected_counts=None):
    """Return the validated object, or raise ContractError.

    Spec context is mandatory for every output. Implementation reports also
    need the accepted plan. Test counts are checked against evaluator-owned
    counts when supplied; an agent report alone never proves test success.
    """
    require(kind in KINDS, f"Unknown contract: {kind}")
    schema = load_json(SCHEMAS / f"{kind}.schema.json")
    errors = list(Draft202012Validator(schema).iter_errors(data))
    if errors:
        first = errors[0]
        raise ContractError(f"{kind} at {list(first.path)}: {first.message}")
    if kind == "spec":
        ids = [item["id"] for item in data["acs"]]
        require(len(ids) == len(set(ids)), "Duplicate acceptance criterion ID")
        require(math.isfinite(data["budget_usd"]), "Budget must be finite")
        for path in data["allowed_paths"]:
            safe_path(path, directory=True)
        return data

    require(spec is not None, "Spec context is required")
    validate_contract("spec", spec)
    require(data["spec_id"] == spec["spec_id"], "Wrong spec_id")
    acs = {item["id"] for item in spec["acs"]}
    if kind == "plan":
        task_ids, covered, files = set(), set(), set()
        for task in data["tasks"]:
            require(task["id"] not in task_ids, "Duplicate plan task ID")
            task_ids.add(task["id"])
            require(set(task["acs"]) <= acs, "Unknown AC in plan")
            covered.update(task["acs"])
            for path in task["files"]:
                allowed_file(path, spec)
                require(path not in files, "Multiple plan tasks own the same file; group them")
                files.add(path)
        require(covered == acs, f"Uncovered ACs: {sorted(acs - covered)}")
    elif kind == "test_plan":
        require(set(data["ac_map"]) == acs, "Test plan must cover exactly the spec ACs")
        mapped = {test for tests in data["ac_map"].values() for test in tests}
        require(mapped == set(data["test_ids"]), "Unknown or unmapped test IDs")
    elif kind == "implementation_report":
        require(plan is not None, "Accepted plan is required")
        validate_contract("plan", plan, spec=spec)
        tasks = {task["id"]: task for task in plan["tasks"]}
        require(data["task_id"] in tasks, "Unknown implementation task ID")
        changed = [item["file"] for item in data["diff_stat"]]
        require(len(changed) == len(set(changed)), "Duplicate diff file")
        require(set(changed) <= set(tasks[data["task_id"]]["files"]), "Unowned diff file")
    elif kind == "test_report" and expected_counts is not None:
        for group in ("f2p", "p2p"):
            require(sum(data[group].values()) == expected_counts[group], f"Incomplete {group} count")
    elif kind == "review":
        for finding in data["findings"]:
            allowed_file(finding["file"], spec)
            require(finding["ac"] in acs, "Unknown review AC")
        require(data["verdict"] != "approve" or
                all(f["severity"] != "error" for f in data["findings"]),
                "Cannot approve unresolved errors")
    return data
