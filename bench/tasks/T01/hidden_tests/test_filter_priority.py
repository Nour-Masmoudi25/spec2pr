"""Evaluator-only acceptance tests for T01; never mount with the agent."""
import pytest

from tasklib import TaskStore


@pytest.mark.parametrize("priority", ["low", "medium", "high"])
def test_matches_requested_priority(priority):
    store = TaskStore()
    tasks = [store.add("Low", "low"), store.add("Medium"), store.add("High", "high")]
    result = store.filter_by_priority(priority)
    assert isinstance(result, list)
    assert result == [task for task in tasks if task.priority == priority]


@pytest.mark.parametrize("priority", ["urgent", "HIGH", " high ", ""],
                         ids=["unknown", "uppercase", "whitespace", "empty"])
def test_rejects_unsupported_strings(priority):
    store = TaskStore()
    store.add("Keep", "high")
    with pytest.raises(ValueError):
        store.filter_by_priority(priority)


@pytest.mark.parametrize("priority", ["low", "medium", "high"])
def test_empty_store_returns_empty_list(priority):
    assert TaskStore().filter_by_priority(priority) == []


def test_no_matching_tasks_returns_empty_list():
    store = TaskStore()
    store.add("Only low", "low")
    assert store.filter_by_priority("high") == []


def test_preserves_creation_order():
    store = TaskStore()
    first = store.add("Z comes first", "high")
    store.add("Excluded", "low")
    second = store.add("A comes second", "high")
    third = store.add("M comes third", "high")
    assert store.filter_by_priority("high") == [first, second, third]


def test_includes_completed_and_incomplete_tasks():
    store = TaskStore()
    completed = store.add("Done", "high")
    incomplete = store.add("Pending", "high")
    store.complete(completed.id)
    assert store.filter_by_priority("high") == [completed, incomplete]


def test_returns_original_objects_in_fresh_lists():
    store = TaskStore()
    task = store.add("Keep", "high")
    first = store.filter_by_priority("high")
    second = store.filter_by_priority("high")
    assert first is not second
    assert len(first) == len(second) == 1
    assert first[0] is second[0] is task
    first.clear()
    assert store.list_tasks() == second == [task]


def test_does_not_change_tasks_order_or_id_allocation():
    store = TaskStore()
    first = store.add("First", "low")
    second = store.add("Second", "high")
    store.complete(first.id)
    before = [task.to_dict() for task in store.list_tasks()]
    store.filter_by_priority("high")
    assert [task.to_dict() for task in store.list_tasks()] == before
    assert store.get(first.id) is first and store.get(second.id) is second
    assert store.add("Third").id == second.id + 1


def test_rejected_priority_leaves_store_unchanged():
    store = TaskStore()
    task = store.add("Original", "high")
    before = task.to_dict()
    with pytest.raises(ValueError):
        store.filter_by_priority("unknown")
    assert store.list_tasks() == [task]
    assert task.to_dict() == before
