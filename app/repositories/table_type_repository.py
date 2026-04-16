from __future__ import annotations

from app.core.db import Database


class TableTypeRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def list_all(self) -> list[dict]:
        return self._db.fetch_all("SELECT id, name, price_per_hour FROM table_types ORDER BY id DESC")

    def create(self, name: str, price_per_hour: float) -> int:
        return self._db.execute(
            "INSERT INTO table_types(name, price_per_hour) VALUES(%s,%s)",
            (name, price_per_hour),
        )

    def update(self, type_id: int, name: str, price_per_hour: float) -> int:
        self._db.execute(
            "UPDATE table_types SET name=%s, price_per_hour=%s WHERE id=%s",
            (name, price_per_hour, type_id),
        )
        return type_id

    def delete(self, type_id: int) -> None:
        self._db.execute("DELETE FROM table_types WHERE id=%s", (type_id,))

