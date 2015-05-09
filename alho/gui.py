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


class SpanWidget:

    def __init__(self, master, db, span_id):
        self.widget = Frame(master)
        self.db = db
        self.span_id = span_id

        self.tags = {}

        self.start_entry = Entry(self.widget)
        self.start_entry.pack(side=tk.LEFT)

        self.tag_entry = Entry(self.widget)
        self.tag_entry.pack(side=tk.LEFT, fill=tk.X)


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
        self.add_span()

    def add_span(self):
        span = SpanWidget(self.span_box, self.db, self.db.add_span().span_id)
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
