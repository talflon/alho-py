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


import time
import tkinter as tk
from datetime import date, timedelta
from tkinter.ttk import Button, Entry, Frame


DATE_FMT = '%Y-%m-%d'


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


class DateChooserEntry(SavableEntry):

    def __init__(self, chooser):
        super().__init__(chooser.widget)
        self.chooser = chooser
        self.entry.bind('<FocusOut>', self.on_focusout)
        self.entry.bind('<Key-Return>', self.on_key_return)
        self.entry.bind('<Key-Escape>', self.on_key_escape)

    def on_focusout(self, *args):
        if self.proposed_valid:
            self.save()

    def on_key_return(self, *args):
        if self.proposed_valid:
            self.save()

    def on_key_escape(self, *args):
        self.revert()

    def normalize(self, value):
        return date(*time.strptime(value, DATE_FMT)[:3]).strftime(DATE_FMT)

    def on_edited_change(self, *args):
        super().on_edited_change(*args)
        self.chooser.editable = self.chooser.editable

    def save(self):
        super().save()
        self.chooser.on_day_set(self.chooser.day)


class DateChooser:

    def __init__(self, master, day=None):
        self.widget = Frame(master)
        if day is None:
            day = date.today()
        self.dec_button = Button(self.widget, text='←',
                                 command=self.on_dec_button)
        self.dec_button.pack(side=tk.LEFT)
        self.entry = DateChooserEntry(self)
        self.entry.widget.pack(side=tk.LEFT)
        self.today_button = Button(self.widget, text='today',
                                   command=self.on_today_button)
        self.today_button.pack(side=tk.LEFT)
        self.inc_button = Button(self.widget, text='→',
                                 command=self.on_inc_button)
        self.inc_button.pack(side=tk.LEFT)
        self.editable = True
        self.day = day

    @property
    def editable(self):
        return self._editable

    @editable.setter
    def editable(self, value):
        value = bool(value)
        self._editable = value
        change_state(self.today_button, disabled=not value)
        for widget in (self.dec_button, self.inc_button):
            change_state(widget,
                         disabled=not(value and self.entry.proposed_valid))
        self.entry.editable = value

    @property
    def day(self):
        return date(*time.strptime(self.entry.external_value, DATE_FMT)[:3])

    @day.setter
    def day(self, value):
        self.entry.external_value = value.strftime(DATE_FMT)
        self.on_day_set(value)

    def on_dec_button(self, *args):
        self.day -= timedelta(days=1)

    def on_inc_button(self, *args):
        self.day += timedelta(days=1)

    def on_today_button(self, *args):
        self.entry.revert()
        self.day = date.today()

    def on_day_set(self, day):
        pass
