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
            edit_time int not null,
            edit_loc int not null,
            edit_ctr int not null,
            timespan_id int not null,
            started int,
            primary key (edit_time, edit_loc, edit_ctr)
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
        return self.set_timespan(self.rand_id64(), 'now')

    def get_timespan_history(self, timespan_id, time_from=0, time_to=2**32):
        for row in self.conn.execute("""
          select {}
            from timespan
            where timespan_id = ?
              and edit_time between ? and ?
            order by edit_time, edit_loc, edit_ctr
        """.format(TimespanEdit.COLUMNS), [timespan_id, time_from, time_to]):
            yield TimespanEdit.from_row(row)

    def get_timespan(self, timespan_id):
        cursor = self.conn.execute("""
          select {}
            from timespan
            where timespan_id = ?
            order by edit_time desc, edit_loc desc, edit_ctr desc limit 1
        """.format(TimespanEdit.COLUMNS), [timespan_id])
        row = cursor.fetchone()
        return TimespanEdit.from_row(row) if row is not None else None

    def delete_timespan(self, timespan_id):
        return self.set_timespan(timespan_id, None)

    def get_next_timespan_timestamp(self, when):
        counter = self.conn.execute("""
          select coalesce(max(edit_ctr) + 1, 0)
            from timespan
            where edit_loc = ?
              and edit_time = ?
        """, [self.location_id, when]).fetchone()[0]
        return TimeStamp(when, self.location_id, counter)

    def set_timespan(self, timespan_id, started):
        now = int(time.time())
        if started == 'now':
            started = now
        edit = TimespanEdit(
            edited=self.get_next_timespan_timestamp(now),
            timespan_id=timespan_id,
            started=started)
        with self.conn:
            self.conn.execute("""
              insert into timespan
                ({})
                values (?, ?, ?, ?, ?)
            """.format(TimespanEdit.COLUMNS), edit.to_row())
        return edit

    def get_timespans(self, time_from, time_to):
        for row in self.conn.execute("""
          select {}
            from timespan as t1
            where started between ? and ?
              and not exists(select 1
                from timespan as t2
                where t1.timespan_id = t2.timespan_id
                  and (t2.edit_time > t1.edit_time
                       or (t2.edit_time = t1.edit_time
                           and (t2.edit_loc > t1.edit_loc
                                or (t2.edit_loc = t1.edit_loc
                                    and t2.edit_ctr > t2.edit_ctr)))))
            order by started, edit_time, edit_loc, edit_ctr
        """.format(TimespanEdit.COLUMNS), [time_from, time_to]):
            yield TimespanEdit.from_row(row)


TimeStamp = namedtuple('TimeStamp', ['time', 'loc', 'ctr'])
TimeStamp.COLUMNS = ','.join(TimeStamp._fields)


class TimespanEdit(namedtuple('TimespanEdit', ['edited', 'timespan_id',
                                               'started'])):
    COLUMNS = ','.join(['edit_' + c for c in TimeStamp.COLUMNS.split(',')] +
                       ['timespan_id', 'started'])

    @classmethod
    def from_row(cls, row):
        return cls(TimeStamp(*row[:3]), *row[3:])

    def to_row(self):
        return tuple(list(self.edited) + list(self)[1:])
