"""Synthetic handoff fixtures test the validator, not a live planner."""
from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from contracts import ContractError, load_json, validate_contract
from contracts.validate import KINDS, SCHEMAS
from bench.check_plans import check_plans

SPEC = {"spec_id": "T01", "description": "Add TaskStore.filter_by_priority(priority).", "acs": [{"id": "AC-1", "text": "Return matching tasks"},
        {"id": "AC-2", "text": "Preserve order"}],
        "allowed_paths": ["src/tasklib/"], "budget_usd": 1.0}
PLAN = {"spec_id": "T01", "tasks": [{"id": "P1", "files": ["src/tasklib/store.py"],
        "acs": ["AC-1", "AC-2"]}], "risks": []}
EXAMPLES = {
    "spec": SPEC,
    "plan": PLAN,
    "test_plan": {"spec_id": "T01", "test_ids": ["case1", "case2"],
                  "ac_map": {"AC-1": ["case1"], "AC-2": ["case2"]}},
    "implementation_report": {"spec_id": "T01", "task_id": "P1",
                              "diff_stat": [{"file": "src/tasklib/store.py", "added": 5, "removed": 0}],
                              "notes": []},
    "test_report": {"spec_id": "T01", "f2p": {"pass": 16, "fail": 0},
                    "p2p": {"pass": 127, "fail": 0}, "lint": "passed"},
    "review": {"spec_id": "T01", "verdict": "approve", "findings": []},
}


def validate(kind, data):
    return validate_contract(kind, data, spec=SPEC, plan=PLAN,
                             expected_counts={"f2p": 16, "p2p": 127})


@pytest.mark.parametrize("kind", sorted(KINDS))
def test_valid_schema_and_example(kind):
    Draft202012Validator.check_schema(load_json(SCHEMAS / f"{kind}.schema.json"))
    assert validate(kind, deepcopy(EXAMPLES[kind])) == EXAMPLES[kind]


@pytest.mark.parametrize("kind,key", [(kind, key) for kind, example in EXAMPLES.items() for key in example])
def test_every_required_field_is_required(kind, key):
    broken = deepcopy(EXAMPLES[kind])
    del broken[key]
    with pytest.raises(ContractError):
        validate(kind, broken)


@pytest.mark.parametrize("kind,key", [(kind, key) for kind, example in EXAMPLES.items() for key in example])
def test_every_top_level_field_rejects_wrong_type(kind, key):
    broken = deepcopy(EXAMPLES[kind])
    broken[key] = None
    with pytest.raises(ContractError):
        validate(kind, broken)


@pytest.mark.parametrize("kind", sorted(KINDS))
def test_unknown_field_is_rejected(kind):
    broken = deepcopy(EXAMPLES[kind])
    broken["unexpected"] = 1
    with pytest.raises(ContractError):
        validate(kind, broken)


@pytest.mark.parametrize("path", ["../tests/test.py", "/etc/passwd", "C:/secret", "src/../tests/a.py",
                                  "src/tasklib/../../tests/a.py", "src/tasklib\\a.py", "src/tasklib//a.py",
                                  "src/tasklib/.git/config", "tests/test.py", "src/tasklibrary/a.py"])
def test_plan_rejects_unsafe_or_disallowed_paths(path):
    plan = deepcopy(PLAN)
    plan["tasks"][0]["files"] = [path]
    with pytest.raises(ContractError):
        validate("plan", plan)


@pytest.mark.parametrize("mutation", ["missing_ac", "unknown_ac", "duplicate_task", "duplicate_owner", "wrong_spec"])
def test_plan_semantic_errors(mutation):
    plan = deepcopy(PLAN)
    if mutation == "missing_ac": plan["tasks"][0]["acs"] = ["AC-1"]
    if mutation == "unknown_ac": plan["tasks"][0]["acs"].append("AC-9")
    if mutation == "duplicate_task":
        plan["tasks"].append({"id": "P1", "files": ["src/tasklib/models.py"], "acs": ["AC-1"]})
    if mutation == "duplicate_owner":
        plan["tasks"].append({"id": "P2", "files": ["src/tasklib/store.py"], "acs": ["AC-1"]})
    if mutation == "wrong_spec": plan["spec_id"] = "T02"
    with pytest.raises(ContractError):
        validate("plan", plan)


@pytest.mark.parametrize("budget", [0, -1, True, float("inf"), float("nan")])
def test_budget_must_be_finite_positive_number(budget):
    spec = deepcopy(SPEC); spec["budget_usd"] = budget
    with pytest.raises(ContractError):
        validate("spec", spec)


def test_duplicate_ac_ids_rejected():
    spec = deepcopy(SPEC); spec["acs"][1]["id"] = "AC-1"
    with pytest.raises(ContractError):
        validate("spec", spec)


@pytest.mark.parametrize("kind", sorted(KINDS - {"spec"}))
def test_outputs_require_context(kind):
    with pytest.raises(ContractError):
        validate_contract(kind, EXAMPLES[kind])


@pytest.mark.parametrize("mutation", ["missing_ac", "unknown_ac", "unknown_test", "unmapped_test"])
def test_test_plan_reference_errors(mutation):
    data = deepcopy(EXAMPLES["test_plan"])
    if mutation == "missing_ac": del data["ac_map"]["AC-2"]
    if mutation == "unknown_ac": data["ac_map"]["AC-9"] = ["case1"]
    if mutation == "unknown_test": data["ac_map"]["AC-1"] = ["unknown"]
    if mutation == "unmapped_test": data["test_ids"].append("unmapped")
    with pytest.raises(ContractError):
        validate("test_plan", data)


@pytest.mark.parametrize("mutation", ["unknown_task", "unowned_file", "duplicate_file", "negative_count"])
def test_implementation_report_errors(mutation):
    data = deepcopy(EXAMPLES["implementation_report"])
    if mutation == "unknown_task": data["task_id"] = "P2"
    if mutation == "unowned_file": data["diff_stat"][0]["file"] = "src/tasklib/models.py"
    if mutation == "duplicate_file":
        data["diff_stat"].append({"file": "src/tasklib/store.py", "added": 2, "removed": 3})
    if mutation == "negative_count": data["diff_stat"][0]["added"] = -1
    with pytest.raises(ContractError):
        validate("implementation_report", data)


@pytest.mark.parametrize("value", [0, 15, 17, -1, True])
def test_incomplete_or_invalid_test_counts(value):
    data = deepcopy(EXAMPLES["test_report"]); data["f2p"]["pass"] = value
    with pytest.raises(ContractError):
        validate("test_report", data)


@pytest.mark.parametrize("mutation", ["approve_error", "unknown_ac", "unsafe_path", "bad_line"])
def test_review_errors(mutation):
    data = deepcopy(EXAMPLES["review"])
    finding = {"file": "src/tasklib/store.py", "line": 3, "ac": "AC-1", "severity": "warning", "message": "Explain this"}
    data["findings"] = [finding]
    if mutation == "approve_error": finding["severity"] = "error"
    if mutation == "unknown_ac": finding["ac"] = "AC-9"
    if mutation == "unsafe_path": finding["file"] = "../secret"
    if mutation == "bad_line": finding["line"] = 0
    with pytest.raises(ContractError):
        validate("review", data)


@pytest.mark.parametrize("text", ['{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}', '{'])
def test_strict_json_loading(tmp_path, text):
    path = tmp_path / "input.json"; path.write_text(text)
    with pytest.raises(ContractError):
        load_json(path)


def test_saved_plan_checker_rejects_missing_and_incomplete_plans(tmp_path):
    tasks, plans = tmp_path/"tasks", tmp_path/"plans"
    (tasks/"T01").mkdir(parents=True); plans.mkdir()
    (tasks/"T01/spec.json").write_text(json.dumps(SPEC))
    assert check_plans(tasks, plans)["valid"] == 0
    broken = deepcopy(PLAN); broken["tasks"][0]["acs"] = ["AC-1"]
    (plans/"T01.json").write_text(json.dumps(broken))
    assert check_plans(tasks, plans)["valid"] == 0
    (plans/"T01.json").write_text(json.dumps(PLAN))
    assert check_plans(tasks, plans)["valid"] == 1


def test_real_benchmark_specs_and_multifile_reference_patches():
    root = Path(__file__).resolve().parents[2] / "bench/tasks"
    tasks = sorted(root.glob("T[0-9][0-9]"))
    assert len(tasks) == 10
    multi = 0
    for task in tasks:
        spec = load_json(task/"spec.json")
        validate_contract("spec", spec)
        metadata = load_json(task/"task.json")
        assert spec["spec_id"] == metadata["task_id"] == task.name
        assert {item["id"] for item in spec["acs"]} == set(metadata["acceptance_map"])
        assert spec["allowed_paths"] == metadata["allowed_paths"]
        assert spec["description"] == (task/"spec.md").read_text(encoding="utf-8")
        assert all(metadata["acceptance_map"].values())
        changed = [line for line in (task/"reference.patch").read_text().splitlines() if line.startswith("+++ b/")]
        if task.name >= "T06" and len(changed) >= 2:
            multi += 1
    assert multi >= 3
