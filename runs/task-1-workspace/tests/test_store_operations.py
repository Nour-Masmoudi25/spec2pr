from copy import deepcopy

import pytest

from tasklib import TaskStore


def test_stores_are_independent():
    first, second = TaskStore(), TaskStore()
    task = first.add("Same")
    assert second.list_tasks() == []
    other = second.add("Same")
    assert task.id == other.id == 1
    first.complete(task.id)
    assert other.completed is False


def test_duplicate_titles_order_and_live_references():
    store = TaskStore()
    first, second = store.add("Same"), store.add("Same")
    tasks = store.list_tasks()
    assert [t.id for t in tasks] == [1, 2]
    assert tasks[0] is first is store.get(1)
    tasks.clear()
    assert store.list_tasks() == [first, second]
    first.title = "Changed"
    assert store.get(1).title == "Changed"


@pytest.mark.parametrize("method", ["get", "complete", "reopen", "update"])
@pytest.mark.parametrize("task_id,error", [(True, ValueError), (0, ValueError), (999, KeyError)])
def test_lookup_error_does_not_change_store(method, task_id, error):
    store = TaskStore()
    task = store.add("Keep")
    with pytest.raises(error):
        getattr(store, method)(task_id)
    assert task.title == "Keep"
    assert task.completed is False


def test_complete_and_reopen_are_idempotent():
    store = TaskStore()
    task = store.add("Work", "high")
    for _ in range(2):
        assert store.complete(task.id) is task
        assert task.completed is True
    for _ in range(2):
        assert store.reopen(task.id) is task
        assert task.completed is False
    assert task.priority == "high"


def test_update_preserves_identity_order_and_status():
    store = TaskStore()
    first, second = store.add("A"), store.add("B")
    store.complete(first.id)
    assert store.update(first.id, title=" New ", priority="low") is first
    assert (first.title, first.priority, first.completed) == ("New", "low", True)
    assert store.list_tasks() == [first, second]


@pytest.mark.parametrize("fields", [{}, {"title": None, "priority": None}])
def test_update_noop(fields):
    store = TaskStore()
    task = store.add("Keep", "high")
    assert store.update(task.id, **fields) is task
    assert (task.title, task.priority) == ("Keep", "high")


@pytest.mark.parametrize("fields", [
    {"title": "Valid", "priority": "invalid"},
    {"title": "  ", "priority": "low"},
    {"title": 123},
])
def test_update_is_atomic(fields):
    store = TaskStore()
    task = store.add("Keep", "high")
    with pytest.raises(ValueError):
        store.update(task.id, **fields)
    assert (task.title, task.priority) == ("Keep", "high")
    assert store.add("Next").id == 2


def test_update_one_field_leaves_other_unchanged():
    store = TaskStore()
    task = store.add("A", "high")
    store.update(task.id, title="B")
    assert (task.title, task.priority) == ("B", "high")
    store.update(task.id, priority="low")
    assert (task.title, task.priority) == ("B", "low")


def test_failed_add_does_not_consume_id():
    store = TaskStore()
    with pytest.raises(ValueError):
        store.add("Valid", "bad")
    assert store.add("First").id == 1


def test_add_many_preserves_input_and_assigns_consecutive_ids():
    store = TaskStore()
    store.add("Existing")
    items = [{"title": " A "}, {"title": "B", "priority": "high"}]
    before = deepcopy(items)
    tasks = store.add_many(items)
    assert items == before
    assert [t.id for t in tasks] == [2, 3]
    assert [t.title for t in tasks] == ["A", "B"]
    assert [t.priority for t in tasks] == ["medium", "high"]
    assert all(t is store.get(t.id) for t in tasks)
    assert store.add("Next").id == 4


def test_empty_batch_is_noop():
    store = TaskStore()
    assert store.add_many([]) == []
    assert store.add("First").id == 1


@pytest.mark.parametrize("bad_entry", [
    {}, None, "text", {"title": " "}, {"title": "B", "priority": None},
    {"title": "B", "id": 10}, {"title": "B", "completed": True},
])
def test_invalid_batch_rolls_back_all_entries(bad_entry):
    store = TaskStore()
    existing = store.add("Existing")
    with pytest.raises(ValueError):
        store.add_many([{"title": "Valid first entry"}, bad_entry])
    assert store.list_tasks() == [existing]
    assert store.add("Next").id == 2


@pytest.mark.parametrize("items", [None, {}, "text", ({"title": "A"},)])
def test_batch_requires_list(items):
    with pytest.raises(ValueError):
        TaskStore().add_many(items)
