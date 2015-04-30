import time

import pytest


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
    assert edit.log_time == now
    assert edit.location_id == db.location_id
    assert edit.timespan_id is not None
    assert edit.log_id is not None


def test_delete_timespan(db, monkeypatch):
    now = 99999
    monkeypatch.setattr(time, 'time', lambda: now)
    edit0 = db.add_timespan()
    edit1 = db.delete_timespan(edit0.timespan_id)
    assert edit1.started is None
    assert edit1.log_time == now
    assert edit1.location_id == db.location_id
    assert edit1.timespan_id == edit0.timespan_id
    assert edit1.log_id is not None
    assert edit1.log_id != edit0.log_id


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


def test_timespan_edit_equality():
    from alho.db import TimespanEdit
    edit = TimespanEdit(1, 2, 3, 4, 5)
    assert edit == TimespanEdit(1, 2, 3, 4, 5)
    assert edit != TimespanEdit(10, 2, 3, 4, 5)
    assert edit != TimespanEdit(1, 5, 3, 4, 5)
    assert edit != TimespanEdit(1, 2, 33, 4, 5)
    assert edit != TimespanEdit(1, 2, 3, 8, 5)
    assert edit != TimespanEdit(1, 2, 3, 4, 500)


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