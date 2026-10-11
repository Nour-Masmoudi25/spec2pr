import csv
import io
import pytest
from tasklib import TaskStore

def read(text):
    return list(csv.reader(io.StringIO(text, newline="")))

def test_ac1_empty_header():
    assert TaskStore().to_csv() == "id,title,priority,completed\n"

def test_ac2_rows_order_and_boolean_spelling():
    store = TaskStore()
    a = store.add("Z", "high")
    store.add("A", "low")
    store.complete(a.id)
    assert store.to_csv() == "id,title,priority,completed\n1,Z,high,true\n2,A,low,false\n"

@pytest.mark.parametrize("title", ["a,b", 'say "hi"', "line1\nline2", "line1\rline2", "line1\r\nline2", "École مرحبا", 'one, "two"\nthree'])
def test_ac3_escaping_unicode_and_embedded_newlines(title):
    store = TaskStore()
    store.add(title)
    text = store.to_csv()
    assert text.endswith("\n")
    assert read(text) == [["id", "title", "priority", "completed"], ["1", title, "medium", "false"]]

def test_ac3_exact_quote_escaping():
    store = TaskStore()
    store.add('a,"b"')
    assert store.to_csv() == 'id,title,priority,completed\n1,"a,""b""",medium,false\n'

def test_ac4_repeat_current_state_and_no_mutation():
    store = TaskStore()
    tasks = store.add_many([{"title": "B"}, {"title": "A"}])
    before = [t.to_dict() for t in tasks]
    text = store.to_csv()
    assert store.to_csv() == text
    assert [t.to_dict() for t in store.list_tasks()] == before
    store.update(1, title="new")
    store.complete(1)
    assert read(store.to_csv())[1] == ["1", "new", "medium", "true"]
    assert store.add("C").id == 3
