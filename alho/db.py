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
import random
from collections import namedtuple


def create_tables(conn):
    with conn:
        conn.execute("""
          create table timespan (
            log_id integer primary key not null,
            log_time int not null,
            location_id int not null,
            timespan_id int not null,
            started int
          );
        """)


class Database:

    def __init__(self, conn, location_id):
        self.conn = conn
        self.location_id = location_id

    def rand_id32(self):
        return random.getrandbits(31)  # TODO: full 32-bit signed?

    def rand_id64(self):
        return random.getrandbits(63)  # TODO: full 64-bit signed?

    def add_timespan(self):
        now = int(time.time())
        edit = TimespanEdit(
            log_id=self.rand_id64(),
            log_time=now,
            location_id=self.location_id,
            timespan_id=self.rand_id32(),
            started=now)
        with self.conn:
            self.conn.execute("""
              insert into timespan
                (log_id, log_time, location_id, timespan_id, started)
                values (?, ?, ?, ?, ?)
            """, edit)
        return edit

    def get_timespan_history(self, timespan_id, time_from=0, time_to=2**32):
        for row in self.conn.execute("""
          select log_id, log_time, location_id, timespan_id, started
            from timespan
            where timespan_id = ?
              and log_time between ? and ?
            order by log_time
        """, [timespan_id, time_from, time_to]):
            yield TimespanEdit(*row)

    def get_timespan(self, timespan_id):
        cursor = self.conn.execute("""
          select log_id, log_time, location_id, timespan_id, started
            from timespan
            where timespan_id = ?
            order by log_time desc limit 1
        """, [timespan_id])
        row = cursor.fetchone()
        return TimespanEdit(*row) if row is not None else None

    def delete_timespan(self, timespan_id):
        edit = TimespanEdit(
            log_id=self.rand_id64(),
            log_time=int(time.time()),
            location_id=self.location_id,
            timespan_id=timespan_id,
            started=None)
        with self.conn:
            self.conn.execute("""
              insert into timespan
                (log_id, log_time, location_id, timespan_id, started)
                values (?, ?, ?, ?, ?)
            """, edit)
        return edit

    def set_timespan(self, timespan_id, started):
        edit = TimespanEdit(
            log_id=self.rand_id64(),
            log_time=int(time.time()),
            location_id=self.location_id,
            timespan_id=timespan_id,
            started=started)
        with self.conn:
            self.conn.execute("""
              insert into timespan
                (log_id, log_time, location_id, timespan_id, started)
                values (?, ?, ?, ?, ?)
            """, edit)
        return edit


class TimespanEdit(namedtuple('TimespanEdit', ['log_id', 'log_time',
                                               'location_id', 'timespan_id',
                                               'started'])):
    pass
