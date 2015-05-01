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


def test_add_timespan(db, monkeypatch):
    now = 99999
    monkeypatch.setattr(time, 'time', lambda: now)
    edit = db.add_timespan()
    assert edit.started == now
    assert edit.edited.time == now
    assert edit.edited.loc == db.location_id
    assert edit.timespan_id is not None
    assert edit.edited.ctr is not None


def test_delete_timespan(db, monkeypatch):
    now = 99999
    monkeypatch.setattr(time, 'time', lambda: now)
    edit0 = db.add_timespan()
    edit1 = db.delete_timespan(edit0.timespan_id)
    assert edit1.started is None
    assert edit1.edited.time == now
    assert edit1.edited.loc == db.location_id
    assert edit1.timespan_id == edit0.timespan_id
    assert edit1.edited != edit0.edited


def test_add_delete_timespan_history(db, monkeypatch):
    t0 = 1001
    monkeypatch.setattr(time, 'time', lambda: t0)
    creation = db.add_timespan()
    t1 = 1005
    monkeypatch.setattr(time, 'time', lambda: t1)
    deletion = db.delete_timespan(creation.timespan_id)
    history = db.get_timespan_history(creation.timespan_id)
    assert list(history) == [creation, deletion]


def test_get_timespan_history_unknown(db):
    timespan_id = db.add_timespan().timespan_id
    assert list(db.get_timespan_history(timespan_id + 3)) == []


def test_get_timespan(db):
    edit = db.add_timespan()
    assert db.get_timespan(edit.timespan_id) == edit


def test_get_timespan_deleted(db, monkeypatch):
    t0 = 1001
    monkeypatch.setattr(time, 'time', lambda: t0)
    edit = db.add_timespan()
    t1 = 1002
    monkeypatch.setattr(time, 'time', lambda: t1)
    deletion = db.delete_timespan(edit.timespan_id)
    assert db.get_timespan(edit.timespan_id) == deletion


def test_get_timespan_unknown(db):
    timespan_id = db.add_timespan().timespan_id
    assert db.get_timespan(timespan_id + 3) is None


def test_set_timespan(db, monkeypatch):
    t0 = 1001
    monkeypatch.setattr(time, 'time', lambda: t0)
    creation = db.add_timespan()
    t1 = 1002
    monkeypatch.setattr(time, 'time', lambda: t1)
    started = 3333
    edit = db.set_timespan(creation.timespan_id, started)
    assert edit.started == started
    assert edit.timespan_id == creation.timespan_id
    assert edit != creation
    assert db.get_timespan(edit.timespan_id) == edit
    assert list(db.get_timespan_history(edit.timespan_id)) == [creation, edit]


def test_get_timespans(db):
    s1 = db.set_timespan(1, 5)
    s2 = db.set_timespan(2, 10)
    s3 = db.set_timespan(3, 7)
    assert list(db.get_timespans(4, 15)) == [s1, s3, s2]
    assert list(db.get_timespans(9, 11)) == [s2]
    assert list(db.get_timespans(0, 8)) == [s1, s3]


def test_get_timespans_deleted(db, monkeypatch):
    t0 = 1001
    monkeypatch.setattr(time, 'time', lambda: t0)
    s1 = db.set_timespan(1, 5)
    s2 = db.set_timespan(2, 10)
    s3 = db.set_timespan(3, 7)
    t1 = 1002
    monkeypatch.setattr(time, 'time', lambda: t1)
    db.delete_timespan(s3.timespan_id)
    assert list(db.get_timespans(4, 15)) == [s1, s2]
    assert list(db.get_timespans(9, 11)) == [s2]
    assert list(db.get_timespans(0, 8)) == [s1]


def test_get_timespans_edited(db, monkeypatch):
    t0 = 1001
    monkeypatch.setattr(time, 'time', lambda: t0)
    s1 = db.set_timespan(1, 5)
    s2 = db.set_timespan(2, 10)
    s3 = db.set_timespan(3, 7)
    t1 = 1002
    monkeypatch.setattr(time, 'time', lambda: t1)
    s2 = db.set_timespan(s2.timespan_id, 3)
    assert list(db.get_timespans(4, 15)) == [s1, s3]
    assert list(db.get_timespans(9, 11)) == []
    assert list(db.get_timespans(0, 8)) == [s2, s1, s3]


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


def test_get_last_timespan(db):
    assert db.get_last_timespan() is None
    s1 = db.set_timespan(1, 10)
    assert db.get_last_timespan() == s1
    s2 = db.set_timespan(2, 50)
    assert db.get_last_timespan() == s2
    s3 = db.set_timespan(3, 25)
    assert db.get_last_timespan() == s2


def test_get_last_timespan_edited(db):
    assert db.get_last_timespan() is None
    s1 = db.set_timespan(1, 10)
    assert db.get_last_timespan() == s1
    s2 = db.set_timespan(2, 50)
    assert db.get_last_timespan() == s2
    s1 = db.set_timespan(s1.timespan_id, 100)
    assert db.get_last_timespan() == s1


def test_get_last_timespan_deleted(db):
    assert db.get_last_timespan() is None
    s1 = db.set_timespan(1, 10)
    assert db.get_last_timespan() == s1
    s2 = db.set_timespan(2, 50)
    assert db.get_last_timespan() == s2
    db.delete_timespan(s2.timespan_id)
    assert db.get_last_timespan() == s1
