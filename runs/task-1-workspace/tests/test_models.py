import pytest

from tasklib import Task


def test_task_defaults_and_unicode_title():
    task = Task(1, "  Réviser 日本語  ")
    assert task.to_dict() == {
        "id": 1, "title": "Réviser 日本語", "priority": "medium", "completed": False
    }


@pytest.mark.parametrize("task_id", [0, -1, True, False, 1.0, "1", None])
def test_invalid_ids(task_id):
    with pytest.raises(ValueError):
        Task(task_id, "Title")


@pytest.mark.parametrize("title", [None, 10, [], "", " \n\t "])
def test_invalid_titles(title):
    with pytest.raises(ValueError):
        Task(1, title)


@pytest.mark.parametrize("priority", [None, [], "HIGH", " high ", "urgent"])
def test_invalid_priorities(priority):
    with pytest.raises(ValueError):
        Task(1, "Title", priority)


@pytest.mark.parametrize("completed", [0, 1, "false", None])
def test_invalid_completion_flags(completed):
    with pytest.raises(ValueError):
        Task(1, "Title", completed=completed)


@pytest.mark.parametrize("priority", ["low", "medium", "high"])
def test_dictionary_roundtrip(priority):
    original = Task(12, "Read  two chapters", priority, True)
    record = original.to_dict()
    restored = Task.from_dict(record)
    assert restored == original
    assert restored is not original
    record["title"] = "Different"
    assert restored.title == original.title == "Read  two chapters"


@pytest.mark.parametrize("field", ["id", "title", "priority", "completed"])
def test_missing_record_fields(field):
    record = Task(1, "Title").to_dict()
    del record[field]
    with pytest.raises(ValueError):
        Task.from_dict(record)


@pytest.mark.parametrize("record", [None, [], {}, {1: "bad key"}])
def test_invalid_records(record):
    with pytest.raises(ValueError):
        Task.from_dict(record)


def test_unknown_record_field_is_rejected():
    record = Task(1, "Title").to_dict()
    record["description"] = "Unexpected"
    with pytest.raises(ValueError):
        Task.from_dict(record)


@pytest.mark.parametrize("field,value", [
    ("id", True), ("title", " "), ("priority", "urgent"), ("completed", 1)
])
def test_serialization_revalidates_mutated_objects(field, value):
    task = Task(1, "Title")
    setattr(task, field, value)
    with pytest.raises(ValueError):
        task.to_dict()


def test_serialization_does_not_mutate_object():
    task = Task(1, "Title")
    task.title = "  Updated  "
    assert task.to_dict()["title"] == "Updated"
    assert task.title == "  Updated  "
