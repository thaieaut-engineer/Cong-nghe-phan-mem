from __future__ import annotations

from app.core.db import Database


class RoleRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def list_all(self) -> list[dict]:
        return self._db.fetch_all("SELECT id, name FROM roles ORDER BY id DESC")

    def create(self, name: str) -> int:
        return self._db.execute("INSERT INTO roles(name) VALUES(%s)", (name,))

    def update(self, role_id: int, name: str) -> int:
        self._db.execute("UPDATE roles SET name=%s WHERE id=%s", (name, role_id))
        return role_id

    def delete(self, role_id: int) -> None:
        self._db.execute("DELETE FROM roles WHERE id=%s", (role_id,))

