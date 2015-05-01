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
from collections import namedtuple


def create_tables(conn):
    with conn:
        conn.execute("""
          create table timespan (
            edit_time integer primary key not null,
            edit_loc int not null,
            timespan_id int not null,
            started int
          )
        """)
        conn.execute("""
          create table timespan_tag (
            edit_time integer primary key not null,
            edit_loc int not null,
            timespan_id int not null,
            name text not null,
            active int not null
          )
        """)


class Database:

    def __init__(self, conn, location_id):
        self.conn = conn
        self.location_id = location_id

    def add_timespan(self):
        return self.set_timespan('new', 'now')

    def get_timespan_history(self, timespan_id, time_from=0, time_to=(2**31)-1):
        for row in self.conn.execute("""
          select {}
            from timespan
            where timespan_id = ?
              and edit_time >= ?
              and edit_time < ?
            order by edit_time
        """.format(TimespanEdit.COLUMNS), [timespan_id,
                                           time_from << 32, time_to << 32]):
            yield TimespanEdit.from_row(row)

    def get_timespan(self, timespan_id):
        cursor = self.conn.execute("""
          select {}
            from timespan
            where timespan_id = ?
            order by edit_time desc limit 1
        """.format(TimespanEdit.COLUMNS), [timespan_id])
        row = cursor.fetchone()
        return TimespanEdit.from_row(row) if row is not None else None

    def get_last_timespan(self):
        cursor = self.conn.execute("""
          select {}
            from timespan as t1
            where not exists(select 1
                from timespan as t2
                where t1.timespan_id = t2.timespan_id
                  and t2.edit_time > t1.edit_time)
            order by started desc, edit_time desc
            limit 1
        """.format(TimespanEdit.COLUMNS))
        row = cursor.fetchone()
        return TimespanEdit.from_row(row) if row is not None else None

    def delete_timespan(self, timespan_id):
        return self.set_timespan(timespan_id, None)

    def get_next_timestamp(self, table, when):
        start = TimeStamp(when, self.location_id, 0)
        start_int = start.as_int
        last_int = self.conn.execute("""
          select max(edit_time)
            from {}
            where edit_time >= ?
              and edit_time < ? + 0xffff
        """.format(table), [start_int, start_int]).fetchone()[0]
        if last_int is None:
            return start
        else:
            return TimeStamp.from_int(last_int).next

    def set_timespan(self, timespan_id, started):
        now = int(time.time())
        if started == 'now':
            started = now
        edited = self.get_next_timestamp('timespan', now)
        if timespan_id == 'new':
            timespan_id = edited.as_int
        edit = TimespanEdit(
            edited=edited,
            timespan_id=timespan_id,
            started=started)
        with self.conn:
            self.conn.execute("""
              insert into timespan
                ({})
                values (?, ?, ?, ?)
            """.format(TimespanEdit.COLUMNS), edit.as_row)
        return edit

    def get_timespans(self, time_from, time_to):
        for row in self.conn.execute("""
          select {}
            from timespan as t1
            where started between ? and ?
              and not exists(select 1
                from timespan as t2
                where t1.timespan_id = t2.timespan_id
                  and t2.edit_time > t1.edit_time)
            order by started, edit_time
        """.format(TimespanEdit.COLUMNS), [time_from, time_to]):
            yield TimespanEdit.from_row(row)

    def add_tag(self, timespan_id, name):
        return self.set_tag(timespan_id, name, 1)

    def remove_tag(self, timespan_id, name):
        return self.set_tag(timespan_id, name, 0)

    def set_tag(self, timespan_id, name, active):
        edited = self.get_next_timestamp('timespan_tag', int(time.time()))
        edit = TagEdit(edited=edited,
                       timespan_id=timespan_id,
                       name=name,
                       active=active)
        with self.conn:
            self.conn.execute("""
              insert into timespan_tag
                ({})
                values (?, ?, ?, ?, ?)
            """.format(TagEdit.COLUMNS), edit.as_row)
        return edit

    def get_tags(self, timespan_id):
        cursor = self.conn.execute("""
          select name
            from timespan_tag as t1
            where timespan_id = ?
              and active
              and not exists(select 1
                from timespan_tag as t2
                where t2.timespan_id = t1.timespan_id
                  and t2.name = t1.name
                  and t2.edit_time > t1.edit_time)
        """, [timespan_id])
        return set(row[0] for row in cursor)


class TimeStamp(namedtuple('TimeStamp', ['time', 'loc', 'ctr'])):

    @property
    def as_int(self):
        return self.time << 32 | (self.loc & 0xffff) << 16 | self.ctr

    @classmethod
    def from_int(cls, i):
        loc = (i >> 16) & 0xffff
        if loc > 0x8000:
            loc -= 0x10000
        return cls((i >> 32) & 0xffffffff, loc, i & 0xffff)

    @property
    def next(self):
        if self.ctr == 0xffff:
            return self._replace(time=self.time + 1, ctr=0)
        return self._replace(ctr=self.ctr + 1)


class TimespanEdit(namedtuple('TimespanEdit', ['edited', 'timespan_id',
                                               'started'])):
    COLUMNS = 'edit_time, edit_loc, timespan_id, started'

    @classmethod
    def from_row(cls, row):
        return cls(TimeStamp.from_int(row[0]), *row[2:])

    @property
    def as_row(self):
        return (self.edited.as_int, self.edited.loc,
                self.timespan_id, self.started)


class TagEdit(namedtuple('TagEdit', ['edited','timespan_id','name','active'])):

    COLUMNS = 'edit_time, edit_loc, timespan_id, name, active'

    @classmethod
    def from_row(cls, row):
        return cls(TimeStamp.from_int(row[0]), *row[2:])

    @property
    def as_row(self):
        return (self.edited.as_int, self.edited.loc,
                self.timespan_id, self.name, self.active)
