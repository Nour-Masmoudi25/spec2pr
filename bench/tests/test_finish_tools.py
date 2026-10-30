"""Synthetic fixtures exercise reporting only; they are never agent results."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load_module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "bench" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


aggregate = load_module("aggregate")
leaks = load_module("check_leaks")


@pytest.fixture
def batches(tmp_path):
    paths = []
    step_groups = [[1, 20, 20], [2, 20, 20], [3, 4, 5], [6, 7, 8], [9, 10, 11]]
    passes = [[True, True, True], [True, False, False], [False, False, False],
              [True, True, True], [True, True, False]]
    for index, task in enumerate(aggregate.TASKS):
        records = []
        for repetition in range(3):
            passed = passes[index][repetition]
            cost = (3 * index + repetition + 1) / 1000
            records.append({"task_id": task, "run_id": f"{task}-{repetition + 1}",
                            "agent": "single", "backend": "docker", "base_commit": "b" * 40,
                            "passed": passed, "status": "passed" if passed else "failed_tests",
                            "steps": step_groups[index][repetition], "cost_usd": cost,
                            "known_cost_usd": cost, "api_error_calls": 0})
        batch = {"agent": "single", "backend": "docker", "image": "sandbox:py312",
                 "evaluation_commit": "a" * 40, "working_tree_dirty": False,
                 "repetitions": 3, "runs": 3, "passed": sum(passes[index]), "results": records}
        path = tmp_path / f"{task}.json"
        path.write_text(json.dumps(batch), encoding="utf-8")
        paths.append(path)
    return paths


def modify(path, change):
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(json.dumps(data), encoding="utf-8")


def test_aggregate_uses_all_fifteen_runs_not_medians_of_batches(batches):
    result = aggregate.aggregate(list(reversed(batches)))
    assert result["passed"] == 9 and result["runs"] == 15
    assert result["pass_rate"] == .6
    assert result["median_steps"] == 8  # median of the five medians would be 10
    assert result["median_cost_usd"] == pytest.approx(.008)
    assert result["median_known_cost_usd_lower_bound"] == pytest.approx(.008)
    assert result["tasks_solved_at_least_once"] == 4
    assert result["pass_cubed"] == .4
    assert [source["task_id"] for source in result["sources"]] == list(aggregate.TASKS)


def test_unknown_full_cost_keeps_lower_bound_and_error_rows(batches):
    def change(data):
        data["results"][0].update(cost_usd=None, api_error_calls=1)
    modify(batches[0], change)
    result = aggregate.aggregate(batches)
    assert result["median_cost_usd"] is None
    assert result["median_known_cost_usd_lower_bound"] == pytest.approx(.008)
    assert result["total_api_error_calls"] == 1
    assert "lower bound" in aggregate.markdown(result)
    assert "full cost is unknown" in aggregate.markdown(result)


@pytest.mark.parametrize("change,message", [
    (lambda d: d.update(working_tree_dirty=True), "working_tree_dirty"),
    (lambda d: d.update(working_tree_dirty="false"), "working_tree_dirty"),
    (lambda d: d.pop("working_tree_dirty"), "working_tree_dirty"),
    (lambda d: d.update(evaluation_commit="c" * 40), "commits differ"),
    (lambda d: d.update(evaluation_commit="834104f"), "40-character"),
    (lambda d: d.update(agent="reference"), "single-agent"),
    (lambda d: d.update(backend="local"), "Docker"),
    (lambda d: d.update(image="different:image"), "image tags differ"),
    (lambda d: d.update(repetitions=2), "3 repetitions"),
    (lambda d: d["results"].pop(), "exactly 3 individual"),
    (lambda d: d["results"][0].update(run_id="T01-2"), "run IDs"),
    (lambda d: d["results"][0].update(base_commit="c" * 40), "baseline commits differ"),
    (lambda d: d["results"][0].update(backend="local"), "run agent/backend"),
    (lambda d: d["results"][0].update(passed="true"), "boolean"),
    (lambda d: d["results"][0].update(status="failed_tests"), "passed/status"),
    (lambda d: d["results"][0].update(steps=True), "steps must be an integer"),
    (lambda d: d["results"][0].update(known_cost_usd=-1), "finite nonnegative"),
    (lambda d: d["results"][0].update(known_cost_usd=float("nan")), "finite nonnegative"),
    (lambda d: d["results"][0].update(cost_usd=float("inf")), "finite nonnegative"),
    (lambda d: d["results"][0].pop("known_cost_usd"), "known_cost_usd"),
    (lambda d: d["results"][0].update(api_error_calls=2), "cannot exceed"),
    (lambda d: d["results"][0].update(cost_usd=None), "unknown cost"),
    (lambda d: d["results"][0].update(known_cost_usd=.5), "inconsistent"),
    (lambda d: d.update(passed=0), "passed count"),
])
def test_rejects_invalid_or_incomparable_batches(batches, change, message):
    modify(batches[0], change)
    with pytest.raises(ValueError, match=message):
        aggregate.aggregate(batches)


def test_rejects_incomplete_duplicate_paths_and_duplicate_tasks(batches):
    with pytest.raises(ValueError, match="exactly 5"):
        aggregate.aggregate(batches[:-1])
    with pytest.raises(ValueError, match="duplicate summary path"):
        aggregate.aggregate(batches[:-1] + [batches[0]])
    batches[-1].write_bytes(batches[0].read_bytes())
    with pytest.raises(ValueError, match="one batch for each"):
        aggregate.aggregate(batches)


def test_aggregate_cli_writes_new_outputs_and_preserves_existing_results(batches, tmp_path, capsys):
    output, evidence = tmp_path / "RESULTS.generated.md", tmp_path / "aggregate.json"
    args = [*map(str, batches), "--output", str(output), "--json-output", str(evidence)]
    assert aggregate.main(args) == 0
    assert "| 0 | Single agent | 5 × 3 | 9/15 (60.0%)" in output.read_text(encoding="utf-8")
    assert json.loads(evidence.read_text())["runs"] == 15
    original = output.read_bytes()
    assert aggregate.main(args) == 2
    assert output.read_bytes() == original


def test_invalid_input_never_creates_result_files(batches, tmp_path):
    modify(batches[0], lambda data: data.update(working_tree_dirty=True))
    output = tmp_path / "RESULTS.md"
    assert aggregate.main([*map(str, batches), "--output", str(output)]) == 2
    assert not output.exists()


def trace(tmp_path, name, lines):
    path = tmp_path / name / "trace.jsonl"
    path.parent.mkdir(parents=True)
    path.write_text(lines, encoding="utf-8")
    return path


def test_scan_finds_nested_outputs_and_json_escaped_names_without_exposing_content(tmp_path, capsys):
    path = trace(tmp_path, "run", '{"step":1,"tools":[{"output":"SECRET test_filter_priority.py"}]}\n'
                 '{"step":2,"assistant":"TEST_ACCEPTANCE.PY and test\\u005facceptance.py"}\n')
    result = leaks.scan_traces([tmp_path, path])
    assert result["trace_files"] == 1  # overlapping inputs are deduplicated
    assert result["occurrences"] == 3
    assert [item["line"] for item in result["matches"]] == [1, 2, 2]
    assert leaks.main([str(tmp_path)]) == 1
    assert "SECRET" not in capsys.readouterr().out


def test_clean_traces_do_not_scan_summary_or_submission(tmp_path):
    trace(tmp_path, "run", '{"step":1,"assistant":"done"}\n')
    (tmp_path / "summary.json").write_text('test_acceptance.py')
    result = leaks.scan_traces([tmp_path])
    assert result["status"] == "clean" and result["occurrences"] == 0
    assert leaks.main([str(tmp_path)]) == 0


@pytest.mark.parametrize("content", ["", "\n\n", "{broken json\n", "[]\n"])
def test_empty_or_malformed_trace_is_inconclusive(tmp_path, content):
    path = trace(tmp_path, "run", content)
    assert leaks.scan_traces([path])["status"] == "incomplete"
    assert leaks.main([str(path)]) == 2


def test_missing_empty_directory_and_wrong_file_fail_closed(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    other = tmp_path / "summary.json"
    other.write_text("{}")
    for path in (empty, tmp_path / "missing", other):
        assert leaks.main([str(path)]) == 2


def test_partly_missing_selection_cannot_report_clean(tmp_path):
    path = trace(tmp_path, "valid", '{"step":1}\n')
    result = leaks.scan_traces([path, tmp_path / "missing"])
    assert result["occurrences"] == 0 and result["status"] == "incomplete"


def test_invalid_encoding_is_inconclusive(tmp_path):
    path = trace(tmp_path, "run", "")
    path.write_bytes(b"\xff\xfe")
    assert leaks.main([str(path)]) == 2


def test_report_output_never_overwrites_input_trace(tmp_path):
    path = trace(tmp_path, "run", '{"step":1}\n')
    original = path.read_bytes()
    assert leaks.main([str(path), "--report", str(path)]) == 2
    assert path.read_bytes() == original
    report = tmp_path / "leaks.json"
    assert leaks.main([str(path), "--report", str(report)]) == 0
    assert json.loads(report.read_text())["status"] == "clean"
