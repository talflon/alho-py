# Alho personal time-tracking system
# Copyright (C) 2015  Daniel Getz
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import re
import time
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


class SavableEntry:

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


class TagEntry(SavableEntry):

    def __init__(self, span):
        tags = span.db.get_tags(span.span_id)
        super().__init__(span.widget, tag_set_to_str(tags))
        self.span = span

    def normalize(self, value):
        return tag_set_to_str(tag_str_to_set(value))

    def save(self):
        old_tags = tag_str_to_set(self.external_value)
        new_tags = tag_str_to_set(self.edited_value)
        for tag in old_tags - new_tags:
            self.span.db.remove_tag(self.span.span_id, tag)
        for tag in new_tags - old_tags:
            self.span.db.add_tag(self.span.span_id, tag)
        super().save()


class SpanWidget:

    def __init__(self, master, db, span_id):
        self.widget = Frame(master)
        self.db = db
        self.span_id = span_id

        start_time = time.strftime(
            '%Y-%m-%d %H:%M:%S',
            time.localtime(db.get_span(span_id).edited.time))
        self.start_entry = SavableEntry(self.widget, start_time)
        self.start_entry.widget.pack(side=tk.LEFT)

        self.tag_entry = TagEntry(self)
        self.tag_entry.widget.pack(side=tk.LEFT, fill=tk.X)


class SpanListWidget:

    def __init__(self, master, db):
        self.widget = Frame(master)
        self.db = db
        self.spans = []

        self.edit_box = Frame(self.widget)
        self.edit_button = Button(self.edit_box, text='edit',
                                  command=self.on_edit_button)
        self.edit_button.pack(side=tk.LEFT)
        self.save_button = Button(self.edit_box, text='save',
                                  command=self.on_save_button)
        self.save_button.pack(side=tk.LEFT)
        self.revert_button = Button(self.edit_box, text='revert',
                                    command=self.on_revert_button)
        self.revert_button.pack(side=tk.LEFT)
        self.edit_box.pack()

        self.editing = False

        self.span_box = Frame(self.widget)
        self.span_box.pack()

        self.switch_box = Frame(self.widget)
        self.switch_button = Button(self.switch_box, text='switch',
                                    command=self.on_switch_button)
        self.switch_button.pack(side=tk.LEFT)
        self.switch_tags = SavableEntry(self.switch_box)
        self.switch_tags.save = self.on_switch_button
        self.switch_tags.widget.pack(side=tk.LEFT)
        self.switch_box.pack()

    @property
    def editing(self):
        return self._editing

    @editing.setter
    def editing(self, value):
        value = bool(value)
        self._editing = value
        change_state(self.edit_button, disabled=value or not self.spans)
        change_state(self.save_button, disabled=not value)
        change_state(self.revert_button, disabled=not value)
        for entry in self.all_span_entries():
            entry.editable = value

    def on_switch_button(self, *args):
        self.add_span(tag_str_to_set(self.switch_tags.edited_value))
        self.switch_tags.revert()

    def on_edit_button(self, *args):
        self.editing = True

    def all_span_entries(self):
        for span in self.spans[:]:
            yield span.start_entry
            yield span.tag_entry

    def on_save_button(self, *args):
        something_invalid = False
        for entry in self.all_span_entries():
            if entry.proposed_valid:
                entry.save()
            else:
                something_invalid = True
        self.editing = something_invalid

    def on_revert_button(self, *args):
        for entry in self.all_span_entries():
            entry.revert()
        self.editing = False

    def add_span(self, tags=()):
        span_id = self.db.add_span().span_id
        for tag_name in tags:
            self.db.add_tag(span_id, tag_name)
        span = SpanWidget(self.span_box, self.db, span_id)
        self.spans.append(span)
        span.widget.pack()
        change_state(self.edit_button, disabled=self.editing)
        span.start_entry.editable = span.tag_entry.editable = self.editing
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
