from __future__ import annotations

from app.core.db import Database


class ServiceRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def list_all(self) -> list[dict]:
        return self._db.fetch_all(
            """
            SELECT s.id, s.name, s.price, s.image_path, s.type_id, st.name AS type_name
            FROM services s
            LEFT JOIN service_types st ON st.id = s.type_id
            ORDER BY s.id DESC
            """.strip()
        )

    def create(self, name: str, price: float, type_id: int | None, image_path: str | None = None) -> int:
        return self._db.execute(
            "INSERT INTO services(name, price, type_id, image_path) VALUES(%s,%s,%s,%s)",
            (name, price, type_id, image_path),
        )

    def update(self, service_id: int, name: str, price: float, type_id: int | None, image_path: str | None = None) -> int:
        self._db.execute(
            "UPDATE services SET name=%s, price=%s, type_id=%s, image_path=%s WHERE id=%s",
            (name, price, type_id, image_path, service_id),
        )
        return service_id

    def delete(self, service_id: int) -> None:
        self._db.execute("DELETE FROM services WHERE id=%s", (service_id,))

