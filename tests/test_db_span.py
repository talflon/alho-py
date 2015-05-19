import itertools

import pytest


def test_add_span(db, fake_time):
    now = int(fake_time.value)
    edit = db.add_span()
    assert edit.started == now
    assert edit.edited.time == now
    assert edit.edited.loc == db.location_id
    assert edit.span_id is not None
    assert edit.edited.ctr is not None


def test_delete_span(db, fake_times):
    edit0 = db.add_span()
    now = int(fake_times.value)
    edit1 = db.delete_span(edit0.span_id)
    assert edit1.started is None
    assert edit1.edited.time == now
    assert edit1.edited.loc == db.location_id
    assert edit1.span_id == edit0.span_id
    assert edit1.edited != edit0.edited


def test_add_delete_span_history(db, fake_times):
    creation = db.add_span()
    deletion = db.delete_span(creation.span_id)
    history = db.get_span_history(creation.span_id)
    assert list(history) == [creation, deletion]


def test_get_span_history_unknown(db, fake_time):
    span_id = db.add_span().span_id
    assert list(db.get_span_history(span_id + 3)) == []


def test_get_span(db, fake_time):
    edit = db.add_span()
    assert db.get_span(edit.span_id) == edit


def test_get_span_deleted(db, fake_times):
    edit = db.add_span()
    deletion = db.delete_span(edit.span_id)
    assert db.get_span(edit.span_id) == deletion


def test_get_span_unknown(db, fake_time):
    span_id = db.add_span().span_id
    assert db.get_span(span_id + 3) is None


def test_set_span(db, fake_times):
    creation = db.add_span()
    started = 3333
    edit = db.set_span(creation.span_id, started)
    assert edit.started == started
    assert edit.span_id == creation.span_id
    assert edit != creation
    assert db.get_span(edit.span_id) == edit
    assert list(db.get_span_history(edit.span_id)) == [creation, edit]


def test_get_spans(db, fake_times):
    s1 = db.set_span(1, 5)
    s2 = db.set_span(2, 10)
    s3 = db.set_span(3, 7)
    assert list(db.get_spans(4, 15)) == [s1, s3, s2]
    assert list(db.get_spans(9, 11)) == [s2]
    assert list(db.get_spans(0, 8)) == [s1, s3]


def test_get_spans_deleted(db, fake_times):
    s1 = db.set_span(1, 5)
    s2 = db.set_span(2, 10)
    s3 = db.set_span(3, 7)
    db.delete_span(s3.span_id)
    assert list(db.get_spans(4, 15)) == [s1, s2]
    assert list(db.get_spans(9, 11)) == [s2]
    assert list(db.get_spans(0, 8)) == [s1]


def test_get_spans_edited(db, fake_times):
    s1 = db.set_span(1, 5)
    s2 = db.set_span(2, 10)
    s3 = db.set_span(3, 7)
    s2 = db.set_span(s2.span_id, 3)
    assert list(db.get_spans(4, 15)) == [s1, s3]
    assert list(db.get_spans(9, 11)) == []
    assert list(db.get_spans(0, 8)) == [s2, s1, s3]


@pytest.mark.parametrize(
    'params', itertools.product([12345, 2**31-2],
                                [22222, 0, -1, 32767, -32768],
                                [0, 1, 32800, 65535]))
def test_timestamp_next(params):
    from alho.db import TimeStamp
    stamp = TimeStamp(*params)
    assert stamp.next > stamp
    assert stamp.next.loc == stamp.loc


@pytest.mark.parametrize(
    'params', itertools.product([12345, 2**31-2],
                                [22222, 0, -1, 32767, -32768],
                                [0, 1, 32800, 65535]))
def test_timestamp_int(params):
    from alho.db import TimeStamp
    stamp = TimeStamp(*params)
    assert TimeStamp.from_int(stamp.as_int) == stamp


def test_get_last_span(db, fake_times):
    assert db.get_last_span() is None
    s1 = db.set_span(1, 10)
    assert db.get_last_span() == s1
    s2 = db.set_span(2, 50)
    assert db.get_last_span() == s2
    s3 = db.set_span(3, 25)
    assert db.get_last_span() == s2


def test_get_last_span_edited(db, fake_times):
    assert db.get_last_span() is None
    s1 = db.set_span(1, 10)
    assert db.get_last_span() == s1
    s2 = db.set_span(2, 50)
    assert db.get_last_span() == s2
    s1 = db.set_span(s1.span_id, 100)
    assert db.get_last_span() == s1


def test_get_last_span_deleted(db, fake_times):
    assert db.get_last_span() is None
    s1 = db.set_span(1, 10)
    assert db.get_last_span() == s1
    s2 = db.set_span(2, 50)
    assert db.get_last_span() == s2
    db.delete_span(s2.span_id)
    assert db.get_last_span() == s1


def test_get_tag_after_add(db, fake_times):
    span = db.add_span()
    assert set(db.get_tags(span.span_id)) == set()
    db.add_tag(span.span_id, 'x')
    assert set(db.get_tags(span.span_id)) == {'x'}
    db.add_tag(span.span_id, 'y')
    assert set(db.get_tags(span.span_id)) == {'x', 'y'}


def test_get_tag_after_remove(db, fake_times):
    span = db.add_span()
    db.add_tag(span.span_id, 'a')
    db.add_tag(span.span_id, 'b')
    db.add_tag(span.span_id, 'c')
    db.remove_tag(span.span_id, 'b')
    assert set(db.get_tags(span.span_id)) == {'a', 'c'}
    db.remove_tag(span.span_id, 'a')
    assert set(db.get_tags(span.span_id)) == {'c'}
    db.remove_tag(span.span_id, 'c')
    assert set(db.get_tags(span.span_id)) == set()


def test_add_tag(db, fake_times):
    span = db.add_span()
    edit = db.add_tag(span.span_id, 'a')
    assert edit.span_id == span.span_id
    assert edit.name == 'a'
    assert edit.active


def test_remove_tag(db, fake_times):
    span = db.add_span()
    db.add_tag(span.span_id, 'a')
    edit = db.remove_tag(span.span_id, 'a')
    assert edit.span_id == span.span_id
    assert edit.name == 'a'
    assert not edit.active


def test_tag_history(db, fake_times):
    span = db.add_span()
    assert list(db.get_tag_history(span.span_id)) == []
    edit0 = db.add_tag(span.span_id, 'x')
    assert list(db.get_tag_history(span.span_id)) == [edit0]
    edit1 = db.add_tag(span.span_id, 'y')
    assert list(db.get_tag_history(span.span_id)) == [edit0, edit1]
    edit2 = db.remove_tag(span.span_id, 'x')
    assert list(db.get_tag_history(span.span_id)) == [edit0, edit1, edit2]


def test_get_next_span(db, fake_times):
    db.set_span(3, 100)
    db.set_span(4, 101)
    assert db.get_next_span(3).span_id == 4
    assert db.get_next_span(4) is None
    db.set_span(3, 102)
    assert db.get_next_span(4).span_id == 3
    assert db.get_next_span(3) is None
    db.set_span(4, 102)
    assert db.get_next_span(3).span_id == 4
    assert db.get_next_span(4) is None
