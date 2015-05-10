import re
import tkinter as tk
from tkinter.ttk import Button, Entry, Frame


TAG_STR_SPLIT_REGEX = re.compile(r'[\s;,]+')
TAG_NAME_REGEX = re.compile(r'^[-\w.&?!]+$')


def tag_str_to_set(tag_str):
    tag_set = set()
    for name in TAG_STR_SPLIT_REGEX.split(tag_str.lower()):
        if name:
            if TAG_NAME_REGEX.match(name):
                tag_set.add(name)
            else:
                raise ValueError('Invalid tag name: %r' % name)
    return tag_set


def tag_set_to_str(tag_set):
    return ', '.join(sorted(tag_set))


def state_change(**flags):
    """Return an appropriate argument to `tkinter.ttk.Widget.state()`.

    Keyword arguments' names are the flags to be sent, and values are treated
    as booleans: `True` turns on the given flag, and `False` turns it off.

    >>> sorted(state_change(hover=False, invalid=True))
    ['!hover', 'invalid']
    """
    return [flag if value else '!' + flag
            for flag, value in flags.items()]


def change_state(widget, **flags):
    """Changes the given state flags of the given `tkinter.ttk.Widget`.

    Keyword arguments' names are the flags to be sent, and values are treated
    as booleans: `True` turns on the given flag, and `False` turns it off.
    """
    widget.state(state_change(**flags))


class EditableField:

    def __init__(self, master, value='', editable=False):
        self.edited_var = tk.StringVar(master)
        self.edited_var.set(value)
        self.widget = self.entry = Entry(master, textvariable=self.edited_var)
        self._external_value = value
        self.editable = editable
        self.edited_var.trace('w', self.on_edited_change)

    @property
    def editable(self):
        return self._editable

    @editable.setter
    def editable(self, value):
        self._editable = bool(value)
        change_state(self.entry, readonly=not self._editable)

    @property
    def external_value(self):
        return self._external_value

    @external_value.setter
    def external_value(self, value):
        old_value = self._external_value
        self._external_value = value
        if self.proposed_value == old_value:
            self.edited_value = value
        else:
            self.on_edited_change()

    @property
    def edited_value(self):
        return self.edited_var.get()

    @edited_value.setter
    def edited_value(self, value):
        self.edited_var.set(value)

    def normalize(self, value):
        return value

    @property
    def proposed_value(self):
        try:
            return self.normalize(self.edited_value)
        except ValueError:
            return self.edited_value

    @property
    def proposed_valid(self):
        try:
            self.normalize(self.edited_value)
            return True
        except ValueError:
            return False

    def save(self):
        self.external_value = self.edited_value = self.proposed_value

    def revert(self):
        self.edited_value = self.external_value

    def on_edited_change(self, *args):
        change_state(self.entry,
                     alternate=self.proposed_value != self.external_value,
                     invalid=not self.proposed_valid)


class SpanWidget:

    def __init__(self, master, db, span_id):
        self.widget = Frame(master)
        self.db = db
        self.span_id = span_id

        self.tags = set(db.get_tags(span_id))

        self.start_entry = Entry(self.widget)
        self.start_entry.pack(side=tk.LEFT)

        self.tag_entry = Entry(self.widget)
        self.tag_entry.pack(side=tk.LEFT, fill=tk.X)
        self.tag_entry.insert(0, tag_set_to_str(self.tags))


class SpanListWidget:

    def __init__(self, master, db):
        self.widget = Frame(master)
        self.db = db
        self.spans = []

        self.span_box = Frame(self.widget)
        self.span_box.pack()

        self.switch_box = Frame(self.widget)
        self.switch_button = Button(self.switch_box, text='switch',
                                    command=self.on_switch_button)
        self.switch_button.pack(side=tk.LEFT)
        self.switch_tags = Entry(self.switch_box)
        self.switch_tags.save = self.on_switch_button
        self.switch_tags.pack(side=tk.LEFT)
        self.switch_box.pack()

    def on_switch_button(self, *args):
        self.add_span(tag_str_to_set(self.switch_tags.get()))
        self.switch_tags.delete(0, tk.END)

    def add_span(self, tags=()):
        span_id = self.db.add_span().span_id
        for tag_name in tags:
            self.db.add_tag(span_id, tag_name)
        span = SpanWidget(self.span_box, self.db, span_id)
        self.spans.append(span)
        span.widget.pack()
        return span


if __name__ == '__main__':
    from .db import Database, create_tables
    import sqlite3
    import random
    conn = sqlite3.connect(':memory:')
    create_tables(conn)
    win = tk.Tk()
    SpanListWidget(win, Database(conn, random.getrandbits(31))).widget.pack()
    win.mainloop()
