from __future__ import annotations

from app.core.db import Database


class ServiceTypeRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def list_all(self) -> list[dict]:
        return self._db.fetch_all("SELECT id, name, image_path FROM service_types ORDER BY id DESC")

    def create(self, name: str, image_path: str | None = None) -> int:
        return self._db.execute("INSERT INTO service_types(name, image_path) VALUES(%s,%s)", (name, image_path))

    def update(self, type_id: int, name: str, image_path: str | None = None) -> int:
        self._db.execute("UPDATE service_types SET name=%s, image_path=%s WHERE id=%s", (name, image_path, type_id))
        return type_id

    def delete(self, type_id: int) -> None:
        self._db.execute("DELETE FROM service_types WHERE id=%s", (type_id,))

