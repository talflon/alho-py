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


import argparse
import os.path
import sqlite3
import random
import tkinter as tk

from ..db import Database, create_tables
from . import SpanListWidget
from .util import SavableEntry


parser = argparse.ArgumentParser(description='Track your time with Alho.')
parser.add_argument('-f', '--file', default='~/.alho.db',
                    help="SQLite DB file to use. Created if doesn't exist.")
parser.add_argument('-i', '--interactive', action='store_true',
                    help='Run interactive Python interpreter after startup.')
args = parser.parse_args()

filename = os.path.normpath(os.path.expanduser(args.file))
already_existed = os.path.exists(filename)
conn = sqlite3.connect(filename)
if not already_existed:
    create_tables(conn)

win = tk.Tk()
SavableEntry.set_theme_defaults(win)
db = Database(conn, random.getrandbits(31))
span_list = SpanListWidget(win, db)
span_list.widget.pack()
if args.interactive:
    import code
    code.interact(local=vars())
else:
    win.mainloop()
