import pytest
import tkinter as tk
from mock import Mock


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


class TestEditableField:

    @pytest.fixture
    def field(self):
        from alho.gui import EditableField
        win = tk.Tk()
        field = EditableField(win)
        field.widget.pack()
        return field

    @pytest.mark.parametrize('value', ['', 'Q', 'oh say, can you seeeeee'])
    def test_initial_value(self, value):
        from alho.gui import EditableField
        win = tk.Tk()
        field = EditableField(win, value)
        field.widget.pack()
        assert field.external_value == value
        assert field.edited_value == value
        assert field.entry.get() == value

    def test_revert_blank(self, field):
        field.editable = True
        field.entry.insert(0, 'hey guys')
        field.revert()
        assert field.entry.get() == ''
        assert field.edited_value == ''

    def test_edit_value(self, field):
        field.editable = True
        value = 'blah blah blah'
        field.entry.insert(0, value)
        assert field.edited_value == value
        assert 'alternate' in field.entry.state()

    def test_editable(self, field):
        field.editable = False
        assert 'readonly' in field.entry.state()
        old_value = field.entry.get()
        field.entry.insert(0, '?')
        assert field.entry.get() == old_value
        field.editable = True
        assert 'readonly' not in field.entry.state()
        field.entry.insert(0, '!')
        assert field.entry.get() == '!' + old_value

    def test_set_edited_value(self, field):
        field.editable = True
        new_value = 'Something Something'
        field.edited_value = new_value
        assert field.edited_value == new_value
        assert field.entry.get() == new_value
        assert 'alternate' in field.entry.state()

    def test_revert_to_external(self, field):
        field.editable = True
        edit_value = '123456'
        new_value = 'oi tud dret'
        field.edited_value = edit_value
        field.external_value = new_value
        field.revert()
        assert field.edited_value == field.external_value == new_value
        assert 'alternate' not in field.entry.state()

    def test_save_to_external(self, field):
        field.editable = True
        edit_value = 'success!'
        field.edited_value = edit_value
        field.save()
        assert field.edited_value == field.external_value == edit_value
        assert 'alternate' not in field.entry.state()

    def test_save_with_external_changed(self, field):
        field.editable = True
        edit_value = '123456'
        ext_value = 'oi tud dret'
        field.edited_value = edit_value
        field.external_value = ext_value
        field.save()
        assert field.edited_value == field.external_value == edit_value
        assert 'alternate' not in field.entry.state()

    @pytest.mark.parametrize('editable', [True, False])
    def test_set_external_value_after_change(self, field, editable):
        field.editable = True
        edit_value = 'different'
        ext_value = 'yet another'
        field.edited_value = edit_value
        field.editable = editable
        field.external_value = ext_value
        assert field.edited_value == edit_value == field.entry.get()
        assert field.external_value == ext_value
        assert 'alternate' in field.entry.state()

    @pytest.mark.parametrize('editable', [True, False])
    def test_set_external_value_when_unchanged(self, field, editable):
        field.editable = editable
        new_value = 'Test'
        field.external_value = new_value
        assert field.edited_value == new_value == field.entry.get()
        assert 'alternate' not in field.entry.state()
        new_value2 = 'omg'
        field.external_value = new_value2
        assert field.edited_value == new_value2 == field.entry.get()
        assert 'alternate' not in field.entry.state()
        field.external_value = ''
        assert field.edited_value == '' == field.entry.get()
        assert 'alternate' not in field.entry.state()

    def test_save_normalize(self, field):
        field.normalize = Mock()
        field.normalize.return_value = 'normal'
        field.editable = True
        field.edited_value = 'abnormal'
        field.save()
        assert field.external_value == 'normal'
        assert field.edited_value == 'normal'
        field.normalize.assert_called_with('abnormal')

    def test_proposed_value(self, field):
        field.normalize = Mock()
        field.normalize.return_value = 'normal'
        field.editable = True
        field.edited_value = 'abnormal'
        assert field.edited_value == 'abnormal'
        assert field.proposed_value == 'normal'
        field.normalize.assert_called_with('abnormal')


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
