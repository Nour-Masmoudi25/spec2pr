"""Check the evaluator using trusted, deliberately defective task copies."""
import importlib.util
import json
from pathlib import Path
import shutil

import pytest


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("task_validator", ROOT / "bench/validate.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


@pytest.fixture
def task_copy(tmp_path):
    destination = tmp_path / "T01"
    shutil.copytree(ROOT / "bench/tasks/T01", destination)
    return destination


def add_hidden_case(task, name, code):
    path = task / "hidden_tests/test_filter_priority.py"
    with path.open("a", encoding="utf-8") as stream:
        stream.write("\n\n" + code + "\n")
    metadata_path = task / "task.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["fail_to_pass"].append("hidden_tests/test_filter_priority.py::" + name)
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")


def test_valid_reference_and_unchanged_baseline(task_copy):
    before = validator.fingerprint(ROOT / "target_repo")
    result = validator.validate_task(task_copy, ROOT / "target_repo")
    assert result["fail_to_pass"] == 16
    assert result["pass_to_pass"] >= 30
    assert result["valid"] is True
    assert validator.fingerprint(ROOT / "target_repo") == before


def test_trap_rejects_hidden_case_already_passing(task_copy):
    add_hidden_case(task_copy, "test_already_passes",
                    "def test_already_passes():\n    assert TaskStore().list_tasks() == []")
    with pytest.raises(ValueError, match="already pass on baseline"):
        validator.validate_task(task_copy, ROOT / "target_repo")


def test_setup_error_is_not_a_legitimate_fail_to_pass(task_copy):
    add_hidden_case(task_copy, "test_fixture_error",
                    "def test_fixture_error(nonexistent_fixture):\n    assert False")
    with pytest.raises(ValueError, match="Setup/teardown"):
        validator.validate_task(task_copy, ROOT / "target_repo")


def test_skipped_hidden_case_is_invalid(task_copy):
    add_hidden_case(task_copy, "test_skipped",
                    '@pytest.mark.skip(reason="trap")\ndef test_skipped():\n    assert False')
    with pytest.raises(ValueError, match="skipped"):
        validator.validate_task(task_copy, ROOT / "target_repo")


def test_broken_reference_is_invalid(task_copy):
    path = task_copy / "reference.patch"
    patch = path.read_text(encoding="utf-8")
    patch = patch.replace(
        '+        return [task for task in self._tasks.values() if task.priority == requested]',
        '+        return []',
    )
    path.write_text(patch, encoding="utf-8")
    with pytest.raises(ValueError, match="Reference patch does not pass"):
        validator.validate_task(task_copy, ROOT / "target_repo")


def test_baseline_fingerprint_mismatch_is_invalid(task_copy):
    path = task_copy / "task.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["base_tree_sha256"] = "0" * 64
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="Baseline content differs"):
        validator.validate_task(task_copy, ROOT / "target_repo")


def test_reference_cannot_modify_visible_tests(task_copy, tmp_path):
    path = task_copy / "reference.patch"
    path.write_text('--- a/tests/test_store.py\n+++ b/tests/test_store.py\n@@ -1 +1 @@\n-import pytest\n+import os\n', encoding="utf-8")
    with pytest.raises(ValueError, match="only src/tasklib"):
        validator.apply_patch(tmp_path, path)
