from __future__ import annotations

from app.core.db import Database


class ServiceRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def list_all(self) -> list[dict]:
        return self._db.fetch_all(
            """
            SELECT s.id, s.name, s.price, s.type_id, st.name AS type_name
            FROM services s
            LEFT JOIN service_types st ON st.id = s.type_id
            ORDER BY s.id DESC
            """.strip()
        )

    def create(self, name: str, price: float, type_id: int | None) -> int:
        return self._db.execute(
            "INSERT INTO services(name, price, type_id) VALUES(%s,%s,%s)",
            (name, price, type_id),
        )

    def update(self, service_id: int, name: str, price: float, type_id: int | None) -> int:
        self._db.execute(
            "UPDATE services SET name=%s, price=%s, type_id=%s WHERE id=%s",
            (name, price, type_id, service_id),
        )
        return service_id

    def delete(self, service_id: int) -> None:
        self._db.execute("DELETE FROM services WHERE id=%s", (service_id,))

