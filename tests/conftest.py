import time

import pytest


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
