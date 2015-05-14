import time
import tkinter as tk
from datetime import date, timedelta

import pytest
from mock import Mock, call


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


class TestSavableEntry:

    @pytest.fixture
    def entry(self, tk_main_win):
        from alho.gui import SavableEntry
        entry = SavableEntry(tk_main_win)
        entry.widget.pack()
        return entry

    @pytest.mark.parametrize('value', ['', 'Q', 'oh say, can you seeeeee'])
    def test_initial_value(self, value, tk_main_win):
        from alho.gui import SavableEntry
        entry = SavableEntry(tk_main_win, value)
        entry.widget.pack()
        assert entry.external_value == value
        assert entry.edited_value == value
        assert entry.entry.get() == value

    def test_revert_blank(self, entry):
        entry.editable = True
        entry.entry.insert(0, 'hey guys')
        entry.revert()
        assert entry.entry.get() == ''
        assert entry.edited_value == ''

    def test_edit_value(self, entry):
        entry.editable = True
        value = 'blah blah blah'
        entry.entry.insert(0, value)
        assert entry.edited_value == value
        assert 'alternate' in entry.entry.state()

    def test_editable(self, entry):
        entry.editable = False
        assert 'readonly' in entry.entry.state()
        old_value = entry.entry.get()
        entry.entry.insert(0, '?')
        assert entry.entry.get() == old_value
        entry.editable = True
        assert 'readonly' not in entry.entry.state()
        entry.entry.insert(0, '!')
        assert entry.entry.get() == '!' + old_value

    def test_set_edited_value(self, entry):
        entry.editable = True
        new_value = 'Something Something'
        entry.edited_value = new_value
        assert entry.edited_value == new_value
        assert entry.entry.get() == new_value
        assert 'alternate' in entry.entry.state()

    def test_revert_to_external(self, entry):
        entry.editable = True
        edit_value = '123456'
        new_value = 'oi tud dret'
        entry.edited_value = edit_value
        entry.external_value = new_value
        entry.revert()
        assert entry.edited_value == entry.external_value == new_value
        assert 'alternate' not in entry.entry.state()

    def test_save_to_external(self, entry):
        entry.editable = True
        edit_value = 'success!'
        entry.edited_value = edit_value
        entry.save()
        assert entry.edited_value == entry.external_value == edit_value
        assert 'alternate' not in entry.entry.state()

    def test_save_with_external_changed(self, entry):
        entry.editable = True
        edit_value = '123456'
        ext_value = 'oi tud dret'
        entry.edited_value = edit_value
        entry.external_value = ext_value
        entry.save()
        assert entry.edited_value == entry.external_value == edit_value
        assert 'alternate' not in entry.entry.state()

    @pytest.mark.parametrize('editable', [True, False])
    def test_set_external_value_after_change(self, entry, editable):
        entry.editable = True
        edit_value = 'different'
        ext_value = 'yet another'
        entry.edited_value = edit_value
        entry.editable = editable
        entry.external_value = ext_value
        assert entry.edited_value == edit_value == entry.entry.get()
        assert entry.external_value == ext_value
        assert 'alternate' in entry.entry.state()

    @pytest.mark.parametrize('editable', [True, False])
    def test_set_external_value_when_unchanged(self, entry, editable):
        entry.editable = editable
        new_value = 'Test'
        entry.external_value = new_value
        assert entry.edited_value == new_value == entry.entry.get()
        assert 'alternate' not in entry.entry.state()
        new_value2 = 'omg'
        entry.external_value = new_value2
        assert entry.edited_value == new_value2 == entry.entry.get()
        assert 'alternate' not in entry.entry.state()
        entry.external_value = ''
        assert entry.edited_value == '' == entry.entry.get()
        assert 'alternate' not in entry.entry.state()

    def test_save_normalize(self, entry):
        entry.normalize = Mock()
        entry.normalize.return_value = 'normal'
        entry.editable = True
        entry.edited_value = 'abnormal'
        entry.save()
        assert entry.external_value == 'normal'
        assert entry.edited_value == 'normal'
        assert call('abnormal') in entry.normalize.call_args_list

    def test_proposed_value(self, entry):
        entry.normalize = Mock()
        entry.normalize.return_value = 'normal'
        entry.editable = True
        entry.edited_value = 'abnormal'
        assert entry.edited_value == 'abnormal'
        assert entry.proposed_value == 'normal'
        assert call('abnormal') in entry.normalize.call_args_list

    def test_alternate_state_normalized_same(self, entry):
        entry.normalize = Mock()
        entry.normalize.return_value = 'normal'
        entry.external_value = 'normal'
        entry.editable = True
        entry.edited_value = 'abnormal'
        assert 'alternate' not in entry.entry.state()
        assert call('abnormal') in entry.normalize.call_args_list

    def test_alternate_state_normalized_different(self, entry):
        entry.normalize = Mock()
        entry.normalize.return_value = 'normal'
        entry.external_value = 'different'
        entry.editable = True
        entry.edited_value = 'abnormal'
        assert 'alternate' in entry.entry.state()
        assert call('abnormal') in entry.normalize.call_args_list

    @pytest.mark.parametrize('editable', [True, False])
    def test_set_external_value_when_normalized_unchanged(self,entry,editable):
        entry.normalize = lambda s: s.split('|')[0]
        entry.editable = editable
        entry.external_value = 'one'
        entry.edited_value = 'one|two'
        entry.external_value = 'three'
        assert entry.edited_value == 'three'

    def test_proposed_value_invalid(self, entry):
        entry.normalize = lambda s: exec('raise ValueError')
        new_value = 'hi'
        entry.edited_value = new_value
        assert entry.proposed_value == entry.edited_value

    def test_proposed_valid(self, entry):
        entry.edited_value = 'blah'
        assert entry.proposed_valid
        assert 'invalid' not in entry.entry.state()
        entry.normalize = lambda s: exec('raise ValueError')
        entry.edited_value = 'bleh'
        assert not entry.proposed_valid
        assert 'invalid' in entry.entry.state()


class TestDateChooser:

    DATES = [
        '1999-12-31',
        '2000-02-28',
        '2008-02-29',
        '1944-06-06',
        '2027-04-01',
        '2015-01-01',
    ]

    @pytest.fixture(autouse=True)
    def main_win(self, tk_main_win):
        self.win = tk_main_win

    def create_chooser(self, *args, **kwargs):
        from alho.gui import DateChooser
        return DateChooser(self.win, *args, **kwargs)

    def mkday(self, day):
        return date(*(int(n) for n in day.split('-')))

    def assert_day(self, chooser, day):
        assert chooser.day == day
        assert chooser.entry.get() == day.strftime('%Y-%m-%d')

    @pytest.mark.parametrize('day', DATES)
    def test_init_day(self, day):
        day = self.mkday(day)
        chooser = self.create_chooser(day=day)
        self.assert_day(chooser, day)

    @pytest.mark.parametrize('day', DATES)
    def test_init_day_default(self, day, fake_time):
        day = self.mkday(day)
        fake_time.value = time.mktime(day.timetuple())
        chooser = self.create_chooser()
        self.assert_day(chooser, day)

    @pytest.mark.parametrize('day', DATES)
    def test_set_day(self, day, fake_time):
        day = self.mkday(day)
        chooser = self.create_chooser()
        chooser.day = day
        self.assert_day(chooser, day)

    @pytest.mark.parametrize('day', DATES)
    def test_set_day_via_entry(self, day, fake_time):
        day = self.mkday(day)
        chooser = self.create_chooser()
        chooser.entry.delete(0, tk.END)
        chooser.entry.insert(0, day.strftime('%Y-%m-%d'))
        self.assert_day(chooser, day)

    @pytest.mark.parametrize('day', DATES)
    def test_inc_button(self, day):
        day = self.mkday(day)
        chooser = self.create_chooser(day=day)
        day += timedelta(days=1)
        chooser.inc_button.invoke()
        self.assert_day(chooser, day)

    @pytest.mark.parametrize('day', DATES)
    def test_dec_button(self, day):
        day = self.mkday(day)
        chooser = self.create_chooser(day=day)
        day -= timedelta(days=1)
        chooser.dec_button.invoke()
        self.assert_day(chooser, day)

    @pytest.mark.parametrize('day', DATES)
    def test_today_button(self, day, fake_time):
        day = self.mkday(day)
        chooser = self.create_chooser(day=date(2000, 1, 1))
        fake_time.value = time.mktime(day.timetuple())
        chooser.today_button.invoke()
        self.assert_day(chooser, day)

    def test_editable(self):
        chooser = self.create_chooser()
        widgets = [chooser.entry, chooser.inc_button, chooser.dec_button,
                   chooser.today_button]
        chooser.editable = True
        assert chooser.editable
        for widget in widgets:
            assert 'disabled' not in widget.state()
        chooser.editable = False
        assert not chooser.editable
        for widget in widgets:
            assert 'disabled' in widget.state()


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
            span_list.editing = False
            assert 'disabled' not in span_list.edit_button.state()
            assert 'disabled' in span_list.revert_button.state()
            assert 'disabled' in span_list.save_button.state()
        else:
            assert 'disabled' in span_list.edit_button.state()
            assert 'disabled' in span_list.revert_button.state()
            assert 'disabled' in span_list.save_button.state()


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

    def test_initial_tag_value(self, mock_db, monkeypatch):
        import alho.gui
        monkeypatch.setattr(alho.gui, 'tag_set_to_str', Mock())
        alho.gui.tag_set_to_str.return_value = '~* Success! *~'
        tags = {'asdf', 'ghjkl'}
        span_widget = self.create_span_widget_for_values(mock_db, tags=tags)
        assert (span_widget.tag_entry.external_value ==
                alho.gui.tag_set_to_str.return_value ==
                span_widget.tag_entry.entry.get())
        alho.gui.tag_set_to_str.assert_called_with(tags)

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
