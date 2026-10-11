import pytest
from tasklib import TaskStore

def test_ac1_empty_exact_keys_and_types():
    result = TaskStore().summary()
    assert result == {"total": 0, "completed": 0, "pending": 0}
    assert all(type(value) is int for value in result.values())

@pytest.mark.parametrize("completed", [0, 1, 2, 3])
def test_ac2_counts_all_priorities_and_duplicates(completed):
    store = TaskStore()
    tasks = [store.add("same", p) for p in ("low", "medium", "high")]
    for task in tasks[:completed]:
        store.complete(task.id)
    assert store.summary() == {"total": 3, "completed": completed, "pending": 3 - completed}

def test_ac3_current_state_after_transitions():
    store = TaskStore()
    task = store.add("first")
    assert store.summary() == {"total": 1, "completed": 0, "pending": 1}
    store.complete(task.id)
    store.complete(task.id)
    assert store.summary() == {"total": 1, "completed": 1, "pending": 0}
    store.reopen(task.id)
    store.add("second")
    assert store.summary() == {"total": 2, "completed": 0, "pending": 2}

def test_ac3_live_task_state():
    store = TaskStore()
    task = store.add("live")
    store.summary()
    task.completed = True
    assert store.summary()["completed"] == 1

def test_ac4_fresh_dict_and_no_mutation():
    store = TaskStore()
    tasks = store.add_many([{"title": "B"}, {"title": "A"}])
    before = [t.to_dict() for t in tasks]
    first = store.summary()
    assert first is not store.summary()
    first.clear()
    assert store.summary() == {"total": 2, "completed": 0, "pending": 2}
    assert [t.to_dict() for t in store.list_tasks()] == before
    assert store.add("C").id == 3
