import time
import tkinter as tk

import pytest


@pytest.fixture
def db():
    from alho.db import Database, create_tables
    import sqlite3
    conn = sqlite3.connect(':memory:')
    create_tables(conn)
    return Database(conn, 12345)


class FakeTime:

    def __init__(self, start, inc=0):
        self.value = start
        self.inc = inc

    def __call__(self):
        result = self.value
        self.value += self.inc
        return result


@pytest.fixture
def fake_time(monkeypatch):
    fake = FakeTime(8765.309)
    monkeypatch.setattr(time, 'time', fake)
    return fake


@pytest.fixture(params=[0, 1.23])
def fake_times(request, monkeypatch):
    fake = FakeTime(1234.56, inc=request.param)
    monkeypatch.setattr(time, 'time', fake)
    return fake


@pytest.fixture(scope='session')
def tk_main_win():
    return tk.Tk()