"""The planner retry policy, tested with a fake planner (no model calls)."""
import json
from pathlib import Path

from pipeline import plan_all

TASK = Path(__file__).resolve().parents[2] / "bench" / "tasks" / "T01"
ALL_ACS = ["AC-1", "AC-2", "AC-3", "AC-4", "AC-5", "AC-6", "AC-7"]
GOOD = {"spec_id": "T01",
        "tasks": [{"id": "T01-1", "files": ["src/tasklib/store.py"], "acs": ALL_ACS}],
        "risks": ["Test risk."]}
BAD = {"spec_id": "T01",
       "tasks": [{"id": "T01-1", "files": ["src/tasklib/store.py"], "acs": ["AC-1"]}],
       "risks": ["Only one criterion is covered on purpose."]}


def reply(plan):
    return {"exit_code": 0, "result": json.dumps(plan), "is_error": False, "cost_usd": 0.01}


def fake_planner(monkeypatch, replies):
    prompts = []

    def call(prompt, timeout=900):
        prompts.append(prompt)
        return replies[len(prompts) - 1]  # a third call would raise IndexError

    monkeypatch.setattr(plan_all, "call_planner", call)
    return prompts


def test_valid_first_reply_needs_no_retry(tmp_path, monkeypatch):
    prompts = fake_planner(monkeypatch, [reply(GOOD)])
    result = plan_all.plan_one(TASK, tmp_path, force=False)
    assert result["status"] == "accepted" and result["attempts"] == 1
    assert len(prompts) == 1


def test_rejected_first_reply_is_retried_once_with_the_error(tmp_path, monkeypatch):
    prompts = fake_planner(monkeypatch, [reply(BAD), reply(GOOD)])
    result = plan_all.plan_one(TASK, tmp_path, force=False)
    assert result["status"] == "accepted" and result["attempts"] == 2
    assert "Validator error" in prompts[1]
    saved = json.loads((tmp_path / "plans" / "T01.json").read_text(encoding="utf-8"))
    assert saved == GOOD
    trace = json.loads((tmp_path / "plan-traces" / "T01.json").read_text(encoding="utf-8"))
    assert [a["accepted"] for a in trace["attempts"]] == [False, True]
    assert trace["attempts"][0]["error"]


def test_second_rejection_stops_and_saves_nothing(tmp_path, monkeypatch):
    prompts = fake_planner(monkeypatch, [reply(BAD), reply(BAD)])
    result = plan_all.plan_one(TASK, tmp_path, force=False)
    assert result["status"] == "rejected after retry" and result["attempts"] == 2
    assert len(prompts) == 2
    assert not (tmp_path / "plans" / "T01.json").exists()
    assert (tmp_path / "plan-traces" / "T01.json").exists()


def test_saved_plan_is_skipped_unless_forced(tmp_path, monkeypatch):
    fake_planner(monkeypatch, [reply(GOOD), reply(GOOD)])
    plan_all.plan_one(TASK, tmp_path, force=False)
    again = plan_all.plan_one(TASK, tmp_path, force=False)
    assert again["status"].startswith("skipped")
    forced = plan_all.plan_one(TASK, tmp_path, force=True)
    assert forced["status"] == "accepted"