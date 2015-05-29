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
          create table local_data (
            loc_id int not null
          )
        """)
        conn.execute("""
          create table span (
            edit_time integer primary key not null,
            edit_loc int not null,
            span_id int not null,
            started int
          )
        """)
        conn.execute("""
          create table span_tag (
            edit_time integer primary key not null,
            edit_loc int not null,
            span_id int not null,
            name text not null,
            active int not null
          )
        """)
        conn.execute("""
          create view current_span as
            select *
            from span as cur_span
            where not exists(select 1
              from span as newer_span
              where newer_span.span_id = cur_span.span_id
                and newer_span.edit_time > cur_span.edit_time)
        """)
        conn.execute("""
          create view current_span_tag as
            select *
            from span_tag as cur_span_tag
            where not exists(select 1
              from span_tag as newer_span_tag
              where newer_span_tag.span_id = cur_span_tag.span_id
                and newer_span_tag.name = cur_span_tag.name
                and newer_span_tag.edit_time > cur_span_tag.edit_time)
        """)


class Database:

    def __init__(self, conn, location_id=None):
        self.conn = conn
        if location_id is not None:
            self.location_id = location_id

    @property
    def location_id(self):
        row = self.conn.execute('select loc_id from local_data').fetchone()
        return row[0] if row else None

    @location_id.setter
    def location_id(self, value):
        with self.conn:
            if self.location_id is None:
                self.conn.execute('insert into local_data (loc_id) values (?)',
                                  [value])
            else:
                self.conn.execute('update local_data set loc_id = ?', [value])

    def add_span(self):
        return self.set_span('new', 'now')

    def get_span_history(self, span_id, time_from=0, time_to=(2**31) - 1):
        for row in self.conn.execute("""
          select {}
            from span
            where span_id = ?
              and edit_time >= ?
              and edit_time < ?
            order by edit_time
        """.format(SpanEdit.COLUMNS), [span_id,
                                       time_from << 32, time_to << 32]):
            yield SpanEdit.from_row(row)

    def get_span(self, span_id):
        cursor = self.conn.execute("""
          select {}
            from span
            where span_id = ?
            order by edit_time desc limit 1
        """.format(SpanEdit.COLUMNS), [span_id])
        row = cursor.fetchone()
        return SpanEdit.from_row(row) if row is not None else None

    def get_last_span(self):
        cursor = self.conn.execute("""
          select {}
            from current_span
            order by started desc, edit_time desc
            limit 1
        """.format(SpanEdit.COLUMNS))
        row = cursor.fetchone()
        return SpanEdit.from_row(row) if row is not None else None

    def delete_span(self, span_id):
        return self.set_span(span_id, None)

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

    def set_span(self, span_id, started):
        now = int(time.time())
        if started == 'now':
            started = now
        edited = self.get_next_timestamp('span', now)
        if span_id == 'new':
            span_id = edited.as_int
        edit = SpanEdit(
            edited=edited,
            span_id=span_id,
            started=started)
        with self.conn:
            self.conn.execute("""
              insert into span
                ({})
                values (?, ?, ?, ?)
            """.format(SpanEdit.COLUMNS), edit.as_row)
        return edit

    def get_spans(self, time_from=-2**31, time_to=2**31-1):
        for row in self.conn.execute("""
          select {}
            from current_span
            where started between ? and ?
            order by started, edit_time
        """.format(SpanEdit.COLUMNS), [time_from, time_to]):
            yield SpanEdit.from_row(row)

    def get_next_span(self, span_id):
        span = self.get_span(span_id)
        cursor = self.conn.execute("""
          select {}
            from current_span
            where (started > ?
                or (started = ? and edit_time > ?))
            order by started, edit_time
            limit 1
        """.format(SpanEdit.COLUMNS), [span.started, span.started,
                                       span.edited.as_int])
        row = cursor.fetchone()
        return SpanEdit.from_row(row) if row is not None else None

    def add_tag(self, span_id, name):
        return self.set_tag(span_id, name, 1)

    def remove_tag(self, span_id, name):
        return self.set_tag(span_id, name, 0)

    def set_tag(self, span_id, name, active):
        edited = self.get_next_timestamp('span_tag', int(time.time()))
        edit = TagEdit(edited=edited,
                       span_id=span_id,
                       name=name,
                       active=active)
        with self.conn:
            self.conn.execute("""
              insert into span_tag
                ({})
                values (?, ?, ?, ?, ?)
            """.format(TagEdit.COLUMNS), edit.as_row)
        return edit

    def get_tags(self, span_id):
        cursor = self.conn.execute("""
          select name
            from current_span_tag
            where span_id = ?
              and active
        """, [span_id])
        return set(row[0] for row in cursor)

    def get_tag_history(self, span_id, time_from=-2**31, time_to=2**31-1):
        for row in self.conn.execute("""
          select {}
            from span_tag
            where span_id = ?
              and edit_time >= ?
              and edit_time < ?
            order by edit_time
        """.format(TagEdit.COLUMNS), [span_id,
                                      time_from << 32, time_to << 32]):
            yield TagEdit.from_row(row)


class TimeStamp(namedtuple('TimeStamp', ['time', 'loc', 'ctr'])):

    @property
    def as_int(self):
        return self.time << 32 | (self.loc & 0xffff) << 16 | self.ctr

    @classmethod
    def from_int(cls, i):
        loc = (i >> 16) & 0xffff
        if loc >= 0x8000:
            loc -= 0x10000
        t = (i >> 32) & 0xffffffff
        if t >= 0x80000000:
            t -= 0x100000000
        return cls(t, loc, i & 0xffff)

    @property
    def next(self):
        if self.ctr == 0xffff:
            return self._replace(time=self.time + 1, ctr=0)
        return self._replace(ctr=self.ctr + 1)


class SpanEdit(namedtuple('SpanEdit', ['edited', 'span_id', 'started'])):
    COLUMNS = 'edit_time, edit_loc, span_id, started'

    @classmethod
    def from_row(cls, row):
        return cls(TimeStamp.from_int(row[0]), *row[2:])

    @property
    def as_row(self):
        return (self.edited.as_int, self.edited.loc,
                self.span_id, self.started)


class TagEdit(namedtuple('TagEdit', ['edited', 'span_id', 'name', 'active'])):

    COLUMNS = 'edit_time, edit_loc, span_id, name, active'

    @classmethod
    def from_row(cls, row):
        return cls(TimeStamp.from_int(row[0]), *row[2:])

    @property
    def as_row(self):
        return (self.edited.as_int, self.edited.loc,
                self.span_id, self.name, self.active)
