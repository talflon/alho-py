import time

import pytest

from alho.db import TimeStamp


@pytest.fixture
def db():
    from alho.db import Database, create_tables
    import sqlite3
    conn = sqlite3.connect(':memory:')
    create_tables(conn)
    return Database(conn, 12345)


def test_add_span(db, monkeypatch):
    now = 99999
    monkeypatch.setattr(time, 'time', lambda: now)
    edit = db.add_span()
    assert edit.started == now
    assert edit.edited.time == now
    assert edit.edited.loc == db.location_id
    assert edit.span_id is not None
    assert edit.edited.ctr is not None


def test_delete_span(db, monkeypatch):
    now = 99999
    monkeypatch.setattr(time, 'time', lambda: now)
    edit0 = db.add_span()
    edit1 = db.delete_span(edit0.span_id)
    assert edit1.started is None
    assert edit1.edited.time == now
    assert edit1.edited.loc == db.location_id
    assert edit1.span_id == edit0.span_id
    assert edit1.edited != edit0.edited


def test_add_delete_span_history(db, monkeypatch):
    t0 = 1001
    monkeypatch.setattr(time, 'time', lambda: t0)
    creation = db.add_span()
    t1 = 1005
    monkeypatch.setattr(time, 'time', lambda: t1)
    deletion = db.delete_span(creation.span_id)
    history = db.get_span_history(creation.span_id)
    assert list(history) == [creation, deletion]


def test_get_span_history_unknown(db):
    span_id = db.add_span().span_id
    assert list(db.get_span_history(span_id + 3)) == []


def test_get_span(db):
    edit = db.add_span()
    assert db.get_span(edit.span_id) == edit


def test_get_span_deleted(db, monkeypatch):
    t0 = 1001
    monkeypatch.setattr(time, 'time', lambda: t0)
    edit = db.add_span()
    t1 = 1002
    monkeypatch.setattr(time, 'time', lambda: t1)
    deletion = db.delete_span(edit.span_id)
    assert db.get_span(edit.span_id) == deletion


def test_get_span_unknown(db):
    span_id = db.add_span().span_id
    assert db.get_span(span_id + 3) is None


def test_set_span(db, monkeypatch):
    t0 = 1001
    monkeypatch.setattr(time, 'time', lambda: t0)
    creation = db.add_span()
    t1 = 1002
    monkeypatch.setattr(time, 'time', lambda: t1)
    started = 3333
    edit = db.set_span(creation.span_id, started)
    assert edit.started == started
    assert edit.span_id == creation.span_id
    assert edit != creation
    assert db.get_span(edit.span_id) == edit
    assert list(db.get_span_history(edit.span_id)) == [creation, edit]


def test_get_spans(db):
    s1 = db.set_span(1, 5)
    s2 = db.set_span(2, 10)
    s3 = db.set_span(3, 7)
    assert list(db.get_spans(4, 15)) == [s1, s3, s2]
    assert list(db.get_spans(9, 11)) == [s2]
    assert list(db.get_spans(0, 8)) == [s1, s3]


def test_get_spans_deleted(db, monkeypatch):
    t0 = 1001
    monkeypatch.setattr(time, 'time', lambda: t0)
    s1 = db.set_span(1, 5)
    s2 = db.set_span(2, 10)
    s3 = db.set_span(3, 7)
    t1 = 1002
    monkeypatch.setattr(time, 'time', lambda: t1)
    db.delete_span(s3.span_id)
    assert list(db.get_spans(4, 15)) == [s1, s2]
    assert list(db.get_spans(9, 11)) == [s2]
    assert list(db.get_spans(0, 8)) == [s1]


def test_get_spans_edited(db, monkeypatch):
    t0 = 1001
    monkeypatch.setattr(time, 'time', lambda: t0)
    s1 = db.set_span(1, 5)
    s2 = db.set_span(2, 10)
    s3 = db.set_span(3, 7)
    t1 = 1002
    monkeypatch.setattr(time, 'time', lambda: t1)
    s2 = db.set_span(s2.span_id, 3)
    assert list(db.get_spans(4, 15)) == [s1, s3]
    assert list(db.get_spans(9, 11)) == []
    assert list(db.get_spans(0, 8)) == [s2, s1, s3]


@pytest.mark.parametrize('stamp', [
    TimeStamp(12345, 22222, 0),
    TimeStamp(12345, 22222, 1),
    TimeStamp(12345, 22222, 32800),
    TimeStamp(12345, 22222, 65535),
])
def test_timestamp_next(stamp):
    assert stamp.next > stamp
    assert stamp.next.loc == stamp.loc


@pytest.mark.parametrize('stamp', [
    TimeStamp(12345, 22222, 0),
    TimeStamp(12345, 22222, 1),
    TimeStamp(12345, 22222, 32800),
    TimeStamp(12345, 22222, 65500),
    TimeStamp(12345, -12345, 0),
    TimeStamp(12345, -12345, 1),
    TimeStamp(12345, -12345, 32800),
    TimeStamp(12345, -12345, 65500),
])
def test_timestamp_int(stamp):
    assert TimeStamp.from_int(stamp.as_int) == stamp


def test_get_last_span(db):
    assert db.get_last_span() is None
    s1 = db.set_span(1, 10)
    assert db.get_last_span() == s1
    s2 = db.set_span(2, 50)
    assert db.get_last_span() == s2
    s3 = db.set_span(3, 25)
    assert db.get_last_span() == s2


def test_get_last_span_edited(db):
    assert db.get_last_span() is None
    s1 = db.set_span(1, 10)
    assert db.get_last_span() == s1
    s2 = db.set_span(2, 50)
    assert db.get_last_span() == s2
    s1 = db.set_span(s1.span_id, 100)
    assert db.get_last_span() == s1


def test_get_last_span_deleted(db):
    assert db.get_last_span() is None
    s1 = db.set_span(1, 10)
    assert db.get_last_span() == s1
    s2 = db.set_span(2, 50)
    assert db.get_last_span() == s2
    db.delete_span(s2.span_id)
    assert db.get_last_span() == s1


def test_add_tag(db):
    span = db.add_span()
    assert set(db.get_tags(span.span_id)) == set()
    db.add_tag(span.span_id, 'x')
    assert set(db.get_tags(span.span_id)) == {'x'}
    db.add_tag(span.span_id, 'y')
    assert set(db.get_tags(span.span_id)) == {'x', 'y'}


def test_remove_tag(db):
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
