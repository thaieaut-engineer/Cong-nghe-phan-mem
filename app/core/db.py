from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

import mysql.connector
from mysql.connector.pooling import MySQLConnectionPool

from app.core.config import DbConfig, get_db_config


class Database:
    def __init__(self, config: DbConfig | None = None, pool_name: str = "billiards_pool") -> None:
        cfg = config or get_db_config()
        self._pool = MySQLConnectionPool(
            pool_name=pool_name,
            pool_size=8,
            host=cfg.host,
            port=cfg.port,
            user=cfg.user,
            password=cfg.password,
            database=cfg.database,
            autocommit=False,
        )

    @contextmanager
    def connection(self) -> Iterator[mysql.connector.MySQLConnection]:
        conn = self._pool.get_connection()
        try:
            yield conn
        finally:
            conn.close()

    def fetch_all(self, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self.connection() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute(query, params)
            rows = cur.fetchall()
            cur.close()
            conn.commit()
            return list(rows)

    def fetch_one(self, query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        with self.connection() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute(query, params)
            row = cur.fetchone()
            cur.close()
            conn.commit()
            return dict(row) if row else None

    def execute(self, query: str, params: tuple[Any, ...] = ()) -> int:
        with self.connection() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            last_id = cur.lastrowid or 0
            cur.close()
            conn.commit()
            return int(last_id)

