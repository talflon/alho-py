import pytest
import tkinter as tk
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
def mock_db():
    db = Mock()
    db.location = 11111
    return db


@pytest.fixture
def span_list(mock_db):
    from alho.gui import SpanListWidget
    win = tk.Tk()
    span_list = SpanListWidget(win, mock_db)
    span_list.widget.pack()
    return span_list


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
    def entry(self):
        from alho.gui import SavableEntry
        win = tk.Tk()
        entry = SavableEntry(win)
        entry.widget.pack()
        return entry

    @pytest.mark.parametrize('value', ['', 'Q', 'oh say, can you seeeeee'])
    def test_initial_value(self, value):
        from alho.gui import SavableEntry
        win = tk.Tk()
        entry = SavableEntry(win, value)
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


class TestSpanListWidget:

    def test_switch_no_tags(self, span_list):
        db = span_list.db
        from alho.db import SpanEdit, TimeStamp
        t = 10000
        span_edit = SpanEdit(TimeStamp(t, span_list.db.location, 0), 123, t)
        db.add_span.return_value = span_edit
        db.get_tags.return_value = []
        span_list.switch_button.invoke()

        db.add_span.assert_called_once_with()
        span_widget = span_list.spans[-1]
        assert_widget_shown(span_widget.widget)
        assert_widget_shown(span_widget.tag_entry)
        assert span_widget.tag_entry.get() == ''
        assert_widget_shown(span_widget.start_entry)

    def test_switch_with_tags(self, span_list):
        db = span_list.db
        from alho.db import SpanEdit, TimeStamp
        from alho.gui import tag_set_to_str
        tags = {'blah', 'bleh', 'blue'}
        t = 10000
        span_id = 456
        span_edit = SpanEdit(TimeStamp(t, span_list.db.location, 0), span_id, t)
        db.add_span.return_value = span_edit
        db.get_tags.return_value = tags.copy()
        span_list.switch_tags.delete(0, tk.END)
        span_list.switch_tags.insert(0, tag_set_to_str(tags))
        span_list.switch_button.invoke()

        span_widget = span_list.spans[-1]
        assert (set(c[0] for c in db.add_tag.call_args_list) ==
                {(span_id, n) for n in tags})
        assert span_widget.tag_entry.get() == tag_set_to_str(tags)
        assert span_list.switch_tags.get() == ''
