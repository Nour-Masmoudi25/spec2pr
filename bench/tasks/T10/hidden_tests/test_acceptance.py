import pytest
from tasklib import TaskStore

@pytest.mark.parametrize('offset,limit,expected',[(0,2,[1,2]),(1,2,[2,3]),(3,5,[4]),(8,2,[]),(0,0,[])])
def test_ac1_slice(offset,limit,expected):
    store = TaskStore()
    tasks = [store.add(str(i)) for i in range(4)]
    store.complete(2)
    result = store.paginate(offset,limit)
    assert [t.id for t in result] == expected
    assert all(t is tasks[t.id-1] for t in result)

def test_ac1_defaults_and_fresh_list():
    store = TaskStore()
    for i in range(12): store.add(str(i))
    result = store.paginate()
    assert len(result) == 10 and result is not store.paginate()
    result.clear()
    assert len(store.list_tasks()) == 12

def test_ac1_empty():
    assert TaskStore().paginate() == []

@pytest.mark.parametrize('field',['offset','limit'])
@pytest.mark.parametrize('value',[-1,True,1.0,'1',None])
def test_ac2_invalid_atomic(field,value):
    store = TaskStore(); store.add('A')
    before = store._snapshot()
    with pytest.raises(ValueError):
        store.paginate(**{field:value})
    assert store._snapshot() == before and store.add('Next').id == 2

def test_ac2_valid_no_mutation():
    store = TaskStore(); store.add('A','high')
    before = store._snapshot()
    store.paginate()
    assert store._snapshot() == before and store.add('Next').id == 2
