import pytest
from tasklib import TaskStore

@pytest.mark.parametrize("title,query", [("Review code", "VIEW"), ("Straße", "STRASSE"), ("École", "éCO"), ("مرحبا", "رح"), ("a[b]c", "[b]")])
def test_ac1_unicode_substring(title, query):
    store = TaskStore()
    task = store.add(title)
    assert store.search(query) == [task]

def test_ac2_empty_and_no_matches():
    store = TaskStore()
    assert store.search("") == []
    a, b = store.add_many([{"title": "one"}, {"title": "two"}])
    assert store.search("") == [a, b]
    assert store.search("missing") == []

def test_ac2_whitespace_is_literal():
    store = TaskStore()
    a = store.add("x y")
    store.add("xy")
    assert store.search(" ") == [a]
    assert store.search(" x ") == []

@pytest.mark.parametrize("query", [None, 1, True, [], {}])
def test_ac3_invalid_queries(query):
    store = TaskStore()
    before = store.add("one")
    with pytest.raises(ValueError):
        store.search(query)
    assert store.list_tasks() == [before]
    assert store.add("two").id == 2

def test_ac4_order_duplicates_completed_live_objects():
    store = TaskStore()
    a = store.add("match", "low")
    store.add("other")
    b = store.add("match", "high")
    store.complete(a.id)
    first = store.search("match")
    second = store.search("match")
    assert first == [a, b]
    assert first[0] is a and first[1] is b
    assert first is not second
    first.clear()
    assert store.search("match") == [a, b]

def test_ac5_no_mutation():
    store = TaskStore()
    tasks = store.add_many([{"title": "B"}, {"title": "A", "priority": "low"}])
    snapshot = [t.to_dict() for t in tasks]
    store.search("a")
    assert [t.to_dict() for t in store.list_tasks()] == snapshot
    assert store.add("C").id == 3
