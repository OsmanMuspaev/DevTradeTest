import os

from psycopg_pool import ConnectionPool


DB_URL = os.getenv("DB_URL", "")
if not DB_URL:
    raise RuntimeError("DB_URL is required (set DB_URL env var)")


pool = ConnectionPool(
    conninfo=DB_URL,
    min_size=int(os.getenv("DB_POOL_MIN", "1")),
    max_size=int(os.getenv("DB_POOL_MAX", "6")),
    open=False,
)


def open_pool() -> None:
    pool.open()


def close_pool() -> None:
    pool.close()

