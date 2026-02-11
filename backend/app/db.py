"""Database connection pool using psycopg2."""

import os
from typing import Any
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

_pool: pool.SimpleConnectionPool | None = None

DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://job_matcher:JobMatcher2024!@127.0.0.1:5432/job_matcher'
)


def get_pool() -> pool.SimpleConnectionPool:
    global _pool
    if _pool is None:
        _pool = pool.SimpleConnectionPool(
            minconn=2,
            maxconn=10,
            dsn=DATABASE_URL,
        )
    return _pool


def close_pool():
    global _pool
    if _pool:
        _pool.closeall()
        _pool = None


def get_conn():
    """Get a connection from the pool."""
    return get_pool().getconn()


def put_conn(conn: Any):
    """Return a connection to the pool."""
    get_pool().putconn(conn)


class DBConnection:
    """Context manager for db connections with auto-return to pool."""

    conn: Any
    cursor: Any

    def __enter__(self):
        self.conn = get_conn()
        self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        return self.conn, self.cursor

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.cursor.close()
        put_conn(self.conn)
        return False


def db():
    """Shorthand: `with db() as (conn, cur):`"""
    return DBConnection()
