import pytest
from tasklib import TaskStore

@pytest.mark.parametrize('entry', [None,{}, {'id':True,'title':'X'}, {'id':1,'title':' '}, {'id':1,'title':'X','extra':0}])
def test_ac1_invalid_entry_atomic(entry):
    store = TaskStore()
    store.add('A'); store.add('B')
    before = store._snapshot()
    with pytest.raises(ValueError):
        store.rename_many([{'id':2,'title':'Changed'},entry])
    assert store._snapshot() == before

@pytest.mark.parametrize('bad',[None,{},'text',()])
def test_ac1_requires_list(bad):
    with pytest.raises(ValueError):
        TaskStore().rename_many(bad)

def test_ac1_duplicate_ids():
    store = TaskStore(); store.add('A')
    with pytest.raises(ValueError):
        store.rename_many([{'id':1,'title':'X'},{'id':1,'title':'Y'}])
    assert store.get(1).title == 'A'

def test_ac1_unknown_id_atomic():
    store = TaskStore(); store.add('A')
    with pytest.raises(KeyError):
        store.rename_many([{'id':1,'title':'X'},{'id':99,'title':'Y'}])
    assert store.get(1).title == 'A' and store.add('Next').id == 2

def test_ac2_valid_batch():
    store = TaskStore()
    a,b = store.add('A','high'),store.add('B','low')
    store.complete(a.id)
    updates = [{'id':2,'title':' Café '},{'id':1,'title':' New '}]
    result = store.rename_many(updates)
    assert result[0] is b and result[1] is a
    assert [t.title for t in store.list_tasks()] == ['New','Café']
    assert a.completed and a.priority == 'high' and b.priority == 'low'
    assert updates[0]['title'] == ' Café ' and store.add('Next').id == 3

def test_ac2_empty():
    store = TaskStore()
    assert store.rename_many([]) == [] and store.add('Next').id == 1
