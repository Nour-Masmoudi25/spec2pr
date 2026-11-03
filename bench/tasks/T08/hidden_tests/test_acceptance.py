import json
import pytest
import tasklib
from tasklib import Task, TaskStore
from tasklib import storage

def test_ac1_public_roundtrip():
    assert tasklib.dumps_store is storage.dumps_store
    assert tasklib.loads_store is storage.loads_store
    original = TaskStore._restore([Task(7,'Café','high',True),Task(2,'B')],12)
    text = tasklib.dumps_store(original)
    assert isinstance(text,str) and 'Café' in text
    assert json.loads(text) == original._snapshot()
    copied = tasklib.loads_store(text)
    assert copied._snapshot() == original._snapshot()
    assert copied.get(7) is not original.get(7)
    copied.update(7,title='Changed')
    assert original.get(7).title == 'Café'
    assert copied.add('Next').id == 12

def test_ac1_empty():
    copied = tasklib.loads_store(tasklib.dumps_store(TaskStore()))
    assert copied.list_tasks() == [] and copied.add('First').id == 1

@pytest.mark.parametrize('text',[None,b'{}','{','null','[]','{}',
    '{"version":1,"version":1,"next_id":1,"tasks":[]}',
    '{"version":1,"next_id":NaN,"tasks":[]}',
    '{"version":2,"next_id":1,"tasks":[]}',
    '{"version":1,"next_id":1,"tasks":[],"extra":0}'])
def test_ac2_invalid_document(text):
    with pytest.raises(ValueError):
        tasklib.loads_store(text)

@pytest.mark.parametrize('kind',['duplicate','counter','taskfield'])
def test_ac2_invalid_records(kind):
    task = Task(1,'A').to_dict()
    doc = {'version':1,'next_id':2,'tasks':[task]}
    if kind == 'duplicate': doc['tasks'].append(dict(task))
    if kind == 'counter': doc['next_id'] = 1
    if kind == 'taskfield': task['extra'] = 0
    with pytest.raises(ValueError):
        tasklib.loads_store(json.dumps(doc))

def test_ac3_no_io(monkeypatch):
    import builtins
    import pathlib
    def forbidden(*args,**kwargs):
        raise AssertionError('Filesystem accessed')
    monkeypatch.setattr(builtins,'open',forbidden)
    monkeypatch.setattr(pathlib.Path,'open',forbidden)
    result = tasklib.loads_store(tasklib.dumps_store(TaskStore()))
    assert result.list_tasks() == []

@pytest.mark.parametrize('kind',['wrong_type','invalid_task'])
def test_ac3_invalid_dump(kind):
    store = TaskStore()
    store.add('A').title = ' '
    with pytest.raises(ValueError):
        tasklib.dumps_store(None if kind == 'wrong_type' else store)
