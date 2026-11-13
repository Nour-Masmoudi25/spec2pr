import pytest
from tasklib import Task, TaskStore

@pytest.mark.parametrize('priority,rank',[('low',0),('medium',1),('high',2)])
def test_ac1_rank(priority,rank):
    value = Task(1,'A',priority).priority_rank()
    assert type(value) is int and value == rank

@pytest.mark.parametrize('bad',['HIGH',None,[],True])
def test_ac1_invalid_rank(bad):
    task = Task(1,'A')
    task.priority = bad
    with pytest.raises(ValueError):
        task.priority_rank()

def test_ac2_stable_order_and_completed():
    store = TaskStore()
    tasks = [store.add(str(i),p) for i,p in enumerate(['medium','high','low','high','medium'])]
    store.complete(tasks[3].id)
    assert store.list_by_priority() == [tasks[i] for i in [1,3,0,4,2]]

def test_ac2_empty():
    assert TaskStore().list_by_priority() == []

def test_ac3_identity_and_no_mutation():
    store = TaskStore()
    low, high = store.add('Low','low'), store.add('High','high')
    before = store._snapshot()
    result = store.list_by_priority()
    assert result[0] is high and result[1] is low
    assert result is not store.list_by_priority()
    result.clear()
    assert store._snapshot() == before and store.add('Next').id == 3
