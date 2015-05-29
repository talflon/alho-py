import hypothesis.strategies as hs
from hypothesis import given


def create_db():
    import sqlite3
    from alho.db import Database, create_tables
    conn = sqlite3.connect(':memory:')
    create_tables(conn)
    return Database(conn)


def ints_in_range(low, high):
    especially = {low, high} | {i for i in (0, -1, 1, low + 1, high - 1)
                                if low <= i <= high}
    return hs.one_of(*(hs.just(i) for i in especially)) | hs.integers(low, high)


def ints_bits_signed(nbits):
    return ints_in_range(-2**(nbits-1), 2**(nbits-1)-1)


def ints_bits_unsigned(nbits):
    return ints_in_range(0, 2**nbits-1)


def test_db_location_starts_null():
    assert create_db().location_id is None


@given(ints_bits_signed(32))
def test_db_set_location(location_id):
    db = create_db()
    db.location_id = location_id
    assert db.location_id == location_id


@given(ints_bits_signed(32))
def test_db_location_saved(location_id):
    from alho.db import Database
    db = create_db()
    db.location_id = location_id
    db2 = Database(db.conn)
    assert db2.location_id == location_id
