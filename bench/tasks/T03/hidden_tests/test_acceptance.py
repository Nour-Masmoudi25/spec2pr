import pytest
from tasklib import TaskStore, save_store, load_store

@pytest.mark.parametrize("index", [0, 1, 2])
def test_ac1_exact_removal_and_order(index):
    store = TaskStore()
    tasks = store.add_many([{"title": "same"}, {"title": "same"}, {"title": "last"}])
    store.complete(tasks[index].id)
    removed = store.delete(tasks[index].id)
    assert removed is tasks[index]
    assert removed.completed is True
    assert store.list_tasks() == tasks[:index] + tasks[index + 1:]
    for task in store.list_tasks():
        assert store.get(task.id) is task
        assert task.completed is False
    with pytest.raises(KeyError):
        store.get(removed.id)

@pytest.mark.parametrize("bad_id", [0, -1, True, False, 1.0, "1", None, [], {}])
def test_ac2_invalid_id_is_atomic(bad_id):
    store = TaskStore()
    task = store.add("keep")
    with pytest.raises(ValueError):
        store.delete(bad_id)
    assert store.list_tasks() == [task]
    assert store.add("next").id == 2

def test_ac2_absent_and_repeated_deletion():
    store = TaskStore()
    with pytest.raises(KeyError):
        store.delete(10)
    task = store.add("remove")
    store.delete(task.id)
    with pytest.raises(KeyError):
        store.delete(task.id)
    assert store.list_tasks() == []
    assert store.add("next").id == 2

def test_ac3_no_id_reuse_after_emptying():
    store = TaskStore()
    tasks = store.add_many([{"title": "one"}, {"title": "two"}])
    store.delete(tasks[1].id)
    store.delete(tasks[0].id)
    assert store.add("three").id == 3

@pytest.mark.parametrize("remove_all", [False, True])
def test_ac4_persistence_keeps_counter(tmp_path, remove_all):
    store = TaskStore()
    tasks = store.add_many([{"title": "one"}, {"title": "two"}, {"title": "three"}])
    store.delete(2)
    if remove_all:
        store.delete(1)
        store.delete(3)
    path = tmp_path / "store.json"
    save_store(store, path)
    restored = load_store(path)
    assert [t.to_dict() for t in restored.list_tasks()] == [t.to_dict() for t in store.list_tasks()]
    assert restored.add("four").id == 4
