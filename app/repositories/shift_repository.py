from __future__ import annotations

from app.core.db import Database


class ShiftRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def list_all(self) -> list[dict]:
        return self._db.fetch_all(
            "SELECT id, name, start_time, end_time FROM shifts ORDER BY id DESC"
        )

    def create(self, name: str, start_time: str, end_time: str) -> int:
        return self._db.execute(
            "INSERT INTO shifts(name, start_time, end_time) VALUES(%s,%s,%s)",
            (name, start_time, end_time),
        )

    def update(self, shift_id: int, name: str, start_time: str, end_time: str) -> int:
        self._db.execute(
            "UPDATE shifts SET name=%s, start_time=%s, end_time=%s WHERE id=%s",
            (name, start_time, end_time, shift_id),
        )
        return shift_id

    def delete(self, shift_id: int) -> None:
        self._db.execute("DELETE FROM shifts WHERE id=%s", (shift_id,))

