import pytest
from tasklib import Task, TaskStore

def test_ac1_independent_copy():
    original = Task(7, 'Café', 'high', True)
    copied = original.copy()
    assert copied == original and copied is not original
    copied.title = 'Changed'
    assert original.title == 'Café'

def test_ac2_clone_values_order_counter():
    original = TaskStore._restore([Task(8,'First','high',True), Task(2,'Second')], 12)
    copied = original.clone()
    assert copied is not original
    assert [t.to_dict() for t in copied.list_tasks()] == [t.to_dict() for t in original.list_tasks()]
    assert all(a is not b for a,b in zip(copied.list_tasks(),original.list_tasks()))
    copied.update(8,title='New')
    original.complete(2)
    assert original.get(8).title == 'First' and not copied.get(2).completed
    assert copied.add('Copy').id == original.add('Original').id == 12

def test_ac2_empty_clone():
    original = TaskStore()
    copied = original.clone()
    assert copied.list_tasks() == [] and copied.add('New').id == 1
    assert original.list_tasks() == []

@pytest.mark.parametrize('field,value', [('title',' '),('id',True),('priority','HIGH'),('completed',1)])
def test_ac3_invalid_copy(field,value):
    task = Task(1,'A')
    setattr(task,field,value)
    with pytest.raises(ValueError):
        task.copy()
    assert getattr(task,field) == value

@pytest.mark.parametrize('field,value', [('title',' '),('id',9),('priority','HIGH'),('completed',1)])
def test_ac3_invalid_clone(field,value):
    store = TaskStore()
    task = store.add('A')
    setattr(task,field,value)
    with pytest.raises(ValueError):
        store.clone()
    assert getattr(task,field) == value and store.add('B').id == 2
