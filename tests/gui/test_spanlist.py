import time
import tkinter as tk
from datetime import date, timedelta

import pytest
from unittest import mock
from unittest.mock import Mock, call


def assert_widget_shown(widget):
    try:
        pack_info = widget.info()
    except tk.TclError:
        pack_info = None
    try:
        grid_info = widget.grid_info()
    except tk.TclError:
        grid_info = None
    assert pack_info or grid_info or widget.place_info()


@pytest.fixture
def mock_db(fake_time):
    fake_time.inc = 1.38
    db = Mock()
    db.location = 11111
    db.get_spans.return_value = []
    return db


def create_span_list(db, win):
    from alho.gui import SpanListWidget
    span_list = SpanListWidget(win, db)
    span_list.widget.pack()
    return span_list


def create_span_edit(loc, span_id, t):
    from alho.db import SpanEdit, TimeStamp
    return SpanEdit(TimeStamp(t, loc, 0), span_id, t)


def create_span_list_with_spans(mock_db, win, num_spans):
    span_list = create_span_list(mock_db, win)
    db = span_list.db
    for span_id in range(1, num_spans + 1):
        span_edit = create_span_edit(db.location, span_id, 10000 + span_id)
        db.add_span.return_value = span_edit
        db.get_span.return_value = span_edit
        db.get_tags.return_value = {}
        span_list.add_span()
    return span_list


@pytest.fixture
def span_list_empty(mock_db, tk_main_win):
    return create_span_list(mock_db, tk_main_win)


@pytest.fixture
def span_list_with_spans(mock_db, tk_main_win):
    return create_span_list_with_spans(mock_db, tk_main_win, 5)


@pytest.fixture(params=[0, 1, 5])
def span_list(mock_db, request, tk_main_win):
    return create_span_list_with_spans(mock_db, tk_main_win, request.param)


class TestTagSetMethods:

    def test_tag_set_to_str(self):
        from alho.gui import tag_set_to_str
        assert tag_set_to_str([]) == ''
        assert tag_set_to_str(['def', 'abc', 'hij']) == 'abc, def, hij'
        assert tag_set_to_str({'a1', 'a2', 'b3', 'b1'}) == 'a1, a2, b1, b3'
        assert tag_set_to_str(iter(['xyz'])) == 'xyz'

    def test_tag_str_to_set_normal(self):
        from alho.gui import tag_str_to_set
        assert tag_str_to_set('') == set()
        assert tag_str_to_set('ab, cb, q') == {'ab', 'cb', 'q'}
        assert tag_str_to_set('blah') == {'blah'}

    def test_tag_str_to_set_different_spaces(self):
        from alho.gui import tag_str_to_set
        assert tag_str_to_set('  \n ') == set()
        assert tag_str_to_set(' , , \t, ') == set()
        assert tag_str_to_set('ab cb    q') == {'ab', 'cb', 'q'}
        assert tag_str_to_set('\nblah  ,') == {'blah'}
        assert tag_str_to_set('a,,,b,,,,,e,d c') == {'a', 'b', 'c', 'd', 'e'}
        assert tag_str_to_set('one; two;three') == {'one', 'two', 'three'}

    def test_tag_str_to_set_upper(self):
        from alho.gui import tag_str_to_set
        assert tag_str_to_set('Ab, cB, QWERTY') == {'ab', 'cb', 'qwerty'}
        assert tag_str_to_set('BLah') == {'blah'}

    @pytest.mark.parametrize('tag_str', ['[stuff]', 'if 1+2=3 then'])
    def test_tag_str_to_set_invalid(self, tag_str):
        from alho.gui import tag_str_to_set
        with pytest.raises(ValueError):
            tag_str_to_set(tag_str)


class TestSpanListWidget:

    def test_switch_no_tags(self, span_list):
        db = span_list.db
        span_edit = create_span_edit(db.location, 123, 10000)
        db.add_span.return_value = span_edit
        db.get_span.return_value = span_edit
        db.get_tags.return_value = []

        old_call_count = db.add_span.call_count
        span_list.switch_button.invoke()
        assert db.add_span.call_count == old_call_count + 1
        db.get_tags.assert_called_with(span_edit.span_id)

        span_widget = span_list.spans[-1]
        assert_widget_shown(span_widget.widget)
        assert_widget_shown(span_widget.tag_entry.widget)
        assert_widget_shown(span_widget.start_entry.widget)

    def test_switch_with_tags(self, span_list):
        db = span_list.db
        from alho.gui import tag_set_to_str
        tags = {'blah', 'bleh', 'blue'}
        span_edit = create_span_edit(db.location, 456, 10000)
        db.add_span.return_value = span_edit
        db.get_span.return_value = span_edit
        db.get_tags.return_value = tags.copy()
        assert span_list.switch_tags.editable
        span_list.switch_tags.edited_value = tag_set_to_str(tags)
        span_list.switch_button.invoke()

        assert (set(c[0] for c in db.add_tag.call_args_list) ==
                {(span_edit.span_id, n) for n in tags})
        db.get_tags.assert_called_with(span_edit.span_id)
        assert span_list.switch_tags.edited_value == ''

    def test_switch_editing_status(self, span_list):
        db = span_list.db
        span_edit = create_span_edit(db.location, 1, 10000)
        db.add_span.return_value = span_edit
        db.get_span.return_value = span_edit
        db.get_tags.return_value = {}
        span_list.editing = False
        span_list.switch_button.invoke()
        span = span_list.spans[-1]
        assert not span.start_entry.editable
        assert not span.tag_entry.editable
        span_list.editing = True
        span_list.switch_button.invoke()
        assert span != span_list.spans[-1]
        span = span_list.spans[-1]
        assert span.start_entry.editable
        assert span.tag_entry.editable

    def test_switch_button_enabled_valid_tags(self, span_list):
        assert 'disabled' not in span_list.switch_button.state()
        span_list.switch_tags.edited_value = 'a,b, c'
        assert 'disabled' not in span_list.switch_button.state()

    def test_switch_button_disabled_invalid_tags(self, span_list):
        span_list.switch_tags.edited_value = '~~~|:-)|~~~'
        assert 'disabled' in span_list.switch_button.state()

    def test_edit_button(self, span_list_with_spans):
        span_list = span_list_with_spans
        span_list.editing = False
        assert 'disabled' not in span_list.edit_button.state()
        span_list.edit_button.invoke()
        for span in span_list.spans:
            assert span.start_entry.editable
            assert span.tag_entry.editable
        assert 'disabled' in span_list.edit_button.state()

    def test_revert_button(self, span_list_with_spans):
        span_list = span_list_with_spans
        span_list.editing = True
        assert 'disabled' not in span_list.revert_button.state()
        for span in span_list.spans:
            span.start_entry.revert = Mock()
            span.tag_entry.revert = Mock()
        span_list.revert_button.invoke()
        for span in span_list.spans:
            span.start_entry.revert.assert_called_once_with()
            span.tag_entry.revert.assert_called_once_with()
        assert not span_list.editing

    def test_save_button_all_valid(self, span_list_with_spans):
        span_list = span_list_with_spans
        span_list.editing = True
        assert 'disabled' not in span_list.save_button.state()
        for span in span_list.spans:
            span.start_entry.save = Mock()
            span.tag_entry.save = Mock()
        span_list.save_button.invoke()
        for span in span_list.spans:
            span.start_entry.save.assert_called_once_with()
            span.tag_entry.save.assert_called_once_with()
        assert not span_list.editing

    def test_editing_button_states(self, span_list):
        if span_list.spans:
            span_list.editing = True
            assert 'disabled' in span_list.edit_button.state()
            assert 'disabled' not in span_list.revert_button.state()
            assert 'disabled' not in span_list.save_button.state()
            assert not span_list.date_chooser.editable
            span_list.editing = False
            assert 'disabled' not in span_list.edit_button.state()
            assert 'disabled' in span_list.revert_button.state()
            assert 'disabled' in span_list.save_button.state()
            assert span_list.date_chooser.editable
        else:
            assert 'disabled' in span_list.edit_button.state()
            assert 'disabled' in span_list.revert_button.state()
            assert 'disabled' in span_list.save_button.state()

    def refresh_and_assert_spans_match(self, span_list, span_edits):
        from alho.gui import SpanWidget
        old_spans = {span.span_id: span for span in span_list.spans}
        span_list.db.get_spans.return_value = span_edits
        mock_refresh = Mock()
        with mock.patch.object(SpanWidget, 'refresh',
                               lambda sw: mock_refresh(sw)):
            span_list.refresh()
        assert ([span.span_id for span in span_list.spans] ==
                [edit.span_id for edit in span_edits])
        for span, span_widget in zip(span_list.spans,
                                     span_list.span_box.pack_slaves()):
            assert span.widget is span_widget
            assert call(span) in mock_refresh.call_args_list
            if span.span_id in old_spans:
                assert span is old_spans[span.span_id]
                del old_spans[span.span_id]
        for span in old_spans.values():  # unused old spans must be destroyed
            assert not span.widget.winfo_exists()

    @pytest.mark.parametrize('before,after', [
        ("[(1, '12:34:56')]",
         "[]"),
        ("[]",
         "[(5, '00:00:00'), (3, '00:00:03')]"),
        ("[(7, '08:08:08'), (1, '08:09:10')]",
         "[(5, '00:00:00'), (3, '00:00:03')]"),
        ("[(2, '11:11:11')]",
         "[(2, '11:10:11'), (5, '12:00:00')]"),
        ("[(2, '11:11:11')]",
         "[(2, '11:10:11'), (5, '10:00:00')]"),
        ("[(4, '15:01:30'), (7, '15:03:22')]",
         "[(7, '15:04:22')]"),
        ("[(4, '15:01:30'), (7, '15:03:22')]",
         "[(4, '15:01:31')]"),
        ("[(1, '09:05:30'), (2, '09:10:00')]",
         "[(2, '10:10:00'), (3, '08:05:15')]"),
    ])
    def test_refresh_spans(self, span_list_empty, before, after):
        span_list = span_list_empty
        db = span_list.db

        def time_int(s):
            return int(time.mktime(time.strptime('2013-05-19 ' + s, TIME_FMT)))

        before = [create_span_edit(db.loc, i, time_int(t))
                  for i, t in eval(before)]
        after = [create_span_edit(db.loc, i, time_int(t))
                 for i, t in eval(after)]
        for span_edit_list in before, after:
            span_edit_list.sort(key=lambda edit: edit.started)
        self.refresh_and_assert_spans_match(span_list, before)
        self.refresh_and_assert_spans_match(span_list, after)

    def test_refresh_calling_get_spans(self, span_list_empty, fake_time):
        span_list = span_list_empty
        db = span_list.db
        day = date(2020, 3, 1)
        day_start = time.mktime(day.timetuple())
        day_end = time.mktime((day + timedelta(days=1)).timetuple())
        span_list.date_chooser.day = day
        span_list.refresh()
        db.get_spans.assert_called_with(day_start, day_end)


TIME_FMT = '%Y-%m-%d %H:%M:%S'


class TestSpanWidget:

    @pytest.fixture(autouse=True)
    def main_win(self, tk_main_win):
        self.win = tk_main_win

    def create_span_widget(self, db, span_id=1):
        from alho.gui import SpanWidget
        span_widget = SpanWidget(self.win, db, span_id)
        span_widget.widget.pack()
        return span_widget

    def create_span_widget_for_values(self, mock_db, span_id=1, t=123456789,
                                      tags=set()):
        mock_db.get_span.return_value = create_span_edit(mock_db.location,
                                                         span_id, t)
        mock_db.get_tags.return_value = tags.copy()
        return self.create_span_widget(mock_db, span_id)

    def test_initial_tag_value(self, mock_db):
        from alho.gui import tag_set_to_str
        tags = {'asdf', 'ghjkl'}
        span_widget = self.create_span_widget_for_values(mock_db, tags=tags)
        assert (span_widget.tag_entry.external_value ==
                tag_set_to_str(tags) ==
                span_widget.tag_entry.entry.get())

    @pytest.mark.parametrize('time_str', [
        '2015-05-13 12:34:56',
        '1984-12-25 00:15:00',
        '2001-03-18 18:03:10',
        '2025-09-01 05:28:04',
    ])
    def test_initial_start_value(self, mock_db, time_str):
        t = int(time.mktime(time.strptime(time_str, TIME_FMT)))
        span_id = 9999
        span_widget = self.create_span_widget_for_values(mock_db,
                                                         span_id=span_id, t=t)
        assert (span_widget.start_entry.external_value ==
                time_str ==
                span_widget.start_entry.entry.get())
        mock_db.get_span.assert_called_with(span_id)

    @pytest.mark.parametrize('old_tags_str,new_tags_str', [
        ('a, b, c', ''),
        ('', 'x, y'),
        ('d, e, f', 'a, b, c, d'),
        ('q, w', 'q, w, e, r, t, y'),
        ('1, 2, 3', '2'),
    ])
    def test_save_tags(self, mock_db, old_tags_str, new_tags_str):
        from alho.gui import tag_str_to_set
        span_id = 300
        old_tags = tag_str_to_set(old_tags_str)
        span_widget = self.create_span_widget_for_values(
            mock_db, span_id=span_id, tags=old_tags)
        new_tags = tag_str_to_set(new_tags_str)
        span_widget.tag_entry.edited_value = new_tags_str
        span_widget.tag_entry.save()
        assert (set(c[0] for c in mock_db.add_tag.call_args_list) ==
                {(span_id, n) for n in new_tags - old_tags})
        assert (set(c[0] for c in mock_db.remove_tag.call_args_list) ==
                {(span_id, n) for n in old_tags - new_tags})

    @pytest.mark.parametrize('time_str', [
        '2015-05-13 12:34:56',
        '1984-12-25 00:15:00',
        '2001-03-18 18:03:10',
        '2025-09-01 05:28:04',
    ])
    def test_save_start(self, mock_db, time_str):
        old_t = 112233
        new_t = int(time.mktime(time.strptime(time_str, TIME_FMT)))
        span_id = 2
        span_widget = self.create_span_widget_for_values(
            mock_db, span_id=span_id, t=old_t)
        span_widget.start_entry.edited_value = time_str
        span_widget.start_entry.save()
        mock_db.set_span.assert_called_with(span_id, new_t)

    def test_refresh(self, mock_db):
        from alho.gui import tag_set_to_str
        old_t = 77777777
        old_tags = {'one', 'two'}
        new_t = 88888888
        new_tags = {'three', '4'}
        span_id = 5
        span_widget = self.create_span_widget_for_values(mock_db,
                                                         span_id=span_id,
                                                         t=old_t,
                                                         tags=old_tags)
        mock_db.get_span.return_value = create_span_edit(mock_db.location,
                                                         span_id, new_t)
        mock_db.get_tags.return_value = new_tags.copy()
        span_widget.refresh()
        assert (span_widget.start_entry.external_value ==
                time.strftime(TIME_FMT, time.localtime(new_t)) ==
                span_widget.start_entry.entry.get())
        assert (span_widget.tag_entry.external_value ==
                tag_set_to_str(new_tags) ==
                span_widget.tag_entry.entry.get())
        mock_db.get_span.assert_called_with(span_id)
        mock_db.get_tags.assert_called_with(span_id)
