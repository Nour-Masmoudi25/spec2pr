import json

import pytest

from tasklib import Task, TaskStore, load_store, save_store
import tasklib.storage as storage


def write_document(tmp_path, document):
    path = tmp_path / "tasks.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def valid_document():
    return {"version": 1, "next_id": 2, "tasks": [Task(1, "First").to_dict()]}


def test_empty_store_roundtrip(tmp_path):
    path = tmp_path / "empty.json"
    save_store(TaskStore(), path)
    restored = load_store(path)
    assert restored.list_tasks() == []
    assert restored.add("First").id == 1


def test_roundtrip_preserves_values_and_independence(tmp_path):
    store = TaskStore()
    first = store.add("Réviser 日本語", "high")
    store.add("Second", "low")
    store.complete(first.id)
    path = tmp_path / "tâches.json"
    save_store(store, str(path))
    assert "Réviser 日本語" in path.read_text(encoding="utf-8")
    restored = load_store(str(path))
    assert restored.list_tasks() == store.list_tasks()
    assert restored.get(1) is not first
    restored.update(1, title="Independent")
    assert first.title == "Réviser 日本語"
    assert restored.add("Third").id == 3


def test_loading_preserves_nonnumeric_order_and_counter_gaps(tmp_path):
    document = {"version": 1, "next_id": 20, "tasks": [
        Task(8, "First").to_dict(), Task(2, "Second").to_dict()
    ]}
    path = write_document(tmp_path, document)
    store = load_store(path)
    assert [t.id for t in store.list_tasks()] == [8, 2]
    save_store(store, path)
    assert json.loads(path.read_text(encoding="utf-8")) == document
    assert store.add("Next").id == 20


def test_save_replaces_existing_file_without_leftover_temp(tmp_path):
    store = TaskStore()
    path = tmp_path / "tasks.json"
    save_store(store, path)
    store.add("Added")
    save_store(store, path)
    assert load_store(path).get(1).title == "Added"
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("field,value", [
    ("title", " "), ("priority", "urgent"), ("completed", 1), ("id", 9),
])
def test_invalid_mutation_preserves_existing_file(tmp_path, field, value):
    store = TaskStore()
    task = store.add("Original")
    path = tmp_path / "tasks.json"
    save_store(store, path)
    before = path.read_bytes()
    setattr(task, field, value)
    with pytest.raises(ValueError):
        save_store(store, path)
    assert path.read_bytes() == before
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("operation", ["fsync", "replace"])
def test_io_failure_preserves_destination_and_cleans_temp(tmp_path, monkeypatch, operation):
    store = TaskStore()
    path = tmp_path / "tasks.json"
    save_store(store, path)
    before = path.read_bytes()
    store.add("Uncommitted")

    def fail(*args):
        raise PermissionError("simulated I/O failure")

    monkeypatch.setattr(storage.os, operation, fail)
    with pytest.raises(PermissionError, match="simulated"):
        save_store(store, path)
    assert path.read_bytes() == before
    assert list(tmp_path.iterdir()) == [path]


def test_missing_file_and_parent_raise_filesystem_errors(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_store(tmp_path / "absent.json")
    with pytest.raises(FileNotFoundError):
        save_store(TaskStore(), tmp_path / "absent" / "tasks.json")


def test_load_permission_error_propagates(tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise PermissionError("denied")

    monkeypatch.setattr(storage.Path, "open", fail)
    with pytest.raises(PermissionError, match="denied"):
        load_store(tmp_path / "tasks.json")


@pytest.mark.parametrize("text", [
    "", "{", "null", "[]", "{}", '{"version":1,"version":1}',
    '{"version":NaN}', '{"version":Infinity}',
])
def test_invalid_json_documents(tmp_path, text):
    path = tmp_path / "bad.json"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError):
        load_store(path)


def test_invalid_utf8(tmp_path):
    path = tmp_path / "bad.json"
    path.write_bytes(b"\xff")
    with pytest.raises(ValueError):
        load_store(path)


@pytest.mark.parametrize("field,value", [
    ("version", 2), ("version", True), ("version", 1.0), ("version", "1"),
    ("next_id", 0), ("next_id", True), ("next_id", 1), ("next_id", "2"),
    ("tasks", {}), ("tasks", None), ("tasks", [None]),
])
def test_invalid_document_fields(tmp_path, field, value):
    document = valid_document()
    document[field] = value
    with pytest.raises(ValueError):
        load_store(write_document(tmp_path, document))


@pytest.mark.parametrize("field", ["version", "next_id", "tasks"])
def test_missing_document_fields(tmp_path, field):
    document = valid_document()
    del document[field]
    with pytest.raises(ValueError):
        load_store(write_document(tmp_path, document))


def test_unknown_document_field(tmp_path):
    document = valid_document()
    document["extra"] = False
    with pytest.raises(ValueError):
        load_store(write_document(tmp_path, document))


def test_duplicate_task_ids(tmp_path):
    document = valid_document()
    document["tasks"].append(Task(1, "Duplicate").to_dict())
    with pytest.raises(ValueError, match="Duplicate task ID"):
        load_store(write_document(tmp_path, document))


def test_duplicate_nested_json_field(tmp_path):
    text = ('{"version":1,"next_id":2,"tasks":['
            '{"id":1,"title":"A","title":"B","priority":"low","completed":false}]}')
    path = tmp_path / "bad.json"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate JSON field"):
        load_store(path)


@pytest.mark.parametrize("field,value", [
    ("id", True), ("title", ""), ("priority", "HIGH"), ("completed", 0),
])
def test_load_validates_task_values(tmp_path, field, value):
    document = valid_document()
    document["tasks"][0][field] = value
    with pytest.raises(ValueError):
        load_store(write_document(tmp_path, document))


def test_loading_failure_does_not_change_existing_store(tmp_path):
    existing = TaskStore()
    task = existing.add("Keep")
    document = valid_document()
    document["tasks"].append({"id": 2})
    with pytest.raises(ValueError):
        load_store(write_document(tmp_path, document))
    assert existing.list_tasks() == [task]
    assert existing.add("Next").id == 2
