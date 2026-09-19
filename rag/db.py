import os

from pgvector.psycopg import register_vector
from psycopg import Connection
from psycopg_pool import ConnectionPool

DATABASE_URL = os.environ["DATABASE_URL"]


def _configure(conn: Connection) -> None:
    register_vector(conn)


pool = ConnectionPool(DATABASE_URL, open=False, configure=_configure)


def open_pool() -> None:
    pool.open(wait=True)


def close_pool() -> None:
    pool.close()
