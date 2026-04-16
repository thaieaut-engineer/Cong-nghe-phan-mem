from __future__ import annotations

from app.core.db import Database


class UserRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def find_by_username(self, username: str) -> dict | None:
        return self._db.fetch_one(
            """
            SELECT u.id, u.username, u.password, u.role_id, r.name AS role_name
            FROM users u
            LEFT JOIN roles r ON r.id = u.role_id
            WHERE u.username=%s
            """.strip(),
            (username,),
        )

    def create_user(self, username: str, hashed_password: str, role_id: int) -> int:
        return self._db.execute(
            "INSERT INTO users(username, password, role_id) VALUES(%s, %s, %s)",
            (username, hashed_password, role_id),
        )

    def list_roles(self) -> list[dict]:
        return self._db.fetch_all("SELECT id, name FROM roles ORDER BY id ASC")

    def get_role_by_id(self, role_id: int) -> dict | None:
        return self._db.fetch_one("SELECT id, name FROM roles WHERE id=%s", (role_id,))

    def list_users_with_roles(self) -> list[dict]:
        return self._db.fetch_all(
            """
            SELECT u.id, u.username, u.role_id, r.name AS role_name
            FROM users u
            LEFT JOIN roles r ON r.id = u.role_id
            ORDER BY u.id DESC
            """.strip()
        )

    def update_user_role(self, user_id: int, role_id: int | None) -> None:
        self._db.execute("UPDATE users SET role_id=%s WHERE id=%s", (role_id, user_id))

    def delete_user(self, user_id: int) -> None:
        self._db.execute("DELETE FROM users WHERE id=%s", (user_id,))

