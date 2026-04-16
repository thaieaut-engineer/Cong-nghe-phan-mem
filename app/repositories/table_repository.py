from __future__ import annotations

from app.core.db import Database


class TableRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def list_all(self) -> list[dict]:
        return self._db.fetch_all(
            """
            SELECT t.id, t.name, t.status, t.type_id, tt.name AS type_name, tt.price_per_hour
            FROM tables t
            LEFT JOIN table_types tt ON tt.id = t.type_id
            ORDER BY t.id DESC
            """.strip()
        )

    def create(self, name: str, type_id: int | None, status: str) -> int:
        return self._db.execute(
            "INSERT INTO tables(name, type_id, status) VALUES(%s,%s,%s)",
            (name, type_id, status),
        )

    def update(self, table_id: int, name: str, type_id: int | None, status: str) -> int:
        self._db.execute(
            "UPDATE tables SET name=%s, type_id=%s, status=%s WHERE id=%s",
            (name, type_id, status, table_id),
        )
        return table_id

    def delete(self, table_id: int) -> None:
        self._db.execute("DELETE FROM tables WHERE id=%s", (table_id,))

