import time
from unittest.mock import patch

import hypothesis
import hypothesis.strategies as hs
import hypothesis.stateful
from hypothesis import given

from alho.db import TimeStamp


def create_db(location):
    import sqlite3
    from alho.db import Database, create_tables
    conn = sqlite3.connect(':memory:')
    create_tables(conn)
    return Database(conn, location)


class DbStateMachine(hypothesis.stateful.GenericStateMachine):

    TAG_NAMES = ['x', 'yz', 'abc', 'blah']

    def __init__(self):
        self.span_ids = set()
        self.db = create_db(12345)
        self.now = 123456789.12394

    def step_strategy(self, action, *args_strategies):
        return hs.tuples(hs.just(action),
                         hs.tuples(*args_strategies),
                         hs.just(0.0) | hs.floats(0.0, 60.0))

    def steps(self):
        strat = self.step_strategy('add_span')
        if self.span_ids:
            strat |= self.step_strategy('delete_span',
                                        hs.sampled_from(self.span_ids))
            strat |= self.step_strategy('set_span',
                                        hs.sampled_from(self.span_ids),
                                        hs.integers(-10, 100))
            strat |= self.step_strategy('set_tag',
                                        hs.sampled_from(self.span_ids),
                                        hs.sampled_from(self.TAG_NAMES),
                                        hs.booleans())
        return strat

    def execute_step(self, step):
        action, args, time_step = step
        self.now += time_step
        with patch.object(time, 'time', lambda: self.now):
            getattr(self, 'do_' + action)(*args)

    def do_add_span(self):
        span_edit = self.db.add_span()
        assert span_edit.span_id not in self.span_ids
        assert span_edit.started == int(self.now)
        self.span_ids.add(span_edit.span_id)
        self.check_current_span_edit(span_edit)

    def do_set_span(self, span_id, started):
        span_edit = self.db.set_span(span_id, started)
        assert span_edit.span_id == span_id
        assert span_edit.started == started
        self.span_ids.add(span_id)
        self.check_current_span_edit(span_edit)

    def do_delete_span(self, span_id):
        span_edit = self.db.delete_span(span_id)
        assert span_edit.span_id == span_id
        assert span_edit.started is None
        self.span_ids.discard(span_id)
        self.check_current_span_edit(span_edit)

    def check_current_edit(self, edit):
        assert edit.edited.time == int(self.now)
        assert edit.edited.loc == self.db.location_id

    def check_history_result(self, history_result, edit):
        history_result = list(history_result)
        assert history_result[-1] == edit
        assert history_result == sorted(history_result,
                                        key=lambda ed: ed.edited.time)
        edited_timestamps = [ed.edited for ed in history_result]
        assert sorted(edited_timestamps) == sorted(set(edited_timestamps))
        for ed in history_result:
            assert ed.span_id == edit.span_id

    def check_current_span_edit(self, span_edit):
        self.check_current_edit(span_edit)
        assert self.db.get_span(span_edit.span_id) == span_edit

        get_spans_result = list(self.db.get_spans())
        if span_edit.started is not None:
            assert span_edit in get_spans_result
        assert get_spans_result == sorted(get_spans_result,
                                          key=lambda edit: edit.started)
        span_ids = [edit.span_id for edit in get_spans_result]
        if span_edit.started is None:
            assert span_edit.span_id not in span_ids
        assert sorted(span_ids) == sorted(set(span_ids))
        edited_timestamps = [edit.edited for edit in get_spans_result]
        assert sorted(edited_timestamps) == sorted(set(edited_timestamps))

        self.check_history_result(self.db.get_span_history(span_edit.span_id),
                                  span_edit)

    def do_set_tag(self, span_id, tag, active):
        expected_tags = set(self.db.get_tags(span_id))
        if active:
            expected_tags.add(tag)
        else:
            expected_tags.discard(tag)
        tag_edit = self.db.set_tag(span_id, tag, active)
        assert tag_edit.span_id == span_id
        assert tag_edit.name == tag
        assert tag_edit.active == active
        self.check_current_edit(tag_edit)

        assert set(self.db.get_tags(span_id)) == expected_tags

        self.check_history_result(self.db.get_tag_history(span_id), tag_edit)


def test_db_ops():
    hypothesis.stateful.run_state_machine_as_test(DbStateMachine)


def test_add_delete_span_history(db, fake_times):
    creation = db.add_span()
    deletion = db.delete_span(creation.span_id)
    history = db.get_span_history(creation.span_id)
    assert list(history) == [creation, deletion]


def test_get_span_history_unknown(db, fake_time):
    span_id = db.add_span().span_id
    assert list(db.get_span_history(span_id + 3)) == []


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


def and_especially(rest, *especially):
    return hs.sampled_from(especially) | rest


def ints_in_range(low, high):
    especially = {low, high} | {i for i in (0, -1, 1, low + 1, high - 1)
                                if low <= i <= high}
    return hs.one_of(*(hs.just(i) for i in especially)) | hs.integers(low, high)


def ints_bits_signed(nbits):
    return ints_in_range(-2**(nbits-1), 2**(nbits-1)-1)


def ints_bits_unsigned(nbits):
    return ints_in_range(0, 2**nbits-1)


def timestamps():
    return hs.builds(TimeStamp,
                     time=ints_bits_signed(32),
                     loc=ints_bits_signed(16),
                     ctr=ints_bits_unsigned(16))


with hypothesis.Settings(max_examples=500):
    @given(timestamps())
    def test_timestamp_next_greater(stamp):
        assert stamp.next > stamp

    @given(timestamps())
    def test_timestamp_next_same_loc(stamp):
        assert stamp.next.loc == stamp.loc

    @given(timestamps())
    def test_timestamp_int(stamp):
        assert TimeStamp.from_int(stamp.as_int) == stamp

    @given(timestamps())
    def test_timestamp_int_64_bit_signed(stamp):
        assert -2 ** 63 <= stamp.as_int < 2 ** 63


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
