import pytest

from tasklib import TaskStore


def test_new_store_is_empty():
    store = TaskStore()
    assert store.list_tasks() == []


def test_add_sets_defaults_and_trims_title():
    store = TaskStore()
    task = store.add("  Read guide  ")

    assert task.title == "Read guide"
    assert task.priority == "medium"
    assert task.completed is False


def test_ids_are_unique():
    store = TaskStore()
    first = store.add("First")
    second = store.add("Second")

    assert first.id != second.id


@pytest.mark.parametrize("title", ["", "   ", None])
def test_invalid_title_is_rejected(title):
    store = TaskStore()

    with pytest.raises(ValueError):
        store.add(title)


def test_invalid_priority_is_rejected():
    store = TaskStore()

    with pytest.raises(ValueError):
        store.add("Read guide", priority="urgent")


def test_complete_marks_task_done():
    store = TaskStore()
    task = store.add("Read guide")

    store.complete(task.id)

    assert store.get(task.id).completed is True


def test_unknown_id_raises_key_error():
    store = TaskStore()

    with pytest.raises(KeyError):
        store.get(999)