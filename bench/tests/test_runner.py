"""Offline integration and boundary checks; no API requests or Docker needed."""
import importlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bench"))
runner = importlib.import_module("bench.run")
runtime = importlib.import_module("runtime")
agent_module = importlib.import_module("agent.agent")


@pytest.mark.parametrize("task_id", ["T01", "T02", "T03", "T04", "T05"])
@pytest.mark.parametrize("control,passed", [("reference", True), ("noop", False)])
def test_full_control_pipeline(task_id, control, passed, tmp_path):
    result = runner.run_attempt(ROOT / "bench/tasks" / task_id, tmp_path / "run",
                                agent=control, backend="local")
    assert result["passed"] is passed
    assert result["status"] == ("passed" if passed else "failed_tests")
    assert result["pass_to_pass"] == {"passed": 127, "total": 127}
    assert result["steps"] == 0
    assert (tmp_path / "run/trace.jsonl").read_text() == ""


def test_no_local_execution_for_model_code(tmp_path):
    with pytest.raises(ValueError, match="only run in Docker"):
        runner.run_attempt(ROOT / "bench/tasks/T01", tmp_path / "run", agent="single", backend="local")
    assert not (tmp_path / "run").exists()


def test_forbidden_edits_are_rejected(tmp_path):
    base, candidate = tmp_path / "base", tmp_path / "candidate"
    base.mkdir()
    (base / "pytest.ini").write_text("original")
    shutil.copytree(base, candidate)
    (candidate / "pytest.ini").write_text("changed")
    with pytest.raises(ValueError, match="forbidden path"):
        runtime.source_changes(base, candidate)


def test_new_deleted_source_and_cache_handling(tmp_path):
    base, candidate = tmp_path / "base", tmp_path / "candidate"
    (base / "src/tasklib").mkdir(parents=True)
    (base / "src/tasklib/old.py").write_text("old")
    shutil.copytree(base, candidate)
    (candidate / "src/tasklib/old.py").unlink()
    (candidate / "src/tasklib/new.py").write_text("new")
    (candidate / ".pytest_cache").mkdir()
    (candidate / ".pytest_cache/state").write_text("cache")
    assert runtime.source_changes(base, candidate) == {"src/tasklib/old.py": None, "src/tasklib/new.py": b"new"}


def test_docker_timeout_removes_container_and_mounts_only_checkout(tmp_path, monkeypatch):
    commands = []
    def fake_run(command, **kwargs):
        commands.append(command)
        if command[1] == "run":
            raise subprocess.TimeoutExpired(command, 1)
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(runtime.subprocess, "run", fake_run)
    with pytest.raises(subprocess.TimeoutExpired):
        runtime.docker_command(tmp_path, ["sh", "-c", "sleep 100"], timeout=1)
    run, cleanup = commands
    assert run[run.index("--network") + 1] == "none"
    assert run.count("-v") == 1
    assert run[run.index("-v") + 1] == f"{tmp_path.resolve()}:/workspace"
    assert "--read-only" in run and "--cap-drop" in run
    assert cleanup == ["docker", "rm", "-f", run[run.index("--name") + 1]]


class ToolCall:
    def __init__(self, identifier, arguments='{"command": "echo ok"}'):
        self.id = identifier
        self.function = SimpleNamespace(name="bash", arguments=arguments)

    def model_dump(self):
        return {"id": self.id, "type": "function", "function": vars(self.function)}


def response(calls):
    return SimpleNamespace(usage=SimpleNamespace(prompt_tokens=100, completion_tokens=20),
                           choices=[SimpleNamespace(message=SimpleNamespace(content="test", tool_calls=calls))])


def fake_client(responses):
    iterator = iter(responses)
    def create(**kwargs):
        result = next(iterator)
        if isinstance(result, Exception):
            raise result
        return result
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


def test_one_line_per_model_call_not_per_tool(tmp_path):
    shell_calls = []
    def shell(command, workdir):
        shell_calls.append(command)
        return {"exit_code": 0, "output": "ok"}
    client = fake_client([response([ToolCall("one"), ToolCall("two")]), response([])])
    result = agent_module.run_agent("spec", str(tmp_path), run_dir=tmp_path / "log",
                                    model_client=client, command_runner=shell)
    rows = [json.loads(line) for line in (tmp_path / "log/trace.jsonl").read_text().splitlines()]
    assert result["steps"] == len(rows) == 2
    assert len(rows[0]["tools"]) == len(shell_calls) == 2
    assert runner.trace_metrics(tmp_path / "log/trace.jsonl")["tokens_in"] == 200
    assert result["status"] == "stopped_by_model"


def test_failed_api_attempts_are_logged_with_unknown_usage(tmp_path):
    BadRequestError = type("BadRequestError", (Exception,), {})
    client = fake_client([BadRequestError(), response([])])
    agent_module.run_agent("spec", str(tmp_path), run_dir=tmp_path / "log", model_client=client)
    metrics = runner.trace_metrics(tmp_path / "log/trace.jsonl")
    assert metrics["steps"] == 2
    assert metrics["cost_usd"] is None


def test_step_limit_and_invalid_arguments(tmp_path):
    client = fake_client([response([ToolCall("bad", "{}")] )])
    result = agent_module.run_agent("spec", str(tmp_path), run_dir=tmp_path / "log",
                                    model_client=client, step_limit=1,
                                    command_runner=lambda *args: pytest.fail("must not execute"))
    assert result["status"] == "step_limit_reached"
    row = json.loads((tmp_path / "log/trace.jsonl").read_text())
    assert row["tools"][0]["exit_code"] == -1


def test_summary_counts_failures_and_requires_all_repeats():
    results = [{"task_id": task, "passed": passed, "steps": 2, "cost_usd": cost}
               for task, passed, cost in [("T01", True, .1), ("T01", False, .2), ("T02", True, None), ("T02", True, .3)]]
    summary = runner.summarize(results)
    assert summary["pass_rate"] == .75
    assert summary["all_repetitions_pass_rate"] == .5
    assert summary["tasks_solved_at_least_once"] == 2
    assert summary["median_cost_usd"] is None


def test_model_receives_no_hidden_bundle(tmp_path, monkeypatch):
    hidden_names = {p.name for p in (ROOT / "bench/tasks").glob("*/hidden_tests/*.py")}
    def fake_agent(spec, workdir, **kwargs):
        files = {p.relative_to(workdir).as_posix() for p in Path(workdir).rglob("*")}
        assert not any(name in spec for name in hidden_names)
        assert not any("hidden_tests" in p or "reference.patch" in p or ".git" in p for p in files)
        assert "pytest.ini" in files
        (kwargs["run_dir"] / "trace.jsonl").write_text("")
        return {"status": "mock_no_model"}
    monkeypatch.setattr(agent_module, "run_agent", fake_agent)
    # The evaluator is mocked too: no candidate code executes on the host.
    metadata = json.loads((ROOT / "bench/tasks/T01/task.json").read_text())
    def fake_tests(*args):
        return {node: "passed" for node in metadata["fail_to_pass"] + metadata["pass_to_pass"]}
    monkeypatch.setattr(runner, "run_tests", fake_tests)
    assert runner.run_attempt(ROOT / "bench/tasks/T01", tmp_path / "run", agent="single", backend="docker")["passed"]
