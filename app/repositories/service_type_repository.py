from __future__ import annotations

from app.core.db import Database


class ServiceTypeRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def list_all(self) -> list[dict]:
        return self._db.fetch_all("SELECT id, name FROM service_types ORDER BY id DESC")

    def create(self, name: str) -> int:
        return self._db.execute("INSERT INTO service_types(name) VALUES(%s)", (name,))

    def update(self, type_id: int, name: str) -> int:
        self._db.execute("UPDATE service_types SET name=%s WHERE id=%s", (name, type_id))
        return type_id

    def delete(self, type_id: int) -> None:
        self._db.execute("DELETE FROM service_types WHERE id=%s", (type_id,))

