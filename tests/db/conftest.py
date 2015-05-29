import pytest


@pytest.fixture
def db():
    from alho.db import Database, create_tables
    import sqlite3
    conn = sqlite3.connect(':memory:')
    create_tables(conn)
    return Database(conn, 12345)
