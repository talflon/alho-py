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
