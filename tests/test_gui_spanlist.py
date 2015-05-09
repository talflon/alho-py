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


def test_tag_set_to_str():
    from alho.gui import tag_set_to_str
    assert tag_set_to_str([]) == ''
    assert tag_set_to_str(['def', 'abc', 'hij']) == 'abc, def, hij'
    assert tag_set_to_str({'a1', 'a2', 'b3', 'b1'}) == 'a1, a2, b1, b3'
    assert tag_set_to_str(iter(['xyz'])) == 'xyz'


def test_tag_str_to_set_normal():
    from alho.gui import tag_str_to_set
    assert tag_str_to_set('') == set()
    assert tag_str_to_set('ab, cb, q') == {'ab', 'cb', 'q'}
    assert tag_str_to_set('blah') == {'blah'}


def test_tag_str_to_set_different_spaces():
    from alho.gui import tag_str_to_set
    assert tag_str_to_set('  \n ') == set()
    assert tag_str_to_set(' , , \t, ') == set()
    assert tag_str_to_set('ab cb    q') == {'ab', 'cb', 'q'}
    assert tag_str_to_set('\nblah  ,') == {'blah'}
    assert tag_str_to_set('a,,,b,,,,,e,d c') == {'a', 'b', 'c', 'd', 'e'}
    assert tag_str_to_set('one; two;three') == {'one', 'two', 'three'}


def test_tag_str_to_set_upper():
    from alho.gui import tag_str_to_set
    assert tag_str_to_set('Ab, cB, QWERTY') == {'ab', 'cb', 'qwerty'}
    assert tag_str_to_set('BLah') == {'blah'}


@pytest.mark.parametrize('tag_str', ['[stuff]', 'if 1+2=3 then'])
def test_tag_str_to_set_invalid(tag_str):
    from alho.gui import tag_str_to_set
    with pytest.raises(ValueError):
        tag_str_to_set(tag_str)


def test_switch_no_tags(span_list):
    from alho.db import SpanEdit, TimeStamp
    t = 10000
    span_edit = SpanEdit(TimeStamp(t, span_list.db.location, 0), 123, t)
    span_list.db.add_span.return_value = span_edit
    span_list.switch_button.invoke()
    span_list.db.add_span.assert_called_once_with()
    span_widget = span_list.spans[-1]
    assert_widget_shown(span_widget.widget)
    assert_widget_shown(span_widget.tag_entry)
    assert span_widget.tag_entry.get() == ''
    assert_widget_shown(span_widget.start_entry)
