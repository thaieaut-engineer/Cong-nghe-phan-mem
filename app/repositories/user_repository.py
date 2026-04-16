from __future__ import annotations

from app.core.db import Database


class UserRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def find_by_username(self, username: str) -> dict | None:
        return self._db.fetch_one(
            "SELECT id, username, password, role_id FROM users WHERE username=%s",
            (username,),
        )

    def create_user(self, username: str, hashed_password: str, role_id: int) -> int:
        return self._db.execute(
            "INSERT INTO users(username, password, role_id) VALUES(%s, %s, %s)",
            (username, hashed_password, role_id),
        )

    def list_roles(self) -> list[dict]:
        return self._db.fetch_all("SELECT id, name FROM roles ORDER BY id ASC")

